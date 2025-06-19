from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import logging
import asyncio
import uuid
import hashlib
import base64
from typing import Set, Optional
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import re
import urllib.parse

from .logger import setup_logger
from . import config
from .task_manager import manager # 导入共享的任务管理器
from .worker import summary_task_worker_sync # 导入同步工作流

setup_logger(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reinvent Insight API", description="YouTube 字幕深度摘要后端服务", version="0.1.0")

# --- 简易认证实现 ---
session_tokens: Set[str] = set()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str

@app.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """验证用户名密码，返回简易 Bearer Token。"""
    if req.username == config.ADMIN_USERNAME and req.password == config.ADMIN_PASSWORD:
        raw = f"{req.username}:{req.password}:{uuid.uuid4()}".encode()
        token = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode()[:48]
        session_tokens.add(token)
        return LoginResponse(token=token)
    raise HTTPException(status_code=401, detail="用户名或密码错误")

def verify_token(authorization: str = None):
    """依赖项：校验 Bearer Token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或令牌缺失")
    token = authorization.split(" ", 1)[1]
    if token not in session_tokens:
        raise HTTPException(status_code=401, detail="令牌无效，请重新登录")
    return True

async def summary_task_worker(url: str, task_id: str):
    """
    异步启动器：将同步的工作函数抛到后台线程执行。
    """
    loop = asyncio.get_running_loop()
    await asyncio.to_thread(summary_task_worker_sync, loop, url, task_id)

# --- API 端点 ---
class SummarizeRequest(BaseModel):
    url: HttpUrl
    task_id: Optional[str] = None

class SummarizeResponse(BaseModel):
    task_id: str
    message: str
    status: str # "created", "reconnected"

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize_endpoint(req: SummarizeRequest, authorization: str = Header(None)):
    """
    接收 URL，创建或重新连接到后台任务。
    """
    verify_token(authorization)
    
    if req.task_id and manager.get_task_state(req.task_id):
        task_id = req.task_id
        logger.info(f"客户端正在尝试重新连接到任务: {task_id}")
        return SummarizeResponse(task_id=task_id, message="任务恢复中，请连接 WebSocket。", status="reconnected")

    task_id = str(uuid.uuid4())
    task = asyncio.create_task(summary_task_worker(str(req.url), task_id))
    manager.create_task(task_id, task)
    
    return SummarizeResponse(task_id=task_id, message="任务已创建，请连接 WebSocket。", status="created")

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id)
        logger.info(f"客户端 {task_id} 断开连接。")

@app.get("/summaries")
async def list_summaries():
    """获取所有已生成的摘要文件列表。"""
    try:
        summaries = []
        if config.OUTPUT_DIR.exists():
            for md_file in config.OUTPUT_DIR.glob("*.md"):
                stat = md_file.stat()
                title_cn = ""
                try:
                    with md_file.open("r", encoding="utf-8") as f:
                        for line in f:
                            stripped = line.strip()
                            if stripped.startswith('# '):
                                title_cn = stripped[2:].strip()
                                break
                except Exception as e:
                    logger.warning(f"提取中文标题失败 {md_file.name}: {e}")
                title_en = md_file.stem
                if not title_cn:
                    title_cn = title_en
                summaries.append({
                    "filename": md_file.name,
                    "title_cn": title_cn,
                    "title_en": title_en,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime,
                    "modified_at": stat.st_mtime
                })
        summaries.sort(key=lambda x: x["modified_at"], reverse=True)
        return {"summaries": summaries}
    except Exception as e:
        logger.error(f"获取摘要列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取摘要列表失败")

@app.get("/summaries/{filename}")
async def get_summary(filename: str):
    """获取指定摘要文件的内容。"""
    try:
        filename = urllib.parse.unquote(filename)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
        if not filename.endswith(".md"):
            filename += ".md"
        file_path = config.OUTPUT_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="摘要文件未找到")
        content = file_path.read_text(encoding="utf-8")
        return {
            "filename": filename,
            "title": file_path.stem,
            "content": content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取摘要文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="读取摘要文件失败")

@app.get("/documents/{path:path}")
async def serve_spa(path: str):
    """为文档页面URL返回主 index.html，以支持前端路由刷新。"""
    index_path = config.BASE_DIR / "web" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="主应用文件未找到")
    return FileResponse(str(index_path))

web_dir = config.BASE_DIR / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
    logger.info(f"成功挂载前端静态文件目录: {web_dir}")
else:
    logger.warning(f"前端目录 'web' 未找到于 {web_dir}，将只提供 API 服务。") 