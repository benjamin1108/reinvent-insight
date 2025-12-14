"""分析工作流基类"""

import os
import re
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any, Union, Protocol
from pathlib import Path

from reinvent_insight.core import config
from reinvent_insight.domain.models import DocumentContent
from reinvent_insight.infrastructure.media.youtube_downloader import VideoMetadata
from reinvent_insight.infrastructure.ai.model_config import get_model_client
from reinvent_insight.infrastructure.ai.observability import set_business_context
from reinvent_insight.services.analysis.post_processors import (
    PostProcessorPipeline,
    PostProcessorContext,
    get_default_pipeline,
)

logger = logging.getLogger(__name__)


# 任务通知接口（依赖倒置）
class TaskNotifier(Protocol):
    """任务通知接口，用于向外部报告任务进度"""
    tasks: Dict[str, Any]
    
    async def update_progress(self, task_id: str, progress: int, message: str) -> None: ...
    async def send_message(self, message: str, task_id: str) -> None: ...
    async def send_result(self, title: str, content: str, task_id: str, filename: str, doc_hash: str) -> None: ...
    async def set_task_error(self, task_id: str, error_msg: str) -> None: ...


# 定义任务根目录
TASKS_ROOT_DIR = "./downloads/tasks"
BASE_PROMPT_PATH = "./prompt/youtbe-deep-summary.txt"


def get_task_dir_path(task_id: str, content_type: str = "youtube") -> str:
    """生成任务目录路径
    
    格式: tasks/YYYYMMDD/HHMM-taskid-type
    
    Args:
        task_id: 任务ID
        content_type: 内容类型 (youtube/pdf/md/txt/document)
    
    Returns:
        任务目录路径
    """
    from datetime import datetime
    now = datetime.now()
    date_dir = now.strftime("%Y%m%d")
    time_prefix = now.strftime("%H%M")
    
    # 类型映射
    type_map = {
        "transcript": "youtube",
        "pdf": "pdf",
        "md": "md",
        "txt": "txt",
        "document": "doc",
        "youtube": "youtube",
    }
    task_type = type_map.get(content_type, "unknown")
    
    # 取task_id前8位作为短标识
    short_id = task_id[:8] if len(task_id) >= 8 else task_id
    
    folder_name = f"{time_prefix}-{short_id}-{task_type}"
    return os.path.join(TASKS_ROOT_DIR, date_dir, folder_name)


def load_base_prompt() -> str:
    """加载基础提示词模板"""
    try:
        with open(BASE_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"基础提示词文件未找到: {BASE_PROMPT_PATH}")
        return ""


