from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Request, Response, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import logging
import asyncio
import uuid
import hashlib
import base64
import subprocess
import tempfile
import os
import sys
import uvicorn
from typing import Set, Optional, Dict, List
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
from .utils import generate_doc_hash, is_pdf_document, extract_pdf_hash  # 从 utils 导入
from .file_watcher import start_watching # 导入文件监控
from .pdf_processor import PDFProcessor  # 导入PDF处理器

setup_logger(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reinvent Insight API", description="YouTube 字幕深度摘要后端服务", version="0.1.0")

@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行的事件。
    1. 初始化哈希映射缓存。
    2. 启动文件系统监控。
    3. 检查 Cookie 健康状态。
    """
    logger.info("应用启动，开始初始化...")
    # 1. 初始化缓存
    init_hash_mappings()
    
    # 2. 启动文件监控，并传入刷新缓存的回调函数
    start_watching(config.OUTPUT_DIR, init_hash_mappings)
    
    # 3. 检查 Cookie 健康状态
    from .cookie_health_check import check_and_warn
    check_and_warn()

# --- 简易认证实现 ---
session_tokens: Set[str] = set()

# --- 短链接映射 ---
# 存储 hash -> 默认文件名 的映射（通常是最新版本）
hash_to_filename: Dict[str, str] = {}
# 存储 hash -> 所有版本文件列表 的映射
hash_to_versions: Dict[str, List[str]] = {}
filename_to_hash: Dict[str, str] = {}

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

def init_hash_mappings():
    """初始化所有文档的基于 video_url 的统一hash映射。"""
    hash_to_filename.clear()
    hash_to_versions.clear()
    filename_to_hash.clear()

    if not config.OUTPUT_DIR.exists():
        return

    video_url_to_files = {}
    
    # 第一遍：基于video_url对所有文件进行分组
    for md_file in config.OUTPUT_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            video_url = metadata.get("video_url")
            
            if video_url:
                if video_url not in video_url_to_files:
                    video_url_to_files[video_url] = []
                video_url_to_files[video_url].append({
                    'filename': md_file.name,
                    'version': metadata.get('version', 0)
                })
        except Exception as e:
            logger.error(f"解析文件 {md_file.name} 时出错，已跳过: {e}")
    
    # 第二遍：为每个分组生成和注册唯一的统一hash
    for video_url, files in video_url_to_files.items():
        doc_hash = generate_doc_hash(video_url)
        if not doc_hash:
            continue

        files.sort(key=lambda x: x['version'], reverse=True)
        latest_file = files[0]['filename']
        
        # 注册核心映射
        hash_to_filename[doc_hash] = latest_file
        hash_to_versions[doc_hash] = [f['filename'] for f in files]
        for file_info in files:
            filename_to_hash[file_info['filename']] = doc_hash

    logger.info(f"--- [重构] 统一Hash映射初始化完成，共处理 {len(hash_to_filename)} 个独立视频。 ---")

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

def clean_content_metadata(content: str, title: str = '') -> str:
    """清理内容中的元数据，返回干净的文本内容"""
    if not content:
        return ''
    
    cleaned_content = content
    
    # 使用yaml库安全地解析和移除YAML Front Matter
    if content.startswith('---'):
        try:
            # 使用更宽松的正则表达式匹配完整的YAML front matter块
            # 允许结束标记前有空行
            match = re.match(r'^---\s*\n(.*?)\n\s*---\s*\n', content, re.DOTALL)
            if match:
                # 验证YAML是否有效
                yaml_content = match.group(1)
                yaml.safe_load(yaml_content)  # 验证YAML语法
                
                # 移除YAML front matter，保留后面的内容
                cleaned_content = content[match.end():]
                logger.debug(f"成功移除YAML front matter，剩余内容长度: {len(cleaned_content)}")
            else:
                # 尝试另一种格式：没有结束标记的情况（用户展示的错误格式）
                # 这种情况下，假设从第一个标题行开始是正文
                lines = content.split('\n')
                for i, line in enumerate(lines[1:], 1):  # 跳过第一行的 ---
                    # 如果遇到 Markdown 标题（# 开头）或者空行后的非 YAML 格式内容
                    if line.strip().startswith('#') or (i > 1 and not line.strip() and i + 1 < len(lines) and not ':' in lines[i + 1]):
                        cleaned_content = '\n'.join(lines[i:])
                        logger.debug(f"检测到不完整的YAML front matter，从第{i}行开始提取内容")
                        break
                else:
                    logger.warning("检测到---开头但无法确定YAML front matter的结束位置")
        except yaml.YAMLError as e:
            logger.warning(f"YAML front matter解析失败，保留原始内容: {e}")
        except Exception as e:
            logger.error(f"处理YAML front matter时发生错误: {e}")
    
    # 清理开头的空行
    cleaned_content = cleaned_content.lstrip()
    
    # 可选：如果标题存在，去除可能重复的H1标题
    if title and cleaned_content:
        # 处理可能的标题变体（考虑空格、标点等）
        escaped_title = re.escape(title)
        # 匹配 # 标题 或 ## 标题 等，允许标题后有标点符号
        markdown_title_pattern = rf'^#+\s*{escaped_title}\s*[!！.。:：]?\s*$'
        cleaned_content = re.sub(markdown_title_pattern, '', cleaned_content, count=1, flags=re.MULTILINE | re.IGNORECASE).lstrip()
    
    return cleaned_content

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

# --- API 端点 ---
class SummarizeRequest(BaseModel):
    url: HttpUrl
    task_id: Optional[str] = None

class SummarizeResponse(BaseModel):
    task_id: str
    message: str
    status: str # "created", "reconnected"

def discover_versions(video_url: str) -> List[Dict[str, any]]:
    """发现指定视频URL的所有版本"""
    versions = []
    
    if not config.OUTPUT_DIR.exists():
        return versions
        
    # 扫描所有文件
    for md_file in config.OUTPUT_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            
            # 检查是否是同一个视频
            if metadata.get('video_url') == video_url:
                version_info = {
                    'filename': md_file.name,
                    'version': metadata.get('version', 0),  # 默认为0（原始版本）
                    'created_at': metadata.get('created_at', ''),
                    'title_cn': metadata.get('title_cn', ''),
                    'title_en': metadata.get('title_en', '')
                }
                versions.append(version_info)
        except Exception as e:
            logger.warning(f"检查文件 {md_file.name} 时出错: {e}")
    
    # 按版本号排序
    versions.sort(key=lambda x: x['version'])
    return versions

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

@app.get("/api/env")
async def get_environment_info():
    """获取环境信息，用于区分开发和生产环境"""
    # 通过多种方式判断环境
    is_dev = any([
        # 检查环境变量（优先级最高）
        os.getenv("ENVIRONMENT", "").lower() == "development",
        os.getenv("ENV", "").lower() == "dev",
        # 检查是否存在开发环境特有的文件
        (config.PROJECT_ROOT / ".git").exists(),  # git目录只在开发环境存在
        (config.PROJECT_ROOT / "pyproject.toml").exists(),  # 项目配置文件
        (config.PROJECT_ROOT / "run-dev.sh").exists(),  # 开发脚本
        # 检查是否在虚拟环境中运行（生产环境通常使用系统包）
        hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
    ])
    
    # 如果明确设置了生产环境变量，则强制为生产环境
    if os.getenv("ENVIRONMENT", "").lower() == "production":
        is_dev = False
    
    return {
        "environment": "development" if is_dev else "production",
        "project_root": str(config.PROJECT_ROOT),
        "host": os.getenv("HOST", "unknown"),
        "port": os.getenv("PORT", "unknown"),
        "version": "0.1.0",
        "is_development": is_dev
    }

@app.get("/api/public/summaries")
async def list_public_summaries():
    """获取所有已生成的摘要文件列表供公开展示，无需认证。"""
    try:
        summaries = []
        video_url_map = {}
        
        if config.OUTPUT_DIR.exists():
            for md_file in config.OUTPUT_DIR.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    metadata = parse_metadata_from_md(content)
                    
                    title_cn = metadata.get("title_cn")
                    title_en = metadata.get("title_en", metadata.get("title", ""))
                    
                    if not title_cn:
                         for line in content.splitlines():
                            stripped = line.strip()
                            if stripped.startswith('# '):
                                title_cn = stripped[2:].strip()
                                break
                    
                    if not title_cn:
                        title_cn = title_en if title_en else md_file.stem
                    
                    doc_hash = filename_to_hash.get(md_file.name)
                    if not doc_hash:
                        continue
                    
                    pure_text = extract_text_from_markdown(content)
                    word_count = count_chinese_words(pure_text)
                    stat = md_file.stat()
                    
                    # 检查是否为PDF文档
                    video_url = metadata.get("video_url", "")
                    is_pdf = is_pdf_document(video_url)
                    
                    summary_data = {
                        "filename": md_file.name,
                        "title_cn": title_cn,
                        "title_en": title_en,
                        "size": stat.st_size,
                        "word_count": word_count,
                        "created_at": stat.st_ctime,
                        "modified_at": stat.st_mtime,
                        "upload_date": metadata.get("upload_date", "1970-01-01"),
                        "video_url": video_url,
                        "is_reinvent": metadata.get("is_reinvent", False),
                        "course_code": metadata.get("course_code"),
                        "level": metadata.get("level"),
                        "hash": doc_hash,
                        "version": metadata.get("version", 0),
                        "is_pdf": is_pdf,  # 添加PDF标识
                        "content_type": "PDF文档" if is_pdf else "YouTube视频"  # 内容类型
                    }
                    
                    video_url = metadata.get("video_url", "")
                    if video_url:
                        if video_url not in video_url_map:
                            video_url_map[video_url] = summary_data
                        else:
                            existing_version = video_url_map[video_url].get("version", 0)
                            new_version = summary_data.get("version", 0)
                            if new_version > existing_version:
                                video_url_map[video_url] = summary_data
                        
                except Exception as e:
                    logger.warning(f"处理文件 {md_file.name} 时出错: {e}")
        
        summaries.extend(video_url_map.values())
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

        # 获取视频URL以查找所有版本
        video_url = metadata.get("video_url", "")
        versions = []
        if video_url:
            versions = discover_versions(video_url)

        # 清理内容中的元数据
        cleaned_content = clean_content_metadata(content, title_cn)

        response_data = {
            "filename": filename,
            "title": title_cn,  # 保持向后兼容
            "title_cn": title_cn,
            "title_en": title_en,
            "content": cleaned_content,  # 返回清理后的内容
            "video_url": video_url,
            "versions": versions  # 添加版本信息
        }
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取公共摘要文件 '{filename}' 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="读取摘要文件失败")

@app.get("/api/public/doc/{doc_hash}")
async def get_public_summary_by_hash(doc_hash: str):
    """通过统一hash获取指定摘要文件的公开内容。"""
    filename = hash_to_filename.get(doc_hash)
    if not filename:
        raise HTTPException(status_code=404, detail="文档未找到")
    
    return await get_public_summary(filename)

@app.get("/api/public/doc/{doc_hash}/{version}")
async def get_public_summary_by_hash_and_version(doc_hash: str, version: int):
    """通过hash和version获取指定摘要文件的公开内容，无需认证。"""
    # 查找默认文件名以获取video_url
    default_filename = hash_to_filename.get(doc_hash)
    if not default_filename:
        raise HTTPException(status_code=404, detail="主文档未找到")
        
    default_file_path = config.OUTPUT_DIR / default_filename
    if not default_file_path.exists():
        raise HTTPException(status_code=404, detail="主文档文件不存在")

    content = default_file_path.read_text(encoding="utf-8")
    metadata = parse_metadata_from_md(content)
    video_url = metadata.get("video_url")

    if not video_url:
        # 如果没有video_url，说明没有多版本，直接返回当前文档
        if version == metadata.get("version", 1):
             return await get_public_summary(default_filename)
        else:
             raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")

    # 根据video_url和version查找目标文件名
    versions = discover_versions(video_url)
    target_version_info = next((v for v in versions if v.get("version") == version), None)

    if not target_version_info or not target_version_info.get("filename"):
        raise HTTPException(status_code=404, detail=f"版本 {version} 的文件未找到")

    # 复用现有的获取文档逻辑
    return await get_public_summary(target_version_info["filename"])

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
            script_path = Path(__file__).parent / "tools" / "generate_pdfs.py"
            logger.info(f"PDF生成脚本路径: {script_path}")
            logger.info(f"脚本是否存在: {script_path.exists()}")
            
            if not script_path.exists():
                logger.error(f"PDF生成工具不存在: {script_path}")
                logger.error(f"当前文件路径: {__file__}")
                logger.error(f"父目录内容: {list(Path(__file__).parent.iterdir())}")
                raise HTTPException(status_code=500, detail="PDF生成工具不存在")
            
            # 使用临时目录作为输出目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_pdf_path = Path(temp_dir) / pdf_filename
                
                # 执行PDF生成命令
                cmd = [
                    "python",
                    str(script_path),
                    "-f", str(md_file_path),
                    "-o", str(temp_dir),
                    "--css", str(config.PROJECT_ROOT / "web" / "css" / "pdf_style.css")
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"PDF生成命令执行失败")
                    logger.error(f"命令: {' '.join(cmd)}")
                    logger.error(f"返回码: {result.returncode}")
                    logger.error(f"标准输出: {result.stdout}")
                    logger.error(f"错误输出: {result.stderr}")
                    raise HTTPException(status_code=500, detail=f"PDF生成失败: {result.stderr or result.stdout or '未知错误'}")
                
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

        # 获取视频URL以查找所有版本
        video_url = metadata.get("video_url", "")
        versions = []
        if video_url:
            versions = discover_versions(video_url)

        # 清理内容中的元数据
        cleaned_content = clean_content_metadata(content, title_cn)

        return {
            "filename": filename,
            "title": title_cn,  # 保持向后兼容
            "title_cn": title_cn,
            "title_en": title_en,
            "content": cleaned_content,  # 返回清理后的内容
            "video_url": video_url,
            "versions": versions  # 添加版本信息
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取摘要文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="读取摘要文件失败")

@app.get("/api/admin/tasks/{task_id}/result")
def get_task_result_content(task_id: str, authorization: str = Header(None)):
    """获取指定任务的完整结果内容（管理员）"""
    verify_token(authorization)
    task = manager.get_task_state(task_id)
    if not task or task.status != "completed" or not task.result_path:
        raise HTTPException(status_code=404, detail="任务未完成或结果不可用")

    file_path = Path(task.result_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="结果文件未找到")

    return FileResponse(file_path, media_type="text/markdown", filename=file_path.name)

@app.post("/api/admin/refresh-cache", status_code=200)
def refresh_cache(authorization: str = Header(None)):
    """
    手动触发服务器端文档缓存的刷新。
    这将重新扫描摘要目录并重建哈希映射。
    """
    verify_token(authorization)
    try:
        logger.info("管理员手动触发缓存刷新...")
        init_hash_mappings()
        logger.info("服务器端缓存已成功刷新。")
        return {"message": "服务器端缓存已成功刷新。"}
    except Exception as e:
        logger.error(f"手动刷新缓存时发生错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"刷新缓存时发生内部错误: {e}")

@app.get("/api/health")
async def health_check():
    """
    系统健康检查端点（公开访问）
    检查主程序和 Cookie Manager 服务的状态
    """
    from .cookie_health_check import CookieHealthCheck
    
    try:
        checker = CookieHealthCheck()
        cookie_status = checker.perform_full_check()
        
        # 判断整体健康状态
        is_healthy = cookie_status['overall_status'] == 'healthy'
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "timestamp": cookie_status['timestamp'],
            "components": {
                "api": {
                    "status": "healthy",
                    "message": "API 服务运行正常"
                },
                "cookies": {
                    "status": cookie_status['overall_status'],
                    "service_running": cookie_status['service']['running'],
                    "file_status": cookie_status['file']['status'],
                    "content_valid": cookie_status['content']['valid'],
                    "issues": cookie_status['issues'],
                    "warnings": cookie_status['warnings']
                }
            }
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/api/admin/cookie-status")
async def get_cookie_status(authorization: str = Header(None)):
    """
    获取详细的 Cookie 状态（需要认证）
    """
    verify_token(authorization)
    
    from .cookie_health_check import CookieHealthCheck
    
    try:
        checker = CookieHealthCheck()
        result = checker.perform_full_check()
        recommendations = checker.get_recommendations(result)
        
        return {
            **result,
            "recommendations": recommendations
        }
    except Exception as e:
        logger.error(f"获取 Cookie 状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class DeleteSummaryRequest(BaseModel):
    filename: str

# --- Frontend Serving ---
web_dir = config.PROJECT_ROOT / "web"

if web_dir.is_dir():
    # Mount static file directories first.
    # This ensures that requests for /js/* and /css/* are handled by StaticFiles.
    # Any other static assets in the root of /web can be added here too.
    app.mount("/js", StaticFiles(directory=web_dir / "js"), name="js")
    app.mount("/css", StaticFiles(directory=web_dir / "css"), name="css")
    
    # Mount components directory for component system
    components_dir = web_dir / "components"
    if components_dir.is_dir():
        app.mount("/components", StaticFiles(directory=components_dir), name="components")
    
    # Mount test directory for component testing
    test_dir = web_dir / "test"
    if test_dir.is_dir():
        app.mount("/test", StaticFiles(directory=test_dir, html=True), name="test")
    
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

# 在API类中添加新的请求模型
class PDFAnalysisRequest(BaseModel):
    title: Optional[str] = None  # 可选的标题，如果为None则由AI生成

# 在API路由中添加新的端点
@app.post("/analyze-pdf")
async def analyze_pdf_endpoint(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    使用Gemini多模态能力分析PDF文件
    """
    verify_token(authorization)
    
    task_id = str(uuid.uuid4())
    
    try:
        # 创建临时文件保存上传的PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(await file.read())
            tmp_file_path = tmp_file.name
        
        # 创建异步任务处理PDF分析
        from .pdf_worker import pdf_analysis_worker_async
        
        # 处理标题：如果没有提供或只是文件名，让AI自动生成
        display_title = title or file.filename or "未命名文档"
        if display_title.lower().endswith('.pdf'):
            display_title = display_title[:-4]
        
        # 构造请求对象
        req = PDFAnalysisRequest(title=display_title)
        
        task = asyncio.create_task(pdf_analysis_worker_async(req, task_id, tmp_file_path))
        manager.create_task(task_id, task)
        
        return SummarizeResponse(task_id=task_id, message="PDF分析任务已创建，请连接 WebSocket。", status="created")
        
    except Exception as e:
        logger.error(f"处理上传PDF失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理上传PDF失败: {str(e)}")

def serve(host: str = "0.0.0.0", port: int = 8001, reload: bool = False):
    """使用 uvicorn 启动 Web 服务器。"""
    uvicorn.run(
        "reinvent_insight.api:app",
        host=host,
        port=port,
        reload=reload
    )

if __name__ == "__main__":
    # uvicorn.run("src.youtube_summarizer.api:app", host="0.0.0.0", port=8001, reload=True)
    uvicorn.run("src.reinvent_insight.api:app", host="0.0.0.0", port=8001, reload=True) 