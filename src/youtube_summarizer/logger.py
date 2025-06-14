import logging
import sys
from rich.logging import RichHandler

def setup_logger(level: str = "INFO") -> None:
    """
    配置根日志记录器。

    Args:
        level (str): 要设置的日志级别 (e.g., "DEBUG", "INFO", "WARNING").
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 移除任何已存在的处理器，以避免重复日志
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 创建一个 RichHandler，它将格式化并为日志输出着色
    handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        log_time_format="[%X]",
        keywords=RichHandler.KEYWORDS + ["SUCCESS"]
    )

    # 创建一个格式化器并将其添加到处理器
    formatter = logging.Formatter(
        fmt="%(message)s",
        datefmt="[%X]"
    )
    handler.setFormatter(formatter)

    # 将处理器添加到根日志记录器
    root_logger.addHandler(handler)

    # 为 httpx 添加特殊处理，因为它在 DEBUG 级别下过于冗长
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info(f"日志级别已设置为: {level.upper()}")

# 添加一个新的日志级别 "SUCCESS"
logging.SUCCESS = 25  # 在 INFO (20) 和 WARNING (30) 之间
logging.addLevelName(logging.SUCCESS, "SUCCESS")

def success(self, message, *args, **kws):
    if self.isEnabledFor(logging.SUCCESS):
        self._log(logging.SUCCESS, message, args, **kws)

logging.Logger.success = success 