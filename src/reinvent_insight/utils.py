"""
工具函数模块
包含项目中通用的辅助函数
"""
import hashlib
import uuid
from typing import Optional
from datetime import datetime


def generate_doc_hash(video_url: str) -> Optional[str]:
    """
    为文档生成一个短的、基于视频URL的唯一hash。
    如果 video_url 不存在，则返回 None。
    """
    if not video_url:
        return None
    return hashlib.md5(video_url.encode()).hexdigest()[:8] 


def generate_pdf_identifier(title: str, content_preview: str = "") -> str:
    """
    为PDF文档生成唯一标识符，用作pseudo video_url
    
    Args:
        title: PDF文档标题
        content_preview: 内容预览（可选，用于增强唯一性）
    
    Returns:
        形如 "pdf://uuid-hash" 的唯一标识符
    """
    # 使用标题+时间戳+随机数生成唯一标识
    timestamp = datetime.now().isoformat()
    unique_data = f"{title}_{timestamp}_{content_preview[:100]}"
    
    # 生成SHA-256哈希的前16位作为唯一标识
    unique_hash = hashlib.sha256(unique_data.encode()).hexdigest()[:16]
    
    return f"pdf://{unique_hash}"


def is_pdf_document(video_url: str) -> bool:
    """
    判断是否为PDF文档
    
    Args:
        video_url: 视频URL或PDF标识符
    
    Returns:
        如果是PDF文档则返回True
    """
    return video_url.startswith("pdf://")


def extract_pdf_hash(video_url: str) -> Optional[str]:
    """
    从PDF标识符中提取hash部分
    
    Args:
        video_url: PDF标识符，如 "pdf://abc123def456"
    
    Returns:
        hash部分，如 "abc123def456"，如果不是PDF标识符则返回None
    """
    if is_pdf_document(video_url):
        return video_url[6:]  # 移除 "pdf://" 前缀
    return None 