class AnalysisWorkflow(ABC):
    """分析工作流抽象基类
    
    定义了标准的分析流程：大纲生成 -> 章节生成 -> 结论生成 -> 报告组装
    子类需要实现具体的内容类型处理逻辑
    """
    
    def __init__(
        self, 
        task_id: str, 
        model_name: str, 
        content: Union[str, DocumentContent], 
        video_metadata: VideoMetadata,
        task_notifier: TaskNotifier,
        is_ultra_mode: bool = False,
        target_version: Optional[int] = None,
        doc_hash: Optional[str] = None
    ):
        """
        初始化工作流
        
        Args:
            task_id: 任务ID
            model_name: 模型名称
            content: 内容（字符串或DocumentContent）
            video_metadata: 视频元数据
            task_notifier: 任务通知器（用于进度报告）
            is_ultra_mode: 是否为Ultra模式
            target_version: 目标版本号（仅Ultra模式）
            doc_hash: 文档哈希（仅Ultra模式）
        """
        self.task_id = task_id
        self.model_name = model_name
        self.content = content
        self.metadata = video_metadata
        self.task_notifier = task_notifier
        
        # Ultra模式参数
        self.is_ultra_mode = is_ultra_mode
        self.target_version = target_version
        self.doc_hash = doc_hash
        
        # 内容类型判断
        if isinstance(content, str):
            self.content_type = "transcript"
            self.transcript = content
            self.is_pdf = False
        elif isinstance(content, DocumentContent):
            self.content_type = content.content_type
            self.transcript = content.text_content or ""
            self.is_pdf = content.is_multimodal
        else:
            raise ValueError(f"不支持的内容类型: {type(content)}")
        
        # 任务目录（使用日期+类型结构）
        self.task_dir = get_task_dir_path(self.task_id, self.content_type)
        os.makedirs(self.task_dir, exist_ok=True)
        
        # 模型客户端
        self.client = self._get_model_client()
        
        # 基础提示词
        self.base_prompt = load_base_prompt()
        
        # 配置
        self.max_retries = 2
        self.generated_title_en = None  # 存储AI生成的英文标题
        self.chapter_metadata: Dict[int, Dict] = {}  # 存储章节元数据
        
        # 后处理管道（默认使用全局管道，可通过子类覆盖）
        self.post_processor_pipeline: Optional[PostProcessorPipeline] = None
    
    def _get_model_client(self):
        """获取模型客户端（子类可覆盖）"""
        if isinstance(self.content, DocumentContent):
            if self.content.is_multimodal:
                return get_model_client("pdf_processing")
            else:
                return get_model_client("document_analysis")
        else:
            return get_model_client("video_summary")
    
    async def run(self):
        """执行完整的分析工作流（模板方法）"""
        # 设置业务上下文
        task_type = "ultra_deep" if self.is_ultra_mode else "video_summary"
        
        with set_business_context(
            task_id=self.task_id,
            task_type=task_type,
            content_type=self.content_type,
            is_pdf=self.is_pdf
        ):
            try:
                # 记录工作流启动上下文
                mode_desc = "Ultra深度模式" if self.is_ultra_mode else "标准模式"
                logger.info(
                    f"[工作流启动] task_id={self.task_id}, "
                    f"模式={mode_desc}, "
                    f"内容类型={self.content_type}, "
                    f"任务目录={self.task_dir}"
                )
                
                await self._log("正在启动深度分析流程...")
                self.task_notifier.tasks[self.task_id].status = "running"

                # 步骤 1: 生成大纲
                outline_content = await self._generate_outline()
                if not outline_content:
                    raise Exception("生成大纲失败")

                title, chapters_raw, introduction = await self._parse_outline_result(outline_content)
                if not title or not chapters_raw:
                    raise Exception("解析大纲失败")
                
                # 清理章节标题
                chapters = [re.sub(r'[\[\]]', '', c).strip() for c in chapters_raw]
                
                # Ultra模式章节数量验证
                await self._validate_chapter_count(chapters, outline_content)
                
                await self._log(f"成功生成标题和 {len(chapters)} 个章节的分析框架")
                
                # 生成带链接的目录
                from reinvent_insight.core.utils import generate_toc_with_links
                toc_md = generate_toc_with_links(chapters)

                # 步骤 2: 并发生成章节
                success = await self._generate_chapters_parallel(chapters, title, outline_content)
                if not success:
                    raise Exception("部分或全部章节内容生成失败")
                
                # 步骤 3: 生成结论
                conclusion_content = await self._generate_conclusion(chapters)
                if not conclusion_content:
                    raise Exception("生成收尾内容失败")
                
                # 步骤 4: 组装最终报告
                final_report, final_filename, doc_hash = await self._assemble_final_report(
                    title, introduction, toc_md, conclusion_content, len(chapters), self.metadata
                )
                if not final_report:
                    raise Exception("组装最终报告失败")
                
                # 步骤 5: 后处理管道（精加工）
                final_report = await self._run_post_processors(
                    final_report, title, doc_hash, len(chapters), outline_content, final_filename
                )

                logger.info(f"[工作流完成] task_id={self.task_id}, 标题={title[:30]}..., 章节数={len(chapters)}, doc_hash={doc_hash}")
                await self._log("分析完成！", progress=100)
                await self.task_notifier.send_result(title, final_report, self.task_id, final_filename, doc_hash)

            except Exception as e:
                error_message = f"工作流遇到严重错误: {e}"
                logger.error(f"任务 {self.task_id} - {error_message}", exc_info=True)
                await self.task_notifier.set_task_error(self.task_id, "分析过程中出现错误，请稍后重试")
    
    # ======= 抽象方法（子类必须实现） =======
    
    @abstractmethod
    async def _generate_outline(self) -> str:
        """生成大纲（需子类实现）"""
        pass
    
    @abstractmethod
    async def _generate_single_chapter(
        self, 
        index: int, 
        chapter_title: str, 
        outline_content: str, 
        previous_chapters: List[Dict] = None,
        rationale: str = ""
    ) -> str:
        """生成单个章节（需子类实现）"""
        pass
    
    @abstractmethod
    async def _generate_conclusion(self, chapters: List[str]) -> str:
        """生成结论（需子类实现）"""
        pass
    
    @abstractmethod
    async def _assemble_final_report(
        self, 
        title: str, 
        introduction: str, 
        toc_md: str, 
        conclusion_content: str, 
        chapter_count: int, 
        metadata: VideoMetadata
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """组装最终报告（需子类实现）"""
        pass
    
    # ======= 通用辅助方法 =======
    
    async def _log(self, message: str, progress: int = None):
        """记录日志到任务管理器"""
        if progress is not None:
            await self.task_notifier.update_progress(self.task_id, progress, message)
        else:
            await self.task_notifier.send_message(message, self.task_id)
    
    async def _parse_outline_result(self, outline_content: str):
        """解析大纲结果"""
        from reinvent_insight.core.utils import parse_outline, extract_titles_from_outline
        
        title, chapters_raw, introduction = parse_outline(outline_content)
        
        # 提取章节元数据（JSON部分）
        self._extract_chapter_metadata(outline_content)
        
        # 对于PDF文档，尝试提取AI生成的英文标题
        if self.is_pdf:
            try:
                title_en, title_cn = extract_titles_from_outline(outline_content)
                if title_en:
                    self.generated_title_en = title_en
                    logger.info(f"从大纲中提取到AI生成的英文标题: {self.generated_title_en}")
            except Exception as e:
                logger.warning(f"无法从大纲中提取英文标题: {e}")
        
        return title, chapters_raw, introduction
    
    def _extract_chapter_metadata(self, outline_content: str):
        """从大纲内容中提取章节元数据（JSON部分）"""
        try:
            # 尝试提取 JSON 块
            json_match = re.search(r'```json\s*([\s\S]*?)```', outline_content)
            if not json_match:
                # 尝试直接匹配 JSON 对象
                json_match = re.search(r'\{[\s\S]*"chapters"[\s\S]*\}', outline_content)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.warning("未能从大纲中提取JSON元数据")
                    return
            else:
                json_str = json_match.group(1)
            
            # 清理JSON字符串
            json_str = json_str.strip()
            
            # 解析JSON
            outline_json = json.loads(json_str)
            
            # 提取章节元数据
            chapters = outline_json.get('chapters', [])
            for chapter in chapters:
                index = chapter.get('index', 0)
                if index > 0:
                    self.chapter_metadata[index] = {
                        'title': chapter.get('title', ''),
                        'source_content_amount': chapter.get('source_content_amount', 'moderate'),
                        'information_density': chapter.get('information_density', 'medium'),
                        'generation_depth': chapter.get('generation_depth', 'detailed'),
                        'subsections': chapter.get('subsections', []),
                        'opening_hook': chapter.get('opening_hook', ''),
                        'closing_transition': chapter.get('closing_transition', ''),
                        'must_include': chapter.get('must_include', []),
                        'must_exclude': chapter.get('must_exclude', []),
                        'prev_chapter_link': chapter.get('prev_chapter_link', ''),
                        'next_chapter_link': chapter.get('next_chapter_link', ''),
                        'rationale': chapter.get('rationale', '')
                    }
            
            logger.info(f"成功提取 {len(self.chapter_metadata)} 个章节的元数据")
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析大纲JSON失败: {e}")
        except Exception as e:
            logger.warning(f"提取章节元数据时出错: {e}")
    
    def _get_chapter_metadata(self, chapter_index: int) -> Dict:
        """获取指定章节的元数据
        
        Args:
            chapter_index: 章节索引（1-based）
            
        Returns:
            章节元数据字典
        """
        return self.chapter_metadata.get(chapter_index, {})
    
    async def _validate_chapter_count(self, chapters: List[str], outline_content: str):
        """验证章节数量（Ultra模式）"""
        if self.is_ultra_mode and len(chapters) > 20:
            logger.warning(f"任务 {self.task_id} - Ultra模式章节数超出限制（{len(chapters)}章），重新生成大纲")
            await self._log(f"章节数过多（{len(chapters)}章），正在重新分析内容结构...")
            
            # 重新生成大纲
            outline_content = await self._generate_outline()
            if not outline_content:
                raise Exception("重新生成大纲失败")
            
            from reinvent_insight.core.utils import parse_outline
            title, chapters_raw, introduction = parse_outline(outline_content)
            if not title or not chapters_raw:
                raise Exception("解析大纲失败")
            
            chapters = [re.sub(r'[\[\]]', '', c).strip() for c in chapters_raw]
            
            # 如果还是超过20章，报错
            if len(chapters) > 20:
                raise Exception(f"Ultra模式章节数仍超过20（{len(chapters)}章），请检查内容结构")
    
    async def _generate_chapters_parallel(
        self, 
        chapters: List[str], 
        title: str, 
        outline_content: str
    ) -> bool:
        """并发生成所有章节"""
        await self._log(f"步骤 2/4: 正在并发生成 {len(chapters)} 个核心章节...")

        # 从配置中读取并发延迟
        concurrent_delay = getattr(self.client.config, 'concurrent_delay', 1.0)
        logger.info(f"使用章节并发生成间隔: {concurrent_delay} 秒")

        # 创建所有章节的生成任务
        tasks = []
        for i, chapter_title in enumerate(chapters):
            delay = i * concurrent_delay
            task = self._generate_single_chapter_with_delay(
                i, chapter_title, outline_content, delay
            )
            tasks.append(task)
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计成功率
        successful_chapters = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"任务 {self.task_id} - 生成章节 '{chapters[i]}' 失败: {result}")
            elif result:
                successful_chapters += 1
                logger.info(f"任务 {self.task_id} - 章节 '{chapters[i]}' 已成功生成。")
        
        await self._log(f"章节分析完成（{successful_chapters}/{len(chapters)}）", progress=75)
        
        return successful_chapters == len(chapters)
    
    async def _generate_single_chapter_with_delay(
        self, 
        index: int, 
        chapter_title: str, 
        outline_content: str, 
        delay: float
    ) -> bool:
        """带延迟的章节生成"""
        if delay > 0:
            await asyncio.sleep(delay)
        
        try:
            # 获取章节元数据
            chapter_meta = self._get_chapter_metadata(index + 1)  # index is 0-based, metadata is 1-based
            rationale = self._build_chapter_rationale(index + 1, chapter_meta)
            
            chapter_content = await self._generate_single_chapter(
                index, chapter_title, outline_content, previous_chapters=None, rationale=rationale
            )
            
            # 更新进度
            progress = 25 + int(50 * ((index + 1) / (index + 10)))
            await self._log(f"章节 {index + 1} 生成完成", progress=progress)
            
            return bool(chapter_content)
        
        except Exception as e:
            logger.error(f"任务 {self.task_id} - 生成章节 '{chapter_title}' 失败: {e}", exc_info=e)
            return False
    
    def _build_chapter_rationale(self, chapter_index: int, chapter_meta: Dict) -> str:
        """构建章节生成的详细指导信息
        
        Args:
            chapter_index: 章节索引（1-based）
            chapter_meta: 章节元数据
            
        Returns:
            格式化的章节指导信息
        """
        if not chapter_meta:
            return ""
        
        parts = []
        
        # 基础 rationale
        if chapter_meta.get('rationale'):
            parts.append(f"**内容范围指导**：{chapter_meta['rationale']}")
        
        # 子章节结构
        subsections = chapter_meta.get('subsections', [])
        if subsections:
            parts.append("\n**子章节结构**（按顺序展开）：")
            for i, sub in enumerate(subsections, 1):
                subtitle = sub.get('subtitle', f'子章节{i}')
                key_points = sub.get('key_points', [])
                if key_points:
                    points_str = '、'.join(key_points)
                    parts.append(f"  {i}. {subtitle}：覆盖 {points_str}")
                else:
                    parts.append(f"  {i}. {subtitle}")
        
        # 开篇指导
        if chapter_meta.get('opening_hook'):
            parts.append(f"\n**开篇方式**：{chapter_meta['opening_hook']}")
        
        # 结尾过渡
        if chapter_meta.get('closing_transition'):
            parts.append(f"\n**结尾过渡**：{chapter_meta['closing_transition']}")
        
        # 必须包含
        must_include = chapter_meta.get('must_include', [])
        if must_include:
            parts.append(f"\n**必须包含**：{'、'.join(must_include)}")
        
        # 必须排除
        must_exclude = chapter_meta.get('must_exclude', [])
        if must_exclude:
            parts.append(f"\n**禁止涉及**（已在其他章节覆盖）：{'、'.join(must_exclude)}")
        
        # 章节连接
        if chapter_meta.get('prev_chapter_link'):
            parts.append(f"\n**与上一章的关系**：{chapter_meta['prev_chapter_link']}")
        if chapter_meta.get('next_chapter_link'):
            parts.append(f"\n**与下一章的关系**：{chapter_meta['next_chapter_link']}")
        
        return '\n'.join(parts)
    
    async def _run_post_processors(
        self,
        report_content: str,
        title: str,
        doc_hash: str,
        chapter_count: int,
        outline_content: str,
        final_filename: str = None
    ) -> str:
        """执行后处理管道
        
        Args:
            report_content: 报告内容
            title: 标题
            doc_hash: 文档哈希
            chapter_count: 章节数量
            outline_content: 大纲内容
            final_filename: 最终文件名
            
        Returns:
            处理后的报告内容
        """
        # 获取管道（优先用实例级，其次用全局）
        pipeline = self.post_processor_pipeline or get_default_pipeline()
        
        # 检查是否有处理器
        if not pipeline.processors:
            logger.debug("没有注册后处理器，跳过后处理")
            return report_content
        
        await self._log("步骤 5/5: 正在进行精加工...", progress=95)
        
        # 构建上下文
        context = PostProcessorContext(
            task_id=self.task_id,
            report_content=report_content,
            title=title,
            doc_hash=doc_hash,
            chapter_count=chapter_count,
            is_ultra_mode=self.is_ultra_mode,
            is_pdf=self.is_pdf,
            content_type=self.content_type,
            task_dir=self.task_dir,
            source_content=self.transcript,
            outline_content=outline_content,
            video_url=self.metadata.video_url if hasattr(self.metadata, 'video_url') else "",
            upload_date=self.metadata.upload_date if hasattr(self.metadata, 'upload_date') else "",
            extra={'article_path': str(config.OUTPUT_DIR / final_filename) if final_filename else None}
        )
        
        try:
            result = await pipeline.run(context)
            if result.success:
                if result.changes:
                    logger.info(f"任务 {self.task_id} - 后处理完成: {result.message}")
                return result.content
            else:
                logger.warning(f"任务 {self.task_id} - 后处理失败: {result.message}")
                return report_content  # 失败时返回原内容
        except Exception as e:
            logger.error(f"任务 {self.task_id} - 后处理异常: {e}", exc_info=True)
            return report_content  # 异常时返回原内容
