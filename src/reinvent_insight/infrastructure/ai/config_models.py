"""AI模型配置数据模型和异常类"""

from dataclasses import dataclass


@dataclass
class ModelConfig:
    """模型配置数据类"""
    task_type: str                    # 任务类型标识
    provider: str                     # 模型提供商 (gemini/xai/alibaba)
    model_name: str                   # 具体模型名称
    api_key: str                      # API密钥
    
    # 思考模式配置
    low_thinking: bool = False        # 是否启用低思考模式（默认false，使用高思考）
    
    # 生成参数
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_output_tokens: int = 8000
    
    # 速率限制
    rate_limit_interval: float = 0.5  # API调用间隔（秒）
    max_retries: int = 3              # 最大重试次数
    retry_backoff_base: float = 2.0   # 重试退避基数
    timeout: int = 120                # API超时时间（秒）
    concurrent_delay: float = 0.5     # 并发处理时每个任务的启动间隔（秒）


class ModelConfigError(Exception):
    """模型配置相关错误的基类"""
    pass


class ConfigurationError(ModelConfigError):
    """配置错误"""
    pass


class UnsupportedProviderError(ModelConfigError):
    """不支持的模型提供商"""
    pass


class APIError(ModelConfigError):
    """API调用错误"""
    pass
