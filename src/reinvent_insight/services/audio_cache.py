"""
音频缓存系统

提供 LRU 缓存管理功能，用于存储和检索 TTS 生成的音频文件
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """音频缓存元数据"""
    hash: str                    # 音频哈希值
    text_hash: str              # 文本哈希值（用于失效检查）
    voice: str                  # 音色名称
    language: str               # 语言类型
    duration: float             # 音频时长（秒）
    file_size: int              # 文件大小（字节）
    file_path: str              # 文件路径
    created_at: str             # 创建时间（ISO 8601）
    last_accessed: str          # 最后访问时间（ISO 8601）
    access_count: int           # 访问次数
    # 预生成相关字段
    article_hash: str = ""      # 关联的文章标识
    source_file: str = ""       # 原始文章文件名
    preprocessing_version: str = ""  # 预处理规则版本号
    is_pregenerated: bool = False   # 是否为预生成（true）


class AudioCache:
    """LRU 音频缓存管理器"""
    
    def __init__(
        self,
        cache_dir: Path,
        max_size_mb: int = 500
    ):
        """
        初始化音频缓存
        
        Args:
            cache_dir: 缓存目录路径
            max_size_mb: 最大缓存大小（MB）
        """
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.metadata: Dict[str, AudioMetadata] = {}
        self.metadata_file = self.cache_dir / "metadata.json"
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载元数据
        self._load_metadata()
        
        logger.info(
            f"AudioCache 初始化成功: {cache_dir}, "
            f"最大大小: {max_size_mb}MB, "
            f"当前缓存: {len(self.metadata)} 个文件"
        )
    
    def _load_metadata(self) -> None:
        """从文件加载元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.metadata = {
                        k: AudioMetadata(**v) for k, v in data.items()
                    }
                logger.info(f"加载了 {len(self.metadata)} 个缓存元数据")
            except Exception as e:
                logger.error(f"加载元数据失败: {e}")
                self.metadata = {}
        else:
            self.metadata = {}
    
    def _save_metadata(self) -> None:
        """保存元数据到文件"""
        try:
            data = {k: asdict(v) for k, v in self.metadata.items()}
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")
    
    def get(self, audio_hash: str) -> Optional[Path]:
        """
        获取缓存的音频文件
        
        Args:
            audio_hash: 音频哈希值
            
        Returns:
            音频文件路径，如果不存在则返回 None
        """
        if audio_hash not in self.metadata:
            return None
        
        metadata = self.metadata[audio_hash]
        file_path = Path(metadata.file_path)
        
        # 检查文件是否存在
        if not file_path.exists():
            logger.warning(f"缓存文件不存在: {file_path}")
            del self.metadata[audio_hash]
            self._save_metadata()
            return None
        
        # 更新访问信息
        metadata.last_accessed = datetime.now().isoformat()
        metadata.access_count += 1
        self._save_metadata()
        
        logger.info(f"缓存命中: {audio_hash}, 访问次数: {metadata.access_count}")
        return file_path
    
    def get_metadata(self, audio_hash: str) -> Optional[AudioMetadata]:
        """
        获取缓存元数据（不更新访问计数）
        
        Args:
            audio_hash: 音频哈希值
            
        Returns:
            元数据对象，如果不存在则返回 None
        """
        return self.metadata.get(audio_hash)

    def put(
        self,
        audio_hash: str,
        audio_data: bytes,
        text_hash: str,
        voice: str,
        language: str,
        duration: float = 0.0,
        article_hash: str = "",
        source_file: str = "",
        preprocessing_version: str = "",
        is_pregenerated: bool = False
    ) -> Path:
        """
        存储音频到缓存
        
        Args:
            audio_hash: 音频哈希值
            audio_data: 音频数据
            text_hash: 文本哈希值
            voice: 音色名称
            language: 语言类型
            duration: 音频时长（秒）
            
        Returns:
            存储的文件路径
        """
        # 检查是否需要淘汰
        file_size = len(audio_data)
        if self.get_cache_size() + file_size > self.max_size_bytes:
            logger.info("缓存空间不足，开始 LRU 淘汰")
            self.evict_lru()
        
        # 生成文件路径
        file_path = self.cache_dir / f"{audio_hash}.wav"
        
        # 写入文件
        try:
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            # 创建元数据
            now = datetime.now().isoformat()
            metadata = AudioMetadata(
                hash=audio_hash,
                text_hash=text_hash,
                voice=voice,
                language=language,
                duration=duration,
                file_size=file_size,
                file_path=str(file_path),
                created_at=now,
                last_accessed=now,
                access_count=0,
                article_hash=article_hash,
                source_file=source_file,
                preprocessing_version=preprocessing_version,
                is_pregenerated=is_pregenerated
            )
            
            self.metadata[audio_hash] = metadata
            self._save_metadata()
            
            logger.info(
                f"音频已缓存: {audio_hash}, "
                f"大小: {file_size / 1024:.2f}KB, "
                f"时长: {duration:.2f}s"
            )
            
            return file_path
            
        except Exception as e:
            logger.error(f"缓存音频失败: {e}")
            raise
    
    def invalidate(self, audio_hash: str) -> bool:
        """
        使缓存失效（删除）
        
        Args:
            audio_hash: 音频哈希值
            
        Returns:
            是否成功删除
        """
        if audio_hash not in self.metadata:
            return False
        
        metadata = self.metadata[audio_hash]
        file_path = Path(metadata.file_path)
        
        try:
            # 删除文件
            if file_path.exists():
                file_path.unlink()
            
            # 删除元数据
            del self.metadata[audio_hash]
            self._save_metadata()
            
            logger.info(f"缓存已失效: {audio_hash}")
            return True
            
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    def evict_lru(self) -> None:
        """
        LRU 淘汰：删除最少使用的文件直到空间足够
        """
        if not self.metadata:
            return
        
        # 按最后访问时间排序
        sorted_items = sorted(
            self.metadata.items(),
            key=lambda x: x[1].last_accessed
        )
        
        evicted_count = 0
        target_size = self.max_size_bytes * 0.8  # 淘汰到 80% 容量
        
        for audio_hash, metadata in sorted_items:
            if self.get_cache_size() <= target_size:
                break
            
            if self.invalidate(audio_hash):
                evicted_count += 1
        
        logger.info(
            f"LRU 淘汰完成: 删除了 {evicted_count} 个文件, "
            f"当前大小: {self.get_cache_size() / 1024 / 1024:.2f}MB"
        )
    
    def get_cache_size(self) -> int:
        """
        获取当前缓存总大小
        
        Returns:
            缓存大小（字节）
        """
        total_size = 0
        for metadata in self.metadata.values():
            total_size += metadata.file_size
        return total_size
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_size = self.get_cache_size()
        total_count = len(self.metadata)
        
        return {
            "total_files": total_count,
            "total_size_mb": total_size / 1024 / 1024,
            "max_size_mb": self.max_size_bytes / 1024 / 1024,
            "usage_percent": (total_size / self.max_size_bytes * 100) if self.max_size_bytes > 0 else 0,
            "cache_dir": str(self.cache_dir)
        }
    
    def find_by_article_hash(self, article_hash: str) -> Optional[AudioMetadata]:
        """
        根据文章哈希查找音频元数据
        
        Args:
            article_hash: 文章哈希值
            
        Returns:
            音频元数据，如果不存在则返回 None
        """
        for metadata in self.metadata.values():
            if metadata.article_hash == article_hash:
                # 验证文件是否存在
                file_path = Path(metadata.file_path)
                if file_path.exists():
                    return metadata
        
        return None
