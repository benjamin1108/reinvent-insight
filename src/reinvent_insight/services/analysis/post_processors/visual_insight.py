"""Visual Insight 后处理器

将深度解读文章转换为可视化 HTML 网页。
"""

import time
import re
from pathlib import Path
from typing import Optional
from loguru import logger

from reinvent_insight.core import config
from .base import PostProcessor, PostProcessorContext, PostProcessorResult, ProcessorPriority


class VisualInsightProcessor(PostProcessor):
    """Visual Insight 生成后处理器
    
    异步处理器：在文章生成完成后，触发 Visual HTML 生成任务。
    不阻塞主流程，Visual 在后台异步完成。
    
    使用示例：
        from reinvent_insight.services.analysis.post_processors import register_processor
        from reinvent_insight.services.analysis.post_processors.visual_insight import VisualInsightProcessor
        
        register_processor(VisualInsightProcessor())
    """
    
    name = "visual_insight"
    description = "生成可视化解读HTML"
    priority = ProcessorPriority.LOWEST  # 最低优先级，最后执行
    is_async = True  # 异步执行，只触发不等待
    
    def __init__(
        self,
        enabled: bool = True,
        min_chapter_count: int = 0,
        model_name: str = None
    ):
        """初始化 Visual Insight 处理器
        
        Args:
            enabled: 是否启用
            min_chapter_count: 最少章节数才触发（0=不限制）
            model_name: AI模型名称（None=使用默认）
        """
        self.enabled = enabled
        self.min_chapter_count = min_chapter_count
        self.model_name = model_name
    
    async def should_run(self, context: PostProcessorContext) -> bool:
        """判断是否应该触发 Visual 生成"""
        if not self.enabled:
            return False
        
        # 检查配置开关
        if not getattr(config, 'VISUAL_AUTO_GENERATE', True):
            logger.debug("Visual 自动生成已禁用（配置）")
            return False
        
        # 章节数检查
        if self.min_chapter_count > 0 and context.chapter_count < self.min_chapter_count:
            logger.debug(f"章节数不足 ({context.chapter_count} < {self.min_chapter_count})，跳过 Visual")
            return False
        
        # 检查是否已存在 Visual HTML
        article_path = self._get_article_path(context)
        if article_path:
            visual_path = self._get_visual_html_path(article_path)
            if visual_path.exists():
                logger.debug(f"Visual HTML 已存在: {visual_path.name}，跳过生成")
                return False
        
        return True
    
    async def process(self, context: PostProcessorContext) -> PostProcessorResult:
        """触发 Visual 生成任务（异步）"""
        try:
            # 获取文章路径
            article_path = self._get_article_path(context)
            if not article_path or not article_path.exists():
                return PostProcessorResult.skip(
                    context.report_content, 
                    f"文章文件不存在"
                )
            
            # 生成任务ID
            task_id = self._generate_task_id(article_path)
            
            # 提取版本号
            version = self._extract_version(article_path.stem)
            
            logger.info(
                f"触发 Visual 生成任务: {task_id}, "
                f"文章: {article_path.name}, 版本: {version}"
            )
            
            # 创建后台任务
            await self._trigger_visual_generation(
                task_id=task_id,
                article_path=str(article_path),
                version=version
            )
            
            return PostProcessorResult.ok(
                context.report_content,  # 不修改内容
                f"已触发 Visual 生成 (task_id: {task_id})"
            )
            
        except Exception as e:
            logger.error(f"触发 Visual 生成失败: {e}", exc_info=True)
            # 异步处理器失败不影响主流程，返回原内容
            return PostProcessorResult.skip(
                context.report_content,
                f"触发失败: {e}"
            )
    
    def _get_article_path(self, context: PostProcessorContext) -> Optional[Path]:
        """获取文章文件路径"""
        # 优先从 extra 中获取（工作流可能已设置）
        if context.get('article_path'):
            return Path(context.get('article_path'))
        
        # 通过 doc_hash 查找
        if context.doc_hash:
            from reinvent_insight.services.document.hash_registry import hash_to_filename
            filename = hash_to_filename.get(context.doc_hash)
            if filename:
                return config.OUTPUT_DIR / filename
        
        return None
    
    def _get_visual_html_path(self, article_path: Path) -> Path:
        """获取对应的 Visual HTML 路径"""
        base_name = article_path.stem
        
        # 检查是否有版本号
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            # 有版本号: xxx_v2.md -> xxx_v2_visual.html
            html_filename = f"{base_name}_visual.html"
        else:
            # 无版本号: xxx.md -> xxx_visual.html
            html_filename = f"{base_name}_visual.html"
        
        return article_path.parent / html_filename
    
    def _generate_task_id(self, article_path: Path) -> str:
        """生成任务ID"""
        base_name = article_path.stem
        
        # 移除版本号后缀
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            base_name = version_match.group(1)
        
        # 标准化文件名
        normalized_name = base_name.replace(' ', '_').replace('–', '-')
        
        return f"visual_{normalized_name}_{int(time.time())}"
    
    def _extract_version(self, filename: str) -> int:
        """从文件名提取版本号"""
        version_match = re.search(r'_v(\d+)', filename)
        return int(version_match.group(1)) if version_match else 0
    
    async def _trigger_visual_generation(
        self, 
        task_id: str, 
        article_path: str, 
        version: int
    ):
        """触发 Visual 生成任务
        
        复用现有的 VisualInterpretationWorker
        """
        from reinvent_insight.services.analysis.visual_worker import VisualInterpretationWorker
        from reinvent_insight.services.analysis.task_manager import manager as task_manager
        
        # 创建工作器
        worker = VisualInterpretationWorker(
            task_id=task_id,
            article_path=article_path,
            model_name=self.model_name,
            version=version
        )
        
        # 创建后台任务（不等待完成）
        task_manager.create_task(task_id, worker.run())
        
        logger.info(f"Visual 生成任务已触发: {task_id}")
