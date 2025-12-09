"""TTS音频生成路由"""

import logging
import base64
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from reinvent_insight.api.schemas.tts import (
    TTSRequest,
    TTSResponse,
    TTSStreamRequest,
)
from reinvent_insight.services.tts_service import TTSService
from reinvent_insight.services.audio_cache import AudioCache
from reinvent_insight.infrastructure.audio.audio_utils import assemble_wav, decode_base64_pcm, calculate_audio_duration
from reinvent_insight.infrastructure.ai.model_config import get_model_client
from reinvent_insight.core import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])

# 服务实例（延迟初始化）
_tts_service: Optional[TTSService] = None
_audio_cache: Optional[AudioCache] = None


def get_tts_service() -> TTSService:
    """获取TTS服务实例（单例）"""
    global _tts_service
    if _tts_service is None:
        client = get_model_client("text_to_speech")
        _tts_service = TTSService(client)
    return _tts_service


def get_audio_cache() -> AudioCache:
    """获取音频缓存实例（单例）"""
    global _audio_cache
    if _audio_cache is None:
        cache_dir = config.PROJECT_ROOT / "downloads" / "tts_cache"
        _audio_cache = AudioCache(cache_dir, max_size_mb=500)
    return _audio_cache


@router.post("/generate", response_model=TTSResponse)
async def generate_tts(req: TTSRequest):
    """
    生成TTS音频（非流式）
    
    检查缓存，如果存在则返回缓存URL，否则生成新音频并缓存
    """
    try:
        tts_service = get_tts_service()
        audio_cache = get_audio_cache()
        
        # 从配置获取默认值
        voice = req.voice or getattr(tts_service.config, 'tts_default_voice', 'Kai')
        language = req.language or getattr(tts_service.config, 'tts_default_language', 'Chinese')
        
        # 计算哈希
        audio_hash = tts_service.calculate_hash(req.text, voice, language)
        
        # 检查缓存
        if req.use_cache:
            cached_path = audio_cache.get(audio_hash)
            if cached_path:
                logger.info(f"TTS缓存命中: {audio_hash}")
                file_size = cached_path.stat().st_size
                duration = calculate_audio_duration(file_size - 44)
                
                return TTSResponse(
                    audio_url=f"/api/tts/cache/{audio_hash}",
                    duration=duration,
                    cached=True,
                    voice=voice,
                    language=language
                )
        
        # 生成音频
        logger.info(f"开始生成TTS音频: {audio_hash}")
        audio_chunks = []
        async for chunk in tts_service.generate_audio_stream(
            req.text, voice, language, req.skip_code_blocks
        ):
            pcm_data = decode_base64_pcm(chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk)
            audio_chunks.append(pcm_data)
        
        # 组装WAV文件
        wav_data = assemble_wav(audio_chunks)
        duration = calculate_audio_duration(len(wav_data) - 44)
        
        # 缓存音频
        text_hash = tts_service.calculate_hash(req.text, "", "")
        audio_cache.put(
            audio_hash=audio_hash,
            audio_data=wav_data,
            text_hash=text_hash,
            voice=voice,
            language=language,
            duration=duration
        )
        
        logger.info(f"TTS音频生成完成: {audio_hash}, 时长: {duration:.2f}s")
        
        return TTSResponse(
            audio_url=f"/api/tts/cache/{audio_hash}",
            duration=duration,
            cached=False,
            voice=voice,
            language=language
        )
        
    except ValueError as e:
        logger.error(f"TTS请求参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TTS生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS生成失败: {str(e)}")


@router.post("/stream")
async def stream_tts(req: TTSStreamRequest):
    """
    流式生成TTS音频（SSE）
    
    实时返回音频块，支持边生成边播放
    """
    article_hash = req.article_hash
    text = req.text
    use_cache = req.use_cache
    skip_code_blocks = req.skip_code_blocks
    
    async def event_generator():
        try:
            tts_service = get_tts_service()
            audio_cache = get_audio_cache()
            
            voice = req.voice or getattr(tts_service.config, 'tts_default_voice', 'Kai')
            language = req.language or getattr(tts_service.config, 'tts_default_language', 'Chinese')
            
            audio_hash = tts_service.calculate_hash(text, voice, language)
            
            # 检查缓存
            if use_cache:
                cached_path = audio_cache.get(audio_hash)
                if cached_path:
                    logger.info(f"TTS缓存命中（流式）: {audio_hash}")
                    file_size = cached_path.stat().st_size
                    duration = calculate_audio_duration(file_size - 44)
                    
                    # 读取缓存的WAV文件并流式发送
                    chunk_size = 48000
                    chunk_index = 0
                    total_bytes = 0
                    
                    with open(cached_path, 'rb') as f:
                        f.seek(44)  # 跳过WAV头
                        
                        while True:
                            pcm_chunk = f.read(chunk_size)
                            if not pcm_chunk:
                                break
                            
                            total_bytes += len(pcm_chunk)
                            chunk_base64 = base64.b64encode(pcm_chunk).decode('utf-8')
                            
                            event_data = {
                                "type": "audio",
                                "data": chunk_base64,
                                "index": chunk_index,
                                "totalBytes": total_bytes,
                                "cached": True
                            }
                            
                            yield f"data: {str(event_data)}\n\n"
                            chunk_index += 1
                    
                    # 发送完成事件
                    yield f"data: {{\"type\": \"end\", \"duration\": {duration}}}\n\n"
                    return
            
            # 生成音频
            logger.info(f"开始流式生成TTS: {audio_hash}")
            audio_chunks = []
            chunk_index = 0
            total_bytes = 0
            
            async for chunk in tts_service.generate_audio_stream(text, voice, language, skip_code_blocks):
                pcm_data = decode_base64_pcm(chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk)
                audio_chunks.append(pcm_data)
                total_bytes += len(pcm_data)
                
                event_data = {
                    "type": "audio",
                    "data": chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk,
                    "index": chunk_index,
                    "totalBytes": total_bytes,
                    "cached": False
                }
                
                yield f"data: {str(event_data)}\n\n"
                chunk_index += 1
            
            # 组装并缓存
            wav_data = assemble_wav(audio_chunks)
            duration = calculate_audio_duration(len(wav_data) - 44)
            
            text_hash = tts_service.calculate_hash(text, "", "")
            audio_cache.put(audio_hash, wav_data, text_hash, voice, language, duration, article_hash)
            
            logger.info(f"流式TTS完成: {audio_hash}, 时长: {duration:.2f}s")
            
            yield f"data: {{\"type\": \"end\", \"duration\": {duration}, \"audioHash\": \"{audio_hash}\"}}\n\n"
            
        except Exception as e:
            logger.error(f"流式TTS失败: {e}", exc_info=True)
            yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
