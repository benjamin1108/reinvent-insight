from fastapi import FastAPI, HTTPException, Header, Request, Response, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
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
from typing import Set, Optional, Dict, List, AsyncGenerator
import json
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import re
import urllib.parse
from zhon import hanzi
import yaml
from datetime import datetime
from urllib.parse import quote

from .logger import setup_logger
from . import config
from .task_manager import manager # 导入共享的任务管理器
from .worker import summary_task_worker_async # 导入新的异步工作流
from .utils import generate_doc_hash, is_pdf_document, extract_pdf_hash  # 从 utils 导入
from .file_watcher import start_watching # 导入文件监控
from .pdf_processor import PDFProcessor  # 导入PDF处理器
from .services.tts_service import TTSService
from .services.audio_cache import AudioCache
from .model_config import get_model_client as get_model_client_by_task
from .audio import decode_base64_pcm, assemble_wav, calculate_audio_duration

setup_logger(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reinvent Insight API", description="YouTube 字幕深度摘要后端服务", version="0.1.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Range", "Content-Type"]
)

# TTS 服务和缓存实例（延迟初始化）
_tts_service: Optional[TTSService] = None
_audio_cache: Optional[AudioCache] = None


def get_tts_service() -> TTSService:
    """获取 TTS 服务实例（单例）"""
    global _tts_service
    if _tts_service is None:
        # 使用 TTS 任务类型获取模型客户端
        model_client = get_model_client_by_task("text_to_speech")
        _tts_service = TTSService(model_client)
    return _tts_service


async def start_visual_watcher():
    """启动可视化解读文件监测器"""
    # 检查配置开关
    visual_enabled = os.getenv("VISUAL_INTERPRETATION_ENABLED", "true").lower() == "true"
    
    if not visual_enabled:
        logger.info("可视化解读功能已禁用（VISUAL_INTERPRETATION_ENABLED=false）")
        return
    
    try:
        from .visual_watcher import VisualInterpretationWatcher
        
        watcher = VisualInterpretationWatcher(
            watch_dir=config.OUTPUT_DIR,
            model_name=config.PREFERRED_MODEL
        )
        
        # 在后台运行监测器
        asyncio.create_task(watcher.start_watching())
        logger.info("可视化解读文件监测器已启动")
        
    except Exception as e:
        logger.error(f"启动可视化解读监测器失败: {e}", exc_info=True)


async def start_tts_pregeneration():
    """启动 TTS 预生成服务"""
    # 检查配置开关
    if not config.TTS_PREGENERATE_ENABLED:
        logger.info("TTS 预生成服务已禁用（TTS_PREGENERATE_ENABLED=false）")
        return
    
    try:
        # 获取预生成服务
        pregeneration_service = get_tts_pregeneration_service()
        
        # 启动服务
        await pregeneration_service.start()
        logger.info("TTS 预生成服务已启动")
        
        # 启动文件监控
        from .file_watcher import start_tts_watching
        
        # 获取当前事件循环，以便在回调中使用
        loop = asyncio.get_running_loop()
        
        def tts_callback(file_path, article_hash, source_file):
            """TTS 预生成回调函数"""
            # 在事件循环中调度异步任务
            asyncio.run_coroutine_threadsafe(
                pregeneration_service.add_task(article_hash, source_file),
                loop
            )
        
        start_tts_watching(config.OUTPUT_DIR, tts_callback)
        logger.info("TTS 预生成文件监控器已启动")
        
    except Exception as e:
        logger.error(f"启动 TTS 预生成服务失败: {e}", exc_info=True)


