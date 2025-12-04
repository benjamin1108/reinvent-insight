import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from asyncio import Queue
from pathlib import Path

logger = logging.getLogger(__name__)

# 导入内容清理函数
try:
    from .api import clean_content_metadata
except ImportError:
    # 如果导入失败，提供一个简单的备用函数
    def clean_content_metadata(content: str, title: str = '') -> str:
        logger.warning("无法导入 clean_content_metadata，使用备用清理函数")
        return content

@dataclass
class TaskState:
    task_id: str
    status: str  # "pending", "running", "completed", "error"
    logs: List[str] = field(default_factory=list)
    progress: int = 0  # 进度百分比
    result_title: Optional[str] = None
    result_summary: Optional[str] = None
    result_path: Optional[str] = None # 最终报告的文件路径
    task: Optional[asyncio.Task] = None
    message_queue: Optional[Queue] = None  # SSE 消息队列

class TaskManager:
    """管理 SSE 连接和后台任务状态"""
    def __init__(self):
        self.tasks: Dict[str, TaskState] = {}
        self.max_queue_size = 100  # 限制队列大小，防止内存溢出

    async def register_sse_connection(self, task_id: str) -> Queue:
        """
        注册 SSE 连接，返回消息队列
        
        Args:
            task_id: 任务ID
            
        Returns:
            Queue: 消息队列，用于接收任务更新
            
        Raises:
            ValueError: 如果任务不存在
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务 {task_id} 不存在")
        
        # 创建新的消息队列
        queue = Queue(maxsize=self.max_queue_size)
        self.tasks[task_id].message_queue = queue
        logger.info(f"SSE 连接已注册到任务: {task_id}")
        
        # 如果任务已经有历史消息，将它们放入队列
        task_state = self.tasks[task_id]
        for log_message in task_state.logs:
            try:
                await queue.put({"type": "log", "message": log_message})
            except asyncio.QueueFull:
                logger.warning(f"任务 {task_id} 的消息队列已满，丢弃历史日志")
                break
        
        # 如果有进度信息，也发送
        if task_state.progress > 0:
            try:
                await queue.put({
                    "type": "progress",
                    "progress": task_state.progress,
                    "message": task_state.logs[-1] if task_state.logs else ""
                })
            except asyncio.QueueFull:
                logger.warning(f"任务 {task_id} 的消息队列已满，丢弃进度信息")
        
        # 如果任务已完成，发送结果
        if task_state.status == "completed":
            await self._send_result_to_queue(task_id)
        elif task_state.status == "error":
            try:
                await queue.put({
                    "type": "error",
                    "message": task_state.logs[-1] if task_state.logs else "未知错误"
                })
            except asyncio.QueueFull:
                logger.warning(f"任务 {task_id} 的消息队列已满，丢弃错误信息")
        
        return queue

    async def unregister_sse_connection(self, task_id: str):
        """
        注销 SSE 连接，清理队列资源
        
        Args:
            task_id: 任务ID
        """
        if task_id in self.tasks:
            self.tasks[task_id].message_queue = None
            logger.info(f"SSE 连接已从任务断开: {task_id}")

    async def send_message(self, message: str, task_id: str):
        """
        发送日志消息到队列
        
        Args:
            message: 日志消息
            task_id: 任务ID
        """
        if task_id in self.tasks:
            self.tasks[task_id].logs.append(message)
            queue = self.tasks[task_id].message_queue
            if queue:
                try:
                    await asyncio.wait_for(
                        queue.put({"type": "log", "message": message}),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"向任务 {task_id} 发送日志消息超时（队列可能已满）")
                except Exception as e:
                    logger.warning(f"向任务 {task_id} 发送日志消息失败: {e}")

    async def send_result(self, title: str, summary: str, task_id: str, filename: str = None, doc_hash: str = None):
        """
        发送任务结果到队列
        
        Args:
            title: 文档标题
            summary: 文档摘要内容
            task_id: 任务ID
            filename: 文件名（可选）
            doc_hash: 文档哈希（可选）
        """
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.status = "completed"
            task_state.result_title = title
            task_state.result_summary = summary
            
            await self._send_result_to_queue(task_id, filename, doc_hash)
    
    async def _send_result_to_queue(self, task_id: str, filename: str = None, doc_hash: str = None):
        """
        内部方法：将结果发送到消息队列
        
        Args:
            task_id: 任务ID
            filename: 文件名（可选）
            doc_hash: 文档哈希（可选）
        """
        task_state = self.tasks[task_id]
        queue = task_state.message_queue
        
        if queue:
            # 清理内容，移除 metadata 和重复标题
            cleaned_summary = clean_content_metadata(
                task_state.result_summary, 
                task_state.result_title
            )
            
            result_data = {
                "type": "result",
                "title": task_state.result_title,
                "summary": cleaned_summary
            }
            
            # 如果没有传入 filename 和 doc_hash，尝试从 result_path 获取
            if not filename and task_state.result_path:
                filename = Path(task_state.result_path).name
            
            if not doc_hash and filename:
                try:
                    from .api import filename_to_hash
                    doc_hash = filename_to_hash.get(filename)
                except (ImportError, KeyError):
                    pass
            
            # 添加文件名和 hash
            if filename:
                result_data["filename"] = filename
            if doc_hash:
                result_data["hash"] = doc_hash
            
            try:
                await asyncio.wait_for(
                    queue.put(result_data),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"向任务 {task_id} 发送结果超时（队列可能已满）")
            except Exception as e:
                logger.warning(f"向任务 {task_id} 发送结果失败: {e}")

    def set_task_result(self, task_id: str, file_path: str):
        """当任务完成时，由工作流调用，用于记录最终产物路径。"""
        if task_id in self.tasks:
            self.tasks[task_id].result_path = file_path
            logger.info(f"任务 {task_id} 结果路径已记录: {file_path}")

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
    
    def get_running_tasks_count(self) -> int:
        """
        获取当前运行中的任务数量
        
        Returns:
            运行中的任务数量
        """
        running_count = sum(
            1 for task in self.tasks.values()
            if task.status == "running"
        )
        return running_count

    def cleanup_task(self, task_id: str):
        pass

    async def set_task_completed(self, task_id: str, result_path: str = None):
        """
        设置任务为完成状态
        
        Args:
            task_id: 任务ID
            result_path: 结果文件路径（可选）
        """
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.status = "completed"
            task_state.progress = 100
            if result_path:
                task_state.result_path = result_path
            logger.info(f"任务 {task_id} 已标记为完成")

    async def update_progress(self, task_id: str, progress: int, message: Optional[str] = None):
        """
        更新任务进度并发送到队列
        
        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            message: 可选的进度消息
        """
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.progress = progress
            if message:
                task_state.logs.append(message)
            
            queue = task_state.message_queue
            if queue:
                try:
                    await asyncio.wait_for(
                        queue.put({
                            "type": "progress",
                            "progress": progress,
                            "message": message or (task_state.logs[-1] if task_state.logs else "")
                        }),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"向任务 {task_id} 更新进度超时（队列可能已满）")
                except Exception as e:
                    logger.warning(f"向任务 {task_id} 更新进度失败: {e}")
    
    async def set_task_error(self, task_id: str, error_info):
        """
        设置任务错误状态并发送到队列
        
        Args:
            task_id: 任务ID
            error_info: 错误信息，可以是字符串或字典
                如果是字典，应包含: error_type, message, technical_details, suggestions 等字段
        """
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.status = "error"
            
            # 处理不同类型的错误信息
            if isinstance(error_info, dict):
                # 结构化错误信息
                error_message = error_info.get("message", "未知错误")
                task_state.logs.append(error_message)
                
                error_data = {
                    "type": "error",
                    "error_type": error_info.get("error_type", "unknown"),
                    "message": error_message,
                    "technical_details": error_info.get("technical_details"),
                    "suggestions": error_info.get("suggestions"),
                    "retry_after": error_info.get("retry_after")
                }
            else:
                # 简单字符串错误消息（向后兼容）
                error_message = str(error_info)
                task_state.logs.append(error_message)
                
                error_data = {
                    "type": "error",
                    "error_type": "unknown",
                    "message": error_message
                }
            
            queue = task_state.message_queue
            if queue:
                try:
                    await asyncio.wait_for(
                        queue.put(error_data),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"向任务 {task_id} 发送错误消息超时（队列可能已满）")
                except Exception as e:
                    logger.warning(f"向任务 {task_id} 发送错误消息失败: {e}")

# 创建一个全局唯一的 TaskManager 实例
manager = TaskManager() 