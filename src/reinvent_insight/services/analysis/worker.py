import asyncio
import logging
import uuid
from reinvent_insight.core import config
from reinvent_insight.core.config import GenerationMode
from reinvent_insight.infrastructure.media import youtube_downloader as downloader
from reinvent_insight.domain.workflows import run_deep_summary_workflow
from .task_manager import manager  # Import the shared manager instance
from pathlib import Path

logger = logging.getLogger(__name__)

async def summary_task_worker_async(
    url: str, 
    task_id: str, 
    is_ultra_mode: bool = False,
    generation_mode: GenerationMode = GenerationMode.CONCURRENT
):
    """
    异步工作函数，负责下载并启动多步骤摘要工作流。
    
    Args:
        url: YouTube 视频链接
        task_id: 任务ID
        is_ultra_mode: 是否为 UltraDeep 模式
        generation_mode: 章节生成模式 (concurrent/sequential)
    """
    mode_str = "UltraDeep" if is_ultra_mode else "Deep"
    gen_mode_str = generation_mode.value
    logger.info(f"[任务启动] task_id={task_id}, 类型=YouTube, 模式={mode_str}, 生成模式={gen_mode_str}, url={url}")
    
    # 1. 下载字幕 (这是一个阻塞操作，在异步函数中通过 to_thread 运行以避免阻塞事件循环)
    try:
        await manager.send_message("正在获取视频字幕...", task_id)
        loop = asyncio.get_running_loop()
        
        # 使用 to_thread 将同步的下载操作放入后台线程
        dl = downloader.SubtitleDownloader(url)
        subtitle_text, metadata, error = await loop.run_in_executor(None, dl.download)

        if error or not subtitle_text or not metadata:
            # 下载失败，发送结构化错误信息
            if error:
                error_dict = error.to_dict()
                error_message = error.message
                
                # 构建详细的错误消息
                if error.suggestions:
                    error_message += "\n\n建议操作："
                    for suggestion in error.suggestions:
                        error_message += f"\n• {suggestion}"
                
                logger.error(f"任务 {task_id} 下载字幕失败: {error.error_type.value} - {error.message}")
                await manager.set_task_error(task_id, error_dict)
            else:
                # 未知错误
                logger.error(f"任务 {task_id} 下载字幕失败: 未知错误")
                await manager.set_task_error(task_id, {
                    "error_type": "unknown",
                    "message": "无法获取字幕，请检查链接",
                    "suggestions": ["检查 URL 是否正确", "检查网络连接"]
                })
            return
            
        video_title = metadata.title
        logger.info(f"[字幕获取成功] task_id={task_id}, 标题={video_title[:50]}..." if len(video_title) > 50 else f"[字幕获取成功] task_id={task_id}, 标题={video_title}")
        
        # 将原始视频标题写入任务目录，供后续重新拼接等操作使用
        from reinvent_insight.domain.workflows.base import get_task_dir_path
        task_dir = get_task_dir_path(task_id, "youtube")
        try:
            Path(task_dir).mkdir(parents=True, exist_ok=True)
            (Path(task_dir) / "video_title.txt").write_text(video_title, encoding="utf-8")
        except Exception as e:
            logger.warning(f"无法写入 video_title.txt: {e}")

        await manager.send_message(f"字幕获取成功，准备开始深度分析", task_id)

    except ValueError as e:
        # URL 验证错误
        logger.error(f"任务 {task_id} URL 验证失败: {e}", exc_info=True)
        await manager.set_task_error(task_id, {
            "error_type": "invalid_url",
            "message": str(e),
            "suggestions": [
                "检查 URL 格式是否正确",
                "确保是有效的 YouTube 链接",
                "示例: https://www.youtube.com/watch?v=VIDEO_ID"
            ]
        })
        return
    except Exception as e:
        # 其他未预期的错误
        logger.error(f"任务 {task_id} 发生未预期错误: {e}", exc_info=True)
        await manager.set_task_error(task_id, {
            "error_type": "unknown",
            "message": f"发生未预期错误: {str(e)}",
            "technical_details": str(e),
            "suggestions": ["请稍后重试", "如果问题持续，请联系技术支持"]
        })
        return

    # 将标题和字幕拼接，为大模型提供更完整的上下文
    content_for_summary = f"视频标题: {video_title}\n\n{subtitle_text}"

    # 2. 运行新的多步骤摘要工作流
    # 这个工作流内部会处理所有的日志、进度和结果发送
    await run_deep_summary_workflow(
        task_id=task_id,
        model_name=config.PREFERRED_MODEL,
        content=content_for_summary,
        video_metadata=metadata,
        task_notifier=manager,
        is_ultra_mode=is_ultra_mode,
        generation_mode=generation_mode
    )

    mode_str = "UltraDeep" if is_ultra_mode else "Deep"
    gen_mode_str = generation_mode.value
    logger.info(f"[任务完成] task_id={task_id}, 类型=YouTube, 模式={mode_str}, 生成模式={gen_mode_str}, 工作流执行完毕")


