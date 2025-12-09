"""Trash management routes"""

import logging
import shutil
from typing import List, Dict
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header

from reinvent_insight.core import config
from reinvent_insight.api.routes.auth import verify_token

# Import from legacy for compatibility
from reinvent_insight.services.document.hash_registry import (
    hash_to_filename,
    hash_to_versions,
    filename_to_hash,
    init_hash_mappings,
)
from reinvent_insight.services.document.metadata_service import (
    parse_metadata_from_md,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["trash"])


@router.delete("/summaries/{doc_hash}")
async def delete_summary(doc_hash: str, authorization: str = Header(None)):
    """
    软删除指定文章(移动到回收站，可恢复)。
    
    移动内容包括:
    - 所有版本的 Markdown 文件
    - 对应的 PDF 文件
    - 可视化解读 HTML 文件
    """
    verify_token(authorization)
    
    # 检查文档是否存在
    versions = hash_to_versions.get(doc_hash, [])
    default_filename = hash_to_filename.get(doc_hash)
    
    if not default_filename and not versions:
        raise HTTPException(status_code=404, detail="文档未找到")
    
    # 创建回收站目录
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    trash_dir.mkdir(exist_ok=True)
    trash_pdf_dir = trash_dir / "pdfs"
    trash_pdf_dir.mkdir(exist_ok=True)
    
    moved_files = []
    errors = []
    
    # 获取要移动的所有文件名(包括所有版本)
    files_to_move = list(versions) if versions else ([default_filename] if default_filename else [])
    
    # 生成删除时间戳，用于避免文件名冲突
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for filename in files_to_move:
        base_name = Path(filename).stem
        
        # 1. 移动 Markdown 文件
        md_path = config.OUTPUT_DIR / filename
        if md_path.exists():
            try:
                # 添加时间戳和 doc_hash 前缀，方便恢复
                trash_filename = f"{doc_hash}_{timestamp}_{filename}"
                trash_path = trash_dir / trash_filename
                shutil.move(str(md_path), str(trash_path))
                moved_files.append(str(trash_path))
                logger.info(f"已移动到回收站: {filename} -> {trash_filename}")
            except Exception as e:
                errors.append(f"移动 {filename} 失败: {str(e)}")
                logger.error(f"移动 Markdown 文件失败: {e}")
        
        # 2. 移动 PDF 文件
        pdf_dir = config.OUTPUT_DIR.parent / "pdfs"
        pdf_filename = filename.replace('.md', '.pdf')
        pdf_path = pdf_dir / pdf_filename
        if pdf_path.exists():
            try:
                trash_pdf_filename = f"{doc_hash}_{timestamp}_{pdf_filename}"
                trash_pdf_path = trash_pdf_dir / trash_pdf_filename
                shutil.move(str(pdf_path), str(trash_pdf_path))
                moved_files.append(str(trash_pdf_path))
                logger.info(f"已移动 PDF 到回收站: {pdf_filename}")
            except Exception as e:
                errors.append(f"移动 PDF {pdf_filename} 失败: {str(e)}")
                logger.error(f"移动 PDF 文件失败: {e}")
        
        # 3. 移动可视化 HTML 文件
        visual_filename = f"{base_name}_visual.html"
        visual_path = config.OUTPUT_DIR / visual_filename
        if visual_path.exists():
            try:
                trash_visual_filename = f"{doc_hash}_{timestamp}_{visual_filename}"
                trash_visual_path = trash_dir / trash_visual_filename
                shutil.move(str(visual_path), str(trash_visual_path))
                moved_files.append(str(trash_visual_path))
                logger.info(f"已移动可视化文件到回收站: {visual_filename}")
            except Exception as e:
                errors.append(f"移动可视化文件 {visual_filename} 失败: {str(e)}")
                logger.error(f"移动可视化文件失败: {e}")
    
    # 4. 更新缓存映射
    if doc_hash in hash_to_filename:
        del hash_to_filename[doc_hash]
    if doc_hash in hash_to_versions:
        del hash_to_versions[doc_hash]
    for filename in files_to_move:
        if filename in filename_to_hash:
            del filename_to_hash[filename]
    
    # 返回结果
    if not moved_files and errors:
        raise HTTPException(status_code=500, detail=f"删除失败: {'; '.join(errors)}")
    
    return {
        "success": True,
        "message": f"已移动 {len(moved_files)} 个文件到回收站",
        "deleted_files": moved_files,
        "errors": errors if errors else None
    }


