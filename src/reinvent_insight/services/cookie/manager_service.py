"""Cookie Manager Service - 管理整个服务的生命周期"""
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from .models import CookieManagerConfig
from .cookie_store import CookieStore
from .refresher import CookieRefresher
from .scheduler import CookieScheduler

logger = logging.getLogger(__name__)


class CookieManagerService:
    """Cookie Manager 服务管理器"""
    
    def __init__(self, config: Optional[CookieManagerConfig] = None):
        """
        初始化服务
        
        Args:
            config: 配置对象，如果为 None 则从环境变量加载
        """
        self.config = config or CookieManagerConfig.from_env()
        
        # 初始化组件
        self.cookie_store = CookieStore(
            store_path=self.config.cookie_store_path,
            netscape_path=self.config.netscape_cookie_path
        )
        
        self.cookie_refresher = CookieRefresher(
            cookie_store=self.cookie_store,
            browser_type=self.config.browser_type,
            browser_timeout=self.config.browser_timeout,
            headless=True,
            max_retry_count=self.config.max_retry_count
        )
        
        self.scheduler = CookieScheduler(
            refresher=self.cookie_refresher,
            interval_hours=self.config.refresh_interval_hours,
            retry_delay_minutes=self.config.retry_delay_minutes
        )
        
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self._background_tasks = set()  # 跟踪后台任务
    
    async def start(self) -> None:
        """启动服务"""
        if self.is_running:
            logger.warning("服务已经在运行")
            return
        
        try:
            logger.info("启动 Cookie Manager 服务")
            
            # 检查 PID 文件
            if self._check_pid_file():
                raise RuntimeError(
                    f"服务已在运行（PID 文件存在: {self.config.pid_file_path}）"
                )
            
            # 创建 PID 文件
            self._create_pid_file()
            
            # 检查是否有 cookies
            cookies = self.cookie_store.load_cookies()
            if not cookies:
                logger.warning(
                    "没有找到 cookies。请使用 'reinvent-insight cookie-manager import' 导入 cookies"
                )
            else:
                logger.info(f"加载了 {len(cookies)} 个 cookies")
            
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Cookie Manager 服务启动成功")
            
            # 等待关闭信号
            await self._shutdown_event.wait()
            
            # 收到关闭信号，停止服务
            logger.info("收到关闭信号，正在停止服务...")
            self.scheduler.stop()
            self._cleanup_pid_file()
            self.is_running = False
            logger.info("服务已停止")
        
        except Exception as e:
            logger.error(f"启动服务失败: {e}")
            self._cleanup_pid_file()
            raise
    
    async def stop(self) -> None:
        """停止服务"""
        if not self.is_running:
            logger.warning("服务未运行")
            return
        
        try:
            logger.info("停止 Cookie Manager 服务")
            
            # 停止调度器
            self.scheduler.stop()
            
            # 清理 PID 文件
            self._cleanup_pid_file()
            
            self.is_running = False
            self._shutdown_event.set()
            
            logger.info("Cookie Manager 服务已停止")
        
        except Exception as e:
            logger.error(f"停止服务失败: {e}")
            raise
    
    def get_status(self) -> dict:
        """
        获取服务状态
        
        Returns:
            状态字典
        """
        return {
            'is_running': self.is_running,
            'config': {
                'refresh_interval_hours': self.config.refresh_interval_hours,
                'browser_type': self.config.browser_type,
                'cookie_store_path': str(self.config.cookie_store_path),
                'netscape_cookie_path': str(self.config.netscape_cookie_path)
            },
            'scheduler': self.scheduler.get_status() if self.is_running else None,
            'cookie_store': {
                'has_cookies': bool(self.cookie_store.load_cookies()),
                'is_valid': self.cookie_store.is_valid(),
                'metadata': self.cookie_store.get_metadata()
            }
        }
    
    def is_service_running(self) -> bool:
        """
        检查服务是否正在运行
        
        Returns:
            True 如果服务正在运行
        """
        return self.is_running
    
    def _check_pid_file(self) -> bool:
        """
        检查 PID 文件是否存在
        
        Returns:
            True 如果 PID 文件存在且进程正在运行
        """
        pid_file = self.config.pid_file_path
        
        if not pid_file.exists():
            return False
        
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # 检查进程是否存在
            try:
                os.kill(pid, 0)  # 发送信号 0 检查进程是否存在
                logger.warning(f"发现运行中的服务进程 (PID: {pid})")
                return True
            except OSError:
                # 进程不存在，清理残留的 PID 文件
                logger.info(f"清理残留的 PID 文件 (进程 {pid} 不存在)")
                pid_file.unlink()
                return False
        
        except Exception as e:
            logger.warning(f"检查 PID 文件失败: {e}")
            return False
    
    def _create_pid_file(self):
        """创建 PID 文件"""
        pid_file = self.config.pid_file_path
        
        try:
            # 确保父目录存在
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入当前进程 PID
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info(f"创建 PID 文件: {pid_file}")
        
        except Exception as e:
            logger.error(f"创建 PID 文件失败: {e}")
            raise
    
    def _cleanup_pid_file(self):
        """清理 PID 文件"""
        pid_file = self.config.pid_file_path
        
        try:
            if pid_file.exists():
                pid_file.unlink()
                logger.info(f"删除 PID 文件: {pid_file}")
        
        except Exception as e:
            logger.warning(f"删除 PID 文件失败: {e}")
    
    def setup_signal_handlers(self):
        """设置信号处理器（用于优雅关闭）"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备关闭服务")
            
            # 立即停止调度器
            try:
                if self.scheduler:
                    logger.info("停止调度器...")
                    self.scheduler.stop()
            except Exception as e:
                logger.warning(f"停止调度器时出错: {e}")
            
            # 清理 PID 文件
            try:
                self._cleanup_pid_file()
            except Exception as e:
                logger.warning(f"清理 PID 文件时出错: {e}")
            
            # 设置关闭事件，让主循环退出
            self.is_running = False
            self._shutdown_event.set()
            
            logger.info("服务关闭信号已处理")
        
        # 注册信号处理器
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("信号处理器已设置")


async def run_service_daemon(config: Optional[CookieManagerConfig] = None):
    """
    以守护进程模式运行服务
    
    Args:
        config: 配置对象
    """
    service = CookieManagerService(config)
    service.setup_signal_handlers()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
    except Exception as e:
        logger.error(f"服务运行异常: {e}")
        raise
    finally:
        await service.stop()


def stop_service(pid_file_path: Optional[Path] = None):
    """
    停止正在运行的服务
    
    Args:
        pid_file_path: PID 文件路径
    """
    if pid_file_path is None:
        config = CookieManagerConfig.from_env()
        pid_file_path = config.pid_file_path
    
    if not pid_file_path.exists():
        logger.warning("服务未运行（PID 文件不存在）")
        return False
    
    try:
        with open(pid_file_path, 'r') as f:
            pid = int(f.read().strip())
        
        logger.info(f"停止服务进程 (PID: {pid})")
        
        # 发送 SIGTERM 信号
        os.kill(pid, signal.SIGTERM)
        
        # 等待进程退出
        import time
        for i in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                logger.info("服务已停止")
                return True
        
        # 如果进程仍在运行，发送 SIGKILL
        logger.warning("进程未响应 SIGTERM，发送 SIGKILL")
        os.kill(pid, signal.SIGKILL)
        return True
    
    except ProcessLookupError:
        logger.warning(f"进程不存在 (PID: {pid})")
        # 清理 PID 文件
        pid_file_path.unlink()
        return False
    except Exception as e:
        logger.error(f"停止服务失败: {e}")
        return False


def get_service_status(pid_file_path: Optional[Path] = None) -> dict:
    """
    获取服务状态
    
    Args:
        pid_file_path: PID 文件路径
        
    Returns:
        状态字典
    """
    if pid_file_path is None:
        config = CookieManagerConfig.from_env()
        pid_file_path = config.pid_file_path
    
    if not pid_file_path.exists():
        return {
            'is_running': False,
            'message': '服务未运行'
        }
    
    try:
        with open(pid_file_path, 'r') as f:
            pid = int(f.read().strip())
        
        # 检查进程是否存在
        try:
            os.kill(pid, 0)
            return {
                'is_running': True,
                'pid': pid,
                'message': f'服务正在运行 (PID: {pid})'
            }
        except OSError:
            return {
                'is_running': False,
                'message': f'服务未运行（残留 PID 文件，进程 {pid} 不存在）'
            }
    
    except Exception as e:
        return {
            'is_running': False,
            'message': f'无法获取状态: {str(e)}'
        }
