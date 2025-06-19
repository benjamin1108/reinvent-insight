import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)

@dataclass
class TaskState:
    task_id: str
    status: str  # "running", "completed", "error"
    logs: List[str] = field(default_factory=list)
    result_title: Optional[str] = None
    result_summary: Optional[str] = None
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
        self.tasks[task_id].websocket = websocket
        logger.info(f"客户端已连接到任务: {task_id}")
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
                await ws.send_json({"message": message})
    
    async def send_result(self, title: str, summary: str, task_id: str):
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.status = "completed"
            task_state.result_title = title
            task_state.result_summary = summary
            ws = task_state.websocket
            if ws:
                await ws.send_json({
                    "type": "result",
                    "title": title,
                    "summary": summary
                })

    async def send_history(self, task_id: str):
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            ws = task_state.websocket
            if not ws:
                return

            for log_message in task_state.logs:
                await ws.send_json({"message": log_message})
            
            if task_state.status == "completed":
                await self.send_result(task_state.result_title, task_state.result_summary, task_id)
            elif task_state.status == "error":
                last_log = task_state.logs[-1] if task_state.logs else "未知错误"
                await self.send_message(last_log, task_id)

    def create_task(self, task_id: str, coro: asyncio.Task):
        state = TaskState(task_id=task_id, status="running", task=coro)
        self.tasks[task_id] = state

    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        return self.tasks.get(task_id)

    def cleanup_task(self, task_id: str):
        pass

# 创建一个全局唯一的 TaskManager 实例
manager = TaskManager() 