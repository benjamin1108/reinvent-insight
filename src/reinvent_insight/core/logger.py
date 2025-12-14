import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar
from rich.logging import RichHandler

# 请求上下文
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
task_id_var: ContextVar[Optional[str]] = ContextVar('task_id', default=None)


class ContextFilter(logging.Filter):
    """添加上下文信息到日志记录
    
    规范：空值时不显示，而不是显示 '-' 占位符
    """
    
    def filter(self, record):
        req_id = request_id_var.get()
        task_id = task_id_var.get()
        
        # 动态生成上下文字段（只显示有值的部分）
        ctx_parts = []
        if req_id:
            ctx_parts.append(f"req={req_id}")
        if task_id:
            ctx_parts.append(f"task={task_id}")
        
        record.context = " ".join(ctx_parts) if ctx_parts else ""
        record.context_sep = " │ " if ctx_parts else ""
        return True


def setup_logger(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    enable_file_logging: bool = True,
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 5
) -> None:
    """
    配置根日志记录器
    
    Args:
        level: 日志级别
        log_dir: 日志文件目录
        enable_file_logging: 是否启用文件日志
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清理现有处理器
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    # 添加上下文过滤器
    context_filter = ContextFilter()
    
    # 1. 控制台处理器 (Rich)
    console_handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        log_time_format="[%X]",
        keywords=RichHandler.KEYWORDS + ["SUCCESS"],
        show_path=True  # 显示文件路径
    )
    console_handler.addFilter(context_filter)
    
    # 增强的格式：包含模块名
    console_formatter = logging.Formatter(
        fmt="%(name)s │ %(message)s",
        datefmt="[%X]"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 2. 文件处理器 (可选)
    if enable_file_logging and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 按日期的日志文件
        log_file = log_dir / f"app_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.addFilter(context_filter)
        
        # 文件格式：包含完整信息（上下文空时不显示）
        file_formatter = logging.Formatter(
            fmt="%(asctime)s │ %(levelname)-8s │ %(name)s:%(lineno)d%(context_sep)s%(context)s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 3. 静默第三方库
    noisy_loggers = [
        "httpx", "httpcore", "uvicorn", "uvicorn.access", 
        "uvicorn.error", "watchfiles", "websockets", 
        "asyncio", "PIL", "multipart"
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    root_logger.info(f"日志系统初始化，级别: {level.upper()}")

# 添加一个新的日志级别 "SUCCESS"
logging.SUCCESS = 25  # 在 INFO (20) 和 WARNING (30) 之间
logging.addLevelName(logging.SUCCESS, "SUCCESS")

def success(self, message, *args, **kws):
    if self.isEnabledFor(logging.SUCCESS):
        self._log(logging.SUCCESS, message, args, **kws)

logging.Logger.success = success

def get_logger(name: str = None) -> logging.Logger:
    """
    获取一个日志记录器实例。
    
    Args:
        name (str): 日志记录器的名称，通常使用 __name__
        
    Returns:
        logging.Logger: 配置好的日志记录器实例
    """
    return logging.getLogger(name) 