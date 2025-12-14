"""Analysis task routes - YouTube/PDF/Document analysis"""

import logging
import uuid
import os
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Query

from reinvent_insight.core import config
from reinvent_insight.api.schemas.analysis import (
    SummarizeRequest,
    SummarizeResponse,
    PDFAnalysisRequest,
    DocumentAnalysisRequest,
)
from reinvent_insight.api.routes.auth import verify_token
from reinvent_insight.services.analysis.task_manager import manager, TaskState
from reinvent_insight.services.analysis.worker_pool import worker_pool, TaskPriority
from reinvent_insight.core.utils.file_utils import generate_doc_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["analysis"])

# 从legacy导入hash映射
from reinvent_insight.services.document.hash_registry import hash_to_filename


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_endpoint(
    req: SummarizeRequest, 
    priority: int = 0,
    force: bool = Query(default=False),
    is_ultra: bool = Query(default=False, description="是否使用 UltraDeep 模式"),
    authorization: str = Header(None)
):
    """
    接收 URL，创建或重新连接到后台任务。
    
    现在使用任务队列系统，支持：
    - 优先级排序（priority: 0-3）
    - 并发控制
    - 队列管理
    - 重复检测（force=false时检查是否已存在）
    """
    verify_token(authorization)
    
    # 如果提供了 task_id，检查是否已存在
    if req.task_id and manager.get_task_state(req.task_id):
        task_id = req.task_id
        logger.info(f"客户端正在尝试重新连接到任务: {task_id}")
        return SummarizeResponse(
            task_id=task_id, 
            message="任务恢复中，请连接 WebSocket。", 
            status="reconnected"
        )

    # 检查是否已存在（除非force=true）
    if not force:
        try:
            from reinvent_insight.infrastructure.media.youtube_downloader import normalize_youtube_url
            url_str = str(req.url)
            
            # 标准化URL并提取video_id
            normalized_url, url_metadata = normalize_youtube_url(url_str)
            video_id = url_metadata.get('video_id')
            
            if video_id:
                # 生成标准化URL的doc_hash
                doc_hash = generate_doc_hash(normalized_url)
                
                # 检查文档是否存在
                filename = hash_to_filename.get(doc_hash)
                if filename:
                    logger.info(f"检测到重复视频: video_id={video_id}, doc_hash={doc_hash}")
                    from reinvent_insight.services.document.metadata_service import parse_metadata_from_md
                    file_path = config.OUTPUT_DIR / filename
                    if file_path.exists():
                        content = file_path.read_text(encoding="utf-8")
                        metadata = parse_metadata_from_md(content)
                        title = metadata.get("title_cn") or metadata.get("title_en", "未知标题")
                        
                        return SummarizeResponse(
                            status="exists",
                            exists=True,
                            doc_hash=doc_hash,
                            title=title,
                            message="该视频已有解读，请使用查看功能或添加force=true参数重新解读",
                            redirect_url=f"/article/{doc_hash}"
                        )
                
                # 检查任务队列中是否已有相同视频的任务
                # 注意：访问 PriorityQueue 的内部队列需要谨慎，这里仅用于检查
                try:
                    # 直接遍历 processing_tasks 更安全
                    for processing_task in worker_pool.processing_tasks.values():
                        if processing_task.task_type == 'youtube':
                            try:
                                task_url, task_metadata = normalize_youtube_url(processing_task.url_or_path)
                                if task_metadata.get('video_id') == video_id:
                                    logger.info(f"检测到正在处理的相同视频: video_id={video_id}")
                                    return SummarizeResponse(
                                        status="in_progress",
                                        exists=True,
                                        in_queue=True,
                                        task_id=processing_task.task_id,
                                        message="该视频的分析任务正在处理中，请稍候"
                                    )
                            except:
                                pass
                except Exception as e:
                    logger.debug(f"检查处理中任务失败: {e}")
                
                # 检查进行中的任务
                for task_id_check, task_state in manager.tasks.items():
                    if hasattr(task_state, 'url_or_path') and task_state.url_or_path:
                        try:
                            task_url, task_metadata = normalize_youtube_url(task_state.url_or_path)
                            if task_metadata.get('video_id') == video_id and task_state.status in ['processing', 'running', 'queued']:
                                logger.info(f"检测到进行中的相同视频任务: video_id={video_id}")
                                return SummarizeResponse(
                                    status="in_progress",
                                    exists=True,
                                    in_progress=True,
                                    task_id=task_id_check,
                                    message="该视频正在分析中，请连接WebSocket查看进度"
                                )
                        except:
                            pass
        except Exception as e:
            logger.warning(f"重复检测失败: {e}")

    task_id = str(uuid.uuid4())
    
    # 记录新任务创建
    logger.info(f"[YouTube分析] 新任务创建 task_id={task_id}, url={req.url}")
    
    # 先在 manager 中创建占位状态
    state = TaskState(task_id=task_id, status="queued", task=None)
    state.url_or_path = str(req.url)
    manager.tasks[task_id] = state
    
    # 映射优先级值
    priority_map = {
        0: TaskPriority.LOW,
        1: TaskPriority.NORMAL,
        2: TaskPriority.HIGH,
        3: TaskPriority.URGENT
    }
    task_priority = priority_map.get(priority, TaskPriority.NORMAL)
    
    # 添加到队列
    success = await worker_pool.add_task(
        task_id=task_id,
        task_type="youtube",
        url_or_path=str(req.url),
        priority=task_priority,
        is_ultra_mode=is_ultra
    )
    
    if not success:
        del manager.tasks[task_id]
        logger.warning(f"[YouTube分析] 任务入队失败（队列已满）task_id={task_id}")
        raise HTTPException(
            status_code=503, 
            detail=f"任务队列已满（{config.ANALYSIS_QUEUE_MAX_SIZE} 个任务），请稍后重试"
        )
    
    queue_size = worker_pool.get_queue_size()
    logger.info(f"[YouTube分析] 任务已入队 task_id={task_id}, priority={task_priority.name}, queue_size={queue_size}")
    return SummarizeResponse(
        task_id=task_id, 
        message=f"任务已加入队列（优先级: {task_priority.name}，排队: {queue_size} 个任务），请连接 WebSocket。", 
        status="created"
    )


