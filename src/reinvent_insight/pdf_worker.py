import asyncio
import logging
import os
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from . import config
from .workflow import run_deep_summary_workflow
from .task_manager import manager
from .pdf_processor import PDFProcessor
from .api import PDFAnalysisRequest
from .downloader import VideoMetadata
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
        await manager.send_message("PDF文件处理成功，正在提取内容...", task_id)
        
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
        
        # 直接从PDF提取文本内容，而不是生成大纲和章节
        await manager.send_message("正在提取PDF文本内容...", task_id)
        
        # 使用简化的内容提取方法
        pdf_content = await extract_pdf_content(processor, pdf_file_info, clean_title)
        
        # 保存提取的原始内容到任务目录
        task_dir = Path("./downloads/tasks") / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存PDF提取的原始内容
        extracted_content_path = task_dir / "pdf_extracted_content.md"
        with open(extracted_content_path, "w", encoding="utf-8") as f:
            f.write(f"# PDF提取的原始内容\n\n")
            f.write(f"**文件名**: {req.title or '未知'}\n")
            f.write(f"**提取时间**: {datetime.now().isoformat()}\n")
            f.write(f"**内容长度**: {len(pdf_content)} 字符\n\n")
            f.write("---\n\n")
            f.write(pdf_content)
        
        logger.info(f"PDF提取内容已保存到: {extracted_content_path}")
        
        # 为PDF生成唯一标识符
        pdf_identifier = generate_pdf_identifier(clean_title or "PDF文档", pdf_content[:200])
        
        # 构造视频元数据（复用现有结构）
        metadata = VideoMetadata(
            title=clean_title or "PDF文档分析",
            upload_date="19700101",
            video_url=pdf_identifier  # 使用唯一的PDF标识符
        )
        
        # 清理临时文件
        try:
            os.unlink(file_path)
        except:
            pass
        
        # 删除Gemini上的文件（仅当文件已上传到Gemini时）
        if not pdf_file_info.get("local_file", False):
            try:
                await processor.delete_file(pdf_file_info["name"])
            except:
                pass
        
        await manager.send_message("PDF内容提取完成，开始深度分析...", task_id)
        
        # 直接运行统一的摘要工作流，让它来处理内容分析和章节生成
        await run_deep_summary_workflow(
            task_id=task_id,
            model_name=config.PREFERRED_MODEL,
            transcript=pdf_content,
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

async def extract_pdf_content(processor: PDFProcessor, pdf_file_info: dict, title: str = None) -> str:
    """
    从PDF中提取文本内容，用于后续的统一工作流处理
    """
    try:
        # 构建内容提取的提示词
        prompt = f"""
请仔细阅读这份PDF文档，并将其内容转换为结构化的文本格式。

要求：
1. 保持原文档的逻辑结构和层次关系
2. 提取所有重要的文本信息，包括标题、段落、列表等
3. 对于图表和架构图，请用文字描述其内容和要点
4. 保持信息的完整性和准确性
5. 使用标准简体中文输出

{f"文档标题：{title}" if title else ""}

请直接输出提取的文本内容，不需要额外的格式说明。
"""
        
        # 创建模型实例
        import google.generativeai as genai
        model = genai.GenerativeModel(processor.model_name)
        
        # 根据文件类型选择处理方式
        if pdf_file_info.get("local_file", False):
            # 使用本地文件
            pdf_file_path = pdf_file_info["uri"]
            
            # 使用异步方式读取文件并处理
            loop = asyncio.get_event_loop()
            
            def read_and_process():
                with open(pdf_file_path, "rb") as f:
                    file_data = f.read()
                return genai.GenerativeModel(processor.model_name).generate_content(
                    [prompt, {"mime_type": "application/pdf", "data": file_data}],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=8000
                    )
                )
            
            response = await loop.run_in_executor(None, read_and_process)
        else:
            # 获取已上传的PDF文件引用
            pdf_file = genai.get_file(name=pdf_file_info["name"])
            
            # 调用Gemini生成API
            response = await model.generate_content_async(
                [prompt, pdf_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8000
                )
            )
        
        # 添加标题前缀（如果有的话）
        content = response.text
        if title:
            content = f"文档标题: {title}\n\n{content}"
        
        return content
        
    except Exception as e:
        logger.error(f"提取PDF内容失败: {str(e)}")
        # 如果提取失败，返回基本信息
        return f"文档标题: {title or 'PDF文档'}\n\n无法提取详细内容，请检查PDF文件格式。"