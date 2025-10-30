"""Cookie Scheduler - 管理定时刷新任务"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from .cookie_refresher import CookieRefresher

logger = logging.getLogger(__name__)


class CookieScheduler:
    """Cookie 定时刷新调度器"""
    
    def __init__(
        self,
        refresher: CookieRefresher,
        interval_hours: int = 6,
        retry_delay_minutes: int = 5
    ):
        """
        初始化调度器
        
        Args:
            refresher: Cookie 刷新器
            interval_hours: 刷新间隔（小时）
            retry_delay_minutes: 失败后重试延迟（分钟）
        """
        self.refresher = refresher
        self.interval_hours = interval_hours
        self.retry_delay_minutes = retry_delay_minutes
        
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_refresh_time: Optional[datetime] = None
        self.next_refresh_time: Optional[datetime] = None
    
    def start(self) -> None:
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已经在运行")
            return
        
        try:
            logger.info(f"启动 Cookie 刷新调度器 (间隔: {self.interval_hours} 小时)")
            
            # 添加定时任务
            self.scheduler.add_job(
                self._refresh_job,
                trigger=IntervalTrigger(hours=self.interval_hours),
                id='cookie_refresh',
                name='Cookie 定时刷新',
                replace_existing=True,
                max_instances=1  # 确保同时只有一个实例运行
            )
            
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            
            # 更新下次运行时间
            self._update_next_run_time()
            
            logger.info(f"调度器启动成功，下次刷新时间: {self.next_refresh_time}")
            logger.info("Cookie 验证将在第一次定时刷新时进行")
        
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止调度器"""
        if not self.is_running:
            logger.warning("调度器未运行")
            return
        
        try:
            logger.info("停止 Cookie 刷新调度器")
            # 立即停止调度器，不等待正在运行的任务
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("调度器已停止")
        
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
            # 即使出错也标记为已停止
            self.is_running = False
    
    async def _initial_validation(self):
        """启动时立即验证 cookies"""
        try:
            logger.info("执行初始 cookie 验证")
            
            # 检查是否有 cookies
            cookies = self.refresher.cookie_store.load_cookies()
            if not cookies:
                logger.warning("没有找到 cookies，跳过初始验证")
                return
            
            # 验证 cookies
            is_valid = await self.refresher.validate_cookies_online(cookies)
            
            if is_valid:
                logger.info("初始验证成功，cookies 有效")
                # 更新元数据
                self.refresher.cookie_store.update_metadata(
                    last_validated=datetime.now().isoformat(),
                    validation_status="valid"
                )
            else:
                logger.warning("初始验证失败，将在下次调度时刷新")
                # 安排提前刷新
                self._schedule_retry()
        
        except Exception as e:
            logger.error(f"初始验证失败: {e}")
    
    async def _refresh_job(self):
        """定时刷新任务"""
        try:
            logger.info("执行定时 cookie 刷新")
            self.last_refresh_time = datetime.now()
            
            # 执行刷新
            success, message = await self.refresher.refresh()
            
            if success:
                logger.info(f"定时刷新成功: {message}")
                # 更新下次运行时间
                self._update_next_run_time()
            else:
                logger.error(f"定时刷新失败: {message}")
                
                # 检查是否应该重试
                if self.refresher.error_recovery.should_retry():
                    # 安排重试
                    self._schedule_retry()
                else:
                    logger.critical(
                        "连续刷新失败次数过多，已停止自动刷新。"
                        "请检查系统状态并手动执行刷新。"
                    )
        
        except Exception as e:
            logger.error(f"定时刷新任务异常: {e}")
            self.refresher.error_recovery.record_failure(str(e))
            
            if self.refresher.error_recovery.should_retry():
                self._schedule_retry()
    
    def _schedule_retry(self):
        """安排重试任务"""
        retry_delay = self.refresher.error_recovery.get_retry_delay()
        retry_time = datetime.now() + timedelta(seconds=retry_delay)
        
        logger.info(f"安排重试任务，将在 {retry_time} 执行")
        
        # 添加一次性重试任务
        self.scheduler.add_job(
            self._refresh_job,
            trigger=DateTrigger(run_date=retry_time),
            id='cookie_refresh_retry',
            name='Cookie 刷新重试',
            replace_existing=True
        )
        
        self.next_refresh_time = retry_time
    
    def _update_next_run_time(self):
        """更新下次运行时间"""
        job = self.scheduler.get_job('cookie_refresh')
        if job and job.next_run_time:
            self.next_refresh_time = job.next_run_time
            logger.debug(f"下次刷新时间: {self.next_refresh_time}")
    
    async def trigger_manual_refresh(self) -> tuple[bool, str]:
        """
        手动触发刷新
        
        Returns:
            (是否成功, 消息)
        """
        logger.info("手动触发 cookie 刷新")
        
        try:
            success, message = await self.refresher.refresh()
            
            if success:
                logger.info(f"手动刷新成功: {message}")
                # 更新下次运行时间
                self._update_next_run_time()
            else:
                logger.error(f"手动刷新失败: {message}")
            
            return success, message
        
        except Exception as e:
            error_msg = f"手动刷新异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        获取下次运行时间
        
        Returns:
            下次运行时间，如果未设置则返回 None
        """
        return self.next_refresh_time
    
    def get_status(self) -> dict:
        """
        获取调度器状态
        
        Returns:
            状态字典
        """
        return {
            'is_running': self.is_running,
            'interval_hours': self.interval_hours,
            'last_refresh_time': self.last_refresh_time.isoformat() if self.last_refresh_time else None,
            'next_refresh_time': self.next_refresh_time.isoformat() if self.next_refresh_time else None,
            'error_recovery': self.refresher.get_error_status()
        }
