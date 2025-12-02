from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import asyncio
import re
from pathlib import Path
import logging
import threading

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
        self._pending_files = {}  # 存储待处理的文件及其定时器
        self._lock = threading.Lock()

    def on_deleted(self, event):
        """当文件或目录被删除时调用。"""
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"检测到摘要文件被删除: {event.src_path}. 准备刷新缓存...")
            # 删除事件立即触发，无需等待
            self.callback()

    def on_created(self, event):
        """当文件或目录被创建时调用。"""
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"检测到新的摘要文件被创建: {event.src_path}. 等待文件完全写入...")
            # 延迟触发，确保文件完全写入
            self._schedule_refresh(event.src_path)

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
    
    def _schedule_refresh(self, file_path):
        """延迟调度缓存刷新，避免文件未完全写入"""
        with self._lock:
            # 取消之前的定时器（如果存在）
            if file_path in self._pending_files:
                self._pending_files[file_path].cancel()
            
            # 创建新的定时器，延迟1秒后执行
            timer = threading.Timer(1.0, self._execute_refresh, args=[file_path])
            self._pending_files[file_path] = timer
            timer.start()
    
    def _execute_refresh(self, file_path):
        """执行实际的缓存刷新"""
        with self._lock:
            # 移除已完成的定时器
            if file_path in self._pending_files:
                del self._pending_files[file_path]
        
        # 验证文件是否存在且可读
        try:
            path = Path(file_path)
            if path.exists() and path.stat().st_size > 0:
                logger.info(f"文件 {file_path} 已完全写入，开始刷新缓存...")
                self.callback()
            else:
                logger.warning(f"文件 {file_path} 不存在或为空，跳过缓存刷新")
        except Exception as e:
            logger.error(f"检查文件 {file_path} 时出错: {e}")

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


class TTSPregenerationEventHandler(FileSystemEventHandler):
    """处理 TTS 预生成目录中的文件系统事件。"""
    
    def __init__(self, tts_callback):
        """
        初始化事件处理器
        
        Args:
            tts_callback: TTS 预生成回调函数，接收 (file_path: Path, article_hash: str, source_file: str)
        """
        self.tts_callback = tts_callback
        self._pending_files = {}  # 存储待处理的文件及其定时器
        self._lock = threading.Lock()
    
    def on_created(self, event):
        """当文件被创建时调用。"""
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"检测到新的文章文件被创建: {event.src_path}. 等待文件完全写入...")
            # 延迟触发，确保文件完全写入
            self._schedule_tts_generation(event.src_path)
    
    def _schedule_tts_generation(self, file_path):
        """延迟调度 TTS 预生成，避免文件未完全写入"""
        with self._lock:
            # 取消之前的定时器（如果存在）
            if file_path in self._pending_files:
                self._pending_files[file_path].cancel()
            
            # 创建新的定时器，延迟 2 秒后执行
            timer = threading.Timer(2.0, self._execute_tts_generation, args=[file_path])
            self._pending_files[file_path] = timer
            timer.start()
    
    def _execute_tts_generation(self, file_path):
        """执行实际的 TTS 预生成"""
        with self._lock:
            # 移除已完成的定时器
            if file_path in self._pending_files:
                del self._pending_files[file_path]
        
        # 验证文件是否存在且可读
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return
            
            file_size = path.stat().st_size
            if file_size < 1024:  # 小于 1KB
                logger.warning(f"文件过小，跳过 TTS 预生成: {file_path}")
                return
            
            # 读取文件内容并提取元数据
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否有 YAML front matter
            if not content.startswith('---'):
                logger.warning(f"文件缺少 YAML 元数据，跳过 TTS 预生成: {file_path}")
                return
            
            # 提取元数据
            yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if not yaml_match:
                logger.warning(f"无法解析 YAML 元数据: {file_path}")
                return
            
            # 简单解析 YAML
            metadata = {}
            yaml_content = yaml_match.group(1)
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"\'')
            
            # 计算 article_hash
            video_url = metadata.get('video_url', '')
            title = metadata.get('title', '')
            upload_date = metadata.get('upload_date', '')
            
            if not any([video_url, title]):
                logger.warning(f"文件缺少必要的元数据，跳过 TTS 预生成: {file_path}")
                return
            
            # 计算哈希
            import hashlib
            hash_content = f"{video_url}|{title}|{upload_date}"
            article_hash = hashlib.sha256(hash_content.encode('utf-8')).hexdigest()[:16]
            
            source_file = path.name
            
            logger.info(
                f"文件 {file_path} 已完全写入，开始 TTS 预生成..."
                f"article_hash={article_hash}, source_file={source_file}"
            )
            
            # 调用预生成回调
            self.tts_callback(path, article_hash, source_file)
            
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {e}", exc_info=True)


def start_tts_watching(path: Path, tts_callback):
    """
    启动 TTS 预生成文件监控
    
    Args:
        path: 监控目录路径
        tts_callback: TTS 预生成回调函数
        
    Returns:
        Observer 对象
    """
    if not path.is_dir():
        logger.warning(f"无法启动 TTS 监控，目录不存在: {path}")
        return None
    
    logger.info(f"启动 TTS 预生成监控，目标目录: {path}")
    event_handler = TTSPregenerationEventHandler(tts_callback)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=False)
    observer.daemon = True
    observer.start()
    logger.info("TTS 预生成监控器已在后台运行。")
    return observer 