import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from fastapi import WebSocket
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
    websocket: Optional[WebSocket] = None
    task: Optional[asyncio.Task] = None
    # 自适应长度相关字段
    adaptive_enabled: bool = False
    length_target: Optional[Dict] = None
    length_statistics: Optional[Dict] = None
    video_analysis: Optional[Dict] = None

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

    async def send_result(self, title: str, summary: str, task_id: str, filename: str = None, doc_hash: str = None):
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            task_state.status = "completed"
            task_state.result_title = title
            task_state.result_summary = summary
            
            # 清理内容，移除 metadata 和重复标题
            cleaned_summary = clean_content_metadata(summary, title)
            
            ws = task_state.websocket
            if ws:
                try:
                    result_data = {
                        "type": "result",
                        "title": title,
                        "summary": cleaned_summary  # 发送清理后的内容
                    }
                    
                    # 如果有文件名和 hash，添加到结果中
                    if filename:
                        result_data["filename"] = filename
                    if doc_hash:
                        result_data["hash"] = doc_hash
                        
                    await ws.send_json(result_data)
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
                    # 获取文件名和 hash（如果有的话）
                    filename = None
                    doc_hash = None
                    if task_state.result_path:
                        # 从文件路径提取文件名
                        filename = Path(task_state.result_path).name
                        # 尝试获取 hash
                        try:
                            from .api import filename_to_hash
                            doc_hash = filename_to_hash.get(filename)
                        except (ImportError, KeyError):
                            pass
                    
                    await self.send_result(task_state.result_title, task_state.result_summary, task_id, filename, doc_hash)
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

    # 自适应长度相关方法
    def set_adaptive_enabled(self, task_id: str, enabled: bool = True):
        """设置任务的自适应功能状态"""
        if task_id in self.tasks:
            self.tasks[task_id].adaptive_enabled = enabled
            logger.info(f"任务 {task_id} 自适应功能{'启用' if enabled else '禁用'}")

    def set_length_target(self, task_id: str, length_target: Dict):
        """设置任务的长度目标"""
        if task_id in self.tasks:
            self.tasks[task_id].length_target = length_target
            logger.info(f"任务 {task_id} 长度目标已设置: {length_target.get('target_length', 'N/A')}字")

    def set_video_analysis(self, task_id: str, video_analysis: Dict):
        """设置任务的视频分析结果"""
        if task_id in self.tasks:
            self.tasks[task_id].video_analysis = video_analysis
            logger.info(f"任务 {task_id} 视频分析结果已设置")

    def update_length_statistics(self, task_id: str, statistics: Dict):
        """更新任务的长度统计信息"""
        if task_id in self.tasks:
            self.tasks[task_id].length_statistics = statistics
            logger.debug(f"任务 {task_id} 长度统计已更新")

    async def send_length_update(self, task_id: str, length_data: Dict):
        """发送长度相关的实时更新"""
        if task_id in self.tasks:
            ws = self.tasks[task_id].websocket
            if ws:
                try:
                    await ws.send_json({
                        "type": "length_update",
                        "data": length_data
                    })
                except Exception as e:
                    logger.warning(f"向客户端 {task_id} 发送长度更新失败 (可能已断开): {e}")

    async def send_adaptive_status(self, task_id: str):
        """发送自适应工作流状态"""
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            ws = task_state.websocket
            if ws and task_state.adaptive_enabled:
                try:
                    adaptive_data = {
                        "adaptive_enabled": task_state.adaptive_enabled,
                        "length_target": task_state.length_target,
                        "video_analysis": task_state.video_analysis,
                        "length_statistics": task_state.length_statistics
                    }
                    await ws.send_json({
                        "type": "adaptive_status",
                        "data": adaptive_data
                    })
                except Exception as e:
                    logger.warning(f"向客户端 {task_id} 发送自适应状态失败 (可能已断开): {e}")

    def get_task_adaptive_info(self, task_id: str) -> Optional[Dict]:
        """获取任务的自适应信息"""
        if task_id in self.tasks:
            task_state = self.tasks[task_id]
            return {
                "adaptive_enabled": task_state.adaptive_enabled,
                "length_target": task_state.length_target,
                "video_analysis": task_state.video_analysis,
                "length_statistics": task_state.length_statistics
            }
        return None

# 创建一个全局唯一的 TaskManager 实例
manager = TaskManager() 