@router.post("/analyze-pdf")
async def analyze_pdf_endpoint(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    priority: int = 0,
    authorization: str = Header(None)
):
    """使用Gemini多模态能力分析PDF文件"""
    verify_token(authorization)
    
    task_id = str(uuid.uuid4())
    
    try:
        # 创建临时文件保存上传的PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(await file.read())
            tmp_file_path = tmp_file.name
        
        # 处理标题
        display_title = title or file.filename or "未命名文档"
        if display_title.lower().endswith('.pdf'):
            display_title = display_title[:-4]
        
        # 先在 manager 中创建占位状态
        state = TaskState(task_id=task_id, status="queued", task=None)
        manager.tasks[task_id] = state
        
        # 映射优先级
        priority_map = {
            0: TaskPriority.LOW,
            1: TaskPriority.NORMAL,
            2: TaskPriority.HIGH,
            3: TaskPriority.URGENT
        }
        task_priority = priority_map.get(priority, TaskPriority.NORMAL)
        
        # 添加到队列
        success = await worker_pool.add_task(
            task_id=task_id,
            task_type="pdf",
            url_or_path=tmp_file_path,
            title=display_title,
            priority=task_priority
        )
        
        if not success:
            os.unlink(tmp_file_path)
            del manager.tasks[task_id]
            raise HTTPException(
                status_code=503, 
                detail=f"任务队列已满（{config.ANALYSIS_QUEUE_MAX_SIZE} 个任务），请稍后重试"
            )
        
        queue_size = worker_pool.get_queue_size()
        return SummarizeResponse(
            task_id=task_id, 
            message=f"PDF分析任务已加入队列（排队: {queue_size} 个任务），请连接 WebSocket。", 
            status="created"
        )
        
    except Exception as e:
        logger.error(f"处理上传PDF失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理上传PDF失败: {str(e)}")


