"""Task streaming routes - SSE for real-time progress updates"""

import logging
import asyncio
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from reinvent_insight.services.analysis.task_manager import manager
from reinvent_insight.api.routes.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}/stream")
async def stream_task_progress(
    task_id: str,
    token: Optional[str] = Query(None, description="认证令牌（EventSource不支持自定义Header）")
):
    """
    通过 SSE 实时接收任务进度更新
    
    Args:
        task_id: 任务ID
        token: 认证令牌（查询参数，因为EventSource不支持自定义Header）
        
    Returns:
        Server-Sent Events (SSE) 流
        
    事件类型:
        - message: 任务进度 {"type": "log|progress|result|error", ...}
        - heartbeat: 保持连接 {"type": "heartbeat"}
    """
    # 验证Token（通过查询参数）
    if token:
        from reinvent_insight.api.routes.auth import session_tokens
        if token not in session_tokens:
            raise HTTPException(status_code=401, detail="令牌无效")
    
    # 检查任务是否存在
    task_state = manager.get_task_state(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"任务未找到: {task_id}")
    
    async def event_generator():
        """生成SSE事件流"""
        try:
            last_log_index = 0
            heartbeat_interval = 15  # 15秒心跳
            last_heartbeat = asyncio.get_event_loop().time()
            
            while True:
                current_time = asyncio.get_event_loop().time()
                
                # 获取最新任务状态
                task_state = manager.get_task_state(task_id)
                if not task_state:
                    logger.warning(f"任务 {task_id} 状态丢失")
                    break
                
                # 发送新的日志消息
                if task_state.logs and len(task_state.logs) > last_log_index:
                    for i in range(last_log_index, len(task_state.logs)):
                        log_message = task_state.logs[i]
                        data = json.dumps({
                            "type": "log",
                            "message": log_message
                        }, ensure_ascii=False)
                        yield f"event: message\ndata: {data}\n\n"
                    last_log_index = len(task_state.logs)
                
                # 发送进度更新
                if task_state.progress is not None:
                    data = json.dumps({
                        "type": "progress",
                        "progress": task_state.progress,
                        "message": task_state.logs[-1] if task_state.logs else ""
                    }, ensure_ascii=False)
                    yield f"event: message\ndata: {data}\n\n"
                
                # 检查任务是否完成
                if task_state.status == 'completed':
                    # 发送结果消息
                    result_path = getattr(task_state, 'result_path', None)
                    filename = result_path.split('/')[-1] if result_path else ''
                    data = json.dumps({
                        "type": "result",
                        "title": getattr(task_state, 'title', '') or getattr(task_state, 'result_title', ''),
                        "filename": filename,
                        "hash": getattr(task_state, 'doc_hash', '') or '',
                        "message": "分析完成"
                    }, ensure_ascii=False)
                    yield f"event: message\ndata: {data}\n\n"
                    logger.info(f"任务 {task_id} 完成，关闭SSE连接")
                    break
                
                # 检查任务是否失败
                elif task_state.status in ['failed', 'error']:
                    # 发送错误消息
                    error_msg = task_state.logs[-1] if task_state.logs else "未知错误"
                    data = json.dumps({
                        "type": "error",
                        "error_type": "analysis_error",
                        "message": error_msg,
                        "suggestions": ["请检查输入内容", "稍后重试"]
                    }, ensure_ascii=False)
                    yield f"event: message\ndata: {data}\n\n"
                    logger.warning(f"任务 {task_id} 失败，关闭SSE连接")
                    break
                
                # 发送心跳
                if current_time - last_heartbeat >= heartbeat_interval:
                    data = json.dumps({"type": "heartbeat"}, ensure_ascii=False)
                    yield f"event: message\ndata: {data}\n\n"
                    last_heartbeat = current_time
                
                # 短暂休眠，避免CPU占用过高
                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            logger.info(f"SSE连接 {task_id} 被取消")
        except Exception as e:
            logger.error(f"SSE流生成错误: {e}", exc_info=True)
            data = json.dumps({
                "type": "error",
                "error_type": "stream_error",
                "message": f"流传输错误: {str(e)}"
            }, ensure_ascii=False)
            yield f"event: message\ndata: {data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{task_id}/status")
async def get_task_status(task_id: str):
    """
    获取任务状态（不使用流式传输）
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    task_state = manager.get_task_state(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"任务未找到: {task_id}")
    
    return {
        "task_id": task_id,
        "status": task_state.status,
        "progress": task_state.progress,
        "logs": task_state.logs[-10:] if task_state.logs else [],  # 只返回最近10条日志
        "completed": task_state.status == 'completed',
        "failed": task_state.status in ['failed', 'error']
    }
