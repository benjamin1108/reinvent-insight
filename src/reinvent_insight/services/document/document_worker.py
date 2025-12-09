"""
文档分析 Worker 模块
处理多种格式的文档分析任务（TXT、MD、PDF、DOCX）
"""
import asyncio
import logging
import os
from pathlib import Path

from reinvent_insight.core import config
from reinvent_insight.domain.workflows import run_deep_summary_workflow
from reinvent_insight.services.analysis.task_manager import manager
from .document_processor import DocumentProcessor
from reinvent_insight.infrastructure.media.youtube_downloader import VideoMetadata
from .utils import generate_document_identifier

logger = logging.getLogger(__name__)


async def document_analysis_worker_async(task_id: str, file_path: str, title: str = None):
    """
    异步工作函数，负责处理文档文件并使用统一的分析工作流
    
    Args:
        task_id: 任务ID
        file_path: 文档文件路径
        title: 可选的文档标题
    """
    try:
        await manager.send_message("正在处理文档文件...", task_id)
        
        # 初始化文档处理器
        processor = DocumentProcessor()
        
        # 处理文档
        document_content = await processor.process_document(file_path, title)
        
        file_ext = Path(file_path).suffix.lower()
        doc_type = file_ext[1:]  # 移除点号
        
        await manager.send_message(
            f"文档处理完成（{doc_type.upper()}），开始深度分析...", 
            task_id
        )
        
        # 生成文档标识符
        doc_identifier = generate_document_identifier(
            document_content.title,
            document_content.text_content[:200] if document_content.text_content else "",
            doc_type
        )
        
        # 构造视频元数据（复用现有结构）
        metadata = VideoMetadata(
            title=document_content.title,
            upload_date="19700101",
            video_url=doc_identifier,  # 使用唯一的文档标识符
            is_reinvent=False,
            course_code=None,
            level=None
        )
        
        await manager.send_message("开始分析文档内容...", task_id)
        
        # 运行统一的摘要工作流
        await run_deep_summary_workflow(
            task_id=task_id,
            model_name=config.PREFERRED_MODEL,
            content=document_content,
            video_metadata=metadata,
            task_notifier=manager
        )
        
        logger.info(f"任务 {task_id} 的文档分析工作流已完成。")
        
        # 工作流完成后清理临时文件
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"已删除临时文档文件: {file_path}")
        except Exception as e:
            logger.warning(f"删除临时文件失败: {e}")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 文档分析失败: {e}", exc_info=True)
        await manager.set_task_error(task_id, f"文档分析失败: {str(e)}")
        
        # 清理临时文件
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception:
                pass
        return
