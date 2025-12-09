"""System routes - Health check, config, queue stats"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse

from reinvent_insight.core import config
from reinvent_insight.api.routes.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/env")
async def get_environment_info():
    """获取环境信息，用于区分开发和生产环境"""
    # 通过多种方式判断环境
    is_dev = any([
        # 检查环境变量（优先级最高）
        os.getenv("ENVIRONMENT", "").lower() == "development",
        os.getenv("ENV", "").lower() == "dev",
        # 检查是否存在开发环境特有的文件
        (config.PROJECT_ROOT / ".git").exists(),
        (config.PROJECT_ROOT / "pyproject.toml").exists(),
        (config.PROJECT_ROOT / "run-dev.sh").exists(),
        # 检查是否在虚拟环境中运行
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


@router.get("/health")
async def health_check():
    """
    系统健康检查端点（公开访问）
    检查主程序和 Cookie Manager 服务的状态
    """
    from reinvent_insight.services.cookie.health_checker import CookieHealthCheck
    
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


@router.get("/config")
async def get_config():
    """
    获取前端配置（公开访问）
    返回前端需要的配置项
    """
    return {
        "tts_audio_button_enabled": config.TTS_AUDIO_BUTTON_ENABLED
    }


@router.get("/queue/stats")
async def get_queue_stats():
    """
    获取任务队列统计信息（公开访问）
    
    返回当前队列状态、并发数、等待任务数等
    """
    from reinvent_insight.services.analysis.worker_pool import worker_pool
    return worker_pool.get_stats()


@router.get("/queue/tasks")
async def get_queue_tasks():
    """
    获取任务队列详细列表（公开访问）
    
    返回正在处理和排队中的任务详情，包括URL、进度等
    注意：doc_hash 只有在任务完成后才会生成
    """
    from reinvent_insight.services.analysis.worker_pool import worker_pool
    return worker_pool.get_task_list()


@router.get("/admin/cookie-status")
async def get_cookie_status(authorization: str = Header(None)):
    """
    获取详细的 Cookie 状态（需要认证）
    """
    verify_token(authorization)
    
    from reinvent_insight.services.cookie.health_checker import CookieHealthCheck
    
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
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/refresh-cache", status_code=200)
def refresh_cache(authorization: str = Header(None)):
    """
    手动触发服务器端文档缓存的刷新。
    这将重新扫描摘要目录并重建哈希映射。
    """
    verify_token(authorization)
    try:
        from reinvent_insight.services.document.hash_registry import init_hash_mappings
        logger.info("管理员手动触发缓存刷新...")
        init_hash_mappings()
        logger.info("服务器端缓存已成功刷新。")
        return {"message": "服务器端缓存已成功刷新。"}
    except Exception as e:
        logger.error(f"手动刷新缓存时发生错误: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"刷新缓存时发生内部错误: {e}")


@router.get("/admin/tasks/{task_id}/result")
async def get_task_result(
    task_id: str,
    authorization: str = Header(None)
):
    """
    获取已完成任务的结果文件
    
    Args:
        task_id: 任务ID
        authorization: 认证令牌
        
    Returns:
        Markdown 文件下载
    """
    verify_token(authorization)
    
    from reinvent_insight.services.analysis.task_manager import manager
    
    task_state = manager.get_task_state(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"任务未找到: {task_id}")
    
    if task_state.status != 'completed':
        raise HTTPException(
            status_code=400, 
            detail=f"任务尚未完成，当前状态: {task_state.status}"
        )
    
    result_path = getattr(task_state, 'result_path', None)
    if not result_path:
        raise HTTPException(status_code=404, detail="任务结果文件路径未找到")
    
    file_path = Path(result_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="结果文件不存在")
    
    return FileResponse(
        path=str(file_path),
        media_type="text/markdown",
        filename=file_path.name
    )
