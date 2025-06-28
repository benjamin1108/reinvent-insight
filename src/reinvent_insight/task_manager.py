import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)

@dataclass
class TaskState:
    task_id: str
    status: str  # "pending", "running", "completed", "error"
    logs: List[str] = field(default_factory=list)
    progress: int = 0  # 进度百分比
    result_title: Optional[str] = None
    result_summary: Optional[str] = None
    result_path: Optional[str] = None # 最终报告的文件路径
    websocket: Optional[WebSocket] = None
    task: Optional[asyncio.Task] = None

class TaskManager:
    """管理 WebSocket 连接和后台任务状态"""
    def __init__(self):
        self.tasks: Dict[str, TaskState] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        if task_id not in self.tasks:
            await websocket.close(code=4001, reason="Invalid task ID")
            logger.warning(f"拒绝了无效任务ID的WebSocket连接: {task_id}")
            return
        
        await websocket.accept()
        
        # 检查是否是首次连接（websocket为None）
        is_first_connection = self.tasks[task_id].websocket is None
        
        self.tasks[task_id].websocket = websocket
        logger.info(f"客户端已连接到任务: {task_id}")
        
        # 只有在重连时才发送历史记录
        if not is_first_connection:
            await self.send_history(task_id)

    def disconnect(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].websocket = None
            logger.info(f"客户端从任务断开: {task_id}")

    async def send_message(self, message: str, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].logs.append(message)
            ws = self.tasks[task_id].websocket
            if ws:
                try:
                    await ws.send_json({"type": "log", "message": message})
                except Exception as e:
                    logger.warning(f"向客户端 {task_id} 发送日志消息失败 (可能已断开): {e}")

    async def send_result(self, title: str, summary: str, task_id: str):
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.status = "completed"
            task_state.result_title = title
            task_state.result_summary = summary
            ws = task_state.websocket
            if ws:
                try:
                    await ws.send_json({
                        "type": "result",
                        "title": title,
                        "summary": summary
                    })
                except Exception as e:
                    logger.warning(f"向客户端 {task_id} 发送最终结果失败 (可能已断开): {e}")

    def set_task_result(self, task_id: str, file_path: str):
        """当任务完成时，由工作流调用，用于记录最终产物路径。"""
        if task_id in self.tasks:
            self.tasks[task_id].result_path = file_path
            logger.info(f"任务 {task_id} 结果路径已记录: {file_path}")

    async def send_history(self, task_id: str):
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            ws = task_state.websocket
            if not ws:
                return

            try:
                for log_message in task_state.logs:
                    await ws.send_json({"type": "log", "message": log_message})
                
                await self.update_progress(task_id, task_state.progress)

                if task_state.status == "completed":
                    await self.send_result(task_state.result_title, task_state.result_summary, task_id)
                elif task_state.status == "error":
                    await self.set_task_error(task_id, task_state.logs[-1] if task_state.logs else "未知错误")
            except Exception as e:
                logger.warning(f"向客户端 {task_id} 发送历史记录失败 (可能已断开): {e}")

    def create_task(self, task_id: str, coro: asyncio.Task):
        # 将 coro 包装一下，确保任务完成时能被正确处理
        async def task_wrapper():
            try:
                await coro
            except asyncio.CancelledError:
                logger.warning(f"任务 {task_id} 被取消。")
            except Exception as e:
                logger.error(f"任务 {task_id} 内部发生未捕获的异常: {e}", exc_info=True)
                # 确保即使在意外情况下也更新任务状态
                await self.set_task_error(task_id, f"工作流发生意外错误: {e}")

        task = asyncio.create_task(task_wrapper())
        state = TaskState(task_id=task_id, status="pending", task=task)
        self.tasks[task_id] = state

    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        return self.tasks.get(task_id)

    def cleanup_task(self, task_id: str):
        pass

    async def update_progress(self, task_id: str, progress: int, message: Optional[str] = None):
        """更新任务进度并发送通知"""
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.progress = progress
            if message:
                task_state.logs.append(message)
            
            ws = task_state.websocket
            if ws:
                try:
                    await ws.send_json({
                        "type": "progress",
                        "progress": progress,
                        "message": message or task_state.logs[-1]
                    })
                except Exception as e:
                    logger.warning(f"向客户端 {task_id} 更新进度失败 (可能已断开): {e}")
    
    async def set_task_error(self, task_id: str, message: str):
        """将任务状态设置为错误并发送通知"""
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.status = "error"
            task_state.logs.append(message)
            ws = task_state.websocket
            if ws:
                try:
                    await ws.send_json({
                        "type": "error",
                        "message": message
                    })
                except Exception as e:
                    logger.warning(f"向客户端 {task_id} 发送错误消息失败 (可能已断开): {e}")

# 创建一个全局唯一的 TaskManager 实例
manager = TaskManager() 