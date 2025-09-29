import asyncio
import logging
import os
from . import config
from .workflow import run_deep_summary_workflow
from .task_manager import manager
from .pdf_processor import PDFProcessor
from .api import PDFAnalysisRequest
from .downloader import VideoMetadata

logger = logging.getLogger(__name__)

async def pdf_analysis_worker_async(req: PDFAnalysisRequest, task_id: str, file_path: str):
    """
    异步工作函数，负责处理PDF文件并启动分析工作流。
    """
    try:
        await manager.send_message("正在上传PDF文件...", task_id)
        
        # 初始化PDF处理器
        processor = PDFProcessor()
        
        # 上传PDF文件
        pdf_file_info = await processor.upload_pdf(file_path)
        await manager.send_message("PDF文件上传成功，正在分析内容...", task_id)
        
        # 生成大纲
        outline_result = await processor.generate_outline(pdf_file_info, req.title)
        outline = outline_result["outline"]
        await manager.send_message("内容大纲生成完成，正在生成详细内容...", task_id)
        
        # 生成各章节内容
        chapters_content = []
        table_of_contents = outline["table_of_contents"]
        
        for i, chapter in enumerate(table_of_contents):
            await manager.send_message(f"正在生成章节 {chapter['id']}/{len(table_of_contents)}: {chapter['title']}...", task_id)
            
            # 生成章节内容
            context = "\n\n".join([c["content"] for c in chapters_content]) if chapters_content else ""
            content = await processor.generate_section_content(chapter, context, pdf_file_info["name"])
            
            chapters_content.append({
                "id": chapter["id"],
                "title": chapter["title"],
                "content": content
            })
            
            # 更新进度
            progress = 50 + int(40 * (i + 1) / len(table_of_contents))
            await manager.update_progress(task_id, progress, f"章节 {chapter['id']} 生成完成")
        
        # 组装最终内容
        await manager.send_message("正在组装最终报告...", task_id)
        
        # 构造视频元数据（复用现有结构）
        metadata = VideoMetadata(
            title=outline["title"],
            upload_date="19700101",
            video_url="pdf_content"
        )
        
        # 构造内容
        content_parts = []
        content_parts.append(f"# {outline['title']}")
        content_parts.append(f"### 引言\n{outline['introduction']}")
        
        # 添加目录
        toc_lines = ["### 主要目录"]
        for chapter in table_of_contents:
            toc_lines.append(f"{chapter['id']}. {chapter['title']}")
        content_parts.append("\n".join(toc_lines))
        
        # 添加章节内容
        for chapter_content in chapters_content:
            content_parts.append(f"### {chapter_content['id']}. {chapter_content['title']}\n\n{chapter_content['content']}")
        
        content_for_summary = "\n\n".join(content_parts)
        
        # 清理临时文件
        try:
            os.unlink(file_path)
        except:
            pass
        
        # 删除Gemini上的文件
        try:
            await processor.delete_file(pdf_file_info["name"])
        except:
            pass
        
        # 运行摘要工作流
        await run_deep_summary_workflow(
            task_id=task_id,
            model_name=config.PREFERRED_MODEL,
            transcript=content_for_summary,
            video_metadata=metadata
        )

        logger.info(f"任务 {task_id} 的PDF分析工作流已完成。")
        
    except Exception as e:
        logger.error(f"任务 {task_id} PDF分析失败: {e}", exc_info=True)
        await manager.set_task_error(task_id, f"PDF分析失败: {str(e)}")
        # 清理临时文件
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except:
                pass
        return