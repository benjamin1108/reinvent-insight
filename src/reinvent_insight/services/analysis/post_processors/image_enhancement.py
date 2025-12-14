"""图片增强后处理器

为文章添加AI生成的配图或相关图表。
"""

import re
import logging
from typing import List, Optional

from .base import PostProcessor, PostProcessorContext, PostProcessorResult, ProcessorPriority

logger = logging.getLogger(__name__)


class ImageEnhancementProcessor(PostProcessor):
    """图片增强后处理器
    
    功能：
    1. 在关键章节插入配图占位符（供后续AI生图）
    2. 为技术概念添加图表说明
    3. 在章节开头添加主题配图
    
    使用示例：
        from reinvent_insight.services.analysis.post_processors import register_processor
        from reinvent_insight.services.analysis.post_processors.image_enhancement import ImageEnhancementProcessor
        
        register_processor(ImageEnhancementProcessor())
    """
    
    name = "image_enhancement"
    description = "为文章添加配图增强"
    priority = ProcessorPriority.NORMAL
    
    def __init__(
        self,
        enabled_for_ultra_only: bool = True,
        min_chapter_count: int = 10,
        max_images: int = 5
    ):
        """初始化图片增强器
        
        Args:
            enabled_for_ultra_only: 是否仅在Ultra模式启用
            min_chapter_count: 最少章节数才启用
            max_images: 最多添加几张图
        """
        self.enabled_for_ultra_only = enabled_for_ultra_only
        self.min_chapter_count = min_chapter_count
        self.max_images = max_images
    
    async def should_run(self, context: PostProcessorContext) -> bool:
        """判断是否应该运行"""
        # Ultra模式检查
        if self.enabled_for_ultra_only and not context.is_ultra_mode:
            return False
        
        # 章节数检查
        if context.chapter_count < self.min_chapter_count:
            return False
        
        return True
    
    async def process(self, context: PostProcessorContext) -> PostProcessorResult:
        """执行图片增强"""
        content = context.report_content
        changes: List[str] = []
        
        try:
            # 1. 找到关键章节（每隔N章添加一张图）
            chapter_pattern = r'(### \d+\. [^\n]+)'
            chapters = list(re.finditer(chapter_pattern, content))
            
            if not chapters:
                return PostProcessorResult.skip(content, "未找到章节标题")
            
            # 计算插入间隔
            interval = max(1, len(chapters) // self.max_images)
            insert_positions = []
            
            for i, match in enumerate(chapters):
                if i > 0 and i % interval == 0 and len(insert_positions) < self.max_images:
                    insert_positions.append(match)
            
            # 2. 在选定位置插入图片占位符
            # 从后往前插入，避免位置偏移
            for match in reversed(insert_positions):
                chapter_title = match.group(1)
                # 提取章节编号和标题
                title_match = re.match(r'### (\d+)\. (.+)', chapter_title)
                if title_match:
                    chapter_num = title_match.group(1)
                    title_text = title_match.group(2)
                    
                    # 生成图片占位符（后续可替换为真实图片）
                    image_placeholder = self._generate_image_placeholder(
                        chapter_num, title_text, context
                    )
                    
                    # 在章节标题后插入
                    insert_pos = match.end()
                    content = content[:insert_pos] + image_placeholder + content[insert_pos:]
                    changes.append(f"章节 {chapter_num} 添加配图占位")
            
            if changes:
                return PostProcessorResult.ok(
                    content, 
                    f"添加了 {len(changes)} 个图片占位符",
                    changes
                )
            else:
                return PostProcessorResult.skip(content, "无需添加配图")
                
        except Exception as e:
            logger.error(f"图片增强处理失败: {e}", exc_info=True)
            return PostProcessorResult.error(context.report_content, str(e))
    
    def _generate_image_placeholder(
        self, 
        chapter_num: str, 
        title_text: str,
        context: PostProcessorContext
    ) -> str:
        """生成图片占位符
        
        Args:
            chapter_num: 章节编号
            title_text: 章节标题
            context: 上下文
            
        Returns:
            图片占位符Markdown
        """
        # 生成图片描述提示（供后续AI生图使用）
        image_prompt = f"技术文章配图：{title_text}"
        
        # 返回占位符格式（可后续替换为真实图片URL）
        placeholder = f"""

<!-- IMAGE_PLACEHOLDER
chapter: {chapter_num}
title: {title_text}
prompt: {image_prompt}
-->

"""
        return placeholder


class DiagramGeneratorProcessor(PostProcessor):
    """图表生成后处理器
    
    识别技术概念并生成Mermaid图表。
    """
    
    name = "diagram_generator"
    description = "为技术概念生成流程图/架构图"
    priority = ProcessorPriority.NORMAL
    
    async def should_run(self, context: PostProcessorContext) -> bool:
        # 仅Ultra模式
        return context.is_ultra_mode
    
    async def process(self, context: PostProcessorContext) -> PostProcessorResult:
        """分析内容并生成图表"""
        content = context.report_content
        changes: List[str] = []
        
        # TODO: 实现以下功能
        # 1. 识别架构描述段落
        # 2. 提取关键组件和关系
        # 3. 生成Mermaid图表
        # 4. 插入到相关章节
        
        # 当前返回跳过（待实现）
        return PostProcessorResult.skip(content, "图表生成器待实现")
