"""
Markdown生成器

负责将提取的内容生成为格式化的Markdown文档。
"""

import logging
import re
from pathlib import Path
from typing import Optional, List

from .models import ExtractedContent, ImageInfo, ConversionResult
from .exceptions import MarkdownGenerationError

logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Markdown生成器
    
    将提取的内容生成为格式化的Markdown文档。
    
    使用示例:
        >>> generator = MarkdownGenerator()
        >>> result = generator.generate(content, output_path="article.md")
    """
    
    def __init__(self):
        """初始化生成器"""
        logger.info("MarkdownGenerator initialized")
    
    def generate(
        self, 
        content: ExtractedContent,
        output_path: Optional[Path] = None
    ) -> ConversionResult:
        """生成Markdown文档
        
        Args:
            content: 提取的内容
            output_path: 输出文件路径（可选）
            
        Returns:
            ConversionResult对象
            
        Raises:
            MarkdownGenerationError: Markdown生成失败
        """
        logger.info("Starting Markdown generation")
        
        try:
            # 构建Markdown文档
            markdown_parts = []
            
            # 1. 添加标题
            if content.title:
                title_md = self._format_title(content.title)
                markdown_parts.append(title_md)
                markdown_parts.append("")  # 空行
            
            # 2. 添加元数据（如果有）
            if content.metadata:
                metadata_md = self._format_metadata(content.metadata)
                if metadata_md:
                    markdown_parts.append(metadata_md)
                    markdown_parts.append("")  # 空行
            
            # 3. 添加正文内容
            markdown_parts.append(content.content)
            
            # 4. 添加图片（如果有且不在正文中）
            if content.images:
                images_md = self._format_images(content.images, content.content)
                if images_md:
                    markdown_parts.append("")  # 空行
                    markdown_parts.append(images_md)
            
            # 合并所有部分
            markdown = "\n".join(markdown_parts)
            
            # 验证Markdown格式
            if not self._validate_markdown(markdown):
                logger.warning("Generated Markdown may have formatting issues")
            
            # 创建统计信息
            stats = {
                "title_length": len(content.title) if content.title else 0,
                "content_length": len(content.content),
                "image_count": len(content.images),
                "has_metadata": bool(content.metadata),
            }
            
            # 创建结果对象
            result = ConversionResult(
                markdown=markdown,
                content=content,
                stats=stats
            )
            
            # 如果指定了输出路径，保存文件
            if output_path:
                result.save(output_path)
                logger.info(f"Markdown saved to {output_path}")
            
            logger.info(f"Markdown generation completed: {len(markdown)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Markdown generation failed: {e}", exc_info=True)
            raise MarkdownGenerationError(f"Failed to generate Markdown: {e}") from e
    
    def _format_title(self, title: str) -> str:
        """格式化标题
        
        Args:
            title: 标题文本
            
        Returns:
            Markdown格式的标题
        """
        # 使用一级标题
        return f"# {title.strip()}"
    
    def _format_metadata(self, metadata: dict) -> str:
        """格式化元数据
        
        Args:
            metadata: 元数据字典
            
        Returns:
            Markdown格式的元数据
        """
        parts = []
        
        # 作者
        if metadata.get("author"):
            parts.append(f"**作者**: {metadata['author']}")
        
        # 日期
        if metadata.get("date"):
            parts.append(f"**日期**: {metadata['date']}")
        
        # 标签
        if metadata.get("tags") and isinstance(metadata["tags"], list):
            tags_str = ", ".join(metadata["tags"])
            parts.append(f"**标签**: {tags_str}")
        
        if parts:
            return " | ".join(parts)
        
        return ""
    
    def _format_images(self, images: List[ImageInfo], content: str) -> str:
        """格式化图片列表
        
        只添加不在正文中的图片。
        
        Args:
            images: 图片列表
            content: 正文内容
            
        Returns:
            Markdown格式的图片列表
        """
        # 检查哪些图片已经在正文中
        images_to_add = []
        for image in images:
            # 简单检查：如果图片URL不在正文中，则添加
            if image.url not in content:
                images_to_add.append(image)
        
        if not images_to_add:
            return ""
        
        # 格式化图片
        parts = ["## 相关图片"]
        parts.append("")
        
        for image in images_to_add:
            parts.append(image.to_markdown())
            parts.append("")  # 图片之间空行
        
        return "\n".join(parts)
    
    def _validate_markdown(self, markdown: str) -> bool:
        """验证Markdown格式
        
        进行基本的格式检查。
        
        Args:
            markdown: Markdown文本
            
        Returns:
            True if valid, False otherwise
        """
        if not markdown or not markdown.strip():
            logger.error("Markdown is empty")
            return False
        
        # 检查是否有基本的Markdown元素
        has_content = len(markdown.strip()) > 0
        
        # 检查标题格式（可选）
        has_title = bool(re.search(r'^#\s+.+', markdown, re.MULTILINE))
        
        # 检查图片语法是否正确
        image_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
        images = re.findall(image_pattern, markdown)
        
        # 检查链接语法是否正确
        link_pattern = r'(?<!!)\[([^\]]+)\]\(([^\)]+)\)'
        links = re.findall(link_pattern, markdown)
        
        logger.debug(f"Markdown validation: has_content={has_content}, "
                    f"has_title={has_title}, images={len(images)}, links={len(links)}")
        
        return has_content
