"""模型客户端基类"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable

from .config_models import ModelConfig, APIError
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class BaseModelClient(ABC):
    """模型客户端抽象基类"""
    
    def __init__(self, config: ModelConfig):
        """
        初始化模型客户端
        
        Args:
            config: 模型配置
        """
        self.config = config
        self._rate_limiter = RateLimiter(config.rate_limit_interval)
        
    @abstractmethod
    async def generate_content(
        self, 
        prompt: str, 
        is_json: bool = False
    ) -> str:
        """
        生成文本内容
        
        Args:
            prompt: 提示词
            is_json: 是否返回JSON格式
            
        Returns:
            生成的文本内容
            
        Raises:
            APIError: API调用失败
        """
        pass
        
    @abstractmethod
    async def generate_content_with_file(
        self,
        prompt: str,
        file_info: Dict[str, Any],
        is_json: bool = False
    ) -> str:
        """
        使用文件生成内容（多模态）
        
        Args:
            prompt: 提示词
            file_info: 文件信息字典
            is_json: 是否返回JSON格式
            
        Returns:
            生成的文本内容
            
        Raises:
            APIError: API调用失败
        """
        pass
        
    async def _apply_rate_limit(self) -> None:
        """应用速率限制"""
        await self._rate_limiter.acquire(self.config.provider)
        
    async def _retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        带指数退避的重试机制
        
        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            APIError: 达到最大重试次数后仍失败
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_base ** attempt
                    logger.warning(
                        f"API调用失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}"
                    )
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"API调用失败，已达最大重试次数 ({self.config.max_retries})"
                    )
        
        raise APIError(f"API调用失败: {last_exception}") from last_exception
