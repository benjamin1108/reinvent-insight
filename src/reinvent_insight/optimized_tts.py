"""
优化的 Gemini TTS 实现
使用真正的流式 API 和并发处理来大幅提升性能
"""

import asyncio
import logging
import base64
import re
from typing import AsyncGenerator, List, Tuple
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Gemini TTS 支持的音色列表
VALID_VOICES = {
    'achernar', 'achird', 'algenib', 'algieba', 'alnilam', 'aoede', 'autonoe',
    'callirrhoe', 'charon', 'despina', 'enceladus', 'erinome', 'fenrir',
    'gacrux', 'iapetus', 'kore', 'laomedeia', 'leda', 'orus', 'puck',
    'pulcherrima', 'rasalgethi', 'sadachbia', 'sadaltager', 'schedar',
    'sulafat', 'umbriel', 'vindemiatrix', 'zephyr', 'zubenelgenubi'
}

DEFAULT_VOICE = 'kore'


class OptimizedGeminiTTS:
    """优化的 Gemini TTS 客户端"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp-audio"):
        """
        初始化 TTS 客户端
        
        Args:
            api_key: Gemini API 密钥
            model: 模型名称（必须是支持 TTS 的模型，如 gemini-2.0-flash-exp-audio）
        """
        self.api_key = api_key
        self.model = model
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # 导入 SDK
        try:
            from google import genai
            from google.genai import types
            self.genai = genai
            self.types = types
            logger.info("✅ google-genai SDK 已加载")
        except ImportError:
            raise ImportError(
                "需要安装 google-genai SDK: pip install google-genai"
            )
    
    def validate_voice(self, voice: str) -> str:
        """验证并规范化音色"""
        if not voice:
            return DEFAULT_VOICE
        voice_lower = voice.lower()
        if voice_lower not in VALID_VOICES:
            logger.warning(f"不支持的音色 '{voice}'，使用默认: {DEFAULT_VOICE}")
            return DEFAULT_VOICE
        return voice_lower
    
    def smart_chunk_text(self, text: str, max_chars: int = 800) -> List[str]:
        """
        智能分块：按句子边界分割，避免截断
        
        Args:
            text: 输入文本
            max_chars: 每块最大字符数
            
        Returns:
            文本块列表
        """
        if len(text) <= max_chars:
            return [text]
        
        # 句子分隔符（中英文）
        sentence_pattern = r'([。！？\.!?]+)'
        parts = re.split(sentence_pattern, text)
        
        # 重新组合句子和标点
        sentences = []
        for i in range(0, len(parts), 2):
            sentence = parts[i]
            punct = parts[i + 1] if i + 1 < len(parts) else ''
            if sentence.strip():
                sentences.append(sentence + punct)
        
        # 组合成块
        chunks = []
        current = ""
        
        for sentence in sentences:
            # 单句超长，强制分割
            if len(sentence) > max_chars:
                if current:
                    chunks.append(current.strip())
                    current = ""
                # 按字符强制分割
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
            # 添加后会超长
            elif len(current) + len(sentence) > max_chars:
                if current:
                    chunks.append(current.strip())
                current = sentence
            # 正常添加
            else:
                current += sentence
        
        if current:
            chunks.append(current.strip())
        
        logger.info(f"📝 文本分块: {len(text)} 字符 → {len(chunks)} 块")
        return chunks
    
    async def stream_tts_chunk(
        self,
        text: str,
        voice: str = "kore",
        chunk_index: int = 0
    ) -> AsyncGenerator[Tuple[int, bytes], None]:
        """
        流式生成单个文本块的音频（使用真正的流式 API）
        
        Args:
            text: 文本内容
            voice: 音色
            chunk_index: 块索引（用于排序）
            
        Yields:
            (chunk_index, audio_data): 块索引和音频数据
        """
        voice = self.validate_voice(voice)
        
        logger.info(f"🎵 开始流式生成块 {chunk_index}: {len(text)} 字符")
        
        try:
            loop = asyncio.get_event_loop()
            
            def _stream_call():
                """同步调用流式 API"""
                client = self.genai.Client(api_key=self.api_key)
                
                # 使用流式 API
                response_stream = client.models.generate_content_stream(
                    model=self.model,
                    contents=text,
                    config=self.types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=self.types.SpeechConfig(
                            voice_config=self.types.VoiceConfig(
                                prebuilt_voice_config=self.types.PrebuiltVoiceConfig(
                                    voice_name=voice
                                )
                            )
                        )
                    )
                )
                
                # 收集所有流式块
                audio_chunks = []
                for chunk in response_stream:
                    if chunk.candidates:
                        for part in chunk.candidates[0].content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                audio_chunks.append(part.inline_data.data)
                
                return audio_chunks
            
            # 在线程池中执行
            audio_chunks = await loop.run_in_executor(self._executor, _stream_call)
            
            # 逐块返回
            for audio_data in audio_chunks:
                if isinstance(audio_data, str):
                    pcm_data = base64.b64decode(audio_data)
                else:
                    pcm_data = audio_data
                
                # 编码为 Base64 返回
                b64_data = base64.b64encode(pcm_data).decode('utf-8')
                yield (chunk_index, b64_data.encode('utf-8'))
            
            logger.info(f"✅ 块 {chunk_index} 完成: {len(audio_chunks)} 个音频片段")
            
        except Exception as e:
            logger.error(f"❌ 块 {chunk_index} 生成失败: {e}")
            raise
    
    async def stream_tts_optimized(
        self,
        text: str,
        voice: str = "kore",
        max_chunk_size: int = 800,
        max_concurrent: int = 3
    ) -> AsyncGenerator[bytes, None]:
        """
        优化的流式 TTS：分块 + 并发 + 流式
        
        策略：
        1. 将长文本智能分块（按句子边界）
        2. 并发请求多个块（控制并发数）
        3. 按顺序返回音频数据
        
        Args:
            text: 输入文本
            voice: 音色
            max_chunk_size: 每块最大字符数
            max_concurrent: 最大并发请求数
            
        Yields:
            bytes: Base64 编码的音频数据
        """
        voice = self.validate_voice(voice)
        
        # 分块
        chunks = self.smart_chunk_text(text, max_chunk_size)
        
        if len(chunks) == 1:
            # 单块，直接流式处理
            logger.info("📦 单块处理，使用流式 API")
            async for _, audio_data in self.stream_tts_chunk(chunks[0], voice, 0):
                yield audio_data
            return
        
        # 多块，并发处理
        logger.info(f"📦 多块处理: {len(chunks)} 块，并发数: {max_concurrent}")
        
        # 创建任务队列
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}  # {chunk_index: [audio_data, ...]}
        
        async def process_chunk(idx: int, chunk_text: str):
            """处理单个块"""
            async with semaphore:
                results[idx] = []
                async for _, audio_data in self.stream_tts_chunk(chunk_text, voice, idx):
                    results[idx].append(audio_data)
        
        # 启动所有任务
        tasks = [
            asyncio.create_task(process_chunk(i, chunk))
            for i, chunk in enumerate(chunks)
        ]
        
        # 按顺序返回结果
        for i in range(len(chunks)):
            # 等待当前块完成
            await tasks[i]
            
            # 返回当前块的所有音频数据
            if i in results:
                for audio_data in results[i]:
                    yield audio_data
                # 释放内存
                del results[i]
        
        logger.info("🎉 所有块处理完成")
    
    async def generate_wav_file(
        self,
        text: str,
        output_path: str,
        voice: str = "kore"
    ) -> str:
        """
        生成完整的 WAV 文件
        
        Args:
            text: 输入文本
            output_path: 输出文件路径
            voice: 音色
            
        Returns:
            输出文件路径
        """
        import wave
        
        voice = self.validate_voice(voice)
        logger.info(f"💾 生成 WAV 文件: {output_path}")
        
        # 收集所有音频数据
        pcm_chunks = []
        async for b64_data in self.stream_tts_optimized(text, voice):
            pcm_data = base64.b64decode(b64_data)
            pcm_chunks.append(pcm_data)
        
        # 合并所有 PCM 数据
        full_pcm = b''.join(pcm_chunks)
        
        # 写入 WAV 文件
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)      # 单声道
            wf.setsampwidth(2)      # 16-bit
            wf.setframerate(24000)  # 24kHz
            wf.writeframes(full_pcm)
        
        logger.info(f"✅ WAV 文件已保存: {output_path} ({len(full_pcm)} bytes)")
        return output_path
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


# ============================================================================
# 使用示例
# ============================================================================

async def example_streaming():
    """示例：流式播放"""
    import os
    
    api_key = os.getenv("GEMINI_API_KEY")
    tts = OptimizedGeminiTTS(api_key)
    
    text = "这是一个测试。" * 100  # 长文本
    
    print("🎵 开始流式生成...")
    chunk_count = 0
    async for audio_chunk in tts.stream_tts_optimized(text, voice="kore"):
        chunk_count += 1
        print(f"📦 收到音频块 {chunk_count}: {len(audio_chunk)} bytes")
    
    print(f"✅ 完成！共 {chunk_count} 个音频块")


async def example_save_file():
    """示例：保存 WAV 文件"""
    import os
    
    api_key = os.getenv("GEMINI_API_KEY")
    tts = OptimizedGeminiTTS(api_key)
    
    text = "人工智能技术正在快速发展。" * 50
    
    output_file = await tts.generate_wav_file(
        text=text,
        output_path="output_optimized.wav",
        voice="kore"
    )
    
    print(f"✅ 文件已保存: {output_file}")


if __name__ == "__main__":
    # 测试流式
    asyncio.run(example_streaming())
    
    # 测试保存文件
    # asyncio.run(example_save_file())