@router.get("/admin/trash")
async def list_trash(authorization: str = Header(None)):
    """获取回收站中的文章列表(需要认证)"""
    verify_token(authorization)
    
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    if not trash_dir.exists():
        return {"items": []}
    
    items = []
    seen_hashes = {}  # 用于去重，只显示每个 doc_hash 的最新删除记录
    
    for md_file in trash_dir.glob("*.md"):
        try:
            # 解析文件名: {doc_hash}_{timestamp}_{original_filename}
            name_parts = md_file.name.split("_", 2)
            if len(name_parts) >= 3:
                doc_hash_val = name_parts[0]
                timestamp = name_parts[1]
                original_filename = name_parts[2]
            else:
                continue
            
            # 读取元数据
            content = md_file.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            
            title_cn = metadata.get("title_cn", "")
            title_en = metadata.get("title_en", metadata.get("title", ""))
            
            if not title_cn:
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith('# '):
                        title_cn = stripped[2:].strip()
                        break
            
            if not title_cn:
                title_cn = title_en if title_en else md_file.stem
            
            # 解析删除时间
            try:
                deleted_at = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                deleted_at_str = deleted_at.isoformat()
            except:
                deleted_at_str = timestamp
            
            item_data = {
                "doc_hash": doc_hash_val,
                "original_filename": original_filename,
                "trash_filename": md_file.name,
                "title_cn": title_cn,
                "title_en": title_en,
                "deleted_at": deleted_at_str,
                "size": md_file.stat().st_size
            }
            
            # 只保留每个 doc_hash 的最新删除记录
            if doc_hash_val not in seen_hashes or timestamp > seen_hashes[doc_hash_val]["timestamp"]:
                seen_hashes[doc_hash_val] = {"data": item_data, "timestamp": timestamp}
                
        except Exception as e:
            logger.warning(f"解析回收站文件 {md_file.name} 失败: {e}")
    
    # 提取去重后的数据
    items = [v["data"] for v in seen_hashes.values()]
    
    # 按删除时间倒序排序
    items.sort(key=lambda x: x["deleted_at"], reverse=True)
    
    return {"items": items}


@router.post("/admin/trash/{doc_hash}/restore")
async def restore_from_trash(doc_hash: str, authorization: str = Header(None)):
    """从回收站恢复文章(需要认证)"""
    verify_token(authorization)
    
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    trash_pdf_dir = trash_dir / "pdfs"
    
    if not trash_dir.exists():
        raise HTTPException(status_code=404, detail="回收站为空")
    
    restored_files = []
    errors = []
    
    # 查找该 doc_hash 对应的所有文件
    pattern = f"{doc_hash}_*"
    
    # 恢复 Markdown 和 HTML 文件
    for trash_file in trash_dir.glob(pattern):
        if trash_file.is_file():
            try:
                # 解析原始文件名
                name_parts = trash_file.name.split("_", 2)
                if len(name_parts) >= 3:
                    original_filename = name_parts[2]
                else:
                    original_filename = trash_file.name
                
                # 确定目标路径
                restore_path = config.OUTPUT_DIR / original_filename
                
                # 移动文件
                shutil.move(str(trash_file), str(restore_path))
                restored_files.append(original_filename)
                logger.info(f"已恢复文件: {original_filename}")
                
            except Exception as e:
                errors.append(f"恢复 {trash_file.name} 失败: {str(e)}")
                logger.error(f"恢复文件失败: {e}")
    
    # 恢复 PDF 文件
    if trash_pdf_dir.exists():
        pdf_dir = config.OUTPUT_DIR.parent / "pdfs"
        pdf_dir.mkdir(exist_ok=True)
        
        for trash_pdf in trash_pdf_dir.glob(pattern):
            if trash_pdf.is_file():
                try:
                    name_parts = trash_pdf.name.split("_", 2)
                    if len(name_parts) >= 3:
                        original_filename = name_parts[2]
                    else:
                        original_filename = trash_pdf.name
                    
                    restore_path = pdf_dir / original_filename
                    shutil.move(str(trash_pdf), str(restore_path))
                    restored_files.append(f"pdfs/{original_filename}")
                    logger.info(f"已恢复 PDF: {original_filename}")
                    
                except Exception as e:
                    errors.append(f"恢复 PDF {trash_pdf.name} 失败: {str(e)}")
                    logger.error(f"恢复 PDF 失败: {e}")
    
    if not restored_files:
        raise HTTPException(status_code=404, detail="回收站中未找到该文档")
    
    # 刷新缓存映射
    init_hash_mappings()
    
    return {
        "success": True,
        "message": f"已恢复 {len(restored_files)} 个文件",
        "restored_files": restored_files,
        "errors": errors if errors else None
    }