@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行的事件。
    1. 初始化哈希映射缓存。
    2. 启动文件系统监控。
    3. 检查 Cookie 健康状态。
    4. 启动可视化解读文件监测器。
    5. 启动 TTS 预生成服务（仅处理手动触发，不监控文件）。
    """
    logger.info("应用启动，开始初始化...")
    # 1. 初始化缓存
    init_hash_mappings()
    
    # 2. 启动文件监控，并传入刷新缓存的回调函数
    start_watching(config.OUTPUT_DIR, init_hash_mappings)
    
    # 3. 检查 Cookie 健康状态
    from .cookie_health_check import check_and_warn
    check_and_warn()
    
    # 4. 启动可视化解读文件监测器
    await start_visual_watcher()
    
    # 5. 启动 TTS 预生成服务（仅处理手动任务，不启动文件监控）
    try:
        pregeneration_service = get_tts_pregeneration_service()
        await pregeneration_service.start()
        logger.info("TTS 预生成服务已启动（按需生成模式，未启动文件监控）")
    except Exception as e:
        logger.error(f"启动 TTS 预生成服务失败: {e}", exc_info=True)
    
    # 6. 启动 Worker Pool（任务队列系统）
    try:
        from .worker_pool import worker_pool
        await worker_pool.start()
        logger.info(
            f"✅ Worker Pool 已启动: "
            f"并发数={config.MAX_CONCURRENT_ANALYSIS_TASKS}, "
            f"队列容量={config.ANALYSIS_QUEUE_MAX_SIZE}"
        )
    except Exception as e:
        logger.error(f"启动 Worker Pool 失败: {e}", exc_info=True)

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
    skipped_count = 0
    error_count = 0
    
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
            else:
                skipped_count += 1
                logger.debug(f"跳过文件 {md_file.name}（无 video_url）")
        except Exception as e:
            error_count += 1
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

    log_msg = f"--- [重构] 统一Hash映射初始化完成，共处理 {len(hash_to_filename)} 个独立视频"
    if skipped_count > 0:
        log_msg += f"，跳过 {skipped_count} 个文件（无video_url）"
    if error_count > 0:
        log_msg += f"，{error_count} 个文件解析失败"
    log_msg += "。 ---"
    logger.info(log_msg)

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


def count_toc_chapters(content: str) -> int:
    """统计 TOC 中的章节数量
    
    只统计「### 主要目录」或「### 目录」区域内的章节数量
    格式如：1. 章节标题、2. 章节标题 等
    """
    # 先提取 TOC 区域（从 ### 主要目录 或 ### 目录 到下一个 ### 标题之间）
    toc_patterns = [
        r'###\s*主要目录\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
        r'###\s*目录\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
        r'###\s*Table of Contents\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
    ]
    
    toc_content = ""
    for pattern in toc_patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            toc_content = match.group(1)
            break
    
    if not toc_content:
        # 如果没找到TOC区域，返回0
        return 0
    
    # 在 TOC 区域内统计编号列表项
    chapters = re.findall(r'^\d+\.\s+.+', toc_content, re.MULTILINE)
    return len(chapters)


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
async def summarize_endpoint(
    req: SummarizeRequest, 
    priority: int = 0,  # 新增优先级参数（0=LOW, 1=NORMAL, 2=HIGH, 3=URGENT）
    force: bool = Query(default=False),  # 新增：是否强制重新解读
    authorization: str = Header(None)
):
    """
    接收 URL，创建或重新连接到后台任务。
    
    现在使用任务队列系统，支持：
    - 优先级排序（priority: 0-3）
    - 并发控制（最大 {config.MAX_CONCURRENT_ANALYSIS_TASKS} 个并发）
    - 队列管理（最大 {config.ANALYSIS_QUEUE_MAX_SIZE} 个等待任务）
    - 重复检测（force=false时检查是否已存在）
    """
    verify_token(authorization)
    
    # 如果提供了 task_id，检查是否已存在
    if req.task_id and manager.get_task_state(req.task_id):
        task_id = req.task_id
        logger.info(f"客户端正在尝试重新连接到任务: {task_id}")
        return SummarizeResponse(
            task_id=task_id, 
            message="任务恢复中，请连接 WebSocket。", 
            status="reconnected"
        )

    # 检查是否已存在（除非force=true）
    if not force:
        try:
            from .downloader import normalize_youtube_url
            url_str = str(req.url)
            
            # 标准化URL并提取video_id
            normalized_url, url_metadata = normalize_youtube_url(url_str)
            video_id = url_metadata.get('video_id')
            
            if video_id:
                # 生成标准化URL的doc_hash
                doc_hash = generate_doc_hash(normalized_url)
                
                # 检查文档是否存在
                filename = hash_to_filename.get(doc_hash)
                if filename:
                    logger.info(f"检测到重复视频: video_id={video_id}, doc_hash={doc_hash}")
                    # 读取文档元数据
                    file_path = config.OUTPUT_DIR / filename
                    if file_path.exists():
                        content = file_path.read_text(encoding="utf-8")
                        metadata = parse_metadata_from_md(content)
                        title = metadata.get("title_cn") or metadata.get("title_en", "未知标题")
                        
                        return {
                            "exists": True,
                            "doc_hash": doc_hash,
                            "title": title,
                            "message": "该视频已有解读，请使用查看功能或添加force=true参数重新解读",
                            "redirect_url": f"/article/{doc_hash}"
                        }
                
                # 检查任务队列中是否已有相同视频的任务
                from .worker_pool import worker_pool
                for queued_task in worker_pool.task_queue:
                    if queued_task.task_type == 'youtube':
                        try:
                            task_url, task_metadata = normalize_youtube_url(queued_task.url_or_path)
                            if task_metadata.get('video_id') == video_id:
                                logger.info(f"检测到队列中已有相同视频: video_id={video_id}")
                                return {
                                    "exists": True,
                                    "in_queue": True,
                                    "task_id": queued_task.task_id,
                                    "message": "该视频的分析任务已在队列中，请稍候"
                                }
                        except:
                            pass
                
                # 检查进行中的任务
                for task_id_check, task_state in manager.tasks.items():
                    if hasattr(task_state, 'url_or_path') and task_state.url_or_path:
                        try:
                            task_url, task_metadata = normalize_youtube_url(task_state.url_or_path)
                            if task_metadata.get('video_id') == video_id and task_state.status in ['processing', 'running', 'queued']:
                                logger.info(f"检测到进行中的相同视频任务: video_id={video_id}")
                                return {
                                    "exists": True,
                                    "in_progress": True,
                                    "task_id": task_id_check,
                                    "message": "该视频正在分析中，请连接WebSocket查看进度"
                                }
                        except:
                            pass
        except Exception as e:
            logger.warning(f"重复检测失败: {e}")
            # 重复检测失败不影响继续分析

    task_id = str(uuid.uuid4())
    
    # 先在 manager 中创建占位状态
    from .task_manager import TaskState
    state = TaskState(task_id=task_id, status="queued", task=None)
    # 保存URL用于重复检测
    state.url_or_path = str(req.url)
    manager.tasks[task_id] = state
    
    # 映射优先级值
    from .worker_pool import worker_pool, TaskPriority
    priority_map = {
        0: TaskPriority.LOW,
        1: TaskPriority.NORMAL,
        2: TaskPriority.HIGH,
        3: TaskPriority.URGENT
    }
    task_priority = priority_map.get(priority, TaskPriority.NORMAL)
    
    # 添加到队列
    success = await worker_pool.add_task(
        task_id=task_id,
        task_type="youtube",
        url_or_path=str(req.url),
        priority=task_priority
    )
    
    if not success:
        # 队列已满，返回错误
        del manager.tasks[task_id]
        raise HTTPException(
            status_code=503, 
            detail=f"任务队列已满（{config.ANALYSIS_QUEUE_MAX_SIZE} 个任务），请稍后重试"
        )
    
    # 返回队列信息
    queue_size = worker_pool.get_queue_size()
    return SummarizeResponse(
        task_id=task_id, 
        message=f"任务已加入队列（优先级: {task_priority.name}，排队: {queue_size} 个任务），请连接 WebSocket。", 
        status="created"
    )

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
                    
                    # 优先级：metadata的created_at > metadata的upload_date > 文件系统时间
                    created_at_value = stat.st_ctime
                    modified_at_value = stat.st_mtime
                    
                    # 1. 尝试从metadata中获取created_at（ISO格式字符串）
                    if metadata.get("created_at"):
                        try:
                            # 解析ISO格式时间字符串为时间戳
                            dt = datetime.fromisoformat(metadata.get("created_at").replace('Z', '+00:00'))
                            created_at_value = dt.timestamp()
                            modified_at_value = created_at_value
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"解析文件 {md_file.name} 的created_at失败: {e}")
                    
                    # 2. 如果没有created_at，尝试使用upload_date（YYYYMMDD格式）
                    elif metadata.get("upload_date"):
                        try:
                            upload_date_str = str(metadata.get("upload_date"))
                            # 解析YYYYMMDD格式，例如 "20241102" 或 "2024-11-02"
                            upload_date_str = upload_date_str.replace('-', '')
                            if len(upload_date_str) == 8:
                                year = int(upload_date_str[0:4])
                                month = int(upload_date_str[4:6])
                                day = int(upload_date_str[6:8])
                                dt = datetime(year, month, day)
                                created_at_value = dt.timestamp()
                                modified_at_value = created_at_value
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"解析文件 {md_file.name} 的upload_date失败: {e}")
                    
                    summary_data = {
                        "filename": md_file.name,
                        "title_cn": title_cn,
                        "title_en": title_en,
                        "size": stat.st_size,
                        "word_count": word_count,
                        "created_at": created_at_value,
                        "modified_at": modified_at_value,
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


@app.get("/api/public/summary/{video_id}")
async def check_summary_by_video_id(video_id: str):
    """
    根据 YouTube video_id 查询是否存在已解析的深度解读。
    
    Args:
        video_id: YouTube 视频 ID（11位字符）
        
    Returns:
        {
            "exists": true/false,
            "hash": "doc_hash" | null,
            "title": "视频标题" | null
        }
    """
    import re
    
    # 验证 video_id 格式（11位字母数字、下划线、连字符）
    if not video_id or not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        return {
            "exists": False,
            "hash": None,
            "title": None,
            "error": "无效的 video_id 格式"
        }
    
    # 根据 video_id 构建标准化 URL
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # 生成 doc_hash
    doc_hash = generate_doc_hash(video_url)
    
    if not doc_hash:
        return {
            "exists": False,
            "hash": None,
            "title": None
        }
    
    # 检查文档是否存在
    filename = hash_to_filename.get(doc_hash)
    if not filename:
        return {
            "exists": False,
            "hash": None,
            "title": None
        }
    
    # 获取标题
    try:
        file_path = config.OUTPUT_DIR / filename
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            title = metadata.get("title_cn") or metadata.get("title_en") or metadata.get("title", "")
            
            return {
                "exists": True,
                "hash": doc_hash,
                "title": title
            }
    except Exception as e:
        logger.warning(f"读取文档 {filename} 失败: {e}")
    
    return {
        "exists": False,
        "hash": None,
        "title": None
    }

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


@app.delete("/api/summaries/{doc_hash}")
async def delete_summary(doc_hash: str, authorization: str = Header(None)):
    """
    软删除指定文章（移动到回收站，可恢复）。
    
    移动内容包括：
    - 所有版本的 Markdown 文件
    - 对应的 PDF 文件
    - 可视化解读 HTML 文件
    """
    verify_token(authorization)
    
    # 检查文档是否存在
    versions = hash_to_versions.get(doc_hash, [])
    default_filename = hash_to_filename.get(doc_hash)
    
    if not default_filename and not versions:
        raise HTTPException(status_code=404, detail="文档未找到")
    
    # 创建回收站目录
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    trash_dir.mkdir(exist_ok=True)
    trash_pdf_dir = trash_dir / "pdfs"
    trash_pdf_dir.mkdir(exist_ok=True)
    
    moved_files = []
    errors = []
    
    # 获取要移动的所有文件名（包括所有版本）
    files_to_move = list(versions) if versions else ([default_filename] if default_filename else [])
    
    import shutil
    from datetime import datetime
    
    # 生成删除时间戳，用于避免文件名冲突
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for filename in files_to_move:
        base_name = Path(filename).stem
        
        # 1. 移动 Markdown 文件
        md_path = config.OUTPUT_DIR / filename
        if md_path.exists():
            try:
                # 添加时间戳和 doc_hash 前缀，方便恢复
                trash_filename = f"{doc_hash}_{timestamp}_{filename}"
                trash_path = trash_dir / trash_filename
                shutil.move(str(md_path), str(trash_path))
                moved_files.append(str(trash_path))
                logger.info(f"已移动到回收站: {filename} -> {trash_filename}")
            except Exception as e:
                errors.append(f"移动 {filename} 失败: {str(e)}")
                logger.error(f"移动 Markdown 文件失败: {e}")
        
        # 2. 移动 PDF 文件
        pdf_dir = config.OUTPUT_DIR.parent / "pdfs"
        pdf_filename = filename.replace('.md', '.pdf')
        pdf_path = pdf_dir / pdf_filename
        if pdf_path.exists():
            try:
                trash_pdf_filename = f"{doc_hash}_{timestamp}_{pdf_filename}"
                trash_pdf_path = trash_pdf_dir / trash_pdf_filename
                shutil.move(str(pdf_path), str(trash_pdf_path))
                moved_files.append(str(trash_pdf_path))
                logger.info(f"已移动 PDF 到回收站: {pdf_filename}")
            except Exception as e:
                errors.append(f"移动 PDF {pdf_filename} 失败: {str(e)}")
                logger.error(f"移动 PDF 文件失败: {e}")
        
        # 3. 移动可视化 HTML 文件
        visual_filename = f"{base_name}_visual.html"
        visual_path = config.OUTPUT_DIR / visual_filename
        if visual_path.exists():
            try:
                trash_visual_filename = f"{doc_hash}_{timestamp}_{visual_filename}"
                trash_visual_path = trash_dir / trash_visual_filename
                shutil.move(str(visual_path), str(trash_visual_path))
                moved_files.append(str(trash_visual_path))
                logger.info(f"已移动可视化文件到回收站: {visual_filename}")
            except Exception as e:
                errors.append(f"移动可视化文件 {visual_filename} 失败: {str(e)}")
                logger.error(f"移动可视化文件失败: {e}")
    
    # 4. 更新缓存映射
    if doc_hash in hash_to_filename:
        del hash_to_filename[doc_hash]
    if doc_hash in hash_to_versions:
        del hash_to_versions[doc_hash]
    for filename in files_to_move:
        if filename in filename_to_hash:
            del filename_to_hash[filename]
    
    # 返回结果
    if not moved_files and errors:
        raise HTTPException(status_code=500, detail=f"删除失败: {'; '.join(errors)}")
    
    return {
        "success": True,
        "message": f"已移动 {len(moved_files)} 个文件到回收站",
        "deleted_files": moved_files,
        "errors": errors if errors else None
    }


# ========== 回收站管理 API ==========

@app.get("/api/admin/trash")
async def list_trash(authorization: str = Header(None)):
    """获取回收站中的文章列表（需要认证）"""
    verify_token(authorization)
    
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    if not trash_dir.exists():
        return {"items": []}
    
    items = []
    seen_hashes = {}  # 用于去重，只显示每个 doc_hash 的最新删除记录
    
    for md_file in trash_dir.glob("*.md"):
        try:
            # 解析文件名: {doc_hash}_{timestamp}_{original_filename}
            name_parts = md_file.name.split("_", 2)
            if len(name_parts) >= 3:
                doc_hash = name_parts[0]
                timestamp = name_parts[1]
                original_filename = name_parts[2]
            else:
                continue
            
            # 读取元数据
            content = md_file.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            
            title_cn = metadata.get("title_cn", "")
            title_en = metadata.get("title_en", metadata.get("title", ""))
            
            if not title_cn:
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith('# '):
                        title_cn = stripped[2:].strip()
                        break
            
            if not title_cn:
                title_cn = title_en if title_en else md_file.stem
            
            # 解析删除时间
            try:
                deleted_at = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                deleted_at_str = deleted_at.isoformat()
            except:
                deleted_at_str = timestamp
            
            item_data = {
                "doc_hash": doc_hash,
                "original_filename": original_filename,
                "trash_filename": md_file.name,
                "title_cn": title_cn,
                "title_en": title_en,
                "deleted_at": deleted_at_str,
                "size": md_file.stat().st_size
            }
            
            # 只保留每个 doc_hash 的最新删除记录
            if doc_hash not in seen_hashes or timestamp > seen_hashes[doc_hash]["timestamp"]:
                seen_hashes[doc_hash] = {"data": item_data, "timestamp": timestamp}
                
        except Exception as e:
            logger.warning(f"解析回收站文件 {md_file.name} 失败: {e}")
    
    # 提取去重后的数据
    items = [v["data"] for v in seen_hashes.values()]
    
    # 按删除时间倒序排序
    items.sort(key=lambda x: x["deleted_at"], reverse=True)
    
    return {"items": items}


@app.post("/api/admin/trash/{doc_hash}/restore")
async def restore_from_trash(doc_hash: str, authorization: str = Header(None)):
    """从回收站恢复文章（需要认证）"""
    verify_token(authorization)
    
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    trash_pdf_dir = trash_dir / "pdfs"
    
    if not trash_dir.exists():
        raise HTTPException(status_code=404, detail="回收站为空")
    
    import shutil
    restored_files = []
    errors = []
    
    # 查找该 doc_hash 对应的所有文件
    pattern = f"{doc_hash}_*"
    
    # 恢复 Markdown 和 HTML 文件
    for trash_file in trash_dir.glob(pattern):
        if trash_file.is_file():
            try:
                # 解析原始文件名
                name_parts = trash_file.name.split("_", 2)
                if len(name_parts) >= 3:
                    original_filename = name_parts[2]
                else:
                    original_filename = trash_file.name
                
                # 确定目标路径
                restore_path = config.OUTPUT_DIR / original_filename
                
                # 移动文件
                shutil.move(str(trash_file), str(restore_path))
                restored_files.append(original_filename)
                logger.info(f"已恢复文件: {original_filename}")
                
            except Exception as e:
                errors.append(f"恢复 {trash_file.name} 失败: {str(e)}")
                logger.error(f"恢复文件失败: {e}")
    
    # 恢复 PDF 文件
    if trash_pdf_dir.exists():
        pdf_dir = config.OUTPUT_DIR.parent / "pdfs"
        pdf_dir.mkdir(exist_ok=True)
        
        for trash_pdf in trash_pdf_dir.glob(pattern):
            if trash_pdf.is_file():
                try:
                    name_parts = trash_pdf.name.split("_", 2)
                    if len(name_parts) >= 3:
                        original_filename = name_parts[2]
                    else:
                        original_filename = trash_pdf.name
                    
                    restore_path = pdf_dir / original_filename
                    shutil.move(str(trash_pdf), str(restore_path))
                    restored_files.append(f"pdfs/{original_filename}")
                    logger.info(f"已恢复 PDF: {original_filename}")
                    
                except Exception as e:
                    errors.append(f"恢复 PDF {trash_pdf.name} 失败: {str(e)}")
                    logger.error(f"恢复 PDF 失败: {e}")
    
    if not restored_files:
        raise HTTPException(status_code=404, detail="回收站中未找到该文档")
    
    # 刷新缓存映射
    init_hash_mappings()
    
    return {
        "success": True,
        "message": f"已恢复 {len(restored_files)} 个文件",
        "restored_files": restored_files,
        "errors": errors if errors else None
    }


@app.delete("/api/admin/trash/{doc_hash}")
async def permanently_delete_from_trash(doc_hash: str, authorization: str = Header(None)):
    """从回收站永久删除文章（需要认证）"""
    verify_token(authorization)
    
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    trash_pdf_dir = trash_dir / "pdfs"
    
    if not trash_dir.exists():
        raise HTTPException(status_code=404, detail="回收站为空")
    
    deleted_files = []
    errors = []
    
    pattern = f"{doc_hash}_*"
    
    # 删除 Markdown 和 HTML 文件
    for trash_file in trash_dir.glob(pattern):
        if trash_file.is_file():
            try:
                trash_file.unlink()
                deleted_files.append(trash_file.name)
                logger.info(f"已永久删除: {trash_file.name}")
            except Exception as e:
                errors.append(f"删除 {trash_file.name} 失败: {str(e)}")
                logger.error(f"永久删除失败: {e}")
    
    # 删除 PDF 文件
    if trash_pdf_dir.exists():
        for trash_pdf in trash_pdf_dir.glob(pattern):
            if trash_pdf.is_file():
                try:
                    trash_pdf.unlink()
                    deleted_files.append(f"pdfs/{trash_pdf.name}")
                    logger.info(f"已永久删除 PDF: {trash_pdf.name}")
                except Exception as e:
                    errors.append(f"删除 PDF {trash_pdf.name} 失败: {str(e)}")
                    logger.error(f"永久删除 PDF 失败: {e}")
    
    # 删除 TTS 缓存
    try:
        audio_cache_dir = config.OUTPUT_DIR.parent / "tts_cache" / doc_hash
        if audio_cache_dir.exists():
            import shutil
            shutil.rmtree(audio_cache_dir)
            deleted_files.append(f"tts_cache/{doc_hash}")
            logger.info(f"已删除 TTS 缓存: {doc_hash}")
    except Exception as e:
        errors.append(f"删除 TTS 缓存失败: {str(e)}")
        logger.error(f"删除 TTS 缓存失败: {e}")
    
    if not deleted_files:
        raise HTTPException(status_code=404, detail="回收站中未找到该文档")
    
    return {
        "success": True,
        "message": f"已永久删除 {len(deleted_files)} 个文件",
        "deleted_files": deleted_files,
        "errors": errors if errors else None
    }


@app.delete("/api/admin/trash")
async def empty_trash(authorization: str = Header(None)):
    """清空回收站（需要认证）"""
    verify_token(authorization)
    
    trash_dir = config.OUTPUT_DIR.parent / "trash"
    
    if not trash_dir.exists():
        return {"success": True, "message": "回收站已为空"}
    
    import shutil
    
    try:
        # 收集所有需要删除的 TTS 缓存
        doc_hashes = set()
        for f in trash_dir.glob("*.md"):
            parts = f.name.split("_", 2)
            if len(parts) >= 1:
                doc_hashes.add(parts[0])
        
        # 删除回收站目录
        shutil.rmtree(trash_dir)
        logger.info("已清空回收站")
        
        # 删除对应的 TTS 缓存
        for doc_hash in doc_hashes:
            audio_cache_dir = config.OUTPUT_DIR.parent / "tts_cache" / doc_hash
            if audio_cache_dir.exists():
                shutil.rmtree(audio_cache_dir)
                logger.info(f"已删除 TTS 缓存: {doc_hash}")
        
        return {
            "success": True,
            "message": f"已清空回收站，删除了 {len(doc_hashes)} 篇文章的相关文件"
        }
    except Exception as e:
        logger.error(f"清空回收站失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空回收站失败: {str(e)}")

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


@app.get("/api/article/{doc_hash}/visual")
async def get_visual_interpretation(doc_hash: str, version: Optional[int] = None):
    """
    获取文章的可视化解读 HTML（版本跟随深度解读）
    
    Args:
        doc_hash: 文档哈希
        version: 可选的版本号（如果不指定，使用默认版本）
        
    Returns:
        HTML 内容或错误信息
    """
    try:
        # 获取文章文件名（可能包含版本号）
        if version is not None:
            # 如果指定了版本，从版本列表中查找
            versions = hash_to_versions.get(doc_hash, [])
            filename = None
            for v_filename in versions:
                if f"_v{version}.md" in v_filename or (version == 0 and "_v" not in v_filename):
                    filename = v_filename
                    break
            if not filename:
                raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")
        else:
            # 使用默认版本
            filename = hash_to_filename.get(doc_hash)
            if not filename:
                raise HTTPException(status_code=404, detail="文章未找到")
        
        # 构建可视化 HTML 文件路径（保持与深度解读相同的版本号）
        base_name = Path(filename).stem
        visual_filename = f"{base_name}_visual.html"
        visual_path = config.OUTPUT_DIR / visual_filename
        
        if not visual_path.exists():
            raise HTTPException(status_code=404, detail="可视化解读尚未生成")
        
        # 读取 HTML 内容
        html_content = visual_path.read_text(encoding="utf-8")
        
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Cache-Control": "public, max-age=3600",
                # 更新 CSP 策略以允许可视化 HTML 所需的外部资源
                # 包含国内 CDN 镜像和原始 CDN
                "Content-Security-Policy": (
                    "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
                    "https://fonts.googleapis.com https://fonts.gstatic.com "
                    "https://fonts.loli.net https://gstatic.loli.net "
                    "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
                    "https://cdnjs.cloudflare.com "
                    "https://lf26-cdn-tos.bytecdntp.com https://lf6-cdn-tos.bytecdntp.com "
                    "https://unpkg.com https://cdn.bootcdn.net; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                    "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
                    "https://cdnjs.cloudflare.com "
                    "https://lf26-cdn-tos.bytecdntp.com https://lf6-cdn-tos.bytecdntp.com "
                    "https://unpkg.com https://cdn.bootcdn.net; "
                    "style-src 'self' 'unsafe-inline' "
                    "https://fonts.googleapis.com https://fonts.loli.net "
                    "https://cdnjs.cloudflare.com https://cdn.bootcdn.net; "
                    "font-src 'self' https://fonts.gstatic.com https://gstatic.loli.net "
                    "https://cdnjs.cloudflare.com https://cdn.bootcdn.net; "
                    "img-src 'self' data: https:;"
                )
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可视化解读失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")


@app.get("/api/article/{doc_hash}/visual/status")
async def get_visual_status(doc_hash: str, version: Optional[int] = None):
    """
    获取可视化解读的生成状态（版本跟随深度解读）
    
    Args:
        doc_hash: 文档哈希
        version: 可选的版本号（如果不指定，使用默认版本）
        
    Returns:
        状态信息: {status: 'pending'|'processing'|'completed'|'failed', version: int}
    """
    try:
        # 获取文章文件名（可能包含版本号）
        if version is not None:
            # 如果指定了版本，从版本列表中查找
            versions = hash_to_versions.get(doc_hash, [])
            filename = None
            for v_filename in versions:
                if f"_v{version}.md" in v_filename or (version == 0 and "_v" not in v_filename):
                    filename = v_filename
                    break
            if not filename:
                raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")
        else:
            # 使用默认版本
            filename = hash_to_filename.get(doc_hash)
            if not filename:
                raise HTTPException(status_code=404, detail="文章未找到")
        
        # 读取文章元数据
        article_path = config.OUTPUT_DIR / filename
        content = article_path.read_text(encoding="utf-8")
        
        # 解析元数据
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                metadata = yaml.safe_load(parts[1])
                visual_info = metadata.get("visual_interpretation", {})
                
                # 提取当前文件的版本号
                import re
                version_match = re.search(r'_v(\d+)\.md$', filename)
                current_version = int(version_match.group(1)) if version_match else 0
                
                return {
                    "status": visual_info.get("status", "pending"),
                    "file": visual_info.get("file"),
                    "generated_at": visual_info.get("generated_at"),
                    "version": current_version
                }
        
        return {"status": "pending", "version": 0}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可视化状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")


# ========== Ultra DeepInsight API ==========

@app.get("/api/article/{doc_hash}/ultra-deep/status")
async def get_ultra_deep_status(doc_hash: str):
    """
    检查Ultra DeepInsight版本的状态
    
    Args:
        doc_hash: 文档哈希
        
    Returns:
        Ultra版本状态信息
    """
    try:
        # 首先检查任务队列中是否有Ultra生成任务
        from .worker_pool import worker_pool
        
        # 检查正在执行的任务（processing_tasks）
        try:
            for task_id, task in worker_pool.processing_tasks.items():
                if hasattr(task, 'task_type') and task.task_type == 'ultra_deep_insight':
                    if hasattr(task, 'doc_hash') and task.doc_hash == doc_hash:
                        return {
                            "exists": False,
                            "status": "generating",
                            "task_info": {
                                "task_id": task_id,
                                "created_at": getattr(task, 'created_at', None),
                                "current_stage": "正在生成中..."
                            },
                            "version": None,
                            "word_count": None
                        }
        except Exception as proc_err:
            logger.warning(f"检查正在执行的任务时出错: {proc_err}")
        
        # 检查排队任务（使用 queue._queue 访问内部队列）
        try:
            queue_items = list(worker_pool.queue._queue) if hasattr(worker_pool.queue, '_queue') else []
            for queued_task in queue_items:
                # PriorityQueue 中的元素可能是元组 (priority, task) 或直接是 task
                task = queued_task[1] if isinstance(queued_task, tuple) else queued_task
                if hasattr(task, 'task_type') and task.task_type == 'ultra_deep_insight':
                    if hasattr(task, 'doc_hash') and task.doc_hash == doc_hash:
                        return {
                            "exists": False,
                            "status": "generating",
                            "task_info": {
                                "task_id": getattr(task, 'task_id', None),
                                "created_at": getattr(task, 'created_at', None),
                                "queue_position": getattr(task, 'queue_position', 0),
                                "current_stage": "排队中..."
                            },
                            "version": None,
                            "word_count": None
                        }
        except Exception as queue_err:
            logger.warning(f"检查队列任务时出错: {queue_err}")
        
        # 检查进行中的任务
        for task_id, task_state in manager.tasks.items():
            if (hasattr(task_state, 'is_ultra_deep') and 
                task_state.is_ultra_deep and
                hasattr(task_state, 'doc_hash') and 
                task_state.doc_hash == doc_hash and
                task_state.status in ['queued', 'running', 'processing']):
                
                progress = getattr(task_state, 'progress', 0)
                current_stage = getattr(task_state, 'current_stage', 'Ultra生成中...')
                
                return {
                    "exists": False,
                    "status": "generating",
                    "task_info": {
                        "task_id": task_id,
                        "created_at": getattr(task_state, 'created_at', None),
                        "progress": progress,
                        "current_stage": current_stage
                    },
                    "version": None,
                    "word_count": None
                }
        
        # 查找该doc_hash的所有版本
        versions = hash_to_versions.get(doc_hash, [])
        
        if not versions:
            return {
                "exists": False,
                "status": "not_exists",
                "version": None,
                "filename": None,
                "word_count": None,
                "generated_at": None
            }
        
        # 遍历所有版本，查承Ultra版本
        for filename in versions:
            try:
                file_path = config.OUTPUT_DIR / filename
                if not file_path.exists():
                    continue
                    
                content = file_path.read_text(encoding="utf-8")
                metadata = parse_metadata_from_md(content)
                
                # 检查是否为Ultra版本
                if metadata.get("is_ultra_deep", False):
                    # 提取版本号
                    version_match = re.search(r'_v(\d+)\.md$', filename)
                    version_num = int(version_match.group(1)) if version_match else 0
                    
                    # 计算字数
                    pure_text = extract_text_from_markdown(content)
                    word_count = count_chinese_words(pure_text)
                    
                    return {
                        "exists": True,
                        "status": "completed",
                        "version": version_num,
                        "filename": filename,
                        "word_count": word_count,
                        "chapter_count": metadata.get("chapter_count"),
                        "generated_at": metadata.get("created_at")
                    }
            except Exception as e:
                logger.warning(f"解析文件 {filename} 时出错: {e}")
                continue
        
        # 没有找到带 is_ultra_deep 标记的版本
        # 检查默认版本的章节数，如果超过15章则视为Ultra
        default_filename = hash_to_filename.get(doc_hash)
        if default_filename:
            try:
                default_file_path = config.OUTPUT_DIR / default_filename
                if default_file_path.exists():
                    default_content = default_file_path.read_text(encoding="utf-8")
                    chapter_count = count_toc_chapters(default_content)
                    
                    if chapter_count > 15:
                        # 章节数超过15，视为已是Ultra级别内容
                        version_match = re.search(r'_v(\d+)\.md$', default_filename)
                        version_num = int(version_match.group(1)) if version_match else 0
                        
                        pure_text = extract_text_from_markdown(default_content)
                        word_count = count_chinese_words(pure_text)
                        
                        return {
                            "exists": True,
                            "status": "completed",
                            "version": version_num,
                            "filename": default_filename,
                            "word_count": word_count,
                            "chapter_count": chapter_count,
                            "generated_at": parse_metadata_from_md(default_content).get("created_at"),
                            "reason": "章节数超过15章，已是深度内容"
                        }
            except Exception as e:
                logger.warning(f"检查默认文件章节数时出错: {e}")
        
        return {
            "exists": False,
            "status": "not_exists",
            "version": None,
            "filename": None,
            "word_count": None,
            "generated_at": None
        }
        
    except Exception as e:
        logger.error(f"获取Ultra状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")


@app.post("/api/article/{doc_hash}/ultra-deep")
async def trigger_ultra_deep_generation(doc_hash: str, authorization: str = Header(None)):
    """
    触发Ultra DeepInsight生成任务
    
    Args:
        doc_hash: 文档哈希
        authorization: 认证令牌
        
    Returns:
        任务创建结果
    """
    verify_token(authorization)
    
    try:
        # 1. 检查文档是否存在
        default_filename = hash_to_filename.get(doc_hash)
        if not default_filename:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        # 2. 读取标准版本的内容和元数据
        file_path = config.OUTPUT_DIR / default_filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文档文件不存在")
        
        content = file_path.read_text(encoding="utf-8")
        metadata = parse_metadata_from_md(content)
        
        # 3. 检查章节数是否符合要求（不超过15章）
        chapter_count = count_toc_chapters(content)
        
        if chapter_count > 15:
            raise HTTPException(
                status_code=400, 
                detail=f"该文章已有{chapter_count}个章节，已是深度内容，不需要生成Ultra DeepInsight"
            )
        
        # 4. 检查是否已存在Ultra版本
        ultra_status = await get_ultra_deep_status(doc_hash)
        if ultra_status["exists"]:
            raise HTTPException(
                status_code=400,
                detail="该文章已存在Ultra DeepInsight版本"
            )
        
        # 5. 获取原始视频URL或文档路径
        video_url = metadata.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="无法获取原始内容来源")
        
        # 6. 确定新版本号
        versions = hash_to_versions.get(doc_hash, [])
        version_numbers = []
        for v_filename in versions:
            version_match = re.search(r'_v(\d+)\.md$', v_filename)
            if version_match:
                version_numbers.append(int(version_match.group(1)))
            elif "_v" not in v_filename:
                version_numbers.append(0)
        
        next_version = max(version_numbers) + 1 if version_numbers else 1
        
        # 7. 创建任务ID
        task_id = str(uuid.uuid4())
        
        # 8. 在manager中创建占位状态
        from .task_manager import TaskState
        state = TaskState(task_id=task_id, status="queued", task=None)
        state.doc_hash = doc_hash  # 添加doc_hash用于状态查询
        state.is_ultra_deep = True  # 标记为Ultra任务
        manager.tasks[task_id] = state
        
        # 9. 添加到任务队列
        from .worker_pool import worker_pool, TaskPriority
        
        success = await worker_pool.add_task(
            task_id=task_id,
            task_type="ultra_deep_insight",
            url_or_path=video_url,
            priority=TaskPriority.LOW,
            # 额外参数
            doc_hash=doc_hash,
            base_version=metadata.get("version", 0),
            next_version=next_version
        )
        
        if not success:
            del manager.tasks[task_id]
            raise HTTPException(
                status_code=503,
                detail=f"任务队列已满，请稍后重试"
            )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Ultra DeepInsight生成任务已启动",
            "estimated_time": "15-20分钟",
            "target_version": next_version,
            "current_chapter_count": chapter_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发Ultra生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@app.get("/api/public/summaries/{filename}/markdown")
async def get_summary_markdown(filename: str):
    """获取指定摘要的原始 Markdown 文件（去除元数据），无需认证。"""
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
        
        # 读取原始内容
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
        
        # 清理内容中的元数据
        cleaned_content = clean_content_metadata(content, title_cn)
        
        # 添加标题到内容开头
        full_content = ''
        if title_en:
            full_content += f"# {title_en}\n\n"
        if title_cn and title_cn != title_en:
            full_content += f"{title_cn}\n\n"
        full_content += cleaned_content
        
        # 生成安全的文件名
        safe_title = title_en or title_cn or file_path.stem
        safe_title = safe_title.replace('/', '-').replace('\\', '-').replace(':', '-')
        safe_title = re.sub(r'[<>:"/\\|?*]', '-', safe_title)
        safe_title = re.sub(r'\s+', '_', safe_title)
        safe_title = safe_title[:100]  # 限制长度
        download_filename = f"{safe_title}.md"
        
        # 对文件名进行 URL 编码
        encoded_filename = quote(download_filename, safe='')
        
        return Response(
            content=full_content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Markdown 文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Markdown 文件失败: {str(e)}")


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

async def generate_sse_stream(task_id: str, request: Request) -> AsyncGenerator[str, None]:
    """
    SSE 流式响应生成器
    
    Args:
        task_id: 任务ID
        request: FastAPI Request 对象，用于检测客户端断开
        
    Yields:
        str: SSE 格式的消息字符串
    """
    try:
        # 注册 SSE 连接，获取消息队列
        queue = await manager.register_sse_connection(task_id)
        logger.info(f"开始为任务 {task_id} 生成 SSE 流")
        
        # 持续从队列读取消息并发送
        while True:
            # 检查客户端是否断开连接
            if await request.is_disconnected():
                logger.info(f"客户端断开连接，停止 SSE 流: {task_id}")
                break
            
            try:
                # 从队列获取消息，设置超时避免无限等待
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                
                # 格式化为 SSE 格式
                # SSE 格式: event: message\ndata: {json}\n\n
                sse_message = f"event: message\ndata: {json.dumps(message, ensure_ascii=False)}\n\n"
                yield sse_message
                
                # 如果是结果或错误消息，任务已完成，关闭连接
                if message.get("type") in ["result", "error"]:
                    logger.info(f"任务 {task_id} 已完成，关闭 SSE 流")
                    break
                    
            except asyncio.TimeoutError:
                # 超时后发送心跳保持连接
                heartbeat = f"event: heartbeat\ndata: {json.dumps({'type': 'heartbeat'})}\n\n"
                yield heartbeat
                continue
                
    except ValueError as e:
        # 任务不存在
        logger.error(f"任务 {task_id} 不存在: {e}")
        error_message = f"event: message\ndata: {json.dumps({'type': 'error', 'message': '任务不存在'}, ensure_ascii=False)}\n\n"
        yield error_message
    except Exception as e:
        # 其他错误
        logger.error(f"SSE 流生成错误 {task_id}: {e}", exc_info=True)
        error_message = f"event: message\ndata: {json.dumps({'type': 'error', 'message': f'服务器错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield error_message
    finally:
        # 清理资源
        await manager.unregister_sse_connection(task_id)
        logger.info(f"SSE 连接已清理: {task_id}")

@app.get("/api/tasks/{task_id}/stream")
async def stream_task_updates(
    task_id: str, 
    request: Request, 
    token: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    SSE 端点，流式推送任务更新
    
    Args:
        task_id: 任务ID
        request: FastAPI Request 对象
        token: 查询参数中的认证 token（EventSource 不支持自定义 Header）
        authorization: Bearer Token（向后兼容）
        
    Returns:
        StreamingResponse with text/event-stream content type
    """
    # 验证认证 - 优先使用查询参数中的 token
    if token:
        # 直接验证 token（不需要 Bearer 前缀）
        if token not in session_tokens:
            raise HTTPException(status_code=401, detail="令牌无效，请重新登录")
    else:
        # 回退到 Header 认证（向后兼容）
        verify_token(authorization)
    
    # 验证任务是否存在
    task_state = manager.get_task_state(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 返回 SSE 流式响应
    return StreamingResponse(
        generate_sse_stream(task_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )



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

@app.get("/api/config")
async def get_config():
    """
    获取前端配置（公开访问）
    返回前端需要的配置项
    """
    return {
        "tts_audio_button_enabled": config.TTS_AUDIO_BUTTON_ENABLED
    }

@app.get("/api/queue/stats")
async def get_queue_stats():
    """
    获取任务队列统计信息（公开访问）
    
    返回当前队列状态、并发数、等待任务数等
    """
    from .worker_pool import worker_pool
    return worker_pool.get_stats()

@app.get("/api/queue/tasks")
async def get_queue_tasks():
    """
    获取任务队列详细列表（公开访问）
    
    返回正在处理和排队中的任务详情，包括URL、进度等
    注意：doc_hash 只有在任务完成后才会生成
    """
    from .worker_pool import worker_pool
    return worker_pool.get_task_list()

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

# ============================================================================
# TTS Queue Management API 端点
# ============================================================================

class TTSQueueStatsResponse(BaseModel):
    """TTS 队列统计信息响应"""
    queue_size: int  # 队列中待处理任务数
    total_tasks: int  # 总任务数
    pending: int  # 待处理任务数
    processing: int  # 处理中任务数
    completed: int  # 已完成任务数
    failed: int  # 失败任务数
    skipped: int  # 跳过任务数
    is_running: bool  # 服务是否运行中


@app.get("/api/tts/queue/stats", response_model=TTSQueueStatsResponse)
async def get_tts_queue_stats():
    """
    获取 TTS 预生成队列统计信息
    
    Returns:
        队列统计信息
    """
    try:
        pregeneration_service = get_tts_pregeneration_service()
        stats = pregeneration_service.get_queue_stats()
        
        return TTSQueueStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"获取队列统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


class TTSTaskInfo(BaseModel):
    """TTS 任务信息"""
    task_id: str
    article_hash: str
    source_file: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    audio_hash: Optional[str] = None


class TTSTaskListResponse(BaseModel):
    """TTS 任务列表响应"""
    tasks: List[TTSTaskInfo]
    total: int


@app.get("/api/tts/queue/tasks", response_model=TTSTaskListResponse)
async def get_tts_tasks(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    获取 TTS 任务列表
    
    Args:
        status: 可选，按状态筛选 (pending, processing, completed, failed, skipped)
        limit: 返回数量限制，默认 50
        
    Returns:
        任务列表
    """
    try:
        from .services.tts_pregeneration_service import TaskStatus
        
        pregeneration_service = get_tts_pregeneration_service()
        
        # 获取所有任务
        all_tasks = list(pregeneration_service.tasks.values())
        
        # 按状态筛选
        if status:
            try:
                status_enum = TaskStatus(status)
                all_tasks = [t for t in all_tasks if t.status == status_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态值: {status}")
        
        # 按创建时间倒序排列
        all_tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        # 限制数量
        tasks = all_tasks[:limit]
        
        # 转换为响应格式
        task_infos = [
            TTSTaskInfo(
                task_id=t.task_id,
                article_hash=t.article_hash,
                source_file=t.source_file,
                status=t.status.value,
                created_at=t.created_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
                retry_count=t.retry_count,
                error_message=t.error_message,
                audio_hash=t.audio_hash
            )
            for t in tasks
        ]
        
        return TTSTaskListResponse(
            tasks=task_infos,
            total=len(all_tasks)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


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
    
    # Mount utils directory for utility modules
    utils_dir = web_dir / "utils"
    if utils_dir.is_dir():
        app.mount("/utils", StaticFiles(directory=utils_dir), name="utils")
    
    # Mount test directory for component testing
    test_dir = web_dir / "test"
    if test_dir.is_dir():
        app.mount("/test", StaticFiles(directory=test_dir, html=True), name="test")
    
    # Mount fonts directory for PDF generation
    fonts_dir = web_dir / "fonts"
    if fonts_dir.is_dir():
        app.mount("/fonts", StaticFiles(directory=fonts_dir), name="fonts")
else:
    logger.warning(f"Frontend directory 'web' not found at {web_dir}, will only serve API.")

# 在API类中添加新的请求模型
class PDFAnalysisRequest(BaseModel):
    title: Optional[str] = None  # 可选的标题，如果为None则由AI生成


class DocumentAnalysisRequest(BaseModel):
    title: Optional[str] = None  # 可选的标题

# 在API路由中添加新的端点
@app.post("/analyze-pdf")
async def analyze_pdf_endpoint(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    priority: int = 0,  # 新增优先级参数
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
        
        # 处理标题
        display_title = title or file.filename or "未命名文档"
        if display_title.lower().endswith('.pdf'):
            display_title = display_title[:-4]
        
        # 先在 manager 中创建占位状态
        from .task_manager import TaskState
        state = TaskState(task_id=task_id, status="queued", task=None)
        manager.tasks[task_id] = state
        
        # 映射优先级
        from .worker_pool import worker_pool, TaskPriority
        priority_map = {
            0: TaskPriority.LOW,
            1: TaskPriority.NORMAL,
            2: TaskPriority.HIGH,
            3: TaskPriority.URGENT
        }
        task_priority = priority_map.get(priority, TaskPriority.NORMAL)
        
        # 添加到队列
        success = await worker_pool.add_task(
            task_id=task_id,
            task_type="pdf",
            url_or_path=tmp_file_path,
            title=display_title,
            priority=task_priority
        )
        
        if not success:
            # 清理临时文件
            os.unlink(tmp_file_path)
            del manager.tasks[task_id]
            raise HTTPException(
                status_code=503, 
                detail=f"任务队列已满（{config.ANALYSIS_QUEUE_MAX_SIZE} 个任务），请稍后重试"
            )
        
        queue_size = worker_pool.get_queue_size()
        return SummarizeResponse(
            task_id=task_id, 
            message=f"PDF分析任务已加入队列（排队: {queue_size} 个任务），请连接 WebSocket。", 
            status="created"
        )
        
    except Exception as e:
        logger.error(f"处理上PDF失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理上PDF失败: {str(e)}")


@app.post("/analyze-document")
async def analyze_document_endpoint(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    priority: int = 0,  # 新增优先级参数
    authorization: str = Header(None)
):
    """
    通用文档分析端点
    支持格式：TXT, MD, PDF, DOCX
    """
    verify_token(authorization)
    
    # 验证文件格式
    file_ext = Path(file.filename).suffix.lower()
    supported_formats = ['.txt', '.md', '.pdf', '.docx']
    
    if file_ext not in supported_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式: {file_ext}. 支持的格式: {', '.join(supported_formats)}"
        )
    
    # 验证文件大小
    max_size = config.MAX_TEXT_FILE_SIZE if file_ext in ['.txt', '.md'] else config.MAX_BINARY_FILE_SIZE
    
    task_id = str(uuid.uuid4())
    
    try:
        # 创建临时文件保存上传的文档
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
            content = await file.read()
            
            # 检查文件大小
            if len(content) > max_size:
                os.unlink(tmp_file.name)
                raise HTTPException(
                    status_code=413,
                    detail=f"文件大小超过限制 ({max_size / 1024 / 1024:.1f}MB)"
                )
            
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # 处理标题
        display_title = title or file.filename or "未命名文档"
        if display_title.lower().endswith(file_ext):
            display_title = display_title[:-len(file_ext)]
        
        # 先在 manager 中创建占位状态
        from .task_manager import TaskState
        state = TaskState(task_id=task_id, status="queued", task=None)
        manager.tasks[task_id] = state
        
        # 映射优先级
        from .worker_pool import worker_pool, TaskPriority
        priority_map = {
            0: TaskPriority.LOW,
            1: TaskPriority.NORMAL,
            2: TaskPriority.HIGH,
            3: TaskPriority.URGENT
        }
        task_priority = priority_map.get(priority, TaskPriority.NORMAL)
        
        # 添加到队列
        success = await worker_pool.add_task(
            task_id=task_id,
            task_type="document",
            url_or_path=tmp_file_path,
            title=display_title,
            priority=task_priority
        )
        
        if not success:
            # 清理临时文件
            os.unlink(tmp_file_path)
            del manager.tasks[task_id]
            raise HTTPException(
                status_code=503, 
                detail=f"任务队列已满（{config.ANALYSIS_QUEUE_MAX_SIZE} 个任务），请稍后重试"
            )
        
        queue_size = worker_pool.get_queue_size()
        return SummarizeResponse(
            task_id=task_id, 
            message=f"文档分析任务已加入队列（{file_ext[1:].upper()}，排队: {queue_size} 个任务），请连接 WebSocket。", 
            status="created"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理上传文档失败: {e}", exc_info=True)
        # 清理临时文件
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"处理上传文档失败: {str(e)}")


# ============================================================================
# TTS (Text-to-Speech) API 端点
# ============================================================================

from .services.tts_service import TTSService
from .services.audio_cache import AudioCache
from .services.tts_text_preprocessor import TTSTextPreprocessor
from .services.tts_pregeneration_service import TTSPregenerationService
from .audio.audio_utils import assemble_wav, decode_base64_pcm, calculate_audio_duration
from .model_config import get_model_client

# 初始化 TTS 服务和缓存（延迟初始化）
_tts_service: Optional[TTSService] = None
_audio_cache: Optional[AudioCache] = None
_tts_preprocessor: Optional[TTSTextPreprocessor] = None
_tts_pregeneration_service: Optional[TTSPregenerationService] = None


def get_tts_service() -> TTSService:
    """获取 TTS 服务实例（单例）"""
    global _tts_service
    if _tts_service is None:
        client = get_model_client("text_to_speech")
        _tts_service = TTSService(client)
    return _tts_service


def get_audio_cache() -> AudioCache:
    """获取音频缓存实例（单例）"""
    global _audio_cache
    if _audio_cache is None:
        cache_dir = config.PROJECT_ROOT / "downloads" / "tts_cache"
        _audio_cache = AudioCache(cache_dir, max_size_mb=500)
    return _audio_cache


def get_tts_preprocessor() -> TTSTextPreprocessor:
    """获取 TTS 文本预处理器实例（单例）"""
    global _tts_preprocessor
    if _tts_preprocessor is None:
        _tts_preprocessor = TTSTextPreprocessor()
    return _tts_preprocessor


def get_tts_pregeneration_service() -> TTSPregenerationService:
    """获取 TTS 预生成服务实例（单例）"""
    global _tts_pregeneration_service
    if _tts_pregeneration_service is None:
        tts_service = get_tts_service()
        audio_cache = get_audio_cache()
        preprocessor = get_tts_preprocessor()
        _tts_pregeneration_service = TTSPregenerationService(
            tts_service, audio_cache, preprocessor
        )
    return _tts_pregeneration_service


class TTSRequest(BaseModel):
    """TTS 生成请求"""
    article_hash: str
    text: str
    voice: Optional[str] = None
    language: Optional[str] = None
    use_cache: bool = True
    skip_code_blocks: bool = True


class TTSResponse(BaseModel):
    """TTS 生成响应"""
    audio_url: str
    duration: float
    cached: bool
    voice: str
    language: str


@app.post("/api/tts/generate", response_model=TTSResponse)
async def generate_tts(req: TTSRequest):
    """
    生成 TTS 音频（非流式）
    
    检查缓存，如果存在则返回缓存 URL，否则生成新音频并缓存
    """
    try:
        tts_service = get_tts_service()
        audio_cache = get_audio_cache()
        
        # 从配置获取默认值
        voice = req.voice or getattr(tts_service.config, 'tts_default_voice', 'Kai')
        language = req.language or getattr(tts_service.config, 'tts_default_language', 'Chinese')
        
        # 计算哈希
        audio_hash = tts_service.calculate_hash(req.text, voice, language)
        
        # 检查缓存
        if req.use_cache:
            cached_path = audio_cache.get(audio_hash)
            if cached_path:
                logger.info(f"TTS 缓存命中: {audio_hash}")
                # 计算时长
                file_size = cached_path.stat().st_size
                duration = calculate_audio_duration(file_size - 44)  # 减去 WAV 头
                
                return TTSResponse(
                    audio_url=f"/api/tts/cache/{audio_hash}",
                    duration=duration,
                    cached=True,
                    voice=voice,
                    language=language
                )
        
        # 生成音频
        logger.info(f"开始生成 TTS 音频: {audio_hash}")
        audio_chunks = []
        async for chunk in tts_service.generate_audio_stream(
            req.text, voice, language, req.skip_code_blocks
        ):
            # 解码 Base64
            pcm_data = decode_base64_pcm(chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk)
            audio_chunks.append(pcm_data)
        
        # 组装 WAV 文件
        wav_data = assemble_wav(audio_chunks)
        duration = calculate_audio_duration(len(wav_data) - 44)
        
        # 缓存音频
        text_hash = tts_service.calculate_hash(req.text, "", "")
        audio_cache.put(
            audio_hash=audio_hash,
            audio_data=wav_data,
            text_hash=text_hash,
            voice=voice,
            language=language,
            duration=duration
        )
        
        logger.info(f"TTS 音频生成完成: {audio_hash}, 时长: {duration:.2f}s")
        
        return TTSResponse(
            audio_url=f"/api/tts/cache/{audio_hash}",
            duration=duration,
            cached=False,
            voice=voice,
            language=language
        )
        
    except ValueError as e:
        logger.error(f"TTS 请求参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TTS 生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS 生成失败: {str(e)}")


class TTSStreamRequest(BaseModel):
    article_hash: str
    text: str
    voice: Optional[str] = None
    language: Optional[str] = None
    use_cache: bool = True
    skip_code_blocks: bool = True


@app.post("/api/tts/stream")
async def stream_tts(req: TTSStreamRequest):
    """
    流式生成 TTS 音频（SSE）
    
    实时返回音频块，支持边生成边播放
    """
    article_hash = req.article_hash
    text = req.text
    use_cache = req.use_cache
    skip_code_blocks = req.skip_code_blocks
    
    async def event_generator():
        try:
            tts_service = get_tts_service()
            audio_cache = get_audio_cache()
            
            # 从配置获取默认值
            voice = req.voice or getattr(tts_service.config, 'tts_default_voice', 'Kai')
            language = req.language or getattr(tts_service.config, 'tts_default_language', 'Chinese')
            
            # 计算哈希
            audio_hash = tts_service.calculate_hash(text, voice, language)
            
            # 检查缓存
            if use_cache:
                cached_path = audio_cache.get(audio_hash)
                if cached_path:
                    logger.info(f"TTS 缓存命中（流式）: {audio_hash}")
                    file_size = cached_path.stat().st_size
                    duration = calculate_audio_duration(file_size - 44)
                    
                    # 读取缓存的 WAV 文件并流式发送
                    # 跳过 WAV 头（44 字节），只发送 PCM 数据
                    chunk_size = 48000  # 每块 48KB (约 1 秒音频)
                    chunk_index = 0
                    total_bytes = 0
                    
                    with open(cached_path, 'rb') as f:
                        # 跳过 WAV 头
                        f.seek(44)
                        
                        while True:
                            pcm_chunk = f.read(chunk_size)
                            if not pcm_chunk:
                                break
                            
                            chunk_index += 1
                            total_bytes += len(pcm_chunk)
                            
                            # 将 PCM 数据编码为 Base64
                            chunk_b64 = base64.b64encode(pcm_chunk).decode('utf-8')
                            
                            # 计算缓冲时长和当前块的时长
                            buffered_duration = total_bytes / (24000 * 2)
                            chunk_duration = len(pcm_chunk) / (24000 * 2)
                            
                            # 发送音频块
                            yield f"event: chunk\n"
                            yield f"data: {json.dumps({
                                'index': chunk_index,
                                'data': chunk_b64,
                                'chunk_size': len(pcm_chunk),
                                'total_bytes': total_bytes,
                                'buffered_duration': round(buffered_duration, 2),
                                'from_cache': True
                            })}\n\n"
                            
                            # 根据音频块的实际时长添加延迟
                            # 前几个块快速发送以建立缓冲，后续块按实际播放速度发送
                            if chunk_index <= 3:
                                await asyncio.sleep(0.05)  # 前3个块快速发送
                            else:
                                await asyncio.sleep(chunk_duration * 0.8)  # 后续块按80%的播放速度发送
                    
                    # 发送完成事件
                    yield f"event: complete\n"
                    yield f"data: {json.dumps({
                        'audio_url': f'/api/tts/cache/{audio_hash}',
                        'duration': duration,
                        'chunk_count': chunk_index,
                        'total_bytes': total_bytes,
                        'from_cache': True,
                        'audio_hash': audio_hash
                    })}\n\n"
                    
                    logger.info(f"缓存音频流式发送完成: {audio_hash}, {chunk_index} 块")
                    return
            
            # 流式生成
            logger.info(f"开始生成 TTS: {audio_hash}")
            audio_segments = []
            chunk_index = 0
            total_bytes = 0
            start_time = asyncio.get_event_loop().time()
            
            async for chunk in tts_service.generate_audio_stream(
                text, voice, language, skip_code_blocks
            ):
                chunk_str = chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk
                chunk_index += 1
                
                logger.info(f"收到音频数据块 {chunk_index}")
                
                try:
                    # Gemini 返回 Base64 编码的 PCM 数据
                    # 解码 Base64 得到原始 PCM
                    pcm_data = base64.b64decode(chunk_str)
                    audio_segments.append(pcm_data)
                    
                    # 更新统计信息
                    chunk_size = len(pcm_data)
                    total_bytes += chunk_size
                    elapsed_time = asyncio.get_event_loop().time() - start_time
                    
                    # 计算当前缓冲的音频时长（PCM: 24000Hz, 16bit, mono）
                    buffered_duration = total_bytes / (24000 * 2)  # 2 bytes per sample
                    
                    # 发送带有进度信息的音频块
                    yield f"event: chunk\n"
                    yield f"data: {json.dumps({
                        'index': chunk_index,
                        'data': chunk_str,
                        'chunk_size': chunk_size,
                        'total_bytes': total_bytes,
                        'buffered_duration': round(buffered_duration, 2),
                        'elapsed_time': round(elapsed_time, 2)
                    })}\n\n"
                    
                    logger.info(
                        f"已发送音频片段 {chunk_index}: "
                        f"{chunk_size} bytes, "
                        f"累计 {total_bytes / 1024:.1f}KB, "
                        f"缓冲时长 {buffered_duration:.2f}s"
                    )
                    
                except Exception as e:
                    logger.error(f"处理音频片段失败: {e}", exc_info=True)
            
            if not audio_segments:
                raise Exception("未生成任何有效音频")
            
            # 合并所有 PCM 数据并添加 WAV 头
            from .audio.audio_utils import assemble_wav
            wav_data = assemble_wav(audio_segments)
            duration = calculate_audio_duration(len(wav_data) - 44)
            total_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(
                f"音频合并完成: "
                f"共 {len(audio_segments)} 段, "
                f"总大小 {len(wav_data)} bytes, "
                f"时长 {duration:.2f}s, "
                f"生成耗时 {total_time:.2f}s"
            )
            
            # 缓存音频
            text_hash = tts_service.calculate_hash(text, "", "")
            audio_cache.put(
                audio_hash=audio_hash,
                audio_data=wav_data,
                text_hash=text_hash,
                voice=voice,
                language=language,
                duration=duration
            )
            
            # 发送完成事件（包含详细统计）
            yield f"event: complete\n"
            yield f"data: {json.dumps({
                'audio_url': f'/api/tts/cache/{audio_hash}',
                'duration': duration,
                'chunk_count': chunk_index,
                'total_bytes': total_bytes,
                'generation_time': round(total_time, 2),
                'audio_hash': audio_hash
            })}\n\n"
            
            logger.info(
                f"TTS 流式生成完成: {audio_hash}, "
                f"{chunk_index} 块, "
                f"{total_bytes / 1024:.1f}KB, "
                f"{total_time:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"TTS 流式生成失败: {e}", exc_info=True)
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e), 'message': '音频生成失败'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/tts/cache/{audio_hash}")
async def get_cached_audio(audio_hash: str):
    """
    获取缓存的音频文件
    
    返回 WAV 格式的音频文件
    """
    try:
        audio_cache = get_audio_cache()
        
        # 获取缓存文件
        cached_path = audio_cache.get(audio_hash)
        
        if not cached_path:
            raise HTTPException(status_code=404, detail="音频文件不存在")
        
        logger.info(f"返回缓存音频: {audio_hash}")
        
        return FileResponse(
            cached_path,
            media_type="audio/wav",
            filename=f"{audio_hash}.wav",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=31536000",  # 缓存1年
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Length, Content-Range"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存音频失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取音频失败: {str(e)}")


class TTSStatusResponse(BaseModel):
    """音频状态查询响应"""
    has_audio: bool
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    status: str  # "ready", "processing", "none"
    voice: Optional[str] = None
    generated_at: Optional[str] = None
    # 渐进式播放相关
    has_partial: bool = False  # 是否有部分音频
    partial_url: Optional[str] = None  # 部分音频URL
    partial_duration: Optional[float] = None  # 部分音频时长
    chunks_generated: int = 0  # 已生成片段数
    total_chunks: int = 0  # 总片段数
    progress_percent: int = 0  # 进度百分比


@app.get("/api/tts/status/{article_hash}", response_model=TTSStatusResponse)
async def get_tts_status(article_hash: str):
    """
    查询文章的 TTS 音频状态
    
    Args:
        article_hash: 文章哈希值
        
    Returns:
        音频状态信息
    """
    try:
        audio_cache = get_audio_cache()
        
        # 查找音频缓存
        audio_metadata = audio_cache.find_by_article_hash(article_hash)
        
        if audio_metadata:
            # 有完整音频
            return TTSStatusResponse(
                has_audio=True,
                audio_url=f"/api/tts/cache/{audio_metadata.hash}",
                duration=audio_metadata.duration,
                status="ready",
                voice=audio_metadata.voice,
                generated_at=audio_metadata.created_at
            )
        
        # 检查是否有处理中的任务
        try:
            pregeneration_service = get_tts_pregeneration_service()
            # 检查服务是否运行中
            if pregeneration_service.is_running:
                for task in pregeneration_service.tasks.values():
                    if task.article_hash == article_hash:
                        from .services.tts_pregeneration_service import TaskStatus
                        if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
                            # 计算进度
                            progress = 0
                            if task.total_chunks > 0:
                                progress = int((task.chunks_generated / task.total_chunks) * 100)
                            elif task.chunks_generated > 0:
                                # 如果还不知道总数，估算进度
                                progress = min(90, 10 + task.chunks_generated)
                            
                            # 检查是否有部分音频
                            partial_info = {}
                            if task.partial_audio_hash:
                                partial_metadata = audio_cache.get_metadata(task.partial_audio_hash)
                                if partial_metadata:
                                    partial_info = {
                                        "has_partial": True,
                                        "partial_url": f"/api/tts/cache/{task.partial_audio_hash}",
                                        "partial_duration": partial_metadata.duration
                                    }
                            
                            return TTSStatusResponse(
                                has_audio=False,
                                status="processing",
                                chunks_generated=task.chunks_generated,
                                total_chunks=task.total_chunks,
                                progress_percent=progress,
                                **partial_info
                            )
        except Exception as e:
            logger.debug(f"检查预生成任务失败: {e}")
        
        # 没有音频
        return TTSStatusResponse(
            has_audio=False,
            status="none"
        )
        
    except Exception as e:
        logger.error(f"查询 TTS 状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询状态失败: {str(e)}")


@app.get("/api/tts/text/{article_hash}")
async def get_tts_text(article_hash: str):
    """
    获取文章的 TTS 预处理文本
    
    Args:
        article_hash: 文章哈希值
        
    Returns:
        纯文本内容
    """
    try:
        text_file = config.TTS_TEXT_DIR / f"{article_hash}.txt"
        
        if not text_file.exists():
            raise HTTPException(status_code=404, detail="TTS 文本不存在")
        
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return Response(
            content=text,
            media_type="text/plain; charset=utf-8"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 TTS 文本失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文本失败: {str(e)}")


class TTSPregenerateRequest(BaseModel):
    """手动触发预生成请求"""
    filename: Optional[str] = None
    article_hash: Optional[str] = None
    text: Optional[str] = None


class TTSPregenerateResponse(BaseModel):
    """手动触发预生成响应"""
    task_id: Optional[str] = None
    status: str
    message: str


@app.post("/api/tts/pregenerate", response_model=TTSPregenerateResponse)
async def trigger_tts_pregeneration(req: TTSPregenerateRequest):
    """
    手动触发 TTS 预生成
    
    Args:
        req: 请求对象，可以包含 filename 或 article_hash
        
    Returns:
        任务信息
    """
    try:
        # 通过 article_hash 查找文件
        if req.article_hash:
            # 直接使用 hash_to_filename 映射
            found_file = hash_to_filename.get(req.article_hash)
            
            if not found_file:
                raise HTTPException(status_code=404, detail=f"找不到 article_hash 对应的文件: {req.article_hash}")
            
            # 添加任务
            pregeneration_service = get_tts_pregeneration_service()
            task_id = await pregeneration_service.add_task(req.article_hash, found_file)
            
            if task_id:
                return TTSPregenerateResponse(
                    task_id=task_id,
                    status="queued",
                    message=f"任务已添加到队列: {task_id}"
                )
            else:
                return TTSPregenerateResponse(
                    status="skipped",
                    message="任务已存在或音频已缓存"
                )
        
        # 通过 filename 查找文件（兼容旧的方式）
        elif req.filename:
            # 验证文件是否存在
            file_path = config.OUTPUT_DIR / req.filename
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"文件不存在: {req.filename}")
            
            # 读取文件元数据
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取元数据
            preprocessor = get_tts_preprocessor()
            metadata, _ = preprocessor.extract_yaml_metadata(content)
            
            video_url = metadata.get('video_url', '')
            title = metadata.get('title', '')
            upload_date = metadata.get('upload_date', '')
            
            if not any([video_url, title]):
                raise HTTPException(status_code=400, detail="文件缺少必要的元数据")
            
            # 计算 article_hash
            article_hash = preprocessor.calculate_article_hash(video_url, title, upload_date)
            
            # 添加任务
            pregeneration_service = get_tts_pregeneration_service()
            task_id = await pregeneration_service.add_task(article_hash, req.filename)
            
            if task_id:
                return TTSPregenerateResponse(
                    task_id=task_id,
                    status="queued",
                    message=f"任务已添加到队列: {task_id}"
                )
            else:
                return TTSPregenerateResponse(
                    status="skipped",
                    message="任务已存在或音频已缓存"
                )
        else:
            raise HTTPException(status_code=400, detail="必须提供 filename 或 article_hash")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发 TTS 预生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"触发预生成失败: {str(e)}")


# --- Frontend Catch-All Route (MUST be last) ---
# This catch-all route MUST be defined *after* all other API routes.
# It serves the main index.html for any other path, enabling client-side routing.
if web_dir.is_dir():
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