"""Main API module - Refactored FastAPI application"""

import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi import HTTPException
from pathlib import Path

from reinvent_insight.core.logger import setup_logger
from reinvent_insight.core import config
from reinvent_insight.api.routes import (
    auth_router,
    analysis_router,
    documents_router,
    trash_router,
    versions_router,
    downloads_router,
    tts_generate_router,
    tts_cache_router,
    tts_pregenerate_router,
    system_router,
    visual_router,
    ultra_deep_router,
    tasks_router,
    subtitles_router,
)

setup_logger(
    level=config.LOG_LEVEL,
    log_dir=config.LOG_DIR if config.LOG_FILE_ENABLED else None,
    enable_file_logging=config.LOG_FILE_ENABLED,
    max_bytes=config.LOG_MAX_BYTES,
    backup_count=config.LOG_BACKUP_COUNT
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Reinvent Insight API", 
    description="YouTube 字幕深度摘要后端服务", 
    version="0.2.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Range", "Content-Type"]
)

# Add logging middleware
from reinvent_insight.api.middleware import RequestLoggingMiddleware
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(documents_router)
app.include_router(trash_router)
app.include_router(versions_router)
app.include_router(downloads_router)
app.include_router(tts_generate_router)
app.include_router(tts_cache_router)
app.include_router(tts_pregenerate_router)
app.include_router(system_router)
app.include_router(visual_router)
app.include_router(ultra_deep_router)
app.include_router(tasks_router)
app.include_router(subtitles_router)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("应用启动")
    
    # Import startup services
    from reinvent_insight.services.document.hash_registry import init_hash_mappings
    from reinvent_insight.services.document.summary_cache import init_summary_cache
    from reinvent_insight.infrastructure.file_system.watcher import start_watching
    from reinvent_insight.services.startup_service import start_visual_watcher, init_post_processors
    from reinvent_insight.services.tts_pregeneration_service import get_tts_pregeneration_service
    from reinvent_insight.services.analysis.worker_pool import worker_pool
    from reinvent_insight.services.cookie.health_checker import check_and_warn
    
    # 1. Initialize hash mappings
    init_hash_mappings()
    
    # 2. Initialize summary cache (depends on hash mappings)
    init_summary_cache()
    
    # 3. Start file monitoring (refresh both hash mappings and summary cache)
    def on_file_change():
        init_hash_mappings()
        init_summary_cache()
    start_watching(config.OUTPUT_DIR, on_file_change)
    
    # 4. Initialize post-processing pipeline
    init_post_processors()
    
    # 5. Check Cookie health status
    check_and_warn()
    
    # 6. Start visual interpretation watcher
    await start_visual_watcher()
    
    # 7. Start TTS pregeneration service (on-demand mode)
    try:
        pregeneration_service = get_tts_pregeneration_service()
        await pregeneration_service.start()
        logger.debug("TTS 预生成服务已启动（按需模式）")
    except Exception as e:
        logger.error(f"启动 TTS 预生成服务失败: {e}", exc_info=True)
    
    # 8. Start Worker Pool (task queue system)
    try:
        await worker_pool.start()
        logger.info(
            f"Worker Pool 已启动（并发: {config.MAX_CONCURRENT_ANALYSIS_TASKS}, "
            f"队列: {config.ANALYSIS_QUEUE_MAX_SIZE}）"
        )
    except Exception as e:
        logger.error(f"启动 Worker Pool 失败: {e}", exc_info=True)


# Mount static files
web_dir = config.PROJECT_ROOT / "web"

if web_dir.is_dir():
    # Mount static file directories
    app.mount("/js", StaticFiles(directory=web_dir / "js"), name="js")
    app.mount("/css", StaticFiles(directory=web_dir / "css"), name="css")
    
    # Mount components directory
    components_dir = web_dir / "components"
    if components_dir.is_dir():
        app.mount("/components", StaticFiles(directory=components_dir), name="components")
    
    # Mount utils directory
    utils_dir = web_dir / "utils"
    if utils_dir.is_dir():
        app.mount("/utils", StaticFiles(directory=utils_dir), name="utils")
    
    # Mount test directory
    test_dir = web_dir / "test"
    if test_dir.is_dir():
        app.mount("/test", StaticFiles(directory=test_dir, html=True), name="test")
    
    # Mount fonts directory
    fonts_dir = web_dir / "fonts"
    if fonts_dir.is_dir():
        app.mount("/fonts", StaticFiles(directory=fonts_dir), name="fonts")
    
    # Mount keyframes directory for screenshot images
    keyframes_dir = config.OUTPUT_DIR / "keyframes"
    if keyframes_dir.is_dir():
        app.mount("/d/keyframes", StaticFiles(directory=keyframes_dir), name="keyframes")
else:
    logger.warning(f"Frontend directory 'web' not found at {web_dir}, will only serve API.")


# Frontend catch-all route (MUST be last)
if web_dir.is_dir():
    @app.get("/{full_path:path}", response_class=FileResponse, include_in_schema=False)
    async def serve_vue_app(request: Request, full_path: str):
        """
        Serve the Vue.js application.
        This allows the client-side router to handle all non-API, non-static-file paths.
        """
        from reinvent_insight.services.document.hash_registry import hash_to_filename
        from reinvent_insight.services.document.metadata_service import (
            parse_metadata_from_md,
            extract_text_from_markdown,
        )
        
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
                    
                    # 提取摘要作为描述
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
                        html_content = re.sub(
                            r'<title>.*?</title>',
                            '',
                            html_content,
                            flags=re.IGNORECASE | re.DOTALL
                        )
                        html_content = html_content.replace('</head>', meta_tags + '\n</head>')
                        
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
    import uvicorn
    import signal
    import os
    
    # 添加信号处理器，解决 run_in_executor 中的同步调用无法中断的问题
    def force_exit(signum, frame):
        logger.info(f"\n收到信号 {signum}，强制退出进程...")
        os._exit(0)
    
    # 在非 reload 模式下注册信号处理器
    if not reload:
        signal.signal(signal.SIGINT, force_exit)
        signal.signal(signal.SIGTERM, force_exit)
    
    # 在 reload 模式下使用 handle_exit 参数
    uvicorn.run(
        "reinvent_insight.api.app:app",
        host=host,
        port=port,
        reload=reload,
        timeout_graceful_shutdown=1  # 设置 1 秒优雅关闭超时
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("reinvent_insight.api.app:app", host="0.0.0.0", port=8001, reload=True)
