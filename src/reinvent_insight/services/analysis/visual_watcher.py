"""
可视化解读文件监测器

该模块监测深度解读文件的变化，自动触发可视化解读的生成任务。
支持版本管理，确保每个版本的深度解读都有对应的可视化解读。
"""

import os
import re
import json
import time
import asyncio
from pathlib import Path
from typing import Set

from reinvent_insight.core.logger import get_logger

from reinvent_insight.core import config
from .task_manager import manager as task_manager

logger = get_logger(__name__)


class VisualInterpretationWatcher:
    """监测深度解读文件变化，自动生成可视化解读"""
    
    def __init__(self, watch_dir: Path, model_name: str):
        """
        初始化文件监测器
        
        Args:
            watch_dir: 监测的目录路径
            model_name: AI模型名称
        """
        self.watch_dir = Path(watch_dir)
        self.model_name = model_name
        self.processed_files: Set[str] = set()  # 已处理的文件集合
        self.cache_file = self.watch_dir / ".visual_processed.json"
        
        self._load_processed_files()
        self._cleanup_temp_files()
        
        logger.info(f"初始化文件监测器 - 目录: {watch_dir}, 模型: {model_name}")
    
    def _load_processed_files(self):
        """从持久化存储加载已处理文件列表"""
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                self.processed_files = set(data)
                logger.info(f"加载已处理文件列表: {len(self.processed_files)} 个文件")
            except Exception as e:
                logger.warning(f"加载已处理文件列表失败: {e}")
                self.processed_files = set()
        else:
            logger.info("未找到已处理文件缓存，从空列表开始")
    
    def _save_processed_files(self):
        """保存已处理文件列表"""
        try:
            self.cache_file.write_text(
                json.dumps(list(self.processed_files), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.debug(f"已保存处理文件列表: {len(self.processed_files)} 个文件")
        except Exception as e:
            logger.error(f"保存已处理文件列表失败: {e}")
    
    def _cleanup_temp_files(self):
        """清理残留的临时文件（.html.tmp）"""
        if not self.watch_dir.exists():
            return
        
        try:
            temp_files = list(self.watch_dir.glob("*.html.tmp"))
            if temp_files:
                logger.info(f"发现 {len(temp_files)} 个残留的临时文件，开始清理...")
                for temp_file in temp_files:
                    try:
                        temp_file.unlink()
                        logger.info(f"已删除临时文件: {temp_file.name}")
                    except Exception as e:
                        logger.warning(f"删除临时文件失败 {temp_file.name}: {e}")
            else:
                logger.debug("未发现残留的临时文件")
        except Exception as e:
            logger.warning(f"清理临时文件时出错: {e}")
    
    async def start_watching(self):
        """开始监测文件变化"""
        logger.info(f"开始监测目录: {self.watch_dir}")
        
        while True:
            try:
                await self._check_new_files()
                await asyncio.sleep(15)  # 每60秒检查一次（增加间隔）
            except Exception as e:
                logger.error(f"文件监测出错: {e}", exc_info=True)
                await asyncio.sleep(120)  # 出错后等待更长时间
    
    async def _check_new_files(self):
        """检查新文件或版本更新，带频率控制"""
        if not self.watch_dir.exists():
            logger.warning(f"监测目录不存在: {self.watch_dir}")
            return
        
        checked_count = 0
        triggered_count = 0
        max_concurrent_tasks = 1  # 每次只处理 1 个任务，避免 API 超限和重复生成
        
        for md_file in self.watch_dir.glob("*.md"):
            checked_count += 1
            file_key = self._get_file_key(md_file)
            
            # 检查是否需要生成可视化
            if await self._should_generate_visual(md_file, file_key):
                # 检查当前运行的任务数
                running_tasks = task_manager.get_running_tasks_count()
                
                if running_tasks >= max_concurrent_tasks:
                    logger.info(
                        f"当前有 {running_tasks} 个任务运行中，"
                        f"达到并发限制 ({max_concurrent_tasks})，跳过 {md_file.name}"
                    )
                    continue
                
                await self._trigger_visual_generation(md_file)
                self.processed_files.add(file_key)
                self._save_processed_files()
                triggered_count += 1
                
                # 任务间添加延迟，避免短时间内大量请求
                if triggered_count > 0:
                    logger.info("等待 10 秒后继续检查下一个文件...")
                    await asyncio.sleep(10)  # 增加延迟到 10 秒
                    break  # 每次只触发 1 个任务
        
        # 只在有触发任务时才记录日志
        if triggered_count > 0:
            logger.info(f"检查了 {checked_count} 个文件，触发了 {triggered_count} 个生成任务")
    
    def _get_file_key(self, md_file: Path) -> str:
        """
        生成文件的唯一标识（包含修改时间）
        
        Args:
            md_file: Markdown 文件路径
            
        Returns:
            文件唯一标识
        """
        stat = md_file.stat()
        return f"{md_file.name}:{stat.st_mtime}"
    
    async def _should_generate_visual(self, md_file: Path, file_key: str) -> bool:
        """
        判断是否需要生成可视化
        
        Args:
            md_file: Markdown 文件路径
            file_key: 文件唯一标识
            
        Returns:
            是否需要生成
        """
        # 1. 先检查对应的可视化 HTML 是否存在
        visual_html = self._get_visual_html_path(md_file)
        html_exists = visual_html.exists()
        
        # 2. 检查是否有临时文件正在生成（.html.tmp）
        temp_html = visual_html.with_suffix('.html.tmp')
        if temp_html.exists():
            logger.info(
                f"跳过 {md_file.name}，检测到临时文件正在生成: {temp_html.name}"
            )
            return False
        
        # 3. 检查是否有正在运行的可视化任务（避免重复生成）
        base_name = md_file.stem
        # 移除版本号后缀以获取基础名称
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            base_name = version_match.group(1)
        
        # 标准化文件名：空格转为下划线，长破折号转为短破折号
        normalized_base = base_name.replace(' ', '_').replace('–', '-')
        
        # 检查是否有相关的可视化任务正在运行
        for task_id, task_state in task_manager.tasks.items():
            if not task_id.startswith('visual_'):
                continue
            
            if task_state.status not in ['pending', 'running']:
                continue
            
            # 从任务 ID 中提取文件名部分（移除 visual_ 前缀和时间戳后缀）
            # 任务 ID 格式: visual_{文件名}_{时间戳}
            task_file_part = task_id[7:]  # 移除 'visual_' 前缀
            task_file_part = '_'.join(task_file_part.split('_')[:-1])  # 移除时间戳
            
            if task_file_part == normalized_base:
                logger.info(
                    f"跳过 {md_file.name}，已有可视化任务正在运行: {task_id} (状态: {task_state.status})"
                )
                return False
        
        # 4. 检查是否已处理过
        if file_key in self.processed_files:
            # 如果 metadata 中有记录，但 HTML 文件不存在
            if not html_exists:
                # 再次检查是否有正在运行的任务（可能正在生成中）
                for task_id, task_state in task_manager.tasks.items():
                    if not task_id.startswith('visual_'):
                        continue
                    if task_state.status not in ['pending', 'running']:
                        continue
                    
                    task_file_part = task_id[7:]
                    task_file_part = '_'.join(task_file_part.split('_')[:-1])
                    normalized_base_check = base_name.replace(' ', '_').replace('–', '-')
                    
                    if task_file_part == normalized_base_check:
                        # HTML 文件缺失但有任务正在运行，跳过
                        return False
                
                # 确实没有任务在运行，可能是生成失败或文件被删除
                logger.warning(
                    f"检测到 metadata 记录存在但 HTML 文件缺失: {md_file.name}，"
                    f"将从 metadata 中移除并重新生成"
                )
                self.processed_files.discard(file_key)
                self._save_processed_files()
                return True
            
            # 如果 HTML 文件存在但大小为 0，说明生成失败
            if html_exists and visual_html.stat().st_size == 0:
                logger.warning(
                    f"检测到 HTML 文件为空: {md_file.name}，"
                    f"将从 metadata 中移除并重新生成"
                )
                self.processed_files.discard(file_key)
                self._save_processed_files()
                # 删除空文件
                try:
                    visual_html.unlink()
                    logger.info(f"已删除空 HTML 文件: {visual_html.name}")
                except Exception as e:
                    logger.warning(f"删除空文件失败: {e}")
                return True
            
            return False
        
        # 5. 如果 HTML 文件不存在，需要生成
        if not html_exists:
            logger.info(f"发现新文件需要生成可视化: {md_file.name}")
            return True
        
        # 6. 检查版本是否匹配
        md_version = self._extract_version(md_file.stem)
        html_version = self._extract_version(visual_html.stem)
        
        if md_version != html_version:
            logger.info(
                f"版本不匹配，需要重新生成: {md_file.name} "
                f"(深度解读 v{md_version} vs 可视化 v{html_version})"
            )
            return True
        
        return False
    
    def _get_visual_html_path(self, md_file: Path) -> Path:
        """
        获取对应的可视化 HTML 文件路径
        
        Args:
            md_file: Markdown 文件路径
            
        Returns:
            对应的 HTML 文件路径
        """
        base_name = md_file.stem
        
        # 移除版本号后缀
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            base_name = version_match.group(1)
            version = int(version_match.group(2))
            html_filename = f"{base_name}_v{version}_visual.html"
        else:
            html_filename = f"{base_name}_visual.html"
        
        return md_file.parent / html_filename
    
    def _extract_version(self, filename: str) -> int:
        """
        从文件名中提取版本号
        
        Args:
            filename: 文件名（不含扩展名）
            
        Returns:
            版本号（0表示无版本）
        """
        # 匹配 _v2 或 _v2_visual 格式
        version_match = re.search(r'_v(\d+)', filename)
        return int(version_match.group(1)) if version_match else 0
    
    async def _trigger_visual_generation(self, md_file: Path):
        """
        触发可视化生成任务
        
        Args:
            md_file: Markdown 文件路径
        """
        try:
            # 生成任务ID（标准化文件名，避免特殊字符）
            base_name = md_file.stem
            # 移除版本号后缀
            version_match = re.match(r'^(.+)_v(\d+)$', base_name)
            if version_match:
                base_name = version_match.group(1)
            
            # 标准化文件名：空格转为下划线
            normalized_name = base_name.replace(' ', '_').replace('–', '-')
            task_id = f"visual_{normalized_name}_{int(time.time())}"
            
            # 提取版本号
            version = self._extract_version(md_file.stem)
            
            # 尝试查找对应的 task_dir
            task_dir = self._find_task_dir_for_article(md_file)
            
            if not task_dir:
                logger.info(
                    f"{md_file.name}：未找到 task_dir，使用一次性生成模式"
                )
            
            logger.info(f"触发可视化生成任务: {task_id} for {md_file.name} (版本: {version}, 分章节: {bool(task_dir)})")
            
            # 创建工作器
            from .visual_worker import VisualInterpretationWorker
            worker = VisualInterpretationWorker(
                task_id=task_id,
                article_path=str(md_file),
                model_name=self.model_name,
                version=version,
                task_dir=task_dir
            )
            
            # 创建后台任务
            task_manager.create_task(task_id, worker.run())
            
            logger.success(f"已触发可视化生成任务: {task_id}")
            
        except Exception as e:
            logger.error(f"触发可视化生成失败: {e}", exc_info=True)
    
    def _find_task_dir_for_article(self, md_file: Path) -> str:
        """
        尝试根据文章查找对应的 task_dir
        
        查找逻辑：搜索 tasks 目录下最近的包含章节文件的任务目录
        
        Args:
            md_file: Markdown 文件路径
            
        Returns:
            task_dir 路径，未找到返回空字符串
        """
        from reinvent_insight.domain.workflows.base import TASKS_ROOT_DIR
        
        tasks_root = Path(TASKS_ROOT_DIR)
        if not tasks_root.exists():
            return ""
        
        # 从文章中提取 video_id 或其他标识符
        try:
            content = md_file.read_text(encoding="utf-8")
            # 提取 doc_hash 或 task_id的一部分
            import yaml
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1])
                    # 尝试从元数据中获取 task_dir
                    if metadata.get("task_dir"):
                        task_dir_path = Path(metadata["task_dir"])
                        if task_dir_path.exists():
                            return str(task_dir_path)
        except Exception:
            pass
        
        # 回退：搜索最近日期目录下的任务目录
        date_dirs = sorted(tasks_root.iterdir(), reverse=True)
        for date_dir in date_dirs[:3]:  # 只检查最近 3 天
            if not date_dir.is_dir():
                continue
            
            for task_dir in sorted(date_dir.iterdir(), reverse=True):
                if not task_dir.is_dir():
                    continue
                
                # 检查是否有章节文件
                chapter_files = list(task_dir.glob("chapter_*.md"))
                if chapter_files:
                    # 进一步验证：检查 article.md 是否与当前文章匹配
                    article_in_task = task_dir / "article.md"
                    if article_in_task.exists():
                        try:
                            task_content = article_in_task.read_text(encoding="utf-8", errors="ignore")[:2000]
                            md_content = md_file.read_text(encoding="utf-8", errors="ignore")[:2000]
                            # 简单比对前 2000 字符
                            if task_content[:500] == md_content[:500]:
                                return str(task_dir)
                        except Exception:
                            pass
        
        return ""
