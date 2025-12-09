"""Reinvent Insight - AI驱动的深度内容分析平台

从新模块重新导出核心功能,保持向后兼容性
"""

__version__ = "2.0.0"

# 导出核心配置
from reinvent_insight.core import config

# 导出文档服务
from reinvent_insight.services.document.hash_registry import (
    hash_to_filename,
    hash_to_versions,
    filename_to_hash,
    init_hash_mappings,
    refresh_doc_hash_mapping,
)

from reinvent_insight.services.document.metadata_service import (
    parse_metadata_from_md,
    extract_text_from_markdown,
    count_chinese_words,
    clean_content_metadata,
    discover_versions,
)

# 导出启动服务
from reinvent_insight.services.startup_service import start_visual_watcher

# 导出AI基础设施
from reinvent_insight.domain import prompts

__all__ = [
    # 版本
    '__version__',
    
    # 配置
    'config',
    
    # 哈希注册表
    'hash_to_filename',
    'hash_to_versions',
    'filename_to_hash',
    'init_hash_mappings',
    'refresh_doc_hash_mapping',
    
    # 元数据服务
    'parse_metadata_from_md',
    'extract_text_from_markdown',
    'count_chinese_words',
    'clean_content_metadata',
    'discover_versions',
    
    # 启动服务
    'start_visual_watcher',
    
    # AI提示词
    'prompts',
]
