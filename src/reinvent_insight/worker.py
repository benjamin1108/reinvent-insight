import asyncio
import logging
import uuid
from typing import Optional, Dict
from . import config, downloader
from .workflow import run_deep_summary_workflow
from .adaptive_workflow import run_adaptive_deep_summary_workflow
from .task_manager import manager  # Import the shared manager instance
from pathlib import Path

logger = logging.getLogger(__name__)

async def summary_task_worker_async(url: str, task_id: str, length_config: Optional[Dict] = None):
    """
    异步工作函数，负责下载并启动多步骤摘要工作流。
    
    Args:
        url: 视频URL
        task_id: 任务ID
        length_config: 长度配置选项，如果提供则使用自适应工作流
    """
    # 1. 下载字幕 (这是一个阻塞操作，在异步函数中通过 to_thread 运行以避免阻塞事件循环)
    try:
        await manager.send_message("正在获取视频字幕...", task_id)
        loop = asyncio.get_running_loop()
        
        # 使用 to_thread 将同步的下载操作放入后台线程
        dl = downloader.SubtitleDownloader(url)
        subtitle_text, metadata = await loop.run_in_executor(None, dl.download)

        if not subtitle_text or not metadata:
            raise ValueError("无法获取字幕，请检查链接。")
            
        video_title = metadata.title
        # 将原始视频标题写入任务目录，供后续重新拼接等操作使用
        task_dir = f"./downloads/tasks/{task_id}"
        try:
            Path(task_dir).mkdir(parents=True, exist_ok=True)
            (Path(task_dir) / "video_title.txt").write_text(video_title, encoding="utf-8")
        except Exception as e:
            logger.warning(f"无法写入 video_title.txt: {e}")

        await manager.send_message(f"字幕获取成功，准备开始深度分析", task_id)

    except Exception as e:
        logger.error(f"任务 {task_id} 下载字幕失败: {e}", exc_info=True)
        await manager.set_task_error(task_id, f"字幕获取失败，请检查视频链接是否正确")
        return

    # 将标题和字幕拼接，为大模型提供更完整的上下文
    content_for_summary = f"视频标题: {video_title}\n\n{subtitle_text}"

    # 2. 根据配置选择工作流类型
    if length_config and length_config.get('enable_adaptive', True):
        # 使用自适应工作流
        await manager.send_message("启用自适应长度生成模式", task_id)
        # 设置任务的自适应状态
        manager.set_adaptive_enabled(task_id, True)
        await run_adaptive_deep_summary_workflow(
            task_id=task_id,
            model_name=config.PREFERRED_MODEL,
            transcript=content_for_summary,
            video_metadata=metadata
        )
        logger.info(f"任务 {task_id} 的自适应工作流已在后台完成。")
    else:
        # 使用标准工作流
        await manager.send_message("使用标准长度生成模式", task_id)
        # 设置任务的自适应状态为禁用
        manager.set_adaptive_enabled(task_id, False)
        await run_deep_summary_workflow(
            task_id=task_id,
            model_name=config.PREFERRED_MODEL,
            transcript=content_for_summary,
            video_metadata=metadata
        )
        logger.info(f"任务 {task_id} 的标准工作流已在后台完成。") 