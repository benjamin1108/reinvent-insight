from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import logging
import asyncio
import uuid
import hashlib
import base64
import subprocess
import tempfile
from typing import Set, Optional, Dict
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import re
import urllib.parse
from zhon import hanzi
import yaml
from urllib.parse import quote

from .logger import setup_logger
from . import config
from .task_manager import manager # 导入共享的任务管理器
from .worker import summary_task_worker_async # 导入新的异步工作流

setup_logger(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reinvent Insight API", description="YouTube 字幕深度摘要后端服务", version="0.1.0")

# --- 简易认证实现 ---
session_tokens: Set[str] = set()

# --- 短链接映射 ---
# 存储 hash -> filename 的映射
hash_to_filename: Dict[str, str] = {}
filename_to_hash: Dict[str, str] = {}

def generate_doc_hash(filename: str) -> str:
    """为文档生成一个短的唯一hash"""
    # 使用MD5生成hash，取前8位
    return hashlib.md5(filename.encode()).hexdigest()[:8]

def init_hash_mappings():
    """初始化已有文档的hash映射"""
    if config.OUTPUT_DIR.exists():
        for md_file in config.OUTPUT_DIR.glob("*.md"):
            filename = md_file.name
            doc_hash = generate_doc_hash(filename)
            hash_to_filename[doc_hash] = filename
            filename_to_hash[filename] = doc_hash
            
# 启动时初始化映射
init_hash_mappings()

def extract_text_from_markdown(content: str) -> str:
    """从 Markdown 内容中提取纯文本，用于准确计算字数"""
    # 移除代码块
    content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)
    content = re.sub(r'`[^`]+`', '', content)
    
    # 移除链接
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
    
    # 移除图片
    content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', content)
    
    # 移除标题标记
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
    
    # 移除粗体和斜体标记
    content = re.sub(r'\*{1,3}([^\*]+)\*{1,3}', r'\1', content)
    content = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', content)
    
    # 移除列表标记
    content = re.sub(r'^[\*\-\+]\s+', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\d+\.\s+', '', content, flags=re.MULTILINE)
    
    # 移除引用标记
    content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
    
    # 移除水平线
    content = re.sub(r'^[-\*_]{3,}$', '', content, flags=re.MULTILINE)
    
    # 移除表格分隔符
    content = re.sub(r'\|', '', content)
    
    # 移除多余的空白字符
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    
    # 去除首尾空白
    content = content.strip()
    
    return content

def parse_metadata_from_md(md_content: str) -> dict:
    """从 Markdown 文件内容中解析 YAML front matter。"""
    try:
        # 使用正则表达式匹配 front matter
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', md_content, re.DOTALL)
        if match:
            front_matter_str = match.group(1)
            metadata = yaml.safe_load(front_matter_str)
            if isinstance(metadata, dict):
                return metadata
    except (yaml.YAMLError, IndexError) as e:
        logger.warning(f"解析 YAML front matter 失败: {e}")
    return {}

def count_chinese_words(text: str) -> int:
    """
    使用 zhon 库统计中文字符和中文标点。
    """
    # 统计汉字 (不包含标点)
    hanzi_chars = re.findall(f'[{hanzi.characters}]', text)
    # 统计中文标点
    punctuation_chars = re.findall(f'[{hanzi.punctuation}]', text)
    return len(hanzi_chars) + len(punctuation_chars)

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
    # 直接创建并运行新的异步 worker
    task = asyncio.create_task(summary_task_worker_async(str(req.url), task_id))
    manager.create_task(task_id, task)
    
    return SummarizeResponse(task_id=task_id, message="任务已创建，请连接 WebSocket。", status="created")

@app.get("/api/public/summaries")
async def list_public_summaries():
    """获取所有已生成的摘要文件列表供公开展示，无需认证。"""
    try:
        summaries = []
        if config.OUTPUT_DIR.exists():
            for md_file in config.OUTPUT_DIR.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    metadata = parse_metadata_from_md(content)
                    
                    # 处理新旧两种格式
                    # 新格式：有title_cn和title_en
                    # 旧格式：只有title
                    title_cn = metadata.get("title_cn")
                    title_en = metadata.get("title_en", metadata.get("title", ""))  # 兼容旧格式
                    
                    # 如果metadata中没有title_cn，从H1获取
                    if not title_cn:
                         for line in content.splitlines():
                            stripped = line.strip()
                            if stripped.startswith('# '):
                                title_cn = stripped[2:].strip()
                                break
                    
                    # 如果还是没有，使用英文标题或文件名
                    if not title_cn:
                        title_cn = title_en if title_en else md_file.stem
                    
                    # 确保hash映射是最新的
                    if md_file.name not in filename_to_hash:
                        doc_hash = generate_doc_hash(md_file.name)
                        hash_to_filename[doc_hash] = md_file.name
                        filename_to_hash[md_file.name] = doc_hash
                    
                    pure_text = extract_text_from_markdown(content)
                    word_count = count_chinese_words(pure_text)
                    stat = md_file.stat()
                    
                    summary_data = {
                        "filename": md_file.name,
                        "title_cn": title_cn,
                        "title_en": title_en,  # 添加英文标题
                        "size": stat.st_size,
                        "word_count": word_count,
                        "created_at": stat.st_ctime,
                        "modified_at": stat.st_mtime,
                        # 从 metadata 中添加新字段
                        "upload_date": metadata.get("upload_date", "1970-01-01"),
                        "video_url": metadata.get("video_url", ""),
                        "is_reinvent": metadata.get("is_reinvent", False),
                        "course_code": metadata.get("course_code"),
                        "level": metadata.get("level"),
                        "hash": filename_to_hash.get(md_file.name, generate_doc_hash(md_file.name))  # 添加hash
                    }
                    summaries.append(summary_data)
                except Exception as e:
                    logger.warning(f"处理文件 {md_file.name} 时出错: {e}")

        # 按上传日期排序，最新的在最前
        summaries.sort(key=lambda x: x.get("upload_date", "1970-01-01"), reverse=True)
        return {"summaries": summaries}
    except Exception as e:
        logger.error(f"获取公共摘要列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取公共摘要列表失败")

@app.get("/api/public/summaries/{filename}")
async def get_public_summary(filename: str):
    """获取指定摘要文件的公开内容，无需认证。"""
    try:
        # 安全性：解码并验证文件名
        filename = urllib.parse.unquote(filename)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
            
        if not filename.endswith(".md"):
            filename += ".md"
            
        file_path = config.OUTPUT_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="摘要文件未找到")
        
        content = file_path.read_text(encoding="utf-8")
        metadata = parse_metadata_from_md(content)
        
        # 处理新旧两种格式
        title_cn = metadata.get("title_cn")
        title_en = metadata.get("title_en", metadata.get("title", ""))  # 兼容旧格式
        
        # 如果metadata中没有title_cn，从H1获取
        if not title_cn:
             for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith('# '):
                    title_cn = stripped[2:].strip()
                    break
        
        # 如果还是没有，使用英文标题或文件名
        if not title_cn:
            title_cn = title_en if title_en else file_path.stem

        return {
            "filename": filename,
            "title": title_cn,  # 保持向后兼容
            "title_cn": title_cn,
            "title_en": title_en,
            "content": content,
            "video_url": metadata.get("video_url", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取公共摘要文件 '{filename}' 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="读取摘要文件失败")

@app.get("/api/public/doc/{doc_hash}")
async def get_public_summary_by_hash(doc_hash: str):
    """通过hash获取指定摘要文件的公开内容，无需认证。"""
    # 查找对应的文件名
    filename = hash_to_filename.get(doc_hash)
    if not filename:
        raise HTTPException(status_code=404, detail="文档未找到")
    
    # 复用现有的获取文档逻辑
    return await get_public_summary(filename)

@app.get("/api/public/summaries/{filename}/pdf")
async def get_summary_pdf(filename: str, response: Response):
    """生成并下载指定摘要的PDF文件，无需认证。"""
    try:
        # 安全性：解码并验证文件名
        filename = urllib.parse.unquote(filename)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
            
        if not filename.endswith(".md"):
            filename += ".md"
            
        md_file_path = config.OUTPUT_DIR / filename
        if not md_file_path.exists():
            raise HTTPException(status_code=404, detail="摘要文件未找到")
        
        # 构建PDF文件路径
        pdf_filename = filename.replace('.md', '.pdf')
        pdf_dir = config.OUTPUT_DIR.parent / "pdfs"
        pdf_dir.mkdir(exist_ok=True)
        pdf_file_path = pdf_dir / pdf_filename
        
        # 如果PDF文件不存在，则生成
        if not pdf_file_path.exists():
            logger.info(f"生成PDF文件: {pdf_filename}")
            
            # 构建生成PDF的命令
            script_path = config.BASE_DIR / "tools" / "generate_pdfs.py"
            if not script_path.exists():
                raise HTTPException(status_code=500, detail="PDF生成工具不存在")
            
            # 使用临时目录作为输出目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_pdf_path = Path(temp_dir) / pdf_filename
                
                # 执行PDF生成命令
                cmd = [
                    "python",
                    str(script_path),
                    "-f", str(md_file_path),
                    "-o", str(temp_dir)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"PDF生成失败: {result.stderr}")
                    raise HTTPException(status_code=500, detail="PDF生成失败")
                
                # 将生成的PDF移动到目标位置
                if temp_pdf_path.exists():
                    temp_pdf_path.rename(pdf_file_path)
                else:
                    raise HTTPException(status_code=500, detail="PDF文件生成后未找到")
        
        # 返回PDF文件
        if pdf_file_path.exists():
            logger.info(f"返回PDF文件: {pdf_filename}")
            
            # 对文件名进行URL编码，处理非ASCII字符
            # 使用RFC 5987格式处理包含非ASCII字符的文件名
            encoded_filename = quote(pdf_filename, safe='')
            
            return FileResponse(
                path=str(pdf_file_path),
                media_type="application/pdf",
                filename=pdf_filename,
                headers={
                    # 使用filename*参数来支持UTF-8编码的文件名
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
                }
            )
        else:
            raise HTTPException(status_code=500, detail="PDF文件不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取PDF文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取PDF文件失败: {str(e)}")

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
async def list_summaries(authorization: str = Header(None)):
    """获取所有已生成的摘要文件列表。"""
    verify_token(authorization)
    # 复用公共列表的逻辑
    return await list_public_summaries()

@app.get("/summaries/{filename}")
async def get_summary(filename: str, authorization: str = Header(None)):
    """获取指定摘要文件的内容。"""
    verify_token(authorization)
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
        metadata = parse_metadata_from_md(content)
        
        # 处理新旧两种格式
        title_cn = metadata.get("title_cn")
        title_en = metadata.get("title_en", metadata.get("title", ""))  # 兼容旧格式
        
        # 如果metadata中没有title_cn，从H1获取
        if not title_cn:
             for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith('# '):
                    title_cn = stripped[2:].strip()
                    break
        
        # 如果还是没有，使用英文标题或文件名
        if not title_cn:
            title_cn = title_en if title_en else file_path.stem

        return {
            "filename": filename,
            "title": title_cn,  # 保持向后兼容
            "title_cn": title_cn,
            "title_en": title_en,
            "content": content,
            "video_url": metadata.get("video_url", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取摘要文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="读取摘要文件失败")

# --- Frontend Serving ---
web_dir = config.BASE_DIR / "web"

if web_dir.is_dir():
    # Mount static file directories first.
    # This ensures that requests for /js/* and /css/* are handled by StaticFiles.
    # Any other static assets in the root of /web can be added here too.
    app.mount("/js", StaticFiles(directory=web_dir / "js"), name="js")
    app.mount("/css", StaticFiles(directory=web_dir / "css"), name="css")
    
    # Mount fonts directory for PDF generation
    fonts_dir = web_dir / "fonts"
    if fonts_dir.is_dir():
        app.mount("/fonts", StaticFiles(directory=fonts_dir), name="fonts")

    # This catch-all route must be defined *after* all other API routes and mounts.
    # It serves the main index.html for any other path, enabling client-side routing.
    @app.get("/{full_path:path}", response_class=FileResponse, include_in_schema=False)
    async def serve_vue_app(request: Request, full_path: str):
        """
        Serve the Vue.js application.
        This allows the client-side router to handle all non-API, non-static-file paths.
        """
        # 检查是否是文档URL
        if full_path.startswith("d/"):
            # 提取hash
            doc_hash = full_path[2:].split('/')[0] if '/' in full_path[2:] else full_path[2:]
            
            # 查找对应的文档
            filename = hash_to_filename.get(doc_hash)
            if filename:
                try:
                    # 读取文档内容以获取标题和描述
                    file_path = config.OUTPUT_DIR / filename
                    content = file_path.read_text(encoding="utf-8")
                    metadata = parse_metadata_from_md(content)
                    
                    # 获取标题
                    title_cn = metadata.get("title_cn")
                    title_en = metadata.get("title_en", metadata.get("title", ""))
                    
                    if not title_cn:
                        for line in content.splitlines():
                            stripped = line.strip()
                            if stripped.startswith('# '):
                                title_cn = stripped[2:].strip()
                                break
                    
                    if not title_cn:
                        title_cn = title_en if title_en else file_path.stem
                    
                    # 提取摘要作为描述（前200个字符）
                    pure_text = extract_text_from_markdown(content)
                    description = pure_text[:200] + "..." if len(pure_text) > 200 else pure_text
                    
                    # 生成带有meta标签的HTML
                    index_path = web_dir / "index.html"
                    if index_path.is_file():
                        html_content = index_path.read_text(encoding="utf-8")
                        
                        # 构建meta标签
                        meta_tags = f'''
  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="article">
  <meta property="og:url" content="{request.url}">
  <meta property="og:title" content="{title_cn} - reinvent Insight">
  <meta property="og:description" content="{description}">
  <meta property="og:site_name" content="reinvent Insight">
  
  <!-- Twitter -->
  <meta property="twitter:card" content="summary_large_image">
  <meta property="twitter:url" content="{request.url}">
  <meta property="twitter:title" content="{title_cn} - reinvent Insight">
  <meta property="twitter:description" content="{description}">
  
  <!-- 基础meta标签 -->
  <meta name="description" content="{description}">
  <title>{title_cn} - reinvent Insight</title>'''
                        
                        # 替换原有的title标签和插入meta标签
                        import re
                        # 替换title
                        html_content = re.sub(
                            r'<title>.*?</title>',
                            '',
                            html_content,
                            flags=re.IGNORECASE | re.DOTALL
                        )
                        # 在</head>前插入meta标签
                        html_content = html_content.replace('</head>', meta_tags + '\n</head>')
                        
                        from fastapi.responses import HTMLResponse
                        return HTMLResponse(content=html_content)
                except Exception as e:
                    logger.error(f"生成文档meta标签失败: {e}")
        
        # 默认返回index.html
        index_path = web_dir / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
        else:
            logger.error(f"Frontend entry point not found at: {index_path}")
            raise HTTPException(status_code=404, detail="Web application not found.")
else:
    logger.warning(f"Frontend directory 'web' not found at {web_dir}, will only serve API.")

def serve(host: str = "0.0.0.0", port: int = 8001, reload: bool = False):
    """使用 uvicorn 启动 Web 服务器。"""
    import uvicorn
    uvicorn.run(
        "src.youtube_summarizer.api:app",
        host=host,
        port=port,
        reload=reload
    ) 