"""Visual interpretation routes"""

import logging
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import yaml
import re

from reinvent_insight.core import config
from reinvent_insight.services.document.hash_registry import (
    hash_to_filename,
    hash_to_versions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/article", tags=["visual"])


@router.get("/{doc_hash}/visual")
async def get_visual_interpretation(doc_hash: str, version: Optional[int] = None):
    """
    获取文章的可视化解读 HTML(版本跟随深度解读)
    
    Args:
        doc_hash: 文档哈希
        version: 可选的版本号(如果不指定，使用默认版本)
        
    Returns:
        HTML 内容或错误信息
    """
    try:
        # 获取文章文件名(可能包含版本号)
        if version is not None:
            # 如果指定了版本，从版本列表中查找
            versions = hash_to_versions.get(doc_hash, [])
            filename = None
            for v_filename in versions:
                if f"_v{version}.md" in v_filename or (version == 0 and "_v" not in v_filename):
                    filename = v_filename
                    break
            if not filename:
                raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")
        else:
            # 使用默认版本
            filename = hash_to_filename.get(doc_hash)
            if not filename:
                raise HTTPException(status_code=404, detail="文章未找到")
        
        # 构建可视化 HTML 文件路径(保持与深度解读相同的版本号)
        base_name = Path(filename).stem
        visual_filename = f"{base_name}_visual.html"
        visual_path = config.OUTPUT_DIR / visual_filename
        
        if not visual_path.exists():
            raise HTTPException(status_code=404, detail="可视化解读尚未生成")
        
        # 读取 HTML 内容
        html_content = visual_path.read_text(encoding="utf-8")
        
        # 动态替换 CDN 链接为本地路径，加快加载速度
        # Chart.js
        html_content = re.sub(
            r'https://cdn\.bootcdn\.net/ajax/libs/Chart\.js/[\d.]+/chart\.umd\.min\.js',
            '/js/vendor/chart.umd.min.js',
            html_content
        )
        html_content = re.sub(
            r'https://cdn\.jsdelivr\.net/npm/chart\.js@[\d.]+/dist/chart\.umd\.min\.js',
            '/js/vendor/chart.umd.min.js',
            html_content
        )
        # Font Awesome CSS
        html_content = re.sub(
            r'https://cdn\.bootcdn\.net/ajax/libs/font-awesome/[\d.]+/css/all\.min\.css',
            '/css/vendor/fontawesome/all.min.css',
            html_content
        )
        html_content = re.sub(
            r'https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome/[\d.]+/css/all\.min\.css',
            '/css/vendor/fontawesome/all.min.css',
            html_content
        )
        
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Cache-Control": "public, max-age=3600",
                # 更新 CSP 策略以允许可视化 HTML 所需的外部资源
                "Content-Security-Policy": (
                    "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
                    "https://fonts.googleapis.com https://fonts.gstatic.com "
                    "https://fonts.loli.net https://gstatic.loli.net "
                    "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
                    "https://cdnjs.cloudflare.com "
                    "https://lf26-cdn-tos.bytecdntp.com https://lf6-cdn-tos.bytecdntp.com "
                    "https://unpkg.com https://cdn.bootcdn.net; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                    "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
                    "https://cdnjs.cloudflare.com "
                    "https://lf26-cdn-tos.bytecdntp.com https://lf6-cdn-tos.bytecdntp.com "
                    "https://unpkg.com https://cdn.bootcdn.net; "
                    "style-src 'self' 'unsafe-inline' "
                    "https://fonts.googleapis.com https://fonts.loli.net "
                    "https://cdnjs.cloudflare.com https://cdn.bootcdn.net; "
                    "font-src 'self' https://fonts.gstatic.com https://gstatic.loli.net "
                    "https://cdnjs.cloudflare.com https://cdn.bootcdn.net; "
                    "img-src 'self' data: https:;"
                )
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可视化解读失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")


@router.get("/{doc_hash}/visual/status")
async def get_visual_status(doc_hash: str, version: Optional[int] = None):
    """
    获取可视化解读的生成状态(版本跟随深度解读)
    
    Args:
        doc_hash: 文档哈希
        version: 可选的版本号(如果不指定，使用默认版本)
        
    Returns:
        状态信息: {status: 'pending'|'processing'|'completed'|'failed', version: int}
    """
    try:
        # 获取文章文件名(可能包含版本号)
        if version is not None:
            # 如果指定了版本，从版本列表中查找
            versions = hash_to_versions.get(doc_hash, [])
            filename = None
            for v_filename in versions:
                if f"_v{version}.md" in v_filename or (version == 0 and "_v" not in v_filename):
                    filename = v_filename
                    break
            if not filename:
                raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")
        else:
            # 使用默认版本
            filename = hash_to_filename.get(doc_hash)
            if not filename:
                raise HTTPException(status_code=404, detail="文章未找到")
        
        # 读取文章元数据
        article_path = config.OUTPUT_DIR / filename
        content = article_path.read_text(encoding="utf-8")
        
        # 解析元数据
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                visual_info = metadata.get("visual_interpretation", {})
                
                # 提取当前文件的版本号
                version_match = re.search(r'_v(\d+)\.md$', filename)
                current_version = int(version_match.group(1)) if version_match else 0
                
                return {
                    "status": visual_info.get("status", "pending"),
                    "file": visual_info.get("file"),
                    "generated_at": visual_info.get("generated_at"),
                    "version": current_version
                }
        
        return {"status": "pending", "version": 0}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可视化状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")
