"""
URL处理器

负责处理和转换图片URL，将相对路径转换为绝对路径。
"""

import logging
from urllib.parse import urljoin, urlparse
from typing import Optional

from .exceptions import URLProcessingError

logger = logging.getLogger(__name__)


class URLProcessor:
    """URL处理器
    
    处理图片URL，包括：
    - 将相对路径转换为绝对路径
    - 验证URL有效性
    - 保留data URI
    - 保留查询参数
    
    使用示例:
        >>> processor = URLProcessor(base_url="https://example.com")
        >>> absolute_url = processor.process_image_url("/images/photo.jpg")
        >>> # 返回: "https://example.com/images/photo.jpg"
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """初始化URL处理器
        
        Args:
            base_url: 网页的基础URL
        """
        self.base_url = base_url
        logger.info(f"URLProcessor initialized with base_url={base_url}")
    
    def process_image_url(self, url: str) -> str:
        """处理图片URL
        
        Args:
            url: 原始图片URL（可能是相对路径）
            
        Returns:
            处理后的绝对URL
            
        Raises:
            URLProcessingError: URL处理失败
        """
        if not url or not url.strip():
            logger.warning("Empty URL provided")
            raise URLProcessingError("URL is empty")
        
        url = url.strip()
        
        # 如果是data URI，直接返回
        if self.is_data_uri(url):
            logger.debug(f"URL is data URI, keeping as-is")
            return url
        
        # 如果已经是绝对URL，直接返回
        if self.is_absolute_url(url):
            logger.debug(f"URL is already absolute: {url}")
            return url
        
        # 如果是相对URL，需要base_url来转换
        if not self.base_url:
            logger.warning(f"Relative URL without base_url: {url}")
            # 没有base_url，返回原URL
            return url
        
        # 转换相对URL为绝对URL
        try:
            absolute_url = urljoin(self.base_url, url)
            logger.debug(f"Converted relative URL: {url} -> {absolute_url}")
            return absolute_url
        except Exception as e:
            logger.error(f"Failed to process URL {url}: {e}")
            raise URLProcessingError(f"Failed to process URL: {e}") from e
    
    def is_valid_url(self, url: str) -> bool:
        """检查URL是否有效
        
        Args:
            url: URL字符串
            
        Returns:
            True if valid, False otherwise
        """
        if not url or not url.strip():
            return False
        
        # data URI总是有效的
        if self.is_data_uri(url):
            return True
        
        try:
            result = urlparse(url)
            # 有效的URL应该有scheme（http/https）或者是相对路径
            return bool(result.scheme in ['http', 'https', ''] and result.path)
        except Exception:
            return False
    
    def is_data_uri(self, url: str) -> bool:
        """检查是否为data URI
        
        Args:
            url: URL字符串
            
        Returns:
            True if data URI, False otherwise
        """
        return url.startswith('data:')
    
    def is_absolute_url(self, url: str) -> bool:
        """检查是否为绝对URL
        
        Args:
            url: URL字符串
            
        Returns:
            True if absolute URL, False otherwise
        """
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False
