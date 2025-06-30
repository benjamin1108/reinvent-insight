"""
工具函数模块
包含项目中通用的辅助函数
"""
import hashlib
from typing import Optional


def generate_doc_hash(video_url: str) -> Optional[str]:
    """
    为文档生成一个短的、基于视频URL的唯一hash。
    如果 video_url 不存在，则返回 None。
    """
    if not video_url:
        return None
    return hashlib.md5(video_url.encode()).hexdigest()[:8] 