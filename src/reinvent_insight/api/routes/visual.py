"""Visual interpretation routes"""

import logging
from typing import Optional, List
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
import yaml
import re

from reinvent_insight.core import config
from reinvent_insight.services.document.hash_registry import (
    hash_to_filename,
    hash_to_versions,
)
from reinvent_insight.services.visual_to_image_service import get_visual_to_image_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/article", tags=["visual"])


def _find_task_dir_for_article(article_path: Path) -> Optional[Path]:
    """查找文章对应的 task_dir（用于分章节生成模式）"""
    from reinvent_insight.domain.workflows.base import TASKS_ROOT_DIR
    
    # 1. 优先从文章元数据中获取 task_dir
    try:
        content = article_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                if metadata.get("task_dir"):
                    task_dir_path = Path(metadata["task_dir"])
                    if task_dir_path.exists():
                        chapter_files = list(task_dir_path.glob("chapter_*.md"))
                        if chapter_files:
                            logger.info(f"从元数据找到 task_dir: {task_dir_path}（{len(chapter_files)} 个章节）")
                            return task_dir_path
    except Exception as e:
        logger.debug(f"从元数据获取 task_dir 失败: {e}")
    
    # 2. 回退：搜索 tasks 目录下最近的匹配任务
    tasks_root = Path(TASKS_ROOT_DIR)
    if not tasks_root.exists():
        return None
    
    # 提取文章标题用于匹配
    article_title = None
    try:
        content = article_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                article_title = metadata.get("title_cn") or metadata.get("title")
    except Exception:
        pass
    
    if not article_title:
        return None
    
    import json
    date_dirs = sorted(tasks_root.iterdir(), reverse=True)
    for date_dir in date_dirs[:3]:  # 只检查最近 3 天
        if not date_dir.is_dir():
            continue
        
        for task_dir in sorted(date_dir.iterdir(), reverse=True):
            if not task_dir.is_dir():
                continue
            
            chapter_files = list(task_dir.glob("chapter_*.md"))
            if not chapter_files:
                continue
            
            # 通过 outline.md 的 title_cn 匹配
            outline_path = task_dir / "outline.md"
            if outline_path.exists():
                try:
                    outline_content = outline_path.read_text(encoding="utf-8")
                    if "```json" in outline_content:
                        json_start = outline_content.find("```json") + 7
                        json_end = outline_content.find("```", json_start)
                        json_str = outline_content[json_start:json_end].strip()
                    else:
                        json_str = outline_content.strip()
                    
                    outline_data = json.loads(json_str)
                    outline_title = outline_data.get("title_cn") or outline_data.get("title")
                    
                    if outline_title and outline_title == article_title:
                        logger.info(f"通过标题匹配找到 task_dir: {task_dir}（{len(chapter_files)} 个章节）")
                        return task_dir
                except Exception as e:
                    logger.debug(f"解析 outline.md 失败: {e}")
    
    logger.debug(f"未找到文章对应的 task_dir: {article_path.name}")
    return None


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


@router.post("/{doc_hash}/visual/to-image")
async def generate_visual_long_image(
    doc_hash: str,
    version: Optional[int] = Query(None, description="版本号"),
    viewport_width: Optional[int] = Query(None, description="视口宽度（像素）"),
    force_regenerate: bool = Query(False, description="是否强制重新生成"),
    authorization: str = Header(None)
):
    """
    生成 Visual Insight 长图
    
    Args:
        doc_hash: 文档哈希
        version: 版本号（可选）
        viewport_width: 视口宽度（可选，默认 1920px）
        force_regenerate: 是否强制重新生成（默认 False）
        
    Returns:
        生成结果 JSON
    """
    from reinvent_insight.api.routes.auth import verify_token
    verify_token(authorization)
    
    try:
        # 检查功能是否启用
        if not config.VISUAL_LONG_IMAGE_ENABLED:
            raise HTTPException(status_code=403, detail="长图生成功能未启用")
        
        logger.info(f"开始生成长图 - doc_hash: {doc_hash}, version: {version}")
        
        # 获取服务
        service = get_visual_to_image_service()
        
        # 生成长图
        result = await service.generate_long_image(
            doc_hash=doc_hash,
            version=version,
            viewport_width=viewport_width,
            force_regenerate=force_regenerate
        )
        
        # 构造图片 URL（添加时间戳破坏 Nginx 缓存）
        image_url = f"/api/article/{doc_hash}/visual/image?t={int(service.get_long_image_path(doc_hash, version).stat().st_mtime)}"
        if version is not None:
            image_url += f"&version={version}"
        
        return {
            "status": result["status"],
            "message": result["message"],
            "image_url": image_url,
            "image_path": result["image_path"],
            "file_size": result["file_size"],
            "dimensions": result["dimensions"],
            "generated_at": result["generated_at"]
        }
        
    except FileNotFoundError as e:
        logger.warning(f"文件未找到: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成长图失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成长图失败: {str(e)}")


