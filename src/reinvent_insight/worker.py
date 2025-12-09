import asyncio
import logging
import uuid
from . import config, downloader
from .workflow import run_deep_summary_workflow
from .task_manager import manager  # Import the shared manager instance
from pathlib import Path

logger = logging.getLogger(__name__)

async def summary_task_worker_async(url: str, task_id: str):
    """
    异步工作函数，负责下载并启动多步骤摘要工作流。
    """
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
        # 将原始视频标题写入任务目录，供后续重新拼接等操作使用
        task_dir = f"./downloads/tasks/{task_id}"
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
        video_metadata=metadata
    )

    logger.info(f"任务 {task_id} 的工作流已在后台完成。")


async def ultra_deep_insight_worker_async(url: str, task_id: str, doc_hash: str, target_version: int):
    """
    Ultra DeepInsight 异步工作函数，生成超深度解读版本
    
    Args:
        url: 原始视频URL或文档路径
        task_id: 任务ID
        doc_hash: 文档哈希值
        target_version: 目标版本号
    """
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
            # 文档文件，需要从已存在的文件中读取内容
            # TODO: 实现文档读取逻辑
            logger.error(f"Ultra任务 {task_id}: 暂不支持文档类型")
            await manager.set_task_error(task_id, {
                "error_type": "not_supported",
                "message": "暂不支持从文档生成Ultra版本"
            })
            return
        
        await manager.send_message("内容获取成功，开始Ultra深度分析...", task_id)
        
        # 2. 运行Ultra深度摘要工作流
        await run_deep_summary_workflow(
            task_id=task_id,
            model_name=config.PREFERRED_MODEL,
            content=content_for_summary,
            video_metadata=metadata,
            is_ultra_mode=True,  # 关键参数：启用Ultra模式
            target_version=target_version,  # 目标版本号
            doc_hash=doc_hash  # 文档哈希
        )
        
        logger.info(f"Ultra任务 {task_id} 的工作流已完成")
        
    except Exception as e:
        logger.error(f"Ultra任务 {task_id} 发生未预期错误: {e}", exc_info=True)
        await manager.set_task_error(task_id, {
            "error_type": "unknown",
            "message": f"发生未预期错误: {str(e)}",
            "technical_details": str(e)
        })
        return 