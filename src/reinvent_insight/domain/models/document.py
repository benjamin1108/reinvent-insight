"""文档内容模型"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class DocumentContent:
    """文档内容封装类（支持多种格式）"""
    file_info: Dict[str, Any]  # 文件信息（包含file_id或本地路径）
    title: str  # 文档标题
    content_type: str = "pdf"  # 内容类型: 'txt', 'md', 'pdf', 'docx'
    text_content: Optional[str] = None  # 文本内容（仅txt/md类型使用）
    
    @property
    def file_id(self) -> str:
        """获取文件ID"""
        return self.file_info.get("name", "")
    
    @property
    def is_local(self) -> bool:
        """是否为本地文件"""
        return self.file_info.get("local_file", False)
    
    @property
    def is_text(self) -> bool:
        """是否为文本类型（TXT/MD）"""
        return self.content_type in ("txt", "md", "text")  # 兼容旧值
    
    @property
    def is_multimodal(self) -> bool:
        """是否为多模态类型（PDF/DOCX）"""
        return self.content_type in ("pdf", "docx", "multimodal")  # 兼容旧值


# 保持向后兼容
PDFContent = DocumentContent
