"""
HTML to Markdown Converter

智能的网页内容提取和转换模块，能够将HTML网页转换为格式化的Markdown文档。

主要特性：
- 代码预处理：快速去除JavaScript、CSS、注释等冗余内容
- LLM智能提取：使用Gemini模型智能识别正文、标题、相关图片
- 广告过滤：自动过滤广告和无关内容
- URL处理：自动转换相对路径为绝对路径
- Markdown生成：生成格式化的标准Markdown文档

使用示例：
    >>> from reinvent_insight.html_to_markdown import HTMLToMarkdownConverter
    >>> 
    >>> converter = HTMLToMarkdownConverter()
    >>> 
    >>> # 从文件转换
    >>> markdown = await converter.convert_from_file(
    ...     "article.html",
    ...     output_path="article.md",
    ...     base_url="https://example.com"
    ... )
    >>> 
    >>> # 从URL转换
    >>> markdown = await converter.convert_from_url(
    ...     "https://example.com/article",
    ...     output_path="article.md"
    ... )
    >>> 
    >>> # 从字符串转换
    >>> html = "<html>...</html>"
    >>> markdown = await converter.convert_from_string(
    ...     html,
    ...     base_url="https://example.com"
    ... )
"""

from .converter import HTMLToMarkdownConverter
from .models import ExtractedContent, ImageInfo, ConversionResult
from .exceptions import (
    HTMLToMarkdownError,
    HTMLParseError,
    ContentExtractionError,
    LLMProcessingError,
    URLProcessingError,
    MarkdownGenerationError,
)

__all__ = [
    "HTMLToMarkdownConverter",
    "ExtractedContent",
    "ImageInfo",
    "ConversionResult",
    "HTMLToMarkdownError",
    "HTMLParseError",
    "ContentExtractionError",
    "LLMProcessingError",
    "URLProcessingError",
    "MarkdownGenerationError",
]

__version__ = "0.1.0"