@router.delete("/admin/trash/{doc_hash}")
async def permanently_delete_from_trash(doc_hash: str, authorization: str = Header(None)):
    """从回收站永久删除文章(需要认证)"""
    verify_token(authorization)
    
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    trash_pdf_dir = trash_dir / "pdfs"
    
    if not trash_dir.exists():
        raise HTTPException(status_code=404, detail="回收站为空")
    
    deleted_files = []
    errors = []
    
    pattern = f"{doc_hash}_*"
    
    # 删除 Markdown 和 HTML 文件
    for trash_file in trash_dir.glob(pattern):
        if trash_file.is_file():
            try:
                trash_file.unlink()
                deleted_files.append(trash_file.name)
                logger.info(f"已永久删除: {trash_file.name}")
            except Exception as e:
                errors.append(f"删除 {trash_file.name} 失败: {str(e)}")
                logger.error(f"永久删除失败: {e}")
    
    # 删除 PDF 文件
    if trash_pdf_dir.exists():
        for trash_pdf in trash_pdf_dir.glob(pattern):
            if trash_pdf.is_file():
                try:
                    trash_pdf.unlink()
                    deleted_files.append(f"pdfs/{trash_pdf.name}")
                    logger.info(f"已永久删除 PDF: {trash_pdf.name}")
                except Exception as e:
                    errors.append(f"删除 PDF {trash_pdf.name} 失败: {str(e)}")
                    logger.error(f"永久删除 PDF 失败: {e}")
    
    # 删除 TTS 缓存
    try:
        audio_cache_dir = config.OUTPUT_DIR.parent / "tts_cache" / doc_hash
        if audio_cache_dir.exists():
            shutil.rmtree(audio_cache_dir)
            deleted_files.append(f"tts_cache/{doc_hash}")
            logger.info(f"已删除 TTS 缓存: {doc_hash}")
    except Exception as e:
        errors.append(f"删除 TTS 缓存失败: {str(e)}")
        logger.error(f"删除 TTS 缓存失败: {e}")
    
    if not deleted_files:
        raise HTTPException(status_code=404, detail="回收站中未找到该文档")
    
    return {
        "success": True,
        "message": f"已永久删除 {len(deleted_files)} 个文件",
        "deleted_files": deleted_files,
        "errors": errors if errors else None
    }


@router.delete("/admin/trash")
async def empty_trash(authorization: str = Header(None)):
    """清空回收站(需要认证)"""
    verify_token(authorization)
    
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    
    if not trash_dir.exists():
        return {"success": True, "message": "回收站已为空"}
    
    try:
        # 收集所有需要删除的 TTS 缓存
        doc_hashes = set()
        for f in trash_dir.glob("*.md"):
            parts = f.name.split("_", 2)
            if len(parts) >= 1:
                doc_hashes.add(parts[0])
        
        # 删除回收站目录
        shutil.rmtree(trash_dir)
        logger.info("已清空回收站")
        
        # 删除对应的 TTS 缓存
        for doc_hash_val in doc_hashes:
            audio_cache_dir = config.OUTPUT_DIR.parent / "tts_cache" / doc_hash_val
            if audio_cache_dir.exists():
                shutil.rmtree(audio_cache_dir)
                logger.info(f"已删除 TTS 缓存: {doc_hash_val}")
        
        return {
            "success": True,
            "message": f"已清空回收站，删除了 {len(doc_hashes)} 篇文章的相关文件"
        }
    except Exception as e:
        logger.error(f"清空回收站失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空回收站失败: {str(e)}")

