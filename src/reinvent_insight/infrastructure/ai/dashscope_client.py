"""DashScope (阿里云通义千问) 模型客户端实现"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .config_models import ModelConfig, ConfigurationError, APIError
from .base_client import BaseModelClient

logger = logging.getLogger(__name__)


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

