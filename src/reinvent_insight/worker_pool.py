"""
任务 Worker Pool - 管理分析任务的队列和并发执行

功能:
1. 任务队列管理（支持优先级）
2. 并发控制（可配置的 worker 数量）
3. 任务超时处理
4. 队列状态监控
"""

import asyncio
import logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from . import config
from .task_manager import manager

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass(order=True)
class WorkerTask:
    """Worker 任务
    
    使用 @dataclass(order=True) 实现优先级队列的自动排序
    priority 字段需要放在第一位用于比较
    """
    # 优先级（负值用于 PriorityQueue，数值越大优先级越高）
    priority: int = field(compare=True)
    
    # 任务 ID（不参与比较）
    task_id: str = field(compare=False)
    
    # 任务类型
    task_type: str = field(default="youtube", compare=False)  # "youtube", "pdf", "document"
    
    # YouTube URL 或文件路径
    url_or_path: str = field(default="", compare=False)
    
    # 可选标题（用于文档分析）
    title: Optional[str] = field(default=None, compare=False)
    
    # 创建时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(), compare=False)
    
    # 回调函数（可选）
    callback: Optional[Callable] = field(default=None, compare=False, repr=False)


class WorkerPool:
    """全局任务 Worker 池
    
    管理所有分析任务的并发执行，支持：
    - 优先级队列
    - 并发数控制
    - 任务超时
    - 状态监控
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        task_timeout: Optional[int] = None
    ):
        """初始化 Worker 池
        
        Args:
            max_workers: 最大并发 worker 数，默认从配置读取
            max_queue_size: 队列最大长度，默认从配置读取
            task_timeout: 任务超时时间（秒），默认从配置读取
        """
        self.max_workers = max_workers or config.MAX_CONCURRENT_ANALYSIS_TASKS
        self.max_queue_size = max_queue_size or config.ANALYSIS_QUEUE_MAX_SIZE
        self.task_timeout = task_timeout or config.ANALYSIS_TASK_TIMEOUT
        
        # 优先级队列
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=self.max_queue_size)
        
        # Worker 运行状态
        self.is_running = False
        self.workers = []
        
        # 统计信息
        self.stats = {
            'total_processed': 0,
            'total_success': 0,
            'total_failed': 0,
            'total_timeout': 0,
            'current_processing': 0
        }
        
        logger.info(
            f"Worker Pool 初始化: "
            f"max_workers={self.max_workers}, "
            f"max_queue_size={self.max_queue_size}, "
            f"task_timeout={self.task_timeout}s"
        )
    
    async def add_task(
        self,
        task_id: str,
        task_type: str,
        url_or_path: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        title: Optional[str] = None,
        callback: Optional[Callable] = None
    ) -> bool:
        """添加任务到队列
        
        Args:
            task_id: 任务 ID
            task_type: 任务类型 ("youtube", "pdf", "document")
            url_or_path: URL 或文件路径
            priority: 任务优先级
            title: 可选标题
            callback: 可选回调函数
            
        Returns:
            bool: 是否成功加入队列
        """
        try:
            # 创建任务对象（使用负优先级，因为 PriorityQueue 是最小堆）
            task = WorkerTask(
                priority=-priority.value,  # 负值：数值越大优先级越高
                task_id=task_id,
                task_type=task_type,
                url_or_path=url_or_path,
                title=title,
                callback=callback
            )
            
            # 非阻塞加入队列
            self.queue.put_nowait(task)
            
            queue_size = self.queue.qsize()
            logger.info(
                f"任务已加入队列: task_id={task_id}, "
                f"type={task_type}, "
                f"priority={priority.name}, "
                f"queue_size={queue_size}/{self.max_queue_size}"
            )
            
            # 更新任务管理器中的状态
            task_state = manager.get_task_state(task_id)
            if task_state:
                task_state.status = "queued"
                asyncio.create_task(
                    manager.send_message(
                        f"任务已加入队列，当前排队: {queue_size} 个任务",
                        task_id
                    )
                )
            
            return True
            
        except asyncio.QueueFull:
            logger.error(f"任务队列已满 ({self.max_queue_size})，无法添加任务: {task_id}")
            
            # 通知任务失败
            task_state = manager.get_task_state(task_id)
            if task_state:
                asyncio.create_task(
                    manager.set_task_error(
                        task_id,
                        {
                            "error_type": "queue_full",
                            "message": f"任务队列已满（当前 {self.max_queue_size} 个任务），请稍后重试",
                            "suggestions": [
                                "等待当前任务完成后重试",
                                "联系管理员增加队列容量"
                            ]
                        }
                    )
                )
            
            return False
        except Exception as e:
            logger.error(f"添加任务到队列失败: {e}", exc_info=True)
            return False
    
    async def _execute_task(self, task: WorkerTask) -> bool:
        """执行单个任务
        
        Args:
            task: 任务对象
            
        Returns:
            bool: 是否执行成功
        """
        task_id = task.task_id
        
        try:
            logger.info(f"开始执行任务: {task_id}, type={task.task_type}")
            
            # 更新状态为运行中
            task_state = manager.get_task_state(task_id)
            if task_state:
                task_state.status = "running"
            
            # 根据任务类型选择不同的 worker
            if task.task_type == "youtube":
                from .worker import summary_task_worker_async
                worker_func = summary_task_worker_async(task.url_or_path, task_id)
                
            elif task.task_type == "pdf":
                from .pdf_worker import pdf_analysis_worker_async
                from .api import PDFAnalysisRequest
                req = PDFAnalysisRequest(title=task.title)
                worker_func = pdf_analysis_worker_async(req, task_id, task.url_or_path)
                
            elif task.task_type == "document":
                from .document_worker import document_analysis_worker_async
                worker_func = document_analysis_worker_async(
                    task_id, task.url_or_path, task.title or "未命名文档"
                )
            else:
                raise ValueError(f"未知的任务类型: {task.task_type}")
            
            # 执行任务（带超时）
            await asyncio.wait_for(worker_func, timeout=self.task_timeout)
            
            # 执行回调
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(task_id, True, None)
                    else:
                        task.callback(task_id, True, None)
                except Exception as e:
                    logger.warning(f"任务回调执行失败: {e}")
            
            logger.info(f"任务执行成功: {task_id}")
            self.stats['total_success'] += 1
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"任务执行超时 ({self.task_timeout}s): {task_id}")
            
            # 通知超时
            await manager.set_task_error(
                task_id,
                {
                    "error_type": "timeout",
                    "message": f"任务执行超时（超过 {self.task_timeout} 秒）",
                    "technical_details": f"任务类型: {task.task_type}",
                    "suggestions": [
                        "检查网络连接是否正常",
                        "检查视频/文档大小是否过大",
                        "联系管理员增加超时时间"
                    ]
                }
            )
            
            self.stats['total_timeout'] += 1
            return False
            
        except Exception as e:
            logger.error(f"任务执行失败: {task_id}, 错误: {e}", exc_info=True)
            
            # 任务可能已经在 worker 中设置了错误，这里不重复设置
            # 只有在任务状态不是 error 时才设置
            task_state = manager.get_task_state(task_id)
            if task_state and task_state.status != "error":
                await manager.set_task_error(
                    task_id,
                    {
                        "error_type": "execution_error",
                        "message": f"任务执行失败: {str(e)}",
                        "technical_details": str(e)
                    }
                )
            
            self.stats['total_failed'] += 1
            return False
    
    async def worker(self, worker_id: int):
        """Worker 循环
        
        Args:
            worker_id: Worker 编号
        """
        logger.info(f"Worker {worker_id} 启动")
        
        while self.is_running:
            task = None
            try:
                # 从队列获取任务（带超时）
                task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=5.0
                )
                
                self.stats['current_processing'] += 1
                self.stats['total_processed'] += 1
                
                logger.info(
                    f"Worker {worker_id} 获取任务: {task.task_id}, "
                    f"优先级: {-task.priority}, "
                    f"队列剩余: {self.queue.qsize()}"
                )
                
                # 执行任务
                success = await self._execute_task(task)
                
                self.stats['current_processing'] -= 1
                
                # 标记任务完成
                self.queue.task_done()
                
                logger.info(
                    f"Worker {worker_id} 完成任务: {task.task_id}, "
                    f"成功: {success}"
                )
                
            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
                
            except Exception as e:
                logger.error(f"Worker {worker_id} 异常: {e}", exc_info=True)
                
                # 如果任务获取成功但执行失败，也要标记完成
                if task:
                    self.stats['current_processing'] -= 1
                    self.queue.task_done()
                
                # 短暂休息后继续
                await asyncio.sleep(1)
        
        logger.info(f"Worker {worker_id} 停止")
    
    async def start(self):
        """启动 Worker 池"""
        if self.is_running:
            logger.warning("Worker Pool 已在运行中")
            return
        
        self.is_running = True
        
        # 启动多个 worker
        self.workers = []
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(self.worker(i))
            self.workers.append(worker_task)
        
        logger.info(
            f"✅ Worker Pool 已启动: "
            f"{self.max_workers} 个 Worker, "
            f"队列容量: {self.max_queue_size}"
        )
    
    async def stop(self, wait_completion: bool = True):
        """停止 Worker 池
        
        Args:
            wait_completion: 是否等待所有任务完成
        """
        if not self.is_running:
            return
        
        logger.info("正在停止 Worker Pool...")
        
        if wait_completion:
            # 等待队列中的所有任务完成
            queue_size = self.queue.qsize()
            if queue_size > 0:
                logger.info(f"等待 {queue_size} 个任务完成...")
                await self.queue.join()
        
        # 停止 worker
        self.is_running = False
        
        # 等待所有 worker 退出
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        logger.info("Worker Pool 已停止")
    
    def get_queue_size(self) -> int:
        """获取队列长度"""
        return self.queue.qsize()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self.stats,
            'queue_size': self.queue.qsize(),
            'max_workers': self.max_workers,
            'max_queue_size': self.max_queue_size,
            'is_running': self.is_running
        }
    
    def is_queue_full(self) -> bool:
        """检查队列是否已满"""
        return self.queue.qsize() >= self.max_queue_size
    
    async def clear_queue(self):
        """清空队列（慎用）"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break
        
        logger.warning("队列已清空")


# 全局 Worker Pool 实例
worker_pool = WorkerPool()
