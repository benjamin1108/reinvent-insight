"""错误恢复机制 - 管理失败计数和重试策略"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class ErrorRecovery:
    """错误恢复策略管理器"""
    
    def __init__(self, max_failures: int = 3):
        """
        初始化错误恢复管理器
        
        Args:
            max_failures: 最大连续失败次数
        """
        self.max_failures = max_failures
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
    
    def should_retry(self) -> bool:
        """
        判断是否应该重试
        
        Returns:
            True 如果应该重试
        """
        if self.failure_count >= self.max_failures:
            logger.warning(f"已达到最大失败次数 ({self.max_failures})，停止重试")
            return False
        return True
    
    def get_retry_delay(self) -> int:
        """
        获取重试延迟时间（秒）
        
        使用指数退避算法：
        - 第1次失败：5分钟 (300秒)
        - 第2次失败：10分钟 (600秒)
        - 第3次失败：20分钟 (1200秒)
        - 最多1小时 (3600秒)
        
        Returns:
            延迟时间（秒）
        """
        base_delay = 300  # 5分钟
        delay = min(base_delay * (2 ** self.failure_count), 3600)
        logger.info(f"计算重试延迟: {delay}秒 (失败次数: {self.failure_count})")
        return delay
    
    def record_failure(self, error_message: str = ""):
        """
        记录失败
        
        Args:
            error_message: 错误消息
        """
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.error(
            f"记录失败 (第 {self.failure_count}/{self.max_failures} 次): {error_message}"
        )
        
        if self.failure_count >= self.max_failures:
            logger.critical(
                f"连续失败 {self.failure_count} 次，已达到最大失败次数！"
                "请检查系统状态并手动干预。"
            )
    
    def record_success(self):
        """记录成功，重置失败计数"""
        if self.failure_count > 0:
            logger.info(f"操作成功，重置失败计数 (之前失败 {self.failure_count} 次)")
        
        self.failure_count = 0
        self.last_failure_time = None
        self.last_success_time = datetime.now()
    
    def reset(self):
        """完全重置状态"""
        logger.info("重置错误恢复状态")
        self.failure_count = 0
        self.last_failure_time = None
        self.last_success_time = None
    
    def get_status(self) -> dict:
        """
        获取当前状态
        
        Returns:
            状态字典
        """
        return {
            'failure_count': self.failure_count,
            'max_failures': self.max_failures,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'should_retry': self.should_retry(),
            'next_retry_delay': self.get_retry_delay() if self.should_retry() else None
        }
    
    def is_healthy(self) -> bool:
        """
        检查系统是否健康
        
        Returns:
            True 如果系统健康（失败次数未达到上限）
        """
        return self.failure_count < self.max_failures
    
    def time_since_last_failure(self) -> Optional[timedelta]:
        """
        获取距离上次失败的时间
        
        Returns:
            时间差，如果没有失败记录则返回 None
        """
        if self.last_failure_time is None:
            return None
        return datetime.now() - self.last_failure_time
    
    def time_since_last_success(self) -> Optional[timedelta]:
        """
        获取距离上次成功的时间
        
        Returns:
            时间差，如果没有成功记录则返回 None
        """
        if self.last_success_time is None:
            return None
        return datetime.now() - self.last_success_time
