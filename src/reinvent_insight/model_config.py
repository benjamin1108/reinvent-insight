"""
统一模型配置系统

该模块提供统一的模型配置管理和客户端接口，支持按任务类型配置不同的模型和参数。
"""

import asyncio
import logging
import time
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Type, Callable
import os

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

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


# ============================================================================
# 异常类
# ============================================================================

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


# ============================================================================
# 速率限制器
# ============================================================================

class RateLimiter:
    """全局速率限制器"""
    
    _lock = asyncio.Lock()
    _last_call_time: Dict[str, float] = {}
    
    def __init__(self, interval: float):
        """
        初始化速率限制器
        
        Args:
            interval: 调用间隔（秒）
        """
        self.interval = interval
        
    async def acquire(self, key: str = "default") -> None:
        """
        获取调用许可，必要时等待
        
        Args:
            key: 限制器键名，用于区分不同的限制器
        """
        async with self._lock:
            now = time.monotonic()
            last_time = self._last_call_time.get(key, 0.0)
            elapsed = now - last_time
            
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                logger.debug(f"触发速率限制 [{key}]，等待 {sleep_time:.2f} 秒")
                await asyncio.sleep(sleep_time)
            
            self._last_call_time[key] = time.monotonic()


# ============================================================================
# 模型客户端抽象基类
# ============================================================================

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


# ============================================================================
# 配置管理器
# ============================================================================

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
            # 获取项目根目录
            from . import config as app_config
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
        
        return ModelConfig(
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
            retry_backoff_base=retry_backoff_base
        )
    
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
        from . import config as app_config
        
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



# ============================================================================
# Gemini 模型客户端
# ============================================================================

