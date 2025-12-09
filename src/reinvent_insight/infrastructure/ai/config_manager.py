"""模型配置管理器"""

import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .config_models import ModelConfig

logger = logging.getLogger(__name__)


class ModelConfigManager:
    """模型配置管理器"""
    
    _instance: Optional['ModelConfigManager'] = None
    _configs: Dict[str, ModelConfig] = {}
    _default_config: Optional[ModelConfig] = None
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/model_config.yaml
        """
        if config_path is None:
            from reinvent_insight.core import config as app_config
            config_path = app_config.PROJECT_ROOT / "config" / "model_config.yaml"
        
        self.config_path = Path(config_path)
        self.load_config()
        
    def load_config(self) -> None:
        """从配置文件和环境变量加载配置"""
        try:
            if not self.config_path.exists():
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                self._load_default_config()
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                logger.warning("配置文件为空，使用默认配置")
                self._load_default_config()
                return
            
            # 加载默认配置
            if 'default' in config_data:
                self._default_config = self._parse_config('default', config_data['default'])
            else:
                self._load_default_config()
            
            # 加载任务特定配置
            if 'tasks' in config_data:
                for task_type, task_config in config_data['tasks'].items():
                    self._configs[task_type] = self._parse_config(task_type, task_config)
            
            logger.info(f"成功加载配置文件: {self.config_path}")
            logger.info(f"已加载 {len(self._configs)} 个任务配置")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}", exc_info=True)
            self._load_default_config()
    
    def _parse_config(self, task_type: str, config_dict: Dict[str, Any]) -> ModelConfig:
        """
        解析配置字典为 ModelConfig 对象
        
        Args:
            task_type: 任务类型
            config_dict: 配置字典
            
        Returns:
            ModelConfig 对象
        """
        # 获取 API Key
        api_key_env = config_dict.get('api_key_env', 'GEMINI_API_KEY')
        api_key = os.getenv(api_key_env, '')
        
        # 检查环境变量覆盖
        provider = self._get_env_override(task_type, 'provider', config_dict.get('provider', 'gemini'))
        model_name = self._get_env_override(task_type, 'model_name', config_dict.get('model_name', 'gemini-2.0-flash-exp'))
        
        # 思考模式配置
        thinking = config_dict.get('thinking', {})
        low_thinking = bool(self._get_env_override(task_type, 'low_thinking', thinking.get('low_thinking', False)))
        
        # 生成参数
        generation = config_dict.get('generation', {})
        temperature = float(self._get_env_override(task_type, 'temperature', generation.get('temperature', 0.7)))
        top_p = float(self._get_env_override(task_type, 'top_p', generation.get('top_p', 0.9)))
        top_k = int(self._get_env_override(task_type, 'top_k', generation.get('top_k', 40)))
        max_output_tokens = int(self._get_env_override(task_type, 'max_output_tokens', generation.get('max_output_tokens', 8000)))
        
        # 速率限制参数
        rate_limit = config_dict.get('rate_limit', {})
        rate_limit_interval = float(self._get_env_override(task_type, 'rate_limit_interval', rate_limit.get('interval', 0.5)))
        max_retries = int(self._get_env_override(task_type, 'max_retries', rate_limit.get('max_retries', 3)))
        retry_backoff_base = float(self._get_env_override(task_type, 'retry_backoff_base', rate_limit.get('retry_backoff_base', 2.0)))
        timeout = int(self._get_env_override(task_type, 'timeout', rate_limit.get('timeout', 120)))
        concurrent_delay = float(self._get_env_override(task_type, 'concurrent_delay', rate_limit.get('concurrent_delay', 0.5)))
        
        # 创建 ModelConfig 实例
        mc = ModelConfig(
            task_type=task_type,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            low_thinking=low_thinking,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            rate_limit_interval=rate_limit_interval,
            max_retries=max_retries,
            retry_backoff_base=retry_backoff_base,
            timeout=timeout,
            concurrent_delay=concurrent_delay
        )
        
        # 解析 TTS 专用配置（仅在 text_to_speech 任务类型时）
        if task_type == 'text_to_speech':
            tts_cfg = config_dict.get('tts', {})
            setattr(mc, 'tts_default_voice', tts_cfg.get('default_voice', 'Kai'))
            setattr(mc, 'tts_default_language', tts_cfg.get('default_language', 'Chinese'))
            setattr(mc, 'tts_sample_rate', tts_cfg.get('sample_rate', 24000))
        
        return mc
    
    def _get_env_override(self, task_type: str, param_name: str, default_value: Any) -> Any:
        """
        获取环境变量覆盖值
        
        环境变量命名规范: MODEL_{TASK_TYPE}_{PARAMETER}
        例如: MODEL_PDF_PROCESSING_MODEL_NAME
        
        Args:
            task_type: 任务类型
            param_name: 参数名称
            default_value: 默认值
            
        Returns:
            环境变量值或默认值
        """
        env_key = f"MODEL_{task_type.upper()}_{param_name.upper()}"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            logger.debug(f"使用环境变量覆盖: {env_key}={env_value}")
            return env_value
        
        return default_value
    
    def _load_default_config(self) -> None:
        """加载硬编码的默认配置"""
        from reinvent_insight.core import config as app_config
        
        self._default_config = ModelConfig(
            task_type='default',
            provider='gemini',
            model_name='gemini-2.0-flash-exp',
            api_key=app_config.GEMINI_API_KEY or '',
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            max_output_tokens=8000,
            rate_limit_interval=0.5,
            max_retries=3,
            retry_backoff_base=2.0
        )
        
        logger.info("使用硬编码的默认配置")
    
    def get_config(self, task_type: str) -> ModelConfig:
        """
        获取指定任务类型的配置
        
        Args:
            task_type: 任务类型
            
        Returns:
            ModelConfig 对象
        """
        if task_type in self._configs:
            return self._configs[task_type]
        
        logger.warning(f"未找到任务类型 '{task_type}' 的配置，使用默认配置")
        return self.get_default_config()
    
    def get_default_config(self) -> ModelConfig:
        """
        获取默认配置
        
        Returns:
            默认 ModelConfig 对象
        """
        if self._default_config is None:
            self._load_default_config()
        
        return self._default_config
    
    def reload_config(self) -> None:
        """重新加载配置（用于热更新）"""
        logger.info("重新加载配置...")
        self._configs.clear()
        self._default_config = None
        self.load_config()
    
    @classmethod
    def get_instance(cls, config_path: Optional[Path] = None) -> 'ModelConfigManager':
        """
        获取单例实例
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            ModelConfigManager 实例
        """
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance
