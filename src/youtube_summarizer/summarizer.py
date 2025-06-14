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
    def summarize(self, text: str, prompt: str) -> str | None:
        """
        对给定的文本进行摘要。

        Args:
            text (str): 需要摘要的源文本 (字幕)。
            prompt (str): 用于指导模型生成内容的提示词。

        Returns:
            str | None: 生成的摘要文本，如果失败则返回 None。
        """
        pass

class GeminiSummarizer(Summarizer):
    """使用 Google Gemini Pro 模型进行摘要。"""
    def __init__(self, api_key: str):
        super().__init__(api_key)
        if self.api_key:
            genai.configure(api_key=self.api_key)
        # 使用系统指令来增强推理能力
        system_instruction = """你是一名专业的技术内容分析师。在处理任何内容时，请：
1. 首先深入理解内容的核心主题和关键概念
2. 分析内容的逻辑结构和论证过程  
3. 识别重要的技术细节、数据和案例
4. 进行批判性思考，评估信息的重要性和相关性
5. 基于以上分析，生成结构化、深度的摘要

请始终采用逐步推理的方式，确保输出的质量和深度。"""
        
        self.model = genai.GenerativeModel(
            'gemini-2.5-pro-preview-06-05',
            system_instruction=system_instruction
        )

    def summarize(self, text: str, prompt: str) -> str | None:
        if not self.api_key:
            logger.error("Gemini API Key 未配置。")
            return None
        
        logger.info("开始使用 Gemini Pro 进行摘要（已开启推理模式）...")
        
        # 增强 prompt 以促进推理
        reasoning_prompt = f"""请按照以下步骤进行深度分析和摘要：

<thinking>
首先，让我仔细分析这个内容：
1. 主题识别：这个内容的核心主题是什么？
2. 结构分析：内容是如何组织的？有哪些主要部分？
3. 关键信息提取：最重要的技术点、数据、案例是什么？
4. 逻辑关系：这些信息之间有什么联系？
5. 价值评估：哪些信息对读者最有价值？
</thinking>

基于以上分析，请严格按照以下要求生成摘要：

{prompt}

# 输入素材
- 提供材料：
```
{text}
```

请确保你的分析过程体现在最终的摘要质量中，生成一份深度、结构化的技术摘要。"""

        try:
            response = self.model.generate_content(
                reasoning_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,  # 适中的创造性
                    top_p=0.9,        # 核采样参数
                    top_k=40,         # 限制候选词数量
                    max_output_tokens=8192,  # 增加输出长度限制
                    response_mime_type="text/plain",
                )
            )
            summary = response.text
            logger.success("Gemini Pro 摘要完成（推理模式）。")
            return summary
        except Exception as e:
            logger.error(f"调用 Gemini API 时发生错误: {e}", exc_info=True)
            # 可以在这里根据具体的 API 错误类型给出更详细的提示
            if "API key not valid" in str(e):
                logger.error("您的 Gemini API 密钥无效，请检查 .env 文件。")
            return None

class XaiSummarizer(Summarizer):
    """XAI 模型摘要器 (占位符)。"""
    def summarize(self, text: str, prompt: str) -> str | None:
        logger.warning("XAI 模型功能尚未实现。")
        raise NotImplementedError("XAI summarizer is not implemented yet.")

class AlibabaSummarizer(Summarizer):
    """Alibaba 模型摘要器 (占位符)。"""
    def summarize(self, text: str, prompt: str) -> str | None:
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