class GeminiClient(BaseModelClient):
    """Gemini模型客户端"""
    
    def __init__(self, config: ModelConfig):
        """
        初始化Gemini客户端
        
        Args:
            config: 模型配置
            
        Raises:
            ConfigurationError: API Key未配置
        """
        super().__init__(config)
        
        if not config.api_key:
            raise ConfigurationError("Gemini API Key 未配置")
        
        try:
            from google import genai
            from google.genai import types
            
            self.genai = genai
            self.types = types
            
            # 创建客户端
            self.client = genai.Client(api_key=config.api_key)
            
            logger.info(f"Gemini客户端初始化成功: {config.model_name}")
            
        except ImportError:
            raise ConfigurationError("google-genai 包未安装")
        except Exception as e:
            raise ConfigurationError(f"Gemini客户端初始化失败: {e}")
    
    async def generate_content(
        self, 
        prompt: str, 
        is_json: bool = False,
        thinking_level: Optional[str] = None
    ) -> str:
        """
        生成文本内容
        
        Args:
            prompt: 提示词
            is_json: 是否返回JSON格式
            thinking_level: 思考级别 ("low", "medium", "high")，如果为None则根据配置自动选择
            
        Returns:
            生成的文本内容
            
        Raises:
            APIError: API调用失败
        """
        await self._apply_rate_limit()
        
        # 如果没有指定thinking_level，根据配置自动选择
        if thinking_level is None:
            thinking_level = "low" if self.config.low_thinking else "high"
        
        logger.info(f"开始使用 {self.config.model_name} 生成内容 (thinking_level={thinking_level}, from_config={thinking_level is None})...")
        
        # 使用新的google.genai SDK
        config = self.types.GenerateContentConfig(
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            max_output_tokens=self.config.max_output_tokens,
            response_mime_type="application/json" if is_json else "text/plain",
            thinking_config=self.types.ThinkingConfig(thinking_level=thinking_level)
        )
        
        async def _generate():
            response = await self.client.aio.models.generate_content(
                model=self.config.model_name,
                contents=prompt,
                config=config
            )
            
            # 提取文本内容
            if not response.text:
                raise APIError("API 返回的内容为空文本")
            
            return response.text
        
        try:
            content = await self._retry_with_backoff(_generate)
            logger.info(f"{self.config.model_name} 内容生成完成")
            return content
            
        except Exception as e:
            logger.error(f"调用 Gemini API 时发生错误: {e}", exc_info=True)
            if "API key not valid" in str(e):
                raise ConfigurationError("Gemini API 密钥无效")
            raise APIError(f"Gemini API 调用失败: {e}") from e
    
    async def generate_content_with_file(
        self,
        prompt: str,
        file_info: Dict[str, Any],
        is_json: bool = False,
        thinking_level: Optional[str] = None
    ) -> str:
        """
        使用文件生成内容（多模态）
        
        Args:
            prompt: 提示词
            file_info: 文件信息字典，包含name、uri、local_file等字段
            is_json: 是否返回JSON格式
            thinking_level: 思考级别 ("low", "medium", "high")，如果为None则根据配置自动选择
            
        Returns:
            生成的文本内容
            
        Raises:
            APIError: API调用失败
        """
        await self._apply_rate_limit()
        
        # 如果没有指定thinking_level，根据配置自动选择
        if thinking_level is None:
            thinking_level = "low" if self.config.low_thinking else "high"
        
        logger.info(f"开始使用 {self.config.model_name} 进行多模态分析 (thinking_level={thinking_level})...")
        
        generation_config = self.genai.types.GenerationConfig(
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            max_output_tokens=self.config.max_output_tokens,
            response_mime_type="application/json" if is_json else "text/plain",
            thinking_config=self.genai.types.ThinkingConfig(thinking_level=thinking_level)
        )
        
        async def _generate():
            # 根据文件类型选择处理方式
            if file_info.get("local_file", False):
                # 使用本地文件
                file_path = file_info["uri"]
                
                # 使用异步方式读取文件并处理
                loop = asyncio.get_event_loop()
                
                def read_and_process():
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                    
                    mime_type = file_info.get("mime_type", "application/pdf")
                    
                    return self.genai.GenerativeModel(self.config.model_name).generate_content(
                        [prompt, {"mime_type": mime_type, "data": file_data}],
                        generation_config=generation_config
                    )
                
                response = await loop.run_in_executor(None, read_and_process)
            else:
                # 获取已上传的文件引用
                file_ref = self.genai.get_file(name=file_info["name"])
                
                # 调用Gemini生成API
                response = await self.model.generate_content_async(
                    [prompt, file_ref],
                    generation_config=generation_config
                )
            
            # 检查是否有候选内容
            if not response.candidates:
                raise APIError("API 返回了空的候选内容")
            
            # 提取文本内容
            content = ''.join(
                part.text for part in response.candidates[0].content.parts
            )
            
            if not content:
                raise APIError("API 返回的内容为空文本")
            
            return content
        
        try:
            content = await self._retry_with_backoff(_generate)
            logger.info(f"{self.config.model_name} 多模态分析完成")
            return content
            
        except Exception as e:
            logger.error(f"调用 Gemini API 进行多模态分析时发生错误: {e}", exc_info=True)
            if "API key not valid" in str(e):
                raise ConfigurationError("Gemini API 密钥无效")
            raise APIError(f"Gemini API 多模态调用失败: {e}") from e
    
    async def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        上传文件到Gemini API
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典
            
        Raises:
            APIError: 上传失败
        """
        try:
            loop = asyncio.get_event_loop()
            
            # 尝试上传文件
            try:
                file_obj = await loop.run_in_executor(
                    None, 
                    lambda: self.genai.upload_file(path=file_path)
                )
                
                file_info = {
                    "name": file_obj.name,
                    "display_name": file_obj.display_name,
                    "mime_type": file_obj.mime_type,
                    "size_bytes": file_obj.size_bytes,
                    "create_time": file_obj.create_time,
                    "expiration_time": file_obj.expiration_time,
                    "uri": file_obj.uri,
                    "local_file": False
                }
                
                logger.info(f"文件上传成功: {file_info['name']}")
                return file_info
                
            except TypeError as te:
                if "ragStoreName" in str(te):
                    # API变更，使用本地文件处理
                    logger.warning("检测到 API 变更，使用本地文件处理")
                    
                    import os
                    file_size = os.path.getsize(file_path)
                    
                    file_info = {
                        "name": f"files/{os.path.basename(file_path)}",
                        "display_name": os.path.basename(file_path),
                        "mime_type": "application/pdf",
                        "size_bytes": file_size,
                        "create_time": None,
                        "expiration_time": None,
                        "uri": file_path,
                        "local_file": True
                    }
                    
                    logger.info(f"使用本地文件处理: {file_info['name']}")
                    return file_info
                else:
                    raise te
                    
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise APIError(f"文件上传失败: {e}") from e
    
    async def delete_file(self, file_id: str) -> bool:
        """
        删除Gemini上传的文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            删除是否成功
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: self.genai.delete_file(name=file_id)
            )
            logger.info(f"已删除文件: {file_id}")
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False
    
    def _split_text_for_streaming(self, text: str, max_chunk_size: int = 100) -> list:
        """
        将长文本按句子切分为多个较短的片段，用于模拟流式体验
        
        策略：按句子边界（。！？.!? 或换行符）切分，每个片段约 50-100 字
        
        Args:
            text: 要切分的文本
            max_chunk_size: 每个片段的最大字符数
            
        Returns:
            文本片段列表
        """
        import re
        
        # 如果文本很短，直接返回
        if len(text) <= max_chunk_size:
            return [text]
        
        # 按句子边界切分（中英文标点）
        # 匹配句子结束符号：。！？.!? 后面可能跟引号、括号等
        sentence_pattern = r'[。！？.!?]+[」』"\'）\)]*'
        
        chunks = []
        current_chunk = ""
        
        # 先按句子切分
        sentences = re.split(f'({sentence_pattern})', text)
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            # 如果有标点符号，加上
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            # 如果当前块加上这个句子不超过限制，就加入
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence
            else:
                # 否则，保存当前块，开始新块
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 如果没有切分成功（可能没有句子边界），强制按字符数切分
        if not chunks or (len(chunks) == 1 and len(chunks[0]) > max_chunk_size):
            logger.debug("没有找到句子边界，强制按字符数切分")
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        
        # 过滤掉空片段
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        logger.info(f"📄 文本切分: {len(text)} 字符 → {len(chunks)} 个片段")
        for i, chunk in enumerate(chunks):
            logger.debug(f"   片段 {i+1}: {len(chunk)} 字符")
        
        return chunks
    
    async def generate_tts_stream(
        self,
        text: str,
        voice: str = "kore",
        language: str = "zh-CN"
    ):
        """
        生成 TTS 音频（使用输入端分片策略实现低延迟流式播放）
        
        策略：
        1. 将长文本切分为多个短片段（50-100字）
        2. 串行请求每个片段的 TTS
        3. 一旦收到第一个片段的音频就立即 yield
        4. 持续处理后续片段，实现连续播放
        
        这样可以将首字延迟从 15 秒降低到 3-5 秒！
        
        Args:
            text: 要转换的文本
            voice: 音色名称（30种可选，如 kore, puck, aoede 等，全小写）
            language: 语言代码（如 zh-CN, en-US 等，Gemini 会自动检测）
            
        Yields:
            bytes: Base64 编码的 PCM 音频数据
            
        Raises:
            APIError: API 调用失败
        """
        await self._apply_rate_limit()
        
        try:
            # 使用新的 google-genai SDK
            try:
                from google import genai
                from google.genai import types
                import base64
            except ImportError:
                logger.warning("google-genai SDK 未安装，TTS 功能不可用")
                raise ConfigurationError(
                    "Gemini TTS 需要 google-genai SDK。请安装: pip install google-genai"
                )
            
            # 记录流开始的详细信息
            start_time = asyncio.get_event_loop().time()
            logger.info(
                f"🎤 开始输入端分片流式 TTS: "
                f"model={self.config.model_name}, "
                f"voice={voice}, "
                f"language={language}, "
                f"text_length={len(text)}"
            )
            
            # 🔥 关键策略：将长文本切分为多个短片段（20-30字，约2-4秒音频）
            text_chunks = self._split_text_for_streaming(text, max_chunk_size=30)
            logger.info(f"✂️  文本已切分为 {len(text_chunks)} 个片段")
            
            # 创建客户端（在主线程中，避免线程安全问题）
            try:
                client = genai.Client(api_key=self.config.api_key)
                logger.debug("Gemini 客户端创建成功")
            except Exception as e:
                logger.error(f"创建 Gemini 客户端失败: {e}", exc_info=True)
                raise ConfigurationError(f"无法创建 Gemini 客户端: {e}") from e
            
            # 处理每个文本片段
            total_chunk_count = 0
            total_bytes = 0
            first_audio_time = None
            
            for segment_index, text_segment in enumerate(text_chunks, 1):
                segment_start_time = asyncio.get_event_loop().time()
                logger.info(f"🎯 处理片段 {segment_index}/{len(text_chunks)}: {len(text_segment)} 字符")
                
                # 为每个片段生成音频
                async def generate_segment_audio(segment_text):
                    """为单个文本片段生成音频"""
                    def _get_stream():
                        return client.models.generate_content_stream(
                            model=self.config.model_name,
                            contents=segment_text,
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=voice
                                        )
                                    )
                                )
                            )
                        )
                    
                    # 在线程池中获取流
                    stream = await asyncio.to_thread(_get_stream)
                    
                    # 收集这个片段的所有音频块
                    segment_audio_chunks = []
                    chunk_index = 0
                    
                    while True:
                        try:
                            chunk = await asyncio.to_thread(lambda: next(stream, None))
                            if chunk is None:
                                break
                            
                            chunk_index += 1
                            
                            # 解析音频数据
                            if hasattr(chunk, 'candidates') and chunk.candidates:
                                candidate = chunk.candidates[0]
                                if hasattr(candidate, 'content') and candidate.content:
                                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                        for part in candidate.content.parts:
                                            if hasattr(part, 'inline_data') and part.inline_data:
                                                if hasattr(part.inline_data, 'data') and part.inline_data.data:
                                                    audio_data = part.inline_data.data
                                                    
                                                    # 解码音频数据
                                                    if isinstance(audio_data, str):
                                                        pcm_data = base64.b64decode(audio_data)
                                                    else:
                                                        pcm_data = audio_data
                                                    
                                                    if pcm_data:
                                                        segment_audio_chunks.append(pcm_data)
                        
                        except StopIteration:
                            break
                        except Exception as e:
                            logger.error(f"读取片段音频块时出错: {e}")
                            break
                    
                    return segment_audio_chunks
                
                # 生成这个片段的音频
                segment_audio_chunks = await generate_segment_audio(text_segment)
                
                if not segment_audio_chunks:
                    logger.warning(f"⚠️  片段 {segment_index} 没有生成音频，跳过")
                    continue
                
                # 记录首个音频片段的延迟
                if first_audio_time is None:
                    first_audio_time = asyncio.get_event_loop().time()
                    first_audio_latency = first_audio_time - start_time
                    logger.info(f"⚡ 首个音频片段延迟: {first_audio_latency:.2f}s （目标 < 5s）")
                
                # 立即 yield 这个片段的所有音频块
                for pcm_data in segment_audio_chunks:
                    b64_data = base64.b64encode(pcm_data).decode('utf-8')
                    total_chunk_count += 1
                    total_bytes += len(pcm_data)
                    
                    logger.info(
                        f"📦 发送片段 {segment_index} 的音频: "
                        f"{len(pcm_data)} bytes, "
                        f"累计 {total_bytes / 1024:.1f}KB"
                    )
                    
                    # ✅ 立即 yield 给前端播放！
                    yield b64_data.encode('utf-8')
                
                segment_time = asyncio.get_event_loop().time() - segment_start_time
                logger.info(f"✅ 片段 {segment_index} 完成，耗时 {segment_time:.2f}s")
            
            # 记录完成统计
            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time
            
            if total_chunk_count == 0:
                logger.warning("⚠️  流式 TTS 完成但没有生成任何音频")
            else:
                avg_chunk_size = total_bytes / total_chunk_count if total_chunk_count > 0 else 0
                logger.info(
                    f"🎉 输入端分片流式 TTS 完成: "
                    f"{len(text_chunks)} 个文本片段, "
                    f"{total_chunk_count} 个音频块, "
                    f"{total_bytes / 1024:.1f}KB, "
                    f"平均块大小 {avg_chunk_size / 1024:.1f}KB, "
                    f"总时长 {total_time:.2f}s"
                )
                
                if first_audio_time:
                    first_audio_latency = first_audio_time - start_time
                    logger.info(f"📊 性能指标: 首音频延迟 {first_audio_latency:.2f}s")
                    
                    if first_audio_latency < 5.0:
                        logger.info("🎯 成功！首音频延迟 < 5 秒")
                    elif first_audio_latency < 10.0:
                        logger.info("✅ 良好！首音频延迟 < 10 秒")
                    else:
                        logger.warning(f"⚠️  首音频延迟较长: {first_audio_latency:.2f}s")
            
        except ConfigurationError:
            # 配置错误直接抛出
            raise
        except Exception as e:
            # 记录详细的错误上下文
            error_context = {
                'model': self.config.model_name,
                'voice': voice,
                'language': language,
                'text_length': len(text),
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
            
            logger.error(
                f"❌ 流式 TTS 失败: {e}\n"
                f"   上下文: {error_context}",
                exc_info=True
            )
            
            # 根据错误类型提供更友好的错误消息
            error_str = str(e).lower()
            
            if "api key not valid" in error_str or "invalid api key" in error_str:
                raise ConfigurationError(
                    f"Gemini API 密钥无效。请检查 GEMINI_API_KEY 环境变量。"
                ) from e
            
            if "voice name" in error_str and "not supported" in error_str:
                raise APIError(
                    f"不支持的音色 '{voice}'。"
                    f"请使用支持的音色（如 kore, puck, aoede 等）。"
                ) from e
            
            if "quota" in error_str or "rate limit" in error_str:
                raise APIError(
                    f"API 配额已用尽或速率限制。请稍后重试。"
                ) from e
            
            if "client has been closed" in error_str:
                raise APIError(
                    f"API 客户端连接已关闭。这可能是网络问题或超时。"
                ) from e
            
            # 通用错误
            raise APIError(
                f"Gemini TTS 流式生成失败: {e}\n"
                f"模型: {self.config.model_name}, 音色: {voice}"
            ) from e
    
    async def generate_tts(
        self,
        text: str,
        voice: str = "Kore",
        language: str = "zh-CN"
    ) -> bytes:
        """
        生成完整的 TTS 音频（非流式）
        
        Args:
            text: 要转换的文本
            voice: 音色名称
            language: 语言代码
            
        Returns:
            Base64 编码的 PCM 音频数据
            
        Raises:
            APIError: API 调用失败
        """
        audio_data = None
        async for chunk in self.generate_tts_stream(text, voice, language):
            audio_data = chunk
            break  # Gemini TTS 返回完整音频，只有一个块
        
        if not audio_data:
            raise APIError("未收到音频数据")
        
        return audio_data



# ============================================================================
# DashScope (阿里云通义千问) 模型客户端
# ============================================================================

class DashScopeClient(BaseModelClient):
    """DashScope (阿里云通义千问) 模型客户端"""
    
    def __init__(self, config: ModelConfig):
        """
        初始化DashScope客户端
        
        Args:
            config: 模型配置
            
        Raises:
            ConfigurationError: API Key未配置或SDK未安装
        """
        super().__init__(config)
        
        if not config.api_key:
            raise ConfigurationError("DashScope API Key 未配置")
        
        try:
            from dashscope import Generation
            import dashscope
            self.dashscope = dashscope
            self.Generation = Generation
            
            # 配置API Key
            dashscope.api_key = config.api_key
            
            logger.info(f"DashScope客户端初始化成功: {config.model_name}")
            
        except ImportError:
            raise ConfigurationError(
                "dashscope 包未安装，请运行: pip install dashscope"
            )
        except Exception as e:
            raise ConfigurationError(f"DashScope客户端初始化失败: {e}")
    
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
        await self._apply_rate_limit()
        
        logger.info(f"开始使用 {self.config.model_name} 生成内容...")
        
        # 构建消息
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        # 如果需要JSON格式，在prompt中添加指示
        if is_json:
            messages[0]['content'] = f"{prompt}\n\n请以JSON格式返回结果。"
        
        async def _generate():
            # DashScope SDK 使用同步调用，需要在executor中运行
            loop = asyncio.get_event_loop()
            
            def _call_api():
                response = self.Generation.call(
                    model=self.config.model_name,
                    messages=messages,
                    result_format='message',
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    max_tokens=self.config.max_output_tokens,
                )
                return response
            
            response = await loop.run_in_executor(None, _call_api)
            
            # 检查响应状态
            if response.status_code != 200:
                raise APIError(
                    f"DashScope API 返回错误: {response.code} - {response.message}"
                )
            
            # 提取内容
            if not response.output or not response.output.choices:
                raise APIError("DashScope API 返回了空的内容")
            
            content = response.output.choices[0].message.content
            
            if not content:
                raise APIError("DashScope API 返回的内容为空文本")
            
            return content
        
        try:
            content = await self._retry_with_backoff(_generate)
            logger.info(f"{self.config.model_name} 内容生成完成")
            return content
            
        except Exception as e:
            logger.error(f"调用 DashScope API 时发生错误: {e}", exc_info=True)
            if "Invalid API-key" in str(e) or "Unauthorized" in str(e):
                raise ConfigurationError("DashScope API 密钥无效")
            raise APIError(f"DashScope API 调用失败: {e}") from e
    
    async def generate_content_with_file(
        self,
        prompt: str,
        file_info: Dict[str, Any],
        is_json: bool = False
    ) -> str:
        """
        使用文件生成内容（多模态）
        
        DashScope 支持多模态输入，包括图片和文档
        
        Args:
            prompt: 提示词
            file_info: 文件信息字典
            is_json: 是否返回JSON格式
            
        Returns:
            生成的文本内容
            
        Raises:
            APIError: API调用失败
        """
        await self._apply_rate_limit()
        
        logger.info(f"开始使用 {self.config.model_name} 进行多模态分析...")
        
        # 构建多模态消息
        content_parts = []
        
        # 添加文本部分
        if is_json:
            content_parts.append({
                'text': f"{prompt}\n\n请以JSON格式返回结果。"
            })
        else:
            content_parts.append({'text': prompt})
        
        # 添加文件部分
        if file_info.get("local_file", False):
            # 本地文件：读取并转换为base64
            import base64
            file_path = file_info["uri"]
            
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            file_base64 = base64.b64encode(file_data).decode('utf-8')
            mime_type = file_info.get("mime_type", "application/pdf")
            
            # DashScope 多模态格式
            content_parts.append({
                'file': f"data:{mime_type};base64,{file_base64}"
            })
        else:
            # 远程文件URL
            content_parts.append({
                'file': file_info.get("uri", "")
            })
        
        messages = [
            {
                'role': 'user',
                'content': content_parts
            }
        ]
        
        async def _generate():
            loop = asyncio.get_event_loop()
            
            def _call_api():
                # 使用支持多模态的模型
                model = self.config.model_name
                # 如果是基础模型，切换到多模态版本
                if model == "qwen-turbo" or model == "qwen-plus":
                    model = "qwen-vl-plus"
                elif model == "qwen-max":
                    model = "qwen-vl-max"
                
                response = self.Generation.call(
                    model=model,
                    messages=messages,
                    result_format='message',
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    max_tokens=self.config.max_output_tokens,
                )
                return response
            
            response = await loop.run_in_executor(None, _call_api)
            
            # 检查响应状态
            if response.status_code != 200:
                raise APIError(
                    f"DashScope API 返回错误: {response.code} - {response.message}"
                )
            
            # 提取内容
            if not response.output or not response.output.choices:
                raise APIError("DashScope API 返回了空的内容")
            
            content = response.output.choices[0].message.content
            
            if not content:
                raise APIError("DashScope API 返回的内容为空文本")
            
            return content
        
        try:
            content = await self._retry_with_backoff(_generate)
            logger.info(f"{self.config.model_name} 多模态分析完成")
            return content
            
        except Exception as e:
            logger.error(f"调用 DashScope API 进行多模态分析时发生错误: {e}", exc_info=True)
            if "Invalid API-key" in str(e) or "Unauthorized" in str(e):
                raise ConfigurationError("DashScope API 密钥无效")
            raise APIError(f"DashScope API 多模态调用失败: {e}") from e
    
    async def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        DashScope 不需要预先上传文件，直接在请求中发送
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典
        """
        import os
        
        file_info = {
            "name": f"local/{os.path.basename(file_path)}",
            "display_name": os.path.basename(file_path),
            "mime_type": "application/pdf",
            "size_bytes": os.path.getsize(file_path),
            "create_time": None,
            "expiration_time": None,
            "uri": file_path,
            "local_file": True
        }
        
        logger.info(f"DashScope 使用本地文件: {file_info['name']}")
        return file_info
    
    async def delete_file(self, file_id: str) -> bool:
        """
        DashScope 不需要删除文件（没有预上传）
        
        Args:
            file_id: 文件ID
            
        Returns:
            总是返回 True
        """
        logger.info(f"DashScope 不需要删除文件: {file_id}")
        return True
    
    def _split_text_for_streaming(self, text: str, max_chunk_size: int = 100) -> list:
        """
        将长文本按句子切分为多个较短的片段，用于流式体验
        
        策略：按句子边界（。！？.!? 或换行符）切分，每个片段约 50-100 字
        
        Args:
            text: 要切分的文本
            max_chunk_size: 每个片段的最大字符数
            
        Returns:
            文本片段列表
        """
        import re
        
        # 如果文本很短，直接返回
        if len(text) <= max_chunk_size:
            return [text]
        
        # 按句子边界切分（中英文标点）
        sentence_pattern = r'[。！？.!?]+[」』"\'）\)]*'
        
        chunks = []
        current_chunk = ""
        
        # 先按句子切分
        sentences = re.split(f'({sentence_pattern})', text)
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            # 如果有标点符号，加上
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            # 如果当前块加上这个句子不超过限制，就加入
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence
            else:
                # 否则，保存当前块，开始新块
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 如果没有切分成功（可能没有句子边界），强制按字符数切分
        if not chunks or (len(chunks) == 1 and len(chunks[0]) > max_chunk_size):
            logger.debug("没有找到句子边界，强制按字符数切分")
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        
        # 过滤掉空片段
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        logger.info(f"📄 文本切分: {len(text)} 字符 → {len(chunks)} 个片段")
        for i, chunk in enumerate(chunks):
            logger.debug(f"   片段 {i+1}: {len(chunk)} 字符")
        
        return chunks
    
    async def generate_tts_stream(
        self,
        text: str,
        voice: str = "Cherry",
        language: str = "Chinese"
    ):
        """
        生成 TTS 音频（使用 MultiModalConversation API + 输入端分片策略）
        
        使用输入端分片策略实现低延迟流式播放：
        1. 将长文本切分为多个短片段（50-100字）
        2. 使用 MultiModalConversation.call 串行处理每个片段
        3. 一旦收到音频数据就立即 yield
        4. 持续处理后续片段，实现连续播放
        
        Args:
            text: 要转换的文本
            voice: 音色名称
            language: 语言类型（Chinese, English 等）
            
        Yields:
            bytes: Base64 编码的 PCM 音频数据
            
        Raises:
            APIError: API 调用失败
        """
        await self._apply_rate_limit()
        
        try:
            import base64
            
            # 记录流开始的详细信息
            start_time = asyncio.get_event_loop().time()
            logger.info(
                f"🎤 开始 Qwen3-TTS 流式 TTS: "
                f"model={self.config.model_name}, "
                f"voice={voice}, "
                f"language={language}, "
                f"text_length={len(text)}"
            )
            
            # 🔥 关键策略：将长文本切分为多个短片段（50-100字）
            text_chunks = self._split_text_for_streaming(text, max_chunk_size=100)
            logger.info(f"✂️  文本已切分为 {len(text_chunks)} 个片段")
            
            # 处理每个文本片段
            total_chunk_count = 0
            total_bytes = 0
            first_audio_time = None
            
            for segment_index, text_segment in enumerate(text_chunks, 1):
                segment_start_time = asyncio.get_event_loop().time()
                logger.info(f"🎯 处理片段 {segment_index}/{len(text_chunks)}: {len(text_segment)} 字符")
                
                # 在片段之间添加短暂延迟，避免请求过快导致连接问题
                if segment_index > 1:
                    await asyncio.sleep(0.5)
                
                # 为每个片段生成音频（使用 MultiModalConversation API）
                loop = asyncio.get_event_loop()
                
                def _call_and_collect_tts():
                    """
                    在同步上下文中调用 DashScope API 并收集所有音频块
                    
                    ⚠️ 关键修复：将整个同步迭代过程放在 executor 中执行
                    避免阻塞事件循环，确保服务器保持响应
                    """
                    response = self.dashscope.MultiModalConversation.call(
                        model=self.config.model_name,
                        api_key=self.config.api_key,
                        text=text_segment,
                        voice=voice,
                        language_type=language,
                        stream=True
                    )
                    
                    # ✅ 在 executor 中完成同步迭代
                    segment_audio_data = b''
                    audio_url = None
                    chunk_count = 0
                    
                    for chunk in response:  # 同步迭代在这里完成，不阻塞事件循环
                        chunk_count += 1
                        logger.debug(f"收到响应块 {chunk_count}: {type(chunk)}")
                        
                        # 检查是否有音频数据
                        if hasattr(chunk, 'output') and chunk.output:
                            logger.debug(f"output 存在: {type(chunk.output)}")
                            
                            if hasattr(chunk.output, 'audio') and chunk.output.audio:
                                audio_obj = chunk.output.audio
                                logger.debug(f"audio 对象: {type(audio_obj)}, data={getattr(audio_obj, 'data', None)[:50] if hasattr(audio_obj, 'data') and audio_obj.data else None}, url={getattr(audio_obj, 'url', None)}")
                                
                                # 流式输出：data 字段包含 Base64 音频数据
                                if hasattr(audio_obj, 'data') and audio_obj.data:
                                    audio_data = audio_obj.data
                                    # 解码 Base64
                                    if isinstance(audio_data, str) and audio_data:
                                        logger.info(f"收到 Base64 音频数据，长度: {len(audio_data)}")
                                        audio_bytes = base64.b64decode(audio_data)
                                        segment_audio_data += audio_bytes
                                
                                # 非流式输出：url 字段包含完整音频文件 URL
                                elif hasattr(audio_obj, 'url') and audio_obj.url:
                                    audio_url = audio_obj.url
                                    logger.info(f"收到音频 URL: {audio_url}")
                            else:
                                logger.warning(f"output 没有 audio 属性或 audio 为空")
                        else:
                            logger.warning(f"chunk 没有 output 属性或 output 为空")
                    
                    logger.info(f"处理了 {chunk_count} 个响应块")
                    return segment_audio_data, audio_url
                
                # ✅ 整个同步过程在 executor 中执行，不阻塞事件循环
                segment_audio_data, audio_url = await loop.run_in_executor(
                    None, _call_and_collect_tts
                )
                
                # 如果收到的是 URL，需要下载音频
                if audio_url and not segment_audio_data:
                    logger.info(f"从 URL 下载音频: {audio_url}")
                    import requests
                    
                    def _download_audio():
                        response = requests.get(audio_url, timeout=30)
                        response.raise_for_status()
                        return response.content
                    
                    segment_audio_data = await loop.run_in_executor(None, _download_audio)
                
                if not segment_audio_data:
                    logger.warning(f"⚠️  片段 {segment_index} 没有生成音频，跳过")
                    continue
                
                # 记录首个音频片段的延迟
                if first_audio_time is None:
                    first_audio_time = asyncio.get_event_loop().time()
                    first_audio_latency = first_audio_time - start_time
                    logger.info(f"⚡ 首个音频片段延迟: {first_audio_latency:.2f}s （目标 < 5s）")
                
                # 编码为 Base64
                b64_data = base64.b64encode(segment_audio_data).decode('utf-8')
                total_chunk_count += 1
                total_bytes += len(segment_audio_data)
                
                logger.info(
                    f"📦 发送片段 {segment_index} 的音频: "
                    f"{len(segment_audio_data)} bytes, "
                    f"累计 {total_bytes / 1024:.1f}KB"
                )
                
                # ✅ 立即 yield 给前端播放！
                yield b64_data.encode('utf-8')
                
                segment_time = asyncio.get_event_loop().time() - segment_start_time
                logger.info(f"✅ 片段 {segment_index} 完成，耗时 {segment_time:.2f}s")
            
            # 记录完成统计
            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time
            
            if total_chunk_count == 0:
                logger.warning("⚠️  流式 TTS 完成但没有生成任何音频")
            else:
                avg_chunk_size = total_bytes / total_chunk_count if total_chunk_count > 0 else 0
                logger.info(
                    f"🎉 Qwen3-TTS 流式 TTS 完成: "
                    f"{len(text_chunks)} 个文本片段, "
                    f"{total_chunk_count} 个音频块, "
                    f"{total_bytes / 1024:.1f}KB, "
                    f"平均块大小 {avg_chunk_size / 1024:.1f}KB, "
                    f"总时长 {total_time:.2f}s"
                )
                
                if first_audio_time:
                    first_audio_latency = first_audio_time - start_time
                    logger.info(f"📊 性能指标: 首音频延迟 {first_audio_latency:.2f}s")
                    
                    if first_audio_latency < 5.0:
                        logger.info("🎯 成功！首音频延迟 < 5 秒")
                    elif first_audio_latency < 10.0:
                        logger.info("✅ 良好！首音频延迟 < 10 秒")
                    else:
                        logger.warning(f"⚠️  首音频延迟较长: {first_audio_latency:.2f}s")
            
        except Exception as e:
            logger.error(f"调用 Qwen3-TTS API 时发生错误: {e}", exc_info=True)
            if "Invalid API-key" in str(e) or "Unauthorized" in str(e):
                raise ConfigurationError("DashScope API 密钥无效")
            raise APIError(f"Qwen3-TTS API 调用失败: {e}") from e
    
    async def generate_tts(
        self,
        text: str,
        voice: str = "Cherry",
        language: str = "Chinese"
    ) -> bytes:
        """
        生成完整的 TTS 音频（非流式）
        
        Args:
            text: 要转换的文本
            voice: 音色名称
            language: 语言类型
            
        Returns:
            bytes: 完整的音频数据（Base64 编码的 PCM）
            
        Raises:
            APIError: API 调用失败
        """
        logger.info(f"开始使用 {self.config.model_name} 生成完整 TTS 音频...")
        
        # 收集所有音频块
        chunks = []
        async for chunk in self.generate_tts_stream(text, voice, language):
            chunks.append(chunk)
        
        # 拼接所有块
        complete_audio = b''.join(chunks)
        
        logger.info(f"TTS 音频生成完成，总大小: {len(complete_audio)} bytes")
        return complete_audio


# ============================================================================
# 模型客户端工厂
# ============================================================================

class ModelClientFactory:
    """模型客户端工厂"""
    
    _client_registry: Dict[str, Type[BaseModelClient]] = {
        "gemini": GeminiClient,
        "dashscope": DashScopeClient,
        # 未来可以添加更多提供商
        # "xai": XAIClient,
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


# ============================================================================
# 便捷函数
# ============================================================================

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



