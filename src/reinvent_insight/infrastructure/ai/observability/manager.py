"""可观测管理器 - 单例模式管理日志写入"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import asyncio
from threading import Lock

from reinvent_insight.core import config
from .models import InteractionRecord
from .formatter import LogFormatter

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """可观测层管理器（单例）"""
    
    _instance: Optional['ObservabilityManager'] = None
    _lock = Lock()
    
    def __init__(self):
        """私有构造函数"""
        self.enabled = config.MODEL_OBSERVABILITY_ENABLED
        self.output_dir = Path(config.MODEL_OBSERVABILITY_OUTPUT_DIR)
        self.log_level = config.MODEL_OBSERVABILITY_LOG_LEVEL
        self.mask_sensitive = config.MODEL_OBSERVABILITY_MASK_SENSITIVE
        self.max_prompt_length = config.MODEL_OBSERVABILITY_MAX_PROMPT_LENGTH
        self.max_response_length = config.MODEL_OBSERVABILITY_MAX_RESPONSE_LENGTH
        
        # 确保输出目录存在
        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"可观测层已启用，日志目录: {self.output_dir}")
        
        self.formatter = LogFormatter()
        
        # 错误计数（用于降级保护）
        self._error_count = 0
        self._max_errors = 3
    
    @classmethod
    def get_instance(cls) -> 'ObservabilityManager':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ObservabilityManager()
        return cls._instance
    
    def is_enabled(self) -> bool:
        """检查是否启用可观测"""
        return self.enabled and self._error_count < self._max_errors
    
    def log_interaction(self, record: Optional[InteractionRecord]) -> None:
        """
        记录一次交互
        
        Args:
            record: 交互记录
        """
        if not self.is_enabled() or record is None:
            return
        
        try:
            # 写入文件
            self._write_to_file(record)
            
            # 重置错误计数
            if self._error_count > 0:
                self._error_count = 0
                
        except Exception as e:
            self._error_count += 1
            logger.error(f"可观测层写入失败 ({self._error_count}/{self._max_errors}): {e}")
            
            if self._error_count >= self._max_errors:
                logger.error("可观测层连续失败次数过多，已自动禁用")
                self.enabled = False
    
    def _write_to_file(self, record: InteractionRecord) -> None:
        """
        写入文件
        
        Args:
            record: 交互记录
        """
        # 按日期分目录
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.output_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # 按提供商分文件
        provider = record.provider
        
        # 写入JSONL格式
        jsonl_file = date_dir / f"{provider}_interactions.jsonl"
        jsonl_line = self.formatter.format_jsonl(record)
        
        with open(jsonl_file, 'a', encoding='utf-8') as f:
            f.write(jsonl_line + '\n')
        
        # 写入人类可读格式
        if self.log_level in ["DETAILED", "FULL"]:
            human_file = date_dir / f"{provider}_interactions_human.txt"
            human_text = self.formatter.format_human_readable(record)
            
            with open(human_file, 'a', encoding='utf-8') as f:
                f.write(human_text)
        
        # 检查文件大小，超过限制时轮转
        self._check_file_rotation(jsonl_file)
    
    def _check_file_rotation(self, file_path: Path) -> None:
        """
        检查文件大小，超过限制时轮转
        
        Args:
            file_path: 文件路径
        """
        try:
            if not file_path.exists():
                return
            
            max_size_bytes = config.MODEL_OBSERVABILITY_MAX_FILE_SIZE_MB * 1024 * 1024
            file_size = file_path.stat().st_size
            
            if file_size > max_size_bytes:
                # 重命名为带时间戳的文件
                timestamp = datetime.now().strftime("%H%M%S")
                new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                new_path = file_path.parent / new_name
                file_path.rename(new_path)
                logger.info(f"日志文件已轮转: {file_path} -> {new_path}")
        except Exception as e:
            logger.warning(f"文件轮转检查失败: {e}")
    
    def cleanup_old_logs(self) -> None:
        """清理过期日志"""
        if not self.enabled:
            return
        
        try:
            retention_days = config.MODEL_OBSERVABILITY_RETENTION_DAYS
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for date_dir in self.output_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                try:
                    # 尝试解析目录名为日期
                    dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                    
                    if dir_date < cutoff_date:
                        # 删除整个目录
                        import shutil
                        shutil.rmtree(date_dir)
                        logger.info(f"已清理过期日志目录: {date_dir}")
                except ValueError:
                    # 不是日期格式的目录，跳过
                    continue
        except Exception as e:
            logger.error(f"清理过期日志失败: {e}")


# 全局单例实例
_manager_instance = None


def get_manager() -> ObservabilityManager:
    """获取可观测管理器实例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ObservabilityManager.get_instance()
    return _manager_instance
