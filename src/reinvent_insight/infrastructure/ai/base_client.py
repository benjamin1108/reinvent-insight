"""模型客户端基类"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional

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
        
        # 可观测层支持
        self._observability_enabled = False
        try:
            from .observability import get_manager
            self._obs_manager = get_manager()
            self._observability_enabled = self._obs_manager.is_enabled()
        except Exception as e:
            logger.debug(f"可观测层初始化失败（将禁用）: {e}")
        
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
    
    def _start_observability_recording(
        self,
        method_name: str
    ) -> Optional[Any]:
        """
        开始可观测层记录（钩子）
        
        Args:
            method_name: 调用的方法名
            
        Returns:
            记录器实例，如果未启用则返回None
        """
        if not self._observability_enabled:
            return None
        
        try:
            from .observability import InteractionRecorder
            recorder = InteractionRecorder()
            recorder.start_recording(
                provider=self.config.provider,
                model_name=self.config.model_name,
                method_name=method_name
            )
            return recorder
        except Exception as e:
            logger.warning(f"可观测层记录启动失败: {e}")
            return None
    
    def _record_request(
        self,
        recorder: Optional[Any],
        prompt: str,
        params: Dict[str, Any]
    ) -> None:
        """
        记录请求信息（钩子）
        
        Args:
            recorder: 记录器实例
            prompt: 提示词
            params: 请求参数
        """
        if recorder is None:
            return
        
        try:
            recorder.record_request(prompt, params)
        except Exception as e:
            logger.warning(f"可观测层请求记录失败: {e}")
    
    def _record_response(
        self,
        recorder: Optional[Any],
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录响应信息（钩子）
        
        Args:
            recorder: 记录器实例
            content: 响应内容
            metadata: 额外元数据
        """
        if recorder is None:
            return
        
        try:
            recorder.record_response(content, metadata or {})
        except Exception as e:
            logger.warning(f"可观测层响应记录失败: {e}")
    
    def _record_error(
        self,
        recorder: Optional[Any],
        exception: Exception
    ) -> None:
        """
        记录错误信息（钩子）
        
        Args:
            recorder: 记录器实例
            exception: 异常对象
        """
        if recorder is None:
            return
        
        try:
            recorder.record_error(exception)
        except Exception as e:
            logger.warning(f"可观测层错误记录失败: {e}")
    
    def _finalize_observability(
        self,
        recorder: Optional[Any]
    ) -> None:
        """
        完成可观测层记录并写入（钩子）
        
        Args:
            recorder: 记录器实例
        """
        if recorder is None or not self._observability_enabled:
            return
        
        try:
            record = recorder.finalize(
                max_prompt_length=self._obs_manager.max_prompt_length,
                max_response_length=self._obs_manager.max_response_length,
                mask_sensitive=self._obs_manager.mask_sensitive
            )
            self._obs_manager.log_interaction(record)
        except Exception as e:
            logger.warning(f"可观测层记录完成失败: {e}")
