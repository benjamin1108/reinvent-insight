import asyncio
import logging
from . import config, downloader, summarizer
from .markdown_processor import process_markdown_file
from .task_manager import manager  # Import the shared manager instance

logger = logging.getLogger(__name__)

def summary_task_worker_sync(loop: asyncio.AbstractEventLoop, url: str, task_id: str):
    """
    这是一个在独立线程中运行的同步工作函数。
    它包含了从下载到完成摘要的完整业务逻辑。
    """
    def send_message_threadsafe(message: str):
        """线程安全地发送消息给客户端"""
        future = asyncio.run_coroutine_threadsafe(manager.send_message(message, task_id), loop)
        try:
            future.result(timeout=10) # 增加超时以应对网络延迟
        except Exception as e:
            logger.warning(f"发送WebSocket消息失败 (任务ID: {task_id}): {e}")

    def send_result_threadsafe(title: str, summary: str):
        """线程安全地发送最终结果"""
        future = asyncio.run_coroutine_threadsafe(manager.send_result(title, summary, task_id), loop)
        try:
            future.result(timeout=10)
        except Exception as e:
            logger.warning(f"发送最终结果失败 (任务ID: {task_id}): {e}")

    model = config.PREFERRED_MODEL
    
    try:
        # 1. 下载字幕 (同步)
        send_message_threadsafe("正在下载字幕...")
        
        dl = downloader.SubtitleDownloader(url)
        subtitle_text, subtitle_path, subtitle_lang = dl.download()

        if not subtitle_text:
            raise ValueError("无法获取字幕，请检查链接。")
        video_title = dl.video_title
        send_message_threadsafe(f"成功下载 '{subtitle_lang}' 字幕。")

        # 2. 读取 Prompt
        prompt_text = config.PROMPT_FILE_PATH.read_text(encoding="utf-8")
        
        # 3. 获取摘要器
        summarizer_instance = summarizer.get_summarizer(model)
        
        # 4. 生成摘要 (同步)
        send_message_threadsafe(f"正在调用 {model} 模型进行摘要...")
        
        # 将视频标题添加到字幕内容前，为模型提供更多上下文
        content_for_summary = f"视频标题: {video_title}\n\n{subtitle_text}"
        summary_md = summarizer_instance.summarize(content_for_summary, prompt_text)
        if not summary_md:
            raise ValueError("摘要生成失败。")
            
        # 5. 保存摘要
        output_filename = video_title
        output_path = config.OUTPUT_DIR / f"{output_filename}.md"
        output_path.write_text(summary_md, encoding="utf-8")
        send_message_threadsafe(f"摘要已保存到 {output_path}")
        
        # 6. 后处理 (同步)
        if process_markdown_file(output_path):
            send_message_threadsafe("已完成文档格式化处理")
        else:
            send_message_threadsafe("文档格式化处理失败，但不影响主要功能")
        
        # 7. 统计
        char_count = len(summary_md)
        price = 0
        if char_count <= 200000:
            price = char_count * 0.0001
        else:
            price = 200000 * 0.0001 + (char_count - 200000) * 0.00015
        price = round(price, 4)
        send_message_threadsafe(f"本摘要输出字数：{char_count}，Gemini 2.5 Pro 预估费用：${price}")
        
        send_message_threadsafe("摘要完成！")
        send_result_threadsafe(video_title, summary_md)

    except Exception as e:
        logger.error(f"任务 {task_id} 失败: {e}", exc_info=True)
        error_message = f"发生严重错误: {e}"
        send_message_threadsafe(error_message)
        if task_id in manager.tasks:
            manager.tasks[task_id].status = "error"
    finally:
        if task_id in manager.tasks:
             logger.info(f"任务 {task_id} 已在后台线程中完成。状态: {manager.tasks[task_id].status}")
        manager.cleanup_task(task_id) 