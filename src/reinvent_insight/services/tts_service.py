"""
文本转语音服务

提供文本预处理、TTS 生成和缓存管理功能
"""

import re
import hashlib
import logging
from typing import AsyncGenerator, Optional
from pathlib import Path

from ..model_config import BaseModelClient, ModelConfig

logger = logging.getLogger(__name__)

# Qwen3-TTS 支持的音色列表
VALID_QWEN_VOICES = {
    # 女声
    'cherry', 'stella', 'luna', 'bella',
    # 男声
    'kai', 'alex', 'william', 'ethan', 'oliver',
    # 儿童
    'emily', 'tommy',
    # 方言
    'cantonese', 'sichuan', 'dongbei',
    # 其他
    'robot', 'narrator', 'announcer', 'customer'
}


class TTSService:
    """文本转语音服务"""
    
    def __init__(self, model_client: BaseModelClient):
        """
        初始化 TTS 服务
        
        Args:
            model_client: 模型客户端实例
        """
        self.client = model_client
        self.config = model_client.config
        
        logger.info(f"TTSService 初始化成功，使用模型: {self.config.model_name}")
    
    def validate_voice(self, voice: Optional[str] = None) -> str:
        """
        验证并规范化音色名称
        
        Args:
            voice: 音色名称，None 则使用配置默认值
            
        Returns:
            规范化后的音色名称（首字母大写）
        """
        # 从配置获取默认音色
        default_voice = getattr(self.config, 'tts_default_voice', 'Kai')
        
        if not voice:
            logger.warning(f"音色为空，使用默认音色: {default_voice}")
            return default_voice
        
        # 转换为小写进行检查
        voice_lower = voice.lower()
        
        # 检查是否在支持列表中
        if voice_lower not in VALID_QWEN_VOICES:
            logger.warning(
                f"不支持的音色 '{voice}'，使用默认音色: {default_voice}。"
                f"支持的音色: {', '.join(sorted(VALID_QWEN_VOICES))}"
            )
            return default_voice
        
        # Qwen TTS 使用首字母大写的格式
        return voice.capitalize()
    
    def preprocess_text(
        self,
        text: str,
        skip_code_blocks: bool = True
    ) -> str:
        """
        清理和准备文本用于 TTS
        
        处理步骤：
        1. 去除 HTML 标签
        2. 去除 Markdown 格式
        3. 处理代码块（跳过或转换为纯文本）
        4. 规范化空白字符
        5. 去除特殊字符
        
        Args:
            text: 原始文本
            skip_code_blocks: 是否跳过代码块
            
        Returns:
            清理后的纯文本
        """
        if not text or not text.strip():
            return ""
        
        # 1. 去除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 2. 去除 Markdown 代码块
        if skip_code_blocks:
            # 去除代码块 ```...```
            text = re.sub(r'```[\s\S]*?```', '', text)
            # 去除行内代码 `...`
            text = re.sub(r'`[^`]+`', '', text)
        
        # 3. 去除 Markdown 格式
        # 粗体 **text** 或 __text__
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        
        # 斜体 *text* 或 _text_
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # 标题 # text
        text = re.sub(r'#+\s+', '', text)
        
        # 链接 [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # 图片 ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
        
        # 列表标记
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # 4. 规范化空白字符
        # 将多个空白字符替换为单个空格
        text = re.sub(r'\s+', ' ', text)
        
        # 去除首尾空白
        text = text.strip()
        
        return text

    def chunk_text(
        self,
        text: str,
        max_chars: int = 600
    ) -> list[str]:
        """
        将长文本分割成多个块
        
        按句子边界分割，确保每块不超过最大字符数
        
        Args:
            text: 要分割的文本
            max_chars: 每块最大字符数
            
        Returns:
            文本块列表
        """
        if len(text) <= max_chars:
            return [text]
        
        # 句子分隔符（中英文）
        sentence_endings = r'[。！？\.!?]+'
        
        # 按句子分割
        sentences = re.split(f'({sentence_endings})', text)
        
        # 重新组合句子和标点
        combined_sentences = []
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            punctuation = sentences[i + 1] if i + 1 < len(sentences) else ''
            combined_sentences.append(sentence + punctuation)
        
        # 将句子组合成块
        chunks = []
        current_chunk = ""
        
        for sentence in combined_sentences:
            # 如果单个句子就超过限制，强制分割
            if len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # 按字符强制分割
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
            
            # 如果添加这个句子会超过限制
            elif len(current_chunk) + len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            
            # 否则添加到当前块
            else:
                current_chunk += sentence
        
        # 添加最后一块
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.info(f"文本分块完成: {len(text)} 字符 -> {len(chunks)} 块")
        return chunks
    
    def calculate_hash(
        self,
        text: str,
        voice: str,
        language: str
    ) -> str:
        """
        计算文本、音色和语言的唯一哈希值
        
        用于缓存键生成
        
        Args:
            text: 文本内容
            voice: 音色名称
            language: 语言类型
            
        Returns:
            16 字符的哈希字符串
        """
        content = f"{text}|{voice}|{language}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        return hash_obj.hexdigest()[:16]
    
    async def generate_audio_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        skip_code_blocks: bool = True
    ) -> AsyncGenerator[bytes, None]:
        """
        生成音频流
        
        Args:
            text: 原始文本
            voice: 音色名称，None 则使用配置默认值
            language: 语言类型，None 则使用配置默认值
            skip_code_blocks: 是否跳过代码块
            
        Yields:
            bytes: Base64 编码的 PCM 音频数据块
            
        Raises:
            ValueError: 文本为空或无效
            APIError: API 调用失败
        """
        # 从配置获取默认值
        voice = voice or getattr(self.config, 'tts_default_voice', 'Kai')
        language = language or getattr(self.config, 'tts_default_language', 'Chinese')
        
        # 验证并规范化音色
        voice = self.validate_voice(voice)
        
        # 预处理文本
        cleaned_text = self.preprocess_text(text, skip_code_blocks)
        
        if not cleaned_text:
            raise ValueError("预处理后的文本为空")
        
        logger.info(f"开始生成音频流，文本长度: {len(cleaned_text)}，音色: {voice}")
        
        # 如果文本超过限制，分块处理
        max_chars = self.config.max_output_tokens
        if len(cleaned_text) > max_chars:
            chunks = self.chunk_text(cleaned_text, max_chars)
            logger.info(f"文本过长，分为 {len(chunks)} 块处理")
            
            for i, chunk in enumerate(chunks):
                logger.info(f"处理第 {i + 1}/{len(chunks)} 块")
                async for audio_chunk in self.client.generate_tts_stream(
                    chunk, voice, language
                ):
                    yield audio_chunk
        else:
            # 直接生成
            async for audio_chunk in self.client.generate_tts_stream(
                cleaned_text, voice, language
            ):
                yield audio_chunk
    
    async def generate_audio(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        skip_code_blocks: bool = True
    ) -> bytes:
        """
        生成完整音频
        
        Args:
            text: 原始文本
            voice: 音色名称，None 则使用配置默认值
            language: 语言类型，None 则使用配置默认值
            skip_code_blocks: 是否跳过代码块
            
        Returns:
            bytes: 完整的音频数据
            
        Raises:
            ValueError: 文本为空或无效
            APIError: API 调用失败
        """
        chunks = []
        async for chunk in self.generate_audio_stream(
            text, voice, language, skip_code_blocks
        ):
            chunks.append(chunk)
        
        complete_audio = b''.join(chunks)
        logger.info(f"音频生成完成，总大小: {len(complete_audio)} bytes")
        
        return complete_audio
