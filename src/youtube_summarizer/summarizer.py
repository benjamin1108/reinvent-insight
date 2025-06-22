import logging
from abc import ABC, abstractmethod
import google.generativeai as genai
from . import config

logger = logging.getLogger(__name__)

class Summarizer(ABC):
    """摘要器接口的抽象基类。"""
    def __init__(self, api_key: str | None):
        self.api_key = api_key

    @abstractmethod
    async def generate_content(self, prompt: str, is_json: bool = False) -> str | None:
        """
        根据给定的提示词生成内容。

        Args:
            prompt (str): 用于指导模型生成内容的完整提示词。
            is_json (bool): 是否要求返回 JSON 格式的内容。

        Returns:
            str | None: 生成的文本内容，如果失败则返回 None。
        """
        pass

class GeminiSummarizer(Summarizer):
    """使用 Google Gemini Pro 模型进行摘要。"""
    def __init__(self, api_key: str):
        super().__init__(api_key)
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
        # 移除了固定的 system_instruction，使其更灵活
        self.model = genai.GenerativeModel(
            'gemini-2.5-pro-preview-06-05',
        )

    async def generate_content(self, prompt: str, is_json: bool = False) -> str | None:
        if not self.api_key:
            logger.error("Gemini API Key 未配置。")
            return None
        
        logger.info("开始使用 Gemini Pro 生成内容...")
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            max_output_tokens=128000,
            response_mime_type="application/json" if is_json else "text/plain",
        )

        try:
            # 使用异步 generate_content_async
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            # 检查是否有候选内容
            if not response.candidates:
                logger.warning("Gemini API 返回了空的候选内容。")
                return None
            
            # 改进对 response.text 的访问，增加错误处理
            content = ''.join(part.text for part in response.candidates[0].content.parts)
            if not content:
                 logger.warning("Gemini API 返回的内容为空文本。")
                 return None
            
            logger.success("Gemini Pro 内容生成完成。")
            return content
        except Exception as e:
            logger.error(f"调用 Gemini API 时发生错误: {e}", exc_info=True)
            if "API key not valid" in str(e):
                logger.error("您的 Gemini API 密钥无效，请检查 .env 文件。")
            return None

class XaiSummarizer(Summarizer):
    """XAI 模型摘要器 (占位符)。"""
    async def generate_content(self, prompt: str, is_json: bool = False) -> str | None:
        logger.warning("XAI 模型功能尚未实现。")
        raise NotImplementedError("XAI summarizer is not implemented yet.")

class AlibabaSummarizer(Summarizer):
    """Alibaba 模型摘要器 (占位符)。"""
    async def generate_content(self, prompt: str, is_json: bool = False) -> str | None:
        logger.warning("Alibaba 模型功能尚未实现。")
        raise NotImplementedError("Alibaba summarizer is not implemented yet.")


# 模型名称到类的映射
MODEL_MAP = {
    "Gemini": (GeminiSummarizer, config.GEMINI_API_KEY),
    "XAI": (XaiSummarizer, config.XAI_API_KEY),
    "Alibaba": (AlibabaSummarizer, config.ALIBABA_API_KEY),
}

def get_summarizer(model_name: str) -> Summarizer | None:
    """
    摘要器工厂函数。

    Args:
        model_name (str): 模型的名称 (e.g., "Gemini").

    Returns:
        Summarizer | None: 对应摘要器的实例，如果模型不存在则返回 None。
    """
    summarizer_class, api_key = MODEL_MAP.get(model_name, (None, None))
    
    if not summarizer_class:
        logger.error(f"未知的模型名称: {model_name}")
        return None
        
    logger.info(f"初始化摘要器: {model_name}")
    return summarizer_class(api_key) 