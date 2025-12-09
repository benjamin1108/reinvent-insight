"""TTS缓存管理路由"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from reinvent_insight.core import config
from reinvent_insight.api.schemas.tts import TTSStatusResponse
from reinvent_insight.services.audio_cache import AudioCache
from reinvent_insight.services.tts_pregeneration_service import TTSPregenerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])

# 服务实例（延迟初始化）
_audio_cache = None
_tts_pregeneration_service = None


def get_audio_cache() -> AudioCache:
    """获取音频缓存实例（单例）"""
    global _audio_cache
    if _audio_cache is None:
        cache_dir = config.PROJECT_ROOT / "downloads" / "tts_cache"
        _audio_cache = AudioCache(cache_dir, max_size_mb=500)
    return _audio_cache


def get_tts_pregeneration_service() -> TTSPregenerationService:
    """获取TTS预生成服务实例"""
    global _tts_pregeneration_service
    if _tts_pregeneration_service is None:
        from reinvent_insight.services.tts_service import TTSService
        from reinvent_insight.services.tts_text_preprocessor import TTSTextPreprocessor
        from reinvent_insight.infrastructure.ai.model_config import get_model_client
        
        client = get_model_client("text_to_speech")
        tts_service = TTSService(client)
        audio_cache = get_audio_cache()
        preprocessor = TTSTextPreprocessor()
        _tts_pregeneration_service = TTSPregenerationService(
            tts_service, audio_cache, preprocessor
        )
    return _tts_pregeneration_service


@router.get("/cache/{audio_hash}")
async def get_cached_audio(audio_hash: str):
    """
    获取缓存的音频文件
    
    返回WAV格式的音频文件
    """
    try:
        audio_cache = get_audio_cache()
        cached_path = audio_cache.get(audio_hash)
        
        if not cached_path:
            raise HTTPException(status_code=404, detail="音频文件不存在")
        
        logger.info(f"返回缓存音频: {audio_hash}")
        
        return FileResponse(
            cached_path,
            media_type="audio/wav",
            filename=f"{audio_hash}.wav",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=31536000",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Length, Content-Range"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存音频失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取音频失败: {str(e)}")


@router.get("/status/{article_hash}", response_model=TTSStatusResponse)
async def get_tts_status(article_hash: str):
    """
    查询文章的TTS音频状态
    
    Args:
        article_hash: 文章哈希值
        
    Returns:
        音频状态信息
    """
    try:
        audio_cache = get_audio_cache()
        
        # 查找音频缓存
        audio_metadata = audio_cache.find_by_article_hash(article_hash)
        
        if audio_metadata:
            return TTSStatusResponse(
                has_audio=True,
                audio_url=f"/api/tts/cache/{audio_metadata.hash}",
                duration=audio_metadata.duration,
                status="ready",
                voice=audio_metadata.voice,
                generated_at=audio_metadata.created_at
            )
        
        # 检查是否有处理中的任务
        try:
            pregeneration_service = get_tts_pregeneration_service()
            if pregeneration_service.is_running:
                for task in pregeneration_service.tasks.values():
                    if task.article_hash == article_hash:
                        from reinvent_insight.services.tts_pregeneration_service import TaskStatus
                        if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
                            # 计算进度
                            progress = 0
                            if task.total_chunks > 0:
                                progress = int((task.chunks_generated / task.total_chunks) * 100)
                            elif task.chunks_generated > 0:
                                progress = min(90, 10 + task.chunks_generated)
                            
                            # 检查是否有部分音频
                            partial_info = {}
                            if task.partial_audio_hash:
                                partial_metadata = audio_cache.get_metadata(task.partial_audio_hash)
                                if partial_metadata:
                                    partial_info = {
                                        "has_partial": True,
                                        "partial_url": f"/api/tts/cache/{task.partial_audio_hash}",
                                        "partial_duration": partial_metadata.duration
                                    }
                            
                            return TTSStatusResponse(
                                has_audio=False,
                                status="processing",
                                chunks_generated=task.chunks_generated,
                                total_chunks=task.total_chunks,
                                progress_percent=progress,
                                **partial_info
                            )
        except Exception as e:
            logger.debug(f"检查预生成任务失败: {e}")
        
        # 没有音频
        return TTSStatusResponse(
            has_audio=False,
            status="none"
        )
        
    except Exception as e:
        logger.error(f"查询TTS状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询状态失败: {str(e)}")


@router.get("/text/{article_hash}")
async def get_tts_text(article_hash: str):
    """
    获取文章的TTS预处理文本
    
    Args:
        article_hash: 文章哈希值
        
    Returns:
        纯文本内容
    """
    try:
        text_file = config.TTS_TEXT_DIR / f"{article_hash}.txt"
        
        if not text_file.exists():
            raise HTTPException(status_code=404, detail="TTS文本不存在")
        
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return Response(
            content=text,
            media_type="text/plain; charset=utf-8"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取TTS文本失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文本失败: {str(e)}")
