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
from reinvent_insight.core.utils.file_utils import generate_doc_hash, is_pdf_document

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
    """获取所有已生成的摘要文件列表供公开展示，无需认证。"""
    try:
        summaries = []
        video_url_map = {}
        
        if config.OUTPUT_DIR.exists():
            for md_file in config.OUTPUT_DIR.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
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
                        title_cn = title_en if title_en else md_file.stem
                    
                    doc_hash = filename_to_hash.get(md_file.name)
                    if not doc_hash:
                        continue
                    
                    pure_text = extract_text_from_markdown(content)
                    word_count = count_chinese_words(pure_text)
                    stat = md_file.stat()
                    
                    # 检查是否为PDF文档
                    video_url = metadata.get("video_url", "")
                    is_pdf = is_pdf_document(video_url)
                    
                    # 优先级：metadata的created_at > metadata的upload_date > 文件系统时间
                    created_at_value = stat.st_ctime
                    modified_at_value = stat.st_mtime
                    
                    if metadata.get("created_at"):
                        try:
                            dt = datetime.fromisoformat(metadata.get("created_at").replace('Z', '+00:00'))
                            created_at_value = dt.timestamp()
                            modified_at_value = created_at_value
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"解析文件 {md_file.name} 的created_at失败: {e}")
                    elif metadata.get("upload_date"):
                        try:
                            upload_date_str = str(metadata.get("upload_date")).replace('-', '')
                            if len(upload_date_str) == 8:
                                year = int(upload_date_str[0:4])
                                month = int(upload_date_str[4:6])
                                day = int(upload_date_str[6:8])
                                dt = datetime(year, month, day)
                                created_at_value = dt.timestamp()
                                modified_at_value = created_at_value
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"解析文件 {md_file.name} 的upload_date失败: {e}")
                    
                    summary_data = {
                        "filename": md_file.name,
                        "title_cn": title_cn,
                        "title_en": title_en,
                        "size": stat.st_size,
                        "word_count": word_count,
                        "created_at": created_at_value,
                        "modified_at": modified_at_value,
                        "upload_date": metadata.get("upload_date", "1970-01-01"),
                        "video_url": video_url,
                        "is_reinvent": metadata.get("is_reinvent", False),
                        "course_code": metadata.get("course_code"),
                        "level": metadata.get("level"),
                        "hash": doc_hash,
                        "version": metadata.get("version", 0),
                        "is_pdf": is_pdf,
                        "content_type": "PDF文档" if is_pdf else "YouTube视频"
                    }
                    
                    if video_url:
                        if video_url not in video_url_map:
                            video_url_map[video_url] = summary_data
                        else:
                            existing_version = video_url_map[video_url].get("version", 0)
                            new_version = summary_data.get("version", 0)
                            if new_version > existing_version:
                                video_url_map[video_url] = summary_data
                        
                except Exception as e:
                    logger.warning(f"处理文件 {md_file.name} 时出错: {e}")
        
        summaries.extend(video_url_map.values())
        summaries.sort(key=lambda x: x.get("upload_date", "1970-01-01"), reverse=True)
        return {"summaries": summaries}
    except Exception as e:
        logger.error(f"获取公共摘要列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取公共摘要列表失败")


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
        versions = []
        if video_url:
            versions = discover_versions(video_url, config.OUTPUT_DIR)

        cleaned_content = clean_content_metadata(content, title_cn)

        return {
            "filename": filename,
            "title": title_cn,
            "title_cn": title_cn,
            "title_en": title_en,
            "content": cleaned_content,
            "video_url": video_url,
            "versions": versions
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取公共摘要文件 '{filename}' 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="读取摘要文件失败")


@router.get("/public/doc/{doc_hash}")
async def get_public_summary_by_hash(doc_hash: str):
    """通过统一hash获取文档信息。"""
    filename = hash_to_filename.get(doc_hash)
    if not filename:
        raise HTTPException(status_code=404, detail="文档未找到")
    
    return {"filename": filename}
