"""
工具函数模块
包含项目中通用的辅助函数
"""
import hashlib
import uuid
from typing import Optional
from datetime import datetime


def generate_doc_hash(source_identifier: str) -> Optional[str]:
    """
    为文档生成一个短的、基于内容来源标识符的唯一hash。
    
    Args:
        source_identifier: 内容来源标识符
            - 视频: YouTube URL (https://www.youtube.com/watch?v=xxx)
            - 文档: 文档标识符 (pdf://xxx, txt://xxx, md://xxx, docx://xxx)
    
    Returns:
        8位MD5哈希，如果source_identifier不存在则返回None
    """
    if not source_identifier:
        return None
    return hashlib.md5(source_identifier.encode()).hexdigest()[:8]


def get_source_identifier(metadata: dict) -> Optional[str]:
    """
    从元数据中获取内容来源标识符（兼容视频和文档）
    
    Args:
        metadata: 文档元数据字典
    
    Returns:
        内容来源标识符（优先返回 content_identifier，否则返回 video_url）
    """
    return metadata.get('content_identifier') or metadata.get('video_url') 


def generate_content_identifier(content_bytes: bytes, doc_type: str = "doc") -> str:
    """
    基于文件内容生成唯一标识符（用于去重）
    
    Args:
        content_bytes: 文件的原始字节内容
        doc_type: 文档类型前缀（如 'txt', 'md', 'pdf', 'docx'）
    
    Returns:
        形如 "doc_type://md5hash" 的唯一标识符
    """
    content_hash = hashlib.md5(content_bytes).hexdigest()[:16]
    return f"{doc_type}://{content_hash}"


def generate_pdf_identifier(title: str, content_preview: str = "") -> str:
    """
    [已废弃] 请使用 generate_content_identifier
    保留此函数仅为兼容性，新代码应使用 generate_content_identifier
    """
    # 如果 content_preview 看起来像是 MD5 hash，直接使用
    if len(content_preview) == 32 and all(c in '0123456789abcdef' for c in content_preview.lower()):
        return f"pdf://{content_preview[:16]}"
    
    # 否则基于内容计算 hash
    unique_data = f"{title}_{content_preview[:100]}"
    unique_hash = hashlib.sha256(unique_data.encode()).hexdigest()[:16]
    return f"pdf://{unique_hash}"


def generate_document_identifier(title: str, content_preview: str = "", doc_type: str = "doc") -> str:
    """
    [已废弃] 请使用 generate_content_identifier
    保留此函数仅为兼容性，新代码应使用 generate_content_identifier
    """
    # 如果 content_preview 看起来像是 MD5 hash，直接使用
    if len(content_preview) == 32 and all(c in '0123456789abcdef' for c in content_preview.lower()):
        return f"{doc_type}://{content_preview[:16]}"
    
    # 否则基于内容计算 hash
    unique_data = f"{title}_{content_preview[:100]}"
    unique_hash = hashlib.sha256(unique_data.encode()).hexdigest()[:16]
    return f"{doc_type}://{unique_hash}"


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


def is_text_document(identifier: str) -> bool:
    """
    判断是否为文本文档（TXT或MD）
    
    Args:
        identifier: 文档标识符
    
    Returns:
        如果是文本文档则返回True
    """
    return identifier.startswith("txt://") or identifier.startswith("md://")


def is_multimodal_document(identifier: str) -> bool:
    """
    判断是否为多模态文档（PDF或DOCX）
    
    Args:
        identifier: 文档标识符
    
    Returns:
        如果是多模态文档则返回True
    """
    return identifier.startswith("pdf://") or identifier.startswith("docx://")


def get_document_type_from_identifier(identifier: str) -> Optional[str]:
    """
    从文档标识符中提取文档类型
    
    Args:
        identifier: 文档标识符，如 "txt://abc123"
    
    Returns:
        文档类型，如 "txt"，如果无法识别则返回None
    """
    if "://" in identifier:
        return identifier.split("://")[0]
    return None
