"""TTS预生成管理路由"""

import logging
from fastapi import APIRouter, HTTPException

from reinvent_insight.core import config
from reinvent_insight.api.schemas.tts import (
    TTSPregenerateRequest,
    TTSPregenerateResponse,
)
from reinvent_insight.services.tts_text_preprocessor import TTSTextPreprocessor
from reinvent_insight.services.tts_pregeneration_service import TTSPregenerationService
from reinvent_insight.services.document.hash_registry import hash_to_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])

# 服务实例（延迟初始化）
_tts_preprocessor = None
_tts_pregeneration_service = None


def get_tts_preprocessor() -> TTSTextPreprocessor:
    """获取TTS文本预处理器实例（单例）"""
    global _tts_preprocessor
    if _tts_preprocessor is None:
        _tts_preprocessor = TTSTextPreprocessor()
    return _tts_preprocessor


def get_tts_pregeneration_service() -> TTSPregenerationService:
    """获取TTS预生成服务实例"""
    global _tts_pregeneration_service
    if _tts_pregeneration_service is None:
        from reinvent_insight.services.tts_service import TTSService
        from reinvent_insight.services.audio_cache import AudioCache
        from reinvent_insight.infrastructure.ai.model_config import get_model_client
        
        client = get_model_client("text_to_speech")
        tts_service = TTSService(client)
        
        cache_dir = config.PROJECT_ROOT / "downloads" / "tts_cache"
        audio_cache = AudioCache(cache_dir, max_size_mb=500)
        preprocessor = get_tts_preprocessor()
        
        _tts_pregeneration_service = TTSPregenerationService(
            tts_service, audio_cache, preprocessor
        )
    return _tts_pregeneration_service


@router.post("/pregenerate", response_model=TTSPregenerateResponse)
async def trigger_tts_pregeneration(req: TTSPregenerateRequest):
    """
    手动触发TTS预生成
    
    Args:
        req: 请求对象，可以包含filename或article_hash
        
    Returns:
        任务信息
    """
    try:
        # 通过article_hash查找文件
        if req.article_hash:
            found_file = hash_to_filename.get(req.article_hash)
            
            if not found_file:
                raise HTTPException(
                    status_code=404, 
                    detail=f"找不到article_hash对应的文件: {req.article_hash}"
                )
            
            pregeneration_service = get_tts_pregeneration_service()
            task_id = await pregeneration_service.add_task(req.article_hash, found_file)
            
            if task_id:
                return TTSPregenerateResponse(
                    task_id=task_id,
                    status="queued",
                    message=f"任务已添加到队列: {task_id}"
                )
            else:
                return TTSPregenerateResponse(
                    status="skipped",
                    message="任务已存在或音频已缓存"
                )
        
        # 通过filename查找文件（兼容旧的方式）
        elif req.filename:
            file_path = config.OUTPUT_DIR / req.filename
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"文件不存在: {req.filename}")
            
            # 读取文件元数据
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取元数据
            preprocessor = get_tts_preprocessor()
            metadata, _ = preprocessor.extract_yaml_metadata(content)
            
            video_url = metadata.get('video_url', '')
            title = metadata.get('title', '')
            upload_date = metadata.get('upload_date', '')
            
            if not any([video_url, title]):
                raise HTTPException(status_code=400, detail="文件缺少必要的元数据")
            
            # 计算article_hash
            article_hash = preprocessor.calculate_article_hash(video_url, title, upload_date)
            
            # 添加任务
            pregeneration_service = get_tts_pregeneration_service()
            task_id = await pregeneration_service.add_task(article_hash, req.filename)
            
            if task_id:
                return TTSPregenerateResponse(
                    task_id=task_id,
                    status="queued",
                    message=f"任务已添加到队列: {task_id}"
                )
            else:
                return TTSPregenerateResponse(
                    status="skipped",
                    message="任务已存在或音频已缓存"
                )
        else:
            raise HTTPException(status_code=400, detail="必须提供filename或article_hash")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发TTS预生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"触发预生成失败: {str(e)}")
