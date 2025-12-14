"""Document management routes"""

import logging
import urllib.parse
import shutil
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse, Response

from reinvent_insight.core import config
from reinvent_insight.api.routes.auth import verify_token
from reinvent_insight.core.utils.file_utils import generate_doc_hash, is_pdf_document, get_source_identifier

# Import from new modules
from reinvent_insight.services.document.hash_registry import (
    hash_to_filename,
    hash_to_versions,
    filename_to_hash,
    init_hash_mappings,
)
from reinvent_insight.services.document.metadata_service import (
    parse_metadata_from_md,
    extract_text_from_markdown,
    count_chinese_words,
    clean_content_metadata,
    discover_versions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/public/summaries")
async def list_public_summaries():
    """获取所有已生成的摘要文件列表供公开展示，无需认证。
    
    使用内存缓存，响应速度显著提升。
    """
    try:
        from reinvent_insight.services.document.summary_cache import get_summary_cache
        
        cache = get_summary_cache()
        summaries = cache.get_all_summaries(sort_by="upload_date", reverse=True)
        
        return {
            "summaries": summaries,
            "cache_version": cache.cache_version
        }
    except Exception as e:
        logger.error(f"获取公共摘要列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取公共摘要列表失败")


@router.get("/public/summaries/paginated")
async def list_public_summaries_paginated(
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "upload_date"
):
    """获取分页的摘要文件列表
    
    Args:
        page: 页码（从 1 开始），默认 1
        page_size: 每页数量，默认 50，最大 100
        sort_by: 排序字段 (upload_date|modified_at|title)
    
    Returns:
        分页后的文档列表，包含总数和分页信息
    """
    try:
        from reinvent_insight.services.document.summary_cache import get_summary_cache
        
        # 参数校验
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 50
        if page_size > 100:
            page_size = 100
        if sort_by not in ("upload_date", "modified_at", "title"):
            sort_by = "upload_date"
        
        cache = get_summary_cache()
        result = cache.get_paginated_summaries(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            reverse=True
        )
        
        return result
    except Exception as e:
        logger.error(f"获取分页摘要列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取分页摘要列表失败")


@router.get("/public/cache-info")
async def get_cache_info():
    """获取缓存状态信息（用于前端判断是否需要刷新）"""
    try:
        from reinvent_insight.services.document.summary_cache import get_summary_cache
        
        cache = get_summary_cache()
        return cache.get_cache_info()
    except Exception as e:
        logger.error(f"获取缓存信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取缓存信息失败")


@router.get("/public/summary/{video_id}")
async def check_summary_by_video_id(video_id: str):
    """根据 YouTube video_id 查询是否存在已解析的深度解读。"""
    import re
    
    if not video_id or not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        return {
            "exists": False,
            "hash": None,
            "title": None,
            "error": "无效的 video_id 格式"
        }
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    doc_hash = generate_doc_hash(video_url)
    
    if not doc_hash:
        return {"exists": False, "hash": None, "title": None}
    
    filename = hash_to_filename.get(doc_hash)
    if not filename:
        return {"exists": False, "hash": None, "title": None}
    
    try:
        file_path = config.OUTPUT_DIR / filename
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            title = metadata.get("title_cn") or metadata.get("title_en") or metadata.get("title", "")
            
            return {"exists": True, "hash": doc_hash, "title": title, "filename": filename}
    except Exception as e:
        logger.warning(f"读取文档 {filename} 失败: {e}")
    
    return {"exists": False, "hash": None, "title": None, "filename": None}


@router.get("/public/summaries/{filename}")
async def get_public_summary(filename: str):
    """获取指定摘要文件的公开内容，无需认证。"""
    try:
        filename = urllib.parse.unquote(filename)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
            
        if not filename.endswith(".md"):
            filename += ".md"
            
        file_path = config.OUTPUT_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="摘要文件未找到")
        
        content = file_path.read_text(encoding="utf-8")
        metadata = parse_metadata_from_md(content)
        
        title_cn = metadata.get("title_cn")
        title_en = metadata.get("title_en", metadata.get("title", ""))
        
        if not title_cn:
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith('# '):
                    title_cn = stripped[2:].strip()
                    break
        
        if not title_cn:
            title_cn = title_en if title_en else file_path.stem

        video_url = metadata.get("video_url", "")
        content_identifier = metadata.get("content_identifier", "")
        
        # 兼容处理：旧文档可能将文档标识符存储在 video_url 中
        # 如果 video_url 是文档格式（pdf://, txt://, md://, docx://），则转移到 content_identifier
        if video_url and "://" in video_url and not video_url.startswith(("http://", "https://")):
            # 这是文档标识符，不是视频 URL
            if not content_identifier:
                content_identifier = video_url
            video_url = ""  # 前端不应该看到这个值
        
        source_id = content_identifier or video_url
        versions = []
        if source_id:
            versions = discover_versions(source_id, config.OUTPUT_DIR)

        cleaned_content = clean_content_metadata(content, title_cn)

        return {
            "filename": filename,
            "title": title_cn,
            "title_cn": title_cn,
            "title_en": title_en,
            "content": cleaned_content,
            "video_url": video_url,
            "content_identifier": content_identifier,
            "versions": versions
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取公共摘要文件 '{filename}' 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="读取摘要文件失败")


@router.get("/public/doc/{doc_hash}")
async def get_public_summary_by_hash(doc_hash: str):
    """通过统一hash获取指定摘要文件的公开内容。
    
    返回完整文档信息包括:
    - filename: 文件名
    - content: 文档内容
    - title_cn/title_en: 标题
    - video_url: 视频链接
    - versions: 版本列表
    
    外部系统可只使用 filename 字段。
    """
    filename = hash_to_filename.get(doc_hash)
    if not filename:
        raise HTTPException(status_code=404, detail="文档未找到")
    
    return await get_public_summary(filename)