@router.post("/analyze-document")
async def analyze_document_endpoint(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    priority: int = 0,
    is_ultra: bool = Query(default=False, description="是否使用 UltraDeep 模式"),
    authorization: str = Header(None)
):
    """
    通用文档分析端点
    支持格式：TXT, MD, PDF, DOCX
    """
    verify_token(authorization)
    
    # 验证文件格式
    file_ext = Path(file.filename).suffix.lower()
    supported_formats = ['.txt', '.md', '.pdf', '.docx']
    
    if file_ext not in supported_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式: {file_ext}. 支持的格式: {', '.join(supported_formats)}"
        )
    
    # 验证文件大小
    max_size = config.MAX_TEXT_FILE_SIZE if file_ext in ['.txt', '.md'] else config.MAX_BINARY_FILE_SIZE
    
    # 读取文件内容（用于去重检查和后续处理）
    content = await file.read()
    
    # 检查文件大小
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制 ({max_size / 1024 / 1024:.1f}MB)"
        )
    
    # 处理标题（用于去重检查）
    display_title = title or file.filename or "未命名文档"
    if display_title.lower().endswith(file_ext):
        display_title = display_title[:-len(file_ext)]
    
    # === 去重检查 ===
    from reinvent_insight.core.utils.file_utils import generate_content_identifier
    
    # 基于文件内容生成 content_identifier（不使用文件名，只用内容）
    doc_type = file_ext[1:]  # 移除点号，如 '.txt' -> 'txt'
    content_identifier = generate_content_identifier(content, doc_type)
    
    # 生成 doc_hash 并检查是否已存在
    doc_hash = generate_doc_hash(content_identifier)
    existing_filename = hash_to_filename.get(doc_hash)
    
    if existing_filename:
        logger.info(f"检测到重复文档: identifier={content_identifier}, doc_hash={doc_hash}")
        from reinvent_insight.services.document.metadata_service import parse_metadata_from_md
        file_path = config.OUTPUT_DIR / existing_filename
        if file_path.exists():
            try:
                existing_content = file_path.read_text(encoding="utf-8")
                metadata = parse_metadata_from_md(existing_content)
                existing_title = metadata.get("title_cn") or metadata.get("title_en", display_title)
                
                return SummarizeResponse(
                    status="exists",
                    exists=True,
                    doc_hash=doc_hash,
                    task_id=None,
                    message=f"文档已存在: {existing_title}"
                )
            except Exception as e:
                logger.warning(f"读取已存在文档失败，继续处理: {e}")
    
    task_id = str(uuid.uuid4())
    
    try:
        # 创建临时文件保存上传的文档
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
            # content 已在上面读取
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # 先在 manager 中创建占位状态
        state = TaskState(task_id=task_id, status="queued", task=None)
        manager.tasks[task_id] = state
        
        # 映射优先级
        priority_map = {
            0: TaskPriority.LOW,
            1: TaskPriority.NORMAL,
            2: TaskPriority.HIGH,
            3: TaskPriority.URGENT
        }
        task_priority = priority_map.get(priority, TaskPriority.NORMAL)
        
        # 添加到队列
        success = await worker_pool.add_task(
            task_id=task_id,
            task_type="document",
            url_or_path=tmp_file_path,
            title=display_title,
            priority=task_priority,
            is_ultra_mode=is_ultra
        )
        
        if not success:
            os.unlink(tmp_file_path)
            del manager.tasks[task_id]
            raise HTTPException(
                status_code=503, 
                detail=f"任务队列已满（{config.ANALYSIS_QUEUE_MAX_SIZE} 个任务），请稍后重试"
            )
        
        queue_size = worker_pool.get_queue_size()
        return SummarizeResponse(
            task_id=task_id, 
            message=f"文档分析任务已加入队列（{file_ext[1:].upper()}，排队: {queue_size} 个任务），请连接 WebSocket。", 
            status="created"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理上传文档失败: {e}", exc_info=True)
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"处理上传文档失败: {str(e)}")
