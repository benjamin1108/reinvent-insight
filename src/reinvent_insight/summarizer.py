import logging
from abc import ABC, abstractmethod
import google.generativeai as genai
from . import config
import asyncio
import time

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
    
    # 全局速率限制器
    _api_lock = asyncio.Lock()
    _last_api_call_time: float = 0.0
    API_CALL_INTERVAL_SECONDS: float = 0.5  # 每两次调用之间至少间隔 0.5 秒

    def __init__(self, api_key: str):
        super().__init__(api_key)
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
        # 移除了固定的 system_instruction，使其更灵活
        self.model = genai.GenerativeModel(
            'gemini-2.5-pro',
        )

    async def generate_content(self, prompt: str, is_json: bool = False) -> str | None:
        if not self.api_key:
            logger.error("Gemini API Key 未配置。")
            return None
        
        # --- 全局速率限制逻辑 ---
        async with self.__class__._api_lock:
            now = time.monotonic()
            elapsed = now - self.__class__._last_api_call_time
            
            if elapsed < self.API_CALL_INTERVAL_SECONDS:
                sleep_time = self.API_CALL_INTERVAL_SECONDS - elapsed
                logger.debug(f"触发API速率限制，将休眠 {sleep_time:.2f} 秒。")
                await asyncio.sleep(sleep_time)
            
            # 更新时间戳，为下一次调用做准备
            self.__class__._last_api_call_time = time.monotonic()
        
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

    async def generate_content_with_pdf(self, prompt: str, pdf_file_info: dict, is_json: bool = False) -> str | None:
        """
        使用PDF文件生成内容（多模态分析）
        
        Args:
            prompt: 提示词
            pdf_file_info: PDF文件信息字典，包含name、uri、local_file等字段
            is_json: 是否返回JSON格式
            
        Returns:
            生成的内容，失败返回None
        """
        if not self.api_key:
            logger.error("Gemini API Key 未配置。")
            return None
        
        # --- 全局速率限制逻辑 ---
        async with self.__class__._api_lock:
            now = time.monotonic()
            elapsed = now - self.__class__._last_api_call_time
            
            if elapsed < self.API_CALL_INTERVAL_SECONDS:
                sleep_time = self.API_CALL_INTERVAL_SECONDS - elapsed
                logger.debug(f"触发API速率限制，将休眠 {sleep_time:.2f} 秒。")
                await asyncio.sleep(sleep_time)
            
            # 更新时间戳，为下一次调用做准备
            self.__class__._last_api_call_time = time.monotonic()
        
        logger.info("开始使用 Gemini Pro 进行PDF多模态分析...")
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            max_output_tokens=128000,
            response_mime_type="application/json" if is_json else "text/plain",
        )

        try:
            # 根据文件类型选择处理方式
            if pdf_file_info.get("local_file", False):
                # 使用本地文件
                pdf_file_path = pdf_file_info["uri"]
                
                # 使用异步方式读取文件并处理
                loop = asyncio.get_event_loop()
                
                def read_and_process():
                    with open(pdf_file_path, "rb") as f:
                        file_data = f.read()
                    return genai.GenerativeModel('gemini-2.5-pro').generate_content(
                        [prompt, {"mime_type": "application/pdf", "data": file_data}],
                        generation_config=generation_config
                    )
                
                response = await loop.run_in_executor(None, read_and_process)
            else:
                # 获取已上传的PDF文件引用
                pdf_file = genai.get_file(name=pdf_file_info["name"])
                
                # 调用Gemini生成API
                response = await self.model.generate_content_async(
                    [prompt, pdf_file],
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
            
            logger.success("Gemini Pro PDF多模态分析完成。")
            return content
        except Exception as e:
            logger.error(f"调用 Gemini API 进行PDF分析时发生错误: {e}", exc_info=True)
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