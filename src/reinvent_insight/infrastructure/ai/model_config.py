"""
统一模型配置系统 - 重构版

该模块提供统一的模型配置管理和客户端接口，支持按任务类型配置不同的模型和参数。

注意：这是重构后的版本，原model_config.py已废弃。
"""

# 导出核心类和函数
from .config_models import (
    ModelConfig,
    ModelConfigError,
    ConfigurationError,
    UnsupportedProviderError,
    APIError,
)

from .rate_limiter import RateLimiter

from .base_client import BaseModelClient

from .config_manager import ModelConfigManager

from .gemini_client import GeminiClient
from .dashscope_client import DashScopeClient

from .client_factory import (
    ModelClientFactory,
    get_model_client,
    get_default_client,
)

__all__ = [
    # 数据模型
    'ModelConfig',
    
    # 异常类
    'ModelConfigError',
    'ConfigurationError',
    'UnsupportedProviderError',
    'APIError',
    
    # 核心类
    'RateLimiter',
    'BaseModelClient',
    'ModelConfigManager',
    'ModelClientFactory',
    
    # 客户端实现
    'GeminiClient',
    'DashScopeClient',
    
    # 便捷函数
    'get_model_client',
    'get_default_client',
]
