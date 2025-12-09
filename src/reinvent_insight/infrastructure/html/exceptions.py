"""
异常类定义

定义了HTML到Markdown转换过程中可能出现的各种异常。
"""


class HTMLToMarkdownError(Exception):
    """HTML到Markdown转换的基础异常类"""
    pass


class HTMLParseError(HTMLToMarkdownError):
    """HTML解析错误
    
    当HTML内容无法被解析时抛出此异常。
    """
    pass


class ContentExtractionError(HTMLToMarkdownError):
    """内容提取错误
    
    当无法从HTML中提取有效内容时抛出此异常。
    """
    pass


class LLMProcessingError(HTMLToMarkdownError):
    """LLM处理错误
    
    当LLM API调用失败或返回无效响应时抛出此异常。
    """
    pass


class URLProcessingError(HTMLToMarkdownError):
    """URL处理错误
    
    当URL处理过程中出现错误时抛出此异常。
    """
    pass


class MarkdownGenerationError(HTMLToMarkdownError):
    """Markdown生成错误
    
    当Markdown生成过程中出现错误时抛出此异常。
    """
    pass
