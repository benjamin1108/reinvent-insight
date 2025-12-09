"""文档哈希注册表 - 管理文档hash到文件名的映射关系"""

import logging
from typing import Dict, List
from pathlib import Path

from reinvent_insight.core import config
from reinvent_insight.core.utils.file_utils import generate_doc_hash

logger = logging.getLogger(__name__)


class HashRegistry:
    """文档哈希注册表（单例）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 存储 hash -> 默认文件名 的映射（通常是最新版本）
        self.hash_to_filename: Dict[str, str] = {}
        # 存储 hash -> 所有版本文件列表 的映射
        self.hash_to_versions: Dict[str, List[str]] = {}
        # 存储 filename -> hash 的反向映射
        self.filename_to_hash: Dict[str, str] = {}
        
        self._initialized = True
    
    def get_filename(self, doc_hash: str) -> str:
        """根据hash获取默认文件名"""
        return self.hash_to_filename.get(doc_hash, "")
    
    def get_versions(self, doc_hash: str) -> List[str]:
        """根据hash获取所有版本文件列表"""
        return self.hash_to_versions.get(doc_hash, [])
    
    def get_hash(self, filename: str) -> str:
        """根据文件名获取hash"""
        return self.filename_to_hash.get(filename, "")
    
    def init_mappings(self, metadata_parser=None):
        """初始化所有文档的基于 video_url 的统一hash映射
        
        Args:
            metadata_parser: 元数据解析函数，如果不提供则使用默认
        """
        self.hash_to_filename.clear()
        self.hash_to_versions.clear()
        self.filename_to_hash.clear()

        if not config.OUTPUT_DIR.exists():
            return

        # 使用默认解析器如果未提供
        if metadata_parser is None:
            from reinvent_insight.services.document.metadata_service import parse_metadata_from_md
            metadata_parser = parse_metadata_from_md

        video_url_to_files = {}
        skipped_count = 0
        error_count = 0
        
        # 第一遍：基于video_url对所有文件进行分组
        for md_file in config.OUTPUT_DIR.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                metadata = metadata_parser(content)
                video_url = metadata.get("video_url")
                
                if video_url:
                    if video_url not in video_url_to_files:
                        video_url_to_files[video_url] = []
                    video_url_to_files[video_url].append({
                        'filename': md_file.name,
                        'version': metadata.get('version', 0)
                    })
                else:
                    skipped_count += 1
                    logger.debug(f"跳过文件 {md_file.name}（无 video_url）")
            except Exception as e:
                error_count += 1
                logger.error(f"解析文件 {md_file.name} 时出错，已跳过: {e}")
        
        # 第二遍：为每个分组生成和注册唯一的统一hash
        for video_url, files in video_url_to_files.items():
            doc_hash = generate_doc_hash(video_url)
            if not doc_hash:
                continue

            files.sort(key=lambda x: x['version'], reverse=True)
            latest_file = files[0]['filename']
            
            # 注册核心映射
            self.hash_to_filename[doc_hash] = latest_file
            self.hash_to_versions[doc_hash] = [f['filename'] for f in files]
            for file_info in files:
                self.filename_to_hash[file_info['filename']] = doc_hash

        log_msg = f"Hash映射初始化完成，共处理 {len(self.hash_to_filename)} 个独立文档"
        if skipped_count > 0:
            log_msg += f"，跳过 {skipped_count} 个文件（无video_url）"
        if error_count > 0:
            log_msg += f"，{error_count} 个文件解析失败"
        logger.info(log_msg)
    
    def refresh_mapping(self, video_url: str, metadata_parser=None):
        """刷新指定文档的hash映射（Ultra完成后调用）
        
        Args:
            video_url: 视频URL
            metadata_parser: 元数据解析函数，如果不提供则使用默认
        """
        if not video_url or not config.OUTPUT_DIR.exists():
            return
        
        # 使用默认解析器如果未提供
        if metadata_parser is None:
            from reinvent_insight.services.document.metadata_service import parse_metadata_from_md
            metadata_parser = parse_metadata_from_md
        
        doc_hash = generate_doc_hash(video_url)
        if not doc_hash:
            return
        
        # 重新扫描该video_url对应的所有版本
        files = []
        for md_file in config.OUTPUT_DIR.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                metadata = metadata_parser(content)
                if metadata.get("video_url") == video_url:
                    files.append({
                        'filename': md_file.name,
                        'version': metadata.get('version', 0)
                    })
            except Exception as e:
                logger.warning(f"刷新映射时解析文件 {md_file.name} 失败: {e}")
        
        if not files:
            return
        
        # 按版本号排序，最新版本在前
        files.sort(key=lambda x: x['version'], reverse=True)
        latest_file = files[0]['filename']
        
        # 更新映射
        self.hash_to_filename[doc_hash] = latest_file
        self.hash_to_versions[doc_hash] = [f['filename'] for f in files]
        for file_info in files:
            self.filename_to_hash[file_info['filename']] = doc_hash
        
        logger.info(f"已刷新文档映射: {doc_hash} -> {latest_file} (共 {len(files)} 个版本)")


# 全局单例实例
_registry = HashRegistry()


# 向后兼容的全局变量（将在后续版本移除）
hash_to_filename = _registry.hash_to_filename
hash_to_versions = _registry.hash_to_versions
filename_to_hash = _registry.filename_to_hash


# 便捷函数
def get_registry() -> HashRegistry:
    """获取哈希注册表单例"""
    return _registry


def init_hash_mappings():
    """初始化哈希映射（向后兼容函数）"""
    _registry.init_mappings()


def refresh_doc_hash_mapping(video_url: str):
    """刷新文档哈希映射（向后兼容函数）"""
    _registry.refresh_mapping(video_url)
