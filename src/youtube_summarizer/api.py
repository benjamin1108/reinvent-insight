from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import logging
import asyncio
import uuid
import hashlib
import base64
from typing import Dict, Set
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import secrets
import re

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

# --- 简易认证实现 -----------------------------------------------------------
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
        # 生成随机 token
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
        
        # 6. 统计字数和费用估算（Gemini 2.5 Pro）
        # 1 token ≈ 1 字/1.3英文单词，粗略用1字=1token估算
        char_count = len(summary_md)
        # 20万token以内，输出价10美元/10万token=0.0001美元/字
        # 20万token以上，输出价15美元/10万token=0.00015美元/字
        if char_count <= 200000:
            price = char_count * 0.0001
        else:
            price = 200000 * 0.0001 + (char_count - 200000) * 0.00015
        price = round(price, 4)
        await manager.send_message(f"本摘要输出字数：{char_count}，Gemini 2.5 Pro 预估费用：${price}", task_id)
        
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

# ------------------ 原有摘要 API ------------------

class SummarizeRequest(BaseModel):
    url: HttpUrl

class SummarizeResponse(BaseModel):
    task_id: str
    message: str

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize_endpoint(req: SummarizeRequest, authorization: str = Header(None)):
    """接收 URL，创建后台任务并返回任务 ID。"""
    # --- 鉴权 ---
    verify_token(authorization)
    
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

@app.get("/summaries")
async def list_summaries():
    """获取所有已生成的摘要文件列表。"""
    try:
        summaries = []
        if config.OUTPUT_DIR.exists():
            for md_file in config.OUTPUT_DIR.glob("*.md"):
                # 获取文件信息
                stat = md_file.stat()

                # 尝试解析文件前 40 行以提取首个 Markdown 标题
                title_cn = ""
                english_candidates = []
                try:
                    with md_file.open("r", encoding="utf-8") as f:
                        for _ in range(40):
                            line = f.readline()
                            if not line:
                                break
                            stripped = line.lstrip()
                            if not stripped.startswith(('#', '###', '##')):
                                continue
                            text = stripped.lstrip('#').strip()
                            # 清理粗体等符号
                            cleaned = re.sub(r'\*+', '', text).strip()
                            # 若以数字. 开头（章节号）则跳过
                            if re.match(r'^\d+\.\s*', cleaned):
                                pass
                            elif re.search(r'[\u4e00-\u9fa5]', cleaned) and len(cleaned) >= 5:
                                title_cn = cleaned
                            if re.search(r'[A-Za-z]{4,}', text):
                                english_candidates.append(text)
                            if title_cn:
                                # 如果中文已找到且已经遍历足够行，可以 break 提前
                                if len(english_candidates) >= 2:
                                    break
                except Exception:
                    pass

                # 始终用文件名（不含扩展名）作为英文标题
                title_en = md_file.stem

                title_in_file = title_en

                summaries.append({
                    "filename": md_file.name,
                    "title": title_in_file,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime,
                    "modified_at": stat.st_mtime
                })
        
        # 按修改时间倒序排列
        summaries.sort(key=lambda x: x["modified_at"], reverse=True)
        return {"summaries": summaries}
    except Exception as e:
        logger.error(f"获取摘要列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取摘要列表失败")

@app.get("/summaries/{filename}")
async def get_summary(filename: str):
    """获取指定摘要文件的内容。"""
    try:
        # 安全检查：确保文件名不包含路径遍历字符
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
        
        # 确保文件名以 .md 结尾
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

def generate_share_token(filename: str) -> str:
    """生成分享令牌"""
    # 使用文件名和当前时间戳生成简单的token
    content = f"{filename}"
    return base64.urlsafe_b64encode(hashlib.md5(content.encode()).digest()).decode().rstrip('=')

@app.post("/share/{filename}")
async def create_share_link(filename: str):
    """创建分享链接"""
    try:
        # 安全检查：确保文件名不包含路径遍历字符
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
        
        # 确保文件名以 .md 结尾
        if not filename.endswith(".md"):
            filename += ".md"
        
        file_path = config.OUTPUT_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="摘要文件未找到")
        
        share_token = generate_share_token(filename)
        return {
            "share_token": share_token,
            "share_url": f"/share/{share_token}",
            "filename": filename
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建分享链接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建分享链接失败")

@app.get("/api/share/{share_token}")
async def get_shared_summary(share_token: str):
    """通过分享令牌获取摘要内容"""
    try:
        # 遍历所有摘要文件，找到匹配的token
        if not config.OUTPUT_DIR.exists():
            raise HTTPException(status_code=404, detail="摘要文件未找到")
            
        for md_file in config.OUTPUT_DIR.glob("*.md"):
            if generate_share_token(md_file.name) == share_token:
                content = md_file.read_text(encoding="utf-8")
                return {
                    "filename": md_file.name,
                    "title": md_file.stem,
                    "content": content,
                    "share_token": share_token
                }
        
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分享摘要失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取分享摘要失败")

# 分享页面路由
@app.get("/share/{share_token}")
async def serve_share_page(share_token: str):
    """为分享链接提供专用的HTML页面"""
    share_html_path = config.BASE_DIR / "web" / "share.html"
    if share_html_path.exists():
        return FileResponse(str(share_html_path))
    else:
        raise HTTPException(status_code=404, detail="分享页面未找到")

# 挂载前端静态文件 - 必须放在最后，避免覆盖 API 路由
# 使用 config.BASE_DIR 来确保路径的准确性
web_dir = config.BASE_DIR / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
    logger.info(f"成功挂载前端静态文件目录: {web_dir}")
else:
    logger.warning(f"前端目录 'web' 未找到于 {web_dir}，将只提供 API 服务。") 