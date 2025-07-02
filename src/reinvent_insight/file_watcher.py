from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from pathlib import Path
import logging

# 这是一个技巧，允许我们延迟导入，避免循环依赖
# 我们不能直接在顶层从 .api 导入 init_hash_mappings，因为 api.py 最终也会导入本模块的东西
try:
    from .api import init_hash_mappings
except ImportError:
    init_hash_mappings = None

logger = logging.getLogger(__name__)

class SummaryDirectoryEventHandler(FileSystemEventHandler):
    """处理摘要目录中的文件系统事件。"""
    
    def __init__(self, callback):
        self.callback = callback

    def on_deleted(self, event):
        """当文件或目录被删除时调用。"""
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"检测到摘要文件被删除: {event.src_path}. 准备刷新缓存...")
            self.callback()

    def on_created(self, event):
        """当文件或目录被创建时调用。"""
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"检测到新的摘要文件被创建: {event.src_path}. 准备刷新缓存...")
            self.callback()

    def on_modified(self, event):
        """当文件或目录被修改时调用。"""
        # 注意：简单地保存文件就会触发此事件。
        # 如果修改元数据（如版本号）后需要立即更新，可以启用此功能。
        # 目前，为避免过于频繁的刷新，我们主要关注创建和删除。
        # 如果需要，可以取消下面的注释。
        # if not event.is_directory and event.src_path.endswith('.md'):
        #     logger.info(f"摘要文件被修改: {event.src_path}. 准备刷新缓存...")
        #     self.callback()
        pass

def start_watching(path: Path, callback):
    """
    在一个独立的线程中启动文件系统监控。

    Args:
        path (Path): 需要监控的目录路径。
        callback (function): 当检测到变化时需要调用的回调函数。
    """
    if not path.is_dir():
        logger.warning(f"无法启动文件监控，因为目录不存在: {path}")
        return

    logger.info(f"启动文件系统监控，目标目录: {path}")
    event_handler = SummaryDirectoryEventHandler(callback)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=False) # 不监控子目录
    observer.daemon = True # 设置为守护线程，这样主程序退出时它也会退出
    observer.start()
    logger.info("文件系统监控器已在后台运行。")
    return observer 