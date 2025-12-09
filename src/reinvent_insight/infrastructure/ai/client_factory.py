"""模型客户端工厂和便捷函数"""

import logging
from typing import Dict, Type

from .config_models import UnsupportedProviderError, ModelConfig
from .base_client import BaseModelClient
from .config_manager import ModelConfigManager
from .gemini_client import GeminiClient
from .dashscope_client import DashScopeClient

logger = logging.getLogger(__name__)


class ModelClientFactory:
    """模型客户端工厂"""
    
    _client_registry: Dict[str, Type[BaseModelClient]] = {
        "gemini": GeminiClient,
        "dashscope": DashScopeClient,
    }
    
    @classmethod
    def create_client(cls, config: ModelConfig) -> BaseModelClient:
        """
        根据配置创建模型客户端
        
        Args:
            config: 模型配置
            
        Returns:
            模型客户端实例
            
        Raises:
            UnsupportedProviderError: 不支持的提供商
        """
        provider = config.provider.lower()
        
        if provider not in cls._client_registry:
            raise UnsupportedProviderError(
                f"不支持的模型提供商: {provider}. "
                f"支持的提供商: {', '.join(cls._client_registry.keys())}"
            )
        
        client_class = cls._client_registry[provider]
        
        try:
            return client_class(config)
        except Exception as e:
            logger.error(f"创建模型客户端失败: {e}", exc_info=True)
            raise
    
    @classmethod
    def register_client(
        cls, 
        provider: str, 
        client_class: Type[BaseModelClient]
    ) -> None:
        """
        注册新的模型客户端类型
        
        Args:
            provider: 提供商名称
            client_class: 客户端类
        """
        provider = provider.lower()
        cls._client_registry[provider] = client_class
        logger.info(f"已注册模型客户端: {provider}")


def get_model_client(task_type: str) -> BaseModelClient:
    """
    获取指定任务类型的模型客户端（便捷函数）
    
    Args:
        task_type: 任务类型 (video_summary, pdf_processing, visual_generation, document_analysis)
        
    Returns:
        模型客户端实例
        
    Example:
        >>> client = get_model_client("visual_generation")
        >>> result = await client.generate_content(prompt)
    """
    config_manager = ModelConfigManager.get_instance()
    config = config_manager.get_config(task_type)
    return ModelClientFactory.create_client(config)


def get_default_client() -> BaseModelClient:
    """
    获取默认模型客户端
    
    Returns:
        默认模型客户端实例
    """
    config_manager = ModelConfigManager.get_instance()
    config = config_manager.get_default_config()
    return ModelClientFactory.create_client(config)
