import asyncio
import logging
import os
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from reinvent_insight.core import config
from reinvent_insight.domain.workflows import run_deep_summary_workflow
from reinvent_insight.services.analysis.task_manager import manager
from reinvent_insight.infrastructure.media.pdf_processor import PDFProcessor
from .api import PDFAnalysisRequest
from reinvent_insight.infrastructure.media.youtube_downloader import VideoMetadata
from .utils import generate_pdf_identifier

logger = logging.getLogger(__name__)

async def pdf_analysis_worker_async(req: PDFAnalysisRequest, task_id: str, file_path: str):
    """
    异步工作函数，负责处理PDF文件并直接使用统一的分析工作流。
    """
    try:
        await manager.send_message("正在处理PDF文件...", task_id)
        
        # 初始化PDF处理器
        processor = PDFProcessor()
        
        # 上传PDF文件
        pdf_file_info = await processor.upload_pdf(file_path)
        await manager.send_message("PDF文件上传成功，准备进行多模态分析...", task_id)
        
        # 处理用户提供的标题：清理文件名后缀和无意义的字符
        clean_title = None
        if req.title:
            clean_title = req.title.strip()
            # 移除常见的文件后缀
            if clean_title.lower().endswith('.pdf'):
                clean_title = clean_title[:-4]
            # 如果标题太短或只是数字/符号，则不使用
            if len(clean_title) < 3 or clean_title.replace('_', '').replace('-', '').replace(' ', '').isdigit():
                clean_title = None
        
        # 为PDF生成唯一标识符
        # 使用临时标识符，实际的英文标题会在workflow中由AI生成
        pdf_identifier = generate_pdf_identifier(clean_title or "PDF_Document", pdf_file_info.get("name", ""))
        
        # 创建PDFContent对象
        from reinvent_insight.domain.models import DocumentContent as PDFContent
        pdf_content = PDFContent(
            file_info=pdf_file_info,
            title=clean_title or "PDF文档分析"
        )
        
        # 构造视频元数据（复用现有结构）
        # 注意：这里的title会在workflow中被AI生成的英文标题替换
        metadata = VideoMetadata(
            title=clean_title or "PDF Document Analysis",  # 临时标题
            upload_date="19700101",
            video_url=pdf_identifier  # 使用唯一的PDF标识符
        )
        
        await manager.send_message("开始使用多模态分析PDF文档...", task_id)
        
        # 直接运行统一的摘要工作流，传递PDFContent对象
        await run_deep_summary_workflow(
            task_id=task_id,
            model_name=config.PREFERRED_MODEL,
            content=pdf_content,
            video_metadata=metadata,
            task_notifier=manager
        )

        logger.info(f"任务 {task_id} 的PDF分析工作流已完成。")
        
        # 工作流完成后清理资源
        # 对于本地文件，删除临时文件
        if pdf_file_info.get("local_file", False):
            try:
                os.unlink(file_path)
                logger.info(f"已删除临时PDF文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {e}")
        else:
            # 对于上传到Gemini的文件，删除远程文件
            try:
                await processor.delete_file(pdf_file_info["name"])
            except Exception as e:
                logger.warning(f"删除Gemini文件失败: {e}")
        
    except Exception as e:
        logger.error(f"任务 {task_id} PDF多模态分析失败: {e}", exc_info=True)
        await manager.set_task_error(task_id, f"PDF多模态分析失败: {str(e)}")
        # 清理临时文件
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except:
                pass
        return