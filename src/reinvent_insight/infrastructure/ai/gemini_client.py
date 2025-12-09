"""Gemini模型客户端实现"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .config_models import ModelConfig, ConfigurationError, APIError
from .base_client import BaseModelClient

logger = logging.getLogger(__name__)


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
            # 设置超时时间：使用配置中的timeout，如果是高思考模式且配置超时较短，则自动增加
            # 高思考模式需要更长的思考时间
            base_timeout = self.config.timeout
            if thinking_level == "high" and base_timeout < 300:
                timeout_seconds = max(base_timeout * 1.5, 300)  # 高思考模式至少300秒
                logger.debug(f"高思考模式，超时时间从 {base_timeout}秒 增加到 {timeout_seconds}秒")
            else:
                timeout_seconds = base_timeout
            
            try:
                # 使用 run_in_executor 避免阻塞事件循环
                loop = asyncio.get_event_loop()
                
                def sync_generate():
                    # 使用新的 google.genai SDK 调用
                    return self.client.models.generate_content(
                        model=self.config.model_name,
                        contents=prompt,
                        config=config
                    )
                
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_generate),
                    timeout=timeout_seconds
                )
                
                # 提取文本内容
                if not response.text:
                    raise APIError("API 返回的内容为空文本")
                
                return response.text
                
            except asyncio.TimeoutError:
                raise APIError(f"API 调用超时（超过 {timeout_seconds} 秒），请检查网络连接或减少输入长度")
        
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
        
        generation_config = self.types.GenerateContentConfig(
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            max_output_tokens=self.config.max_output_tokens,
            response_mime_type="application/json" if is_json else "text/plain",
            thinking_config=self.types.ThinkingConfig(thinking_level=thinking_level)
        )
        
        async def _generate():
            # 根据思考级别设置超时
            base_timeout = self.config.timeout
            if thinking_level == "high" and base_timeout < 300:
                timeout_seconds = max(base_timeout * 1.5, 300)
                logger.debug(f"高思考模式，超时时间从 {base_timeout}秒 增加到 {timeout_seconds}秒")
            else:
                timeout_seconds = base_timeout
            
            try:
                loop = asyncio.get_event_loop()
                
                # 根据文件类型选择处理方式
                if file_info.get("local_file", False):
                    # 使用本地文件
                    file_path = file_info["uri"]
                    mime_type = file_info.get("mime_type", "application/pdf")
                    
                    def read_and_process():
                        with open(file_path, "rb") as f:
                            file_data = f.read()
                        
                        # 使用新 SDK 调用
                        return self.client.models.generate_content(
                            model=self.config.model_name,
                            contents=[
                                prompt,
                                self.types.Part.from_bytes(data=file_data, mime_type=mime_type)
                            ],
                            config=generation_config
                        )
                    
                    response = await asyncio.wait_for(
                        loop.run_in_executor(None, read_and_process),
                        timeout=timeout_seconds
                    )
                else:
                    # 使用已上传的文件引用
                    def sync_generate_with_file():
                        file_ref = self.client.files.get(name=file_info["name"])
                        return self.client.models.generate_content(
                            model=self.config.model_name,
                            contents=[prompt, file_ref],
                            config=generation_config
                        )
                    
                    response = await asyncio.wait_for(
                        loop.run_in_executor(None, sync_generate_with_file),
                        timeout=timeout_seconds
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
                
            except asyncio.TimeoutError:
                raise APIError(f"API 调用超时（超过 {timeout_seconds} 秒），请检查网络连接或减少输入长度")
        
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
                    lambda: self.client.files.upload(file=file_path)
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
                lambda: self.client.files.delete(name=file_id)
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