async def ultra_deep_insight_worker_async(
    url: str, 
    task_id: str, 
    doc_hash: str, 
    target_version: int,
    content_identifier: str = None
):
    """
    Ultra DeepInsight 异步工作函数，生成超深度解读版本
    
    Args:
        url: 原始视频URL或文档路径
        task_id: 任务ID
        doc_hash: 文档哈希值
        target_version: 目标版本号
        content_identifier: 文档标识符（仅文档类型使用）
    """
    logger.info(f"[Ultra任务启动] task_id={task_id}, doc_hash={doc_hash}, target_version={target_version}")
    
    try:
        await manager.send_message("正在启动Ultra DeepInsight生成...", task_id)
        
        # 1. 获取原始内容
        # 判断是否为YouTube URL
        if "youtube.com" in url or "youtu.be" in url:
            # YouTube 视频
            await manager.send_message("正在获取视频字幕...", task_id)
            loop = asyncio.get_running_loop()
            
            dl = downloader.SubtitleDownloader(url)
            subtitle_text, metadata, error = await loop.run_in_executor(None, dl.download)
            
            if error or not subtitle_text or not metadata:
                if error:
                    error_dict = error.to_dict()
                    logger.error(f"Ultra任务 {task_id} 下载字幕失败: {error.error_type.value}")
                    await manager.set_task_error(task_id, error_dict)
                else:
                    logger.error(f"Ultra任务 {task_id} 下载字幕失败: 未知错误")
                    await manager.set_task_error(task_id, {
                        "error_type": "unknown",
                        "message": "无法获取字幕，请检查链接"
                    })
                return
            
            video_title = metadata.title
            content_for_summary = f"视频标题: {video_title}\n\n{subtitle_text}"
            
        else:
            # 文档文件，从 raw_documents 读取原始文件
            await manager.send_message("正在读取原始文档...", task_id)
            
            # url 在文档类型中是文件路径
            file_path = url
            
            if not Path(file_path).exists():
                logger.error(f"Ultra任务 {task_id}: 原始文档不存在 - {file_path}")
                await manager.set_task_error(task_id, {
                    "error_type": "source_not_found",
                    "message": "原始文档不存在，无法生成 Ultra 版本"
                })
                return
            
            # 使用 DocumentProcessor 处理文档
            from reinvent_insight.services.document.document_processor import DocumentProcessor
            from reinvent_insight.infrastructure.media.youtube_downloader import VideoMetadata
            
            processor = DocumentProcessor()
            document_content = await processor.process_document(file_path)
            
            # 构造 metadata
            metadata = VideoMetadata(
                title=document_content.title,
                upload_date="19700101",
                video_url="",
                content_identifier=content_identifier
            )
            
            await manager.send_message("文档读取成功，开始 Ultra 深度分析...", task_id)
            
            # 运行 Ultra 深度摘要工作流（使用 DocumentContent 而非字符串）
            await run_deep_summary_workflow(
                task_id=task_id,
                model_name=config.PREFERRED_MODEL,
                content=document_content,  # DocumentContent 对象
                video_metadata=metadata,
                task_notifier=manager,
                is_ultra_mode=True,
                target_version=target_version,
                doc_hash=doc_hash
            )
            
            logger.info(f"[Ultra任务完成] task_id={task_id}, doc_hash={doc_hash}, 类型=文档")
            return  # 文档类型处理完成，直接返回
        
        await manager.send_message("内容获取成功，开始Ultra深度分析...", task_id)
        
        # 2. 运行Ultra深度摘要工作流
        await run_deep_summary_workflow(
            task_id=task_id,
            model_name=config.PREFERRED_MODEL,
            content=content_for_summary,
            video_metadata=metadata,
            task_notifier=manager,
            is_ultra_mode=True,  # 关键参数：启用Ultra模式
            target_version=target_version,  # 目标版本号
            doc_hash=doc_hash  # 文档哈希
        )
        
        logger.info(f"[Ultra任务完成] task_id={task_id}, doc_hash={doc_hash}")
        
    except Exception as e:
        logger.error(f"Ultra任务 {task_id} 发生未预期错误: {e}", exc_info=True)
        await manager.set_task_error(task_id, {
            "error_type": "unknown",
            "message": f"发生未预期错误: {str(e)}",
            "technical_details": str(e)
        })
        return 