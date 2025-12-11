"""分析工作流基类"""

import os
import re
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any, Union, Protocol
from pathlib import Path
from loguru import logger

from reinvent_insight.core import config
from reinvent_insight.domain.models import DocumentContent
from reinvent_insight.infrastructure.media.youtube_downloader import VideoMetadata
from reinvent_insight.infrastructure.ai.model_config import get_model_client


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
        
        # 任务目录
        self.task_dir = os.path.join(TASKS_ROOT_DIR, self.task_id)
        os.makedirs(self.task_dir, exist_ok=True)
        
        # 模型客户端
        self.client = self._get_model_client()
        
        # 基础提示词
        self.base_prompt = load_base_prompt()
        
        # 配置
        self.max_retries = 2
        self.generated_title_en = None  # 存储AI生成的英文标题
    
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
        try:
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
            
            # 步骤 3.5: Ultra 模式后校验（可选）
            if self.is_ultra_mode:
                proofread_success = await self._run_proofreading()
                if proofread_success:
                    # 校对成功后需要重新加载章节和结论
                    chapters, conclusion_content, toc_md = await self._reload_after_proofreading()
            
            # 步骤 4: 组装最终报告
            final_report, final_filename, doc_hash = await self._assemble_final_report(
                title, introduction, toc_md, conclusion_content, len(chapters), self.metadata
            )
            if not final_report:
                raise Exception("组装最终报告失败")

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
            chapter_content = await self._generate_single_chapter(
                index, chapter_title, outline_content, previous_chapters=None, rationale=""
            )
            
            # 更新进度
            progress = 25 + int(50 * ((index + 1) / (index + 10)))
            await self._log(f"章节 {index + 1} 生成完成", progress=progress)
            
            return bool(chapter_content)
        
        except Exception as e:
            logger.error(f"任务 {self.task_id} - 生成章节 '{chapter_title}' 失败: {e}", exc_info=e)
            return False
    
    async def _run_proofreading(self) -> bool:
        """
        执行后校验（Ultra 模式专用）
        
        判断是否需要校对，如需要则执行校对流程。
        
        Returns:
            校对是否成功执行（如果不需要校对则返回 False）
        """
        try:
            from reinvent_insight.services.analysis.proofreader import ArticleProofreader
            
            proofreader = ArticleProofreader(self.task_id, self.task_dir)
            
            if not await proofreader.should_proofread():
                logger.info(f"任务 {self.task_id} - 章节数未达到校对阈值，跳过校对")
                return False
            
            await self._log("正在进行全局校对优化...")
            
            success = await proofreader.run()
            
            if success:
                await self._log("校对完成，文章结构已优化")
            else:
                logger.warning(f"任务 {self.task_id} - 校对未成功，使用原始章节")
            
            return success
            
        except Exception as e:
            logger.error(f"任务 {self.task_id} - 校对过程出错: {e}", exc_info=True)
            return False
    
    async def _reload_after_proofreading(self) -> Tuple[List[str], str, str]:
        """
        校对后重新加载章节和目录
        
        校对可能会改变章节数量和结构，需要重新加载。
        
        Returns:
            (chapters, conclusion_content, toc_md)
        """
        import re
        from pathlib import Path
        from reinvent_insight.core.utils import generate_toc_with_links
        
        task_path = Path(self.task_dir)
        
        # 重新加载章节标题
        chapter_files = sorted(
            task_path.glob("chapter_*.md"),
            key=lambda f: int(re.search(r'chapter_(\d+)', f.name).group(1))
        )
        
        chapters = []
        for chapter_file in chapter_files:
            content = chapter_file.read_text(encoding="utf-8")
            # 提取标题（## 数字. 标题 格式）
            match = re.match(r'## \d+\.\s*(.+)', content)
            if match:
                chapters.append(match.group(1).strip())
            else:
                # 备用：从文件名推断
                chapters.append(f"章节 {chapter_file.stem.replace('chapter_', '')}")
        
        # 重新生成目录
        toc_md = generate_toc_with_links(chapters)
        
        # 重新加载结论
        conclusion_path = task_path / "conclusion.md"
        conclusion_content = ""
        if conclusion_path.exists():
            conclusion_content = conclusion_path.read_text(encoding="utf-8")
        
        logger.info(f"任务 {self.task_id} - 校对后重新加载: {len(chapters)} 个章节")
        
        return chapters, conclusion_content, toc_md
