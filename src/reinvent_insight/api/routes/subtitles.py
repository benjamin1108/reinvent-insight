"""Subtitle API routes - 提供视频字幕获取和翻译接口"""

import logging
import re
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from reinvent_insight.core import config
from reinvent_insight.core.utils.file_utils import generate_doc_hash
from reinvent_insight.infrastructure.media.youtube_downloader import SubtitleDownloader
from reinvent_insight.services.document.hash_registry import hash_to_filename
from reinvent_insight.services.subtitle_translation_service import (
    get_cached_translation, 
    is_translating, 
    trigger_subtitle_translation
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["subtitles"])


async def _get_article_content_by_video_id(video_id: str) -> Optional[str]:
    """
    根据 video_id 获取解读文章内容
    
    Args:
        video_id: YouTube 视频 ID
        
    Returns:
        文章内容，如果不存在则返回 None
    """
    try:
        # 根据 video_id 生成 doc_hash
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        doc_hash = generate_doc_hash(video_url)
        
        if not doc_hash:
            return None
        
        # 查找文件名
        filename = hash_to_filename.get(doc_hash)
        if not filename:
            return None
        
        # 读取文章内容
        file_path = config.OUTPUT_DIR / filename
        if not file_path.exists():
            return None
        
        content = file_path.read_text(encoding="utf-8")
        
        # 移除 YAML front matter，只保留正文
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        
        return content
        
    except Exception as e:
        logger.warning(f"获取文章内容失败 video_id={video_id}: {e}")
        return None


@router.get("/public/subtitle/{video_id}")
async def get_subtitle_by_video_id(video_id: str, lang: Optional[str] = None):
    """
    根据 YouTube video_id 获取 VTT 字幕内容。
    
    Args:
        video_id: YouTube 视频 ID（11位字符）
        lang: 可选，指定语言代码（如 'en', 'zh-Hans'）
        
    Returns:
        VTT 字幕内容（原始格式，便于前端解析时间轴）
    """
    # 验证 video_id 格式
    if not video_id or not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        raise HTTPException(status_code=400, detail="无效的 video_id 格式")
    
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # 使用 SubtitleDownloader 获取元数据
        loop = asyncio.get_running_loop()
        dl = SubtitleDownloader(video_url)
        
        # 获取元数据（在线程池中执行，避免阻塞）
        success = await loop.run_in_executor(None, dl._fetch_metadata)
        if not success or not dl.metadata:
            raise HTTPException(status_code=404, detail="无法获取视频元数据")
        
        sanitized_title = dl.metadata.sanitized_title
        
        # 查找 VTT 字幕文件
        possible_langs = ['en', 'en-US', 'en-GB', 'zh-Hans', 'zh-CN', 'zh']
        
        # 如果指定了语言，优先查找
        if lang:
            possible_langs = [lang] + [l for l in possible_langs if l != lang]
        
        vtt_path = None
        found_lang = None
        
        for search_lang in possible_langs:
            path = config.SUBTITLE_DIR / f"{sanitized_title}.{search_lang}.vtt"
            if path.exists():
                vtt_path = path
                found_lang = search_lang
                break
        
        if not vtt_path:
            # 字幕文件不存在，尝试下载
            logger.info(f"字幕文件不存在，尝试下载: video_id={video_id}")
            _, _, error = await loop.run_in_executor(None, dl.download)
            
            if error:
                raise HTTPException(
                    status_code=404, 
                    detail=f"字幕下载失败: {error.message}"
                )
            
            # 再次查找
            for search_lang in possible_langs:
                path = config.SUBTITLE_DIR / f"{sanitized_title}.{search_lang}.vtt"
                if path.exists():
                    vtt_path = path
                    found_lang = search_lang
                    break
        
        if not vtt_path or not vtt_path.exists():
            raise HTTPException(status_code=404, detail="未找到字幕文件")
        
        # 读取 VTT 内容
        vtt_content = vtt_path.read_text(encoding="utf-8")
        
        logger.info(f"返回字幕: video_id={video_id}, lang={found_lang}")
        
        return {
            "video_id": video_id,
            "lang": found_lang,
            "vtt": vtt_content,
            "translated": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取字幕失败 video_id={video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取字幕失败: {str(e)}")


@router.get("/public/subtitle/{video_id}/translated")
async def get_translated_subtitle(video_id: str, force: bool = False):
    """
    查询翻译后的中文字幕（非阻塞）。
    
    - 有缓存 → 立即返回
    - 正在翻译中 → 返回 generating: true
    - 未开始 → 触发后台翻译，返回 generating: true
    
    Args:
        video_id: YouTube 视频 ID（11位字符）
        force: 是否强制重新翻译（忽略缓存）
    """
    # 验证 video_id 格式
    if not video_id or not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        raise HTTPException(status_code=400, detail="无效的 video_id 格式")
    
    try:
        # 检查翻译缓存
        if not force:
            cached_vtt = get_cached_translation(video_id)
            if cached_vtt:
                logger.info(f"使用缓存的翻译字幕: video_id={video_id}")
                return {
                    "video_id": video_id,
                    "lang": "zh",
                    "vtt": cached_vtt,
                    "translated": True,
                    "cached": True,
                    "generating": False
                }
        
        # 检查是否正在翻译中
        if is_translating(video_id):
            logger.info(f"字幕正在翻译中: video_id={video_id}")
            return {
                "video_id": video_id,
                "translated": False,
                "generating": True,
                "message": "字幕正在翻译中，请稍后重试"
            }
        
        # 获取解读文章内容
        article_content = await _get_article_content_by_video_id(video_id)
        
        # 触发后台翻译任务
        asyncio.create_task(trigger_subtitle_translation(video_id, article_content, force))
        
        return {
            "video_id": video_id,
            "translated": False,
            "generating": True,
            "message": "已触发字幕翻译，请稍后重试"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取翻译字幕失败 video_id={video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"翻译字幕失败: {str(e)}")
