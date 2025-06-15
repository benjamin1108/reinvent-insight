from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, HttpUrl
import logging
import asyncio
import uuid
from typing import Dict, Set
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .logger import setup_logger
from . import config, downloader, summarizer

# 使用 config.py 中定义的 BASE_DIR，路径更可靠
setup_logger(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reinvent Insight API", description="YouTube 字幕深度摘要后端服务", version="0.1.0")

# --- 后台任务管理 ---
background_tasks: Set[asyncio.Task] = set()

@app.on_event("shutdown")
def shutdown_event():
    logger.info("应用正在关闭，开始取消所有后台任务...")
    for task in background_tasks:
        task.cancel()
    logger.info("所有后台任务已请求取消。")

class ConnectionManager:
    """管理 WebSocket 连接"""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_message(self, message: str, task_id: str):
        if task_id in self.active_connections:
            await self.active_connections[task_id].send_json({"message": message})
            
    async def send_result(self, title: str, summary: str, task_id: str):
        if task_id in self.active_connections:
            await self.active_connections[task_id].send_json({
                "type": "result",
                "title": title,
                "summary": summary
            })

manager = ConnectionManager()

async def summary_task_worker(url: str, task_id: str):
    """实际执行摘要任务的后台工作函数"""
    # 短暂等待，确保 WebSocket 连接已建立
    await asyncio.sleep(0.1)
    model = config.PREFERRED_MODEL
    
    try:
        # 1. 下载字幕
        await manager.send_message("正在下载字幕...", task_id)
        subtitle_text, subtitle_path, subtitle_lang = downloader.download_subtitles(url)
        if not subtitle_text:
            await manager.send_message(f"错误: 无法获取字幕，请检查链接。", task_id)
            return
        video_title = subtitle_path.stem.split('.')[0]
        await manager.send_message(f"成功下载 '{subtitle_lang}' 字幕。", task_id)

        # 2. 读取 Prompt
        prompt_text = config.PROMPT_FILE_PATH.read_text(encoding="utf-8")
        
        # 3. 获取摘要器
        summarizer_instance = summarizer.get_summarizer(model)
        
        # 4. 生成摘要
        await manager.send_message(f"正在调用 {model} 模型进行摘要...", task_id)
        summary_md = summarizer_instance.summarize(subtitle_text, prompt_text)
        if not summary_md:
            await manager.send_message("错误: 摘要生成失败。", task_id)
            return
            
        # 5. 保存摘要
        output_filename = video_title
        output_path = config.OUTPUT_DIR / f"{output_filename}.md"
        output_path.write_text(summary_md, encoding="utf-8")
        await manager.send_message(f"摘要已保存到 {output_path}", task_id)

        await manager.send_message("摘要完成！", task_id)
        await manager.send_result(video_title, summary_md, task_id)

    except asyncio.CancelledError:
        logger.warning(f"任务 {task_id} 已被取消。")
        await manager.send_message("错误: 服务器关闭，任务已被取消。", task_id)
    except Exception as e:
        logger.error(f"任务 {task_id} 失败: {e}", exc_info=True)
        await manager.send_message(f"发生严重错误: {e}", task_id)
    finally:
        manager.disconnect(task_id)


class SummarizeRequest(BaseModel):
    url: HttpUrl

class SummarizeResponse(BaseModel):
    task_id: str
    message: str

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize_endpoint(req: SummarizeRequest):
    """接收 URL，创建后台任务并返回任务 ID。"""
    task_id = str(uuid.uuid4())
    
    task = asyncio.create_task(summary_task_worker(str(req.url), task_id))
    background_tasks.add(task)
    # 当任务完成后，从集合中移除，避免内存泄漏
    task.add_done_callback(background_tasks.discard)
    
    return SummarizeResponse(task_id=task_id, message="任务已创建，请通过 WebSocket 连接获取进度。")


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        while True:
            # 保持连接以接收服务器推送
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id)
        logger.info(f"客户端 {task_id} 断开连接。")

# 挂载前端静态文件
# 使用 config.BASE_DIR 来确保路径的准确性
web_dir = config.BASE_DIR / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
    logger.info(f"成功挂载前端静态文件目录: {web_dir}")
else:
    logger.warning(f"前端目录 'web' 未找到于 {web_dir}，将只提供 API 服务。") 