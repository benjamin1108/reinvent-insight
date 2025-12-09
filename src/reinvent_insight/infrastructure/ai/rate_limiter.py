"""速率限制器"""

import asyncio
import time
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """全局速率限制器"""
    
    _lock = asyncio.Lock()
    _last_call_time: Dict[str, float] = {}
    
    def __init__(self, interval: float):
        """
        初始化速率限制器
        
        Args:
            interval: 调用间隔（秒）
        """
        self.interval = interval
        
    async def acquire(self, key: str = "default") -> None:
        """
        获取调用许可，必要时等待
        
        Args:
            key: 限制器键名，用于区分不同的限制器
        """
        async with self._lock:
            now = time.monotonic()
            last_time = self._last_call_time.get(key, 0.0)
            elapsed = now - last_time
            
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                logger.debug(f"触发速率限制 [{key}]，等待 {sleep_time:.2f} 秒")
                await asyncio.sleep(sleep_time)
            
            self._last_call_time[key] = time.monotonic()