@router.get("/{doc_hash}/visual/image")
async def get_visual_long_image(
    doc_hash: str,
    version: Optional[int] = Query(None, description="版本号"),
    t: Optional[int] = Query(None, description="缓存破坏时间戳（仅用于 URL 参数）")
):
    """
    获取 Visual Insight 长图
    
    Args:
        doc_hash: 文档哈希
        version: 版本号（可选）
        
    Returns:
        PNG 图片文件
    """
    from datetime import datetime, timezone
    
    try:
        # 检查功能是否启用
        if not config.VISUAL_LONG_IMAGE_ENABLED:
            raise HTTPException(status_code=403, detail="长图功能未启用")
        
        # 获取服务
        service = get_visual_to_image_service()
        
        # 获取长图路径
        image_path = service.get_long_image_path(doc_hash, version)
        
        if not image_path or not image_path.exists():
            raise HTTPException(
                status_code=404, 
                detail="长图尚未生成，请先调用 POST /{doc_hash}/visual/to-image 生成"
            )
        
        # 获取文件修改时间作为 ETag
        file_stat = image_path.stat()
        mtime = file_stat.st_mtime
        etag = f'"{doc_hash}-{int(mtime)}"'
        last_modified = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 返回图片文件（禁用缓存 + ETag 双重保障）
        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=image_path.name,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "ETag": etag,
                "Last-Modified": last_modified,
                # 防止 CDN/代理缓存
                "CDN-Cache-Control": "no-cache",
                "Surrogate-Control": "no-store",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取长图失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")


class PostProcessRequest(BaseModel):
    """后处理请求"""
    processor: str  # visual_insight, keyframe_screenshot
    video_url: Optional[str] = None  # keyframe_screenshot 需要
    force: bool = False  # 强制重新生成（忽略已存在检查）


@router.post("/{doc_hash}/post-process")
async def trigger_post_processor(
    doc_hash: str,
    request: PostProcessRequest,
    version: Optional[int] = Query(None, description="版本号"),
    authorization: str = Header(None)
):
    """
    触发指定的后处理器
    
    Args:
        doc_hash: 文档哈希
        request.processor: 处理器名称 (visual_insight, keyframe_screenshot)
        request.video_url: YouTube URL（keyframe_screenshot 需要）
        version: 版本号（可选）
        
    Returns:
        触发结果
    """
    from reinvent_insight.services.analysis.post_processors import (
        get_default_pipeline,
        PostProcessorContext
    )
    from reinvent_insight.api.routes.auth import verify_token
    verify_token(authorization)
    
    try:
        # 获取文章文件名
        if version is not None:
            versions = hash_to_versions.get(doc_hash, [])
            filename = None
            for v_filename in versions:
                if f"_v{version}.md" in v_filename or (version == 0 and "_v" not in v_filename):
                    filename = v_filename
                    break
            if not filename:
                raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")
        else:
            filename = hash_to_filename.get(doc_hash)
            if not filename:
                raise HTTPException(status_code=404, detail="文章未找到")
        
        # 读取文章内容
        article_path = config.OUTPUT_DIR / filename
        content = article_path.read_text(encoding="utf-8")
        
        # 查找对应的 task_dir（用于分章节生成模式）
        task_dir = _find_task_dir_for_article(article_path)
        
        # 解析元数据获取标题和章节数
        title = "Unknown"
        chapter_count = 0
        video_url = request.video_url or ""
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                title = metadata.get("title", metadata.get("title_cn", "Unknown"))
                video_url = video_url or metadata.get("video_url", "")
                chapter_count = metadata.get("chapter_count", 0)
        
        # 如果元数据没有 chapter_count，通过正则统计
        if chapter_count == 0:
            chapter_count = len(re.findall(r'^##+ ', content, re.MULTILINE))
        
        # 构建上下文
        context = PostProcessorContext(
            task_id=f"manual_{doc_hash}",
            report_content=content,
            title=title,
            doc_hash=doc_hash,
            chapter_count=chapter_count,
            content_type="youtube" if video_url else "document",
            video_url=video_url,
            is_ultra_mode=True,
            task_dir=str(task_dir) if task_dir else None,
            extra={"article_path": str(article_path)}
        )
        
        # 获取管道并找到指定处理器
        pipeline = get_default_pipeline()
        target_processor = None
        
        for proc in pipeline.processors:
            if proc.name == request.processor:
                target_processor = proc
                break
        
        if not target_processor:
            available = [p.name for p in pipeline.processors]
            raise HTTPException(
                status_code=400,
                detail=f"处理器 '{request.processor}' 不存在。可用: {available}"
            )
        
        # 检查条件（force=True 时跳过检查）
        should_run = request.force or await target_processor.should_run(context)
        if not should_run:
            # 返回详细的跳过原因
            skip_reasons = []
            if hasattr(target_processor, 'enabled') and not target_processor.enabled:
                skip_reasons.append(f"处理器未启用 (ENABLE_KEYFRAME_SCREENSHOT=false)")
            if hasattr(target_processor, 'min_chapter_count'):
                if context.chapter_count < target_processor.min_chapter_count:
                    skip_reasons.append(f"章节数不足: {context.chapter_count} < {target_processor.min_chapter_count}")
            
            # visual_insight 特定检查
            if request.processor == "visual_insight":
                article_path = target_processor._get_article_path(context)
                if article_path:
                    visual_path = target_processor._get_visual_html_path(article_path)
                    if visual_path.exists():
                        skip_reasons.append(f"Visual HTML 已存在: {visual_path.name}（使用 force=true 强制重新生成）")
            
            if request.processor == "keyframe_screenshot":
                if context.content_type != "youtube":
                    skip_reasons.append(f"content_type='{context.content_type}', 需要 'youtube'")
                if not context.video_url:
                    skip_reasons.append("缺少 video_url")
            
            return {
                "status": "skipped",
                "processor": request.processor,
                "message": "条件不满足，未执行",
                "reasons": skip_reasons or ["未知原因"],
                "context_info": {
                    "content_type": context.content_type,
                    "video_url": context.video_url[:50] + "..." if context.video_url and len(context.video_url) > 50 else context.video_url,
                    "chapter_count": context.chapter_count
                }
            }
        
        # 执行处理器
        result = await target_processor.process(context)
        
        return {
            "status": "success" if result.success else "error",
            "processor": request.processor,
            "message": result.message,
            "task_id": f"manual_{doc_hash}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发后处理器失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")
