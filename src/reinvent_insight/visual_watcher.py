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

from loguru import logger

from . import config
from .task_manager import manager as task_manager

logger = logger.bind(name=__name__)


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
    
    async def start_watching(self):
        """开始监测文件变化"""
        logger.info(f"开始监测目录: {self.watch_dir}")
        
        while True:
            try:
                await self._check_new_files()
                await asyncio.sleep(30)  # 每30秒检查一次
            except Exception as e:
                logger.error(f"文件监测出错: {e}", exc_info=True)
                await asyncio.sleep(60)  # 出错后等待更长时间
    
    async def _check_new_files(self):
        """检查新文件或版本更新，带频率控制"""
        if not self.watch_dir.exists():
            logger.warning(f"监测目录不存在: {self.watch_dir}")
            return
        
        checked_count = 0
        triggered_count = 0
        max_concurrent_tasks = 2  # 最多同时处理 2 个任务，避免 API 超限
        
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
                    logger.info("等待 5 秒后继续检查下一个文件...")
                    await asyncio.sleep(5)
        
        if checked_count > 0:
            logger.debug(f"检查了 {checked_count} 个文件，触发了 {triggered_count} 个生成任务")
    
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
        # 1. 检查是否已处理过
        if file_key in self.processed_files:
            return False
        
        # 2. 检查是否有正在运行的可视化任务（避免重复生成）
        base_name = md_file.stem
        # 移除版本号后缀以获取基础名称
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            base_name = version_match.group(1)
        
        # 检查是否有相关的可视化任务正在运行
        # 遍历所有任务，查找与当前文件相关的可视化任务
        for task_id, task_state in task_manager.tasks.items():
            # 检查任务 ID 是否包含 _visual 标识
            if '_visual' not in task_id:
                continue
            
            # 检查任务状态是否为运行中或待处理
            if task_state.status not in ['pending', 'running']:
                continue
            
            # 检查任务 ID 是否与当前文件相关
            # workflow 触发的任务格式：{task_id}_visual
            # watcher 触发的任务格式：visual_{filename}_{timestamp}
            normalized_base = base_name.replace(' ', '_')
            if normalized_base in task_id or base_name in task_id:
                logger.info(
                    f"跳过 {md_file.name}，已有可视化任务正在运行: {task_id} (状态: {task_state.status})"
                )
                return False
        
        # 3. 检查对应的可视化 HTML 是否存在
        visual_html = self._get_visual_html_path(md_file)
        if not visual_html.exists():
            logger.info(f"发现新文件需要生成可视化: {md_file.name}")
            return True
        
        # 4. 检查版本是否匹配
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
            # 生成任务ID
            task_id = f"visual_{md_file.stem}_{int(time.time())}"
            
            # 提取版本号
            version = self._extract_version(md_file.stem)
            
            logger.info(f"触发可视化生成任务: {task_id} for {md_file.name} (版本: {version})")
            
            # 创建工作器
            from .visual_worker import VisualInterpretationWorker
            worker = VisualInterpretationWorker(
                task_id=task_id,
                article_path=str(md_file),
                model_name=self.model_name,
                version=version
            )
            
            # 创建后台任务
            task_manager.create_task(task_id, worker.run())
            
            logger.success(f"已触发可视化生成任务: {task_id}")
            
        except Exception as e:
            logger.error(f"触发可视化生成失败: {e}", exc_info=True)
