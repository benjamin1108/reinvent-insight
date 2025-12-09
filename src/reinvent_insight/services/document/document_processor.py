"""
文档处理器模块
提供统一的文档处理接口，支持多种文档格式（TXT、MD、PDF、DOCX）
"""
import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from loguru import logger

from reinvent_insight.core import config
from reinvent_insight.domain.models import DocumentContent
from reinvent_insight.core.utils.file_utils import generate_pdf_identifier

logger = logger.bind(name=__name__)


class DocumentProcessor:
    """统一文档处理器，负责格式识别和策略选择"""
    
    # 支持的文档格式映射
    SUPPORTED_FORMATS = {
        'text': ['.txt', '.md'],
        'multimodal': ['.pdf', '.docx']
    }
    
    # 文档类型映射
    DOCUMENT_TYPE_MAP = {
        '.txt': {
            'type': 'text',
            'mime_type': 'text/plain',
            'strategy': 'text_injection'
        },
        '.md': {
            'type': 'text',
            'mime_type': 'text/markdown',
            'strategy': 'text_injection'
        },
        '.pdf': {
            'type': 'multimodal',
            'mime_type': 'application/pdf',
            'strategy': 'multimodal_analysis'
        },
        '.docx': {
            'type': 'multimodal',
            'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'strategy': 'multimodal_analysis'
        }
    }
    
    def __init__(self):
        """初始化文档处理器"""
        self.pdf_processor = None  # 延迟加载
    
    async def process_document(
        self, 
        file_path: str, 
        title: Optional[str] = None
    ) -> DocumentContent:
        """
        处理文档并返回统一的内容对象
        
        Args:
            file_path: 文档文件路径
            title: 可选的文档标题
            
        Returns:
            DocumentContent对象
            
        Raises:
            ValueError: 不支持的文件格式
            FileNotFoundError: 文件不存在
            IOError: 文件读取失败
        """
        # 验证文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 获取文档类型
        doc_type = self._get_document_type(file_path)
        
        logger.info(f"处理文档: {file_path}, 类型: {doc_type}")
        
        # 根据文档类型选择处理策略
        if doc_type == 'text':
            return await self._process_text_document(file_path, title)
        elif doc_type == 'multimodal':
            return await self._process_multimodal_document(file_path, title)
        else:
            raise ValueError(f"不支持的文档类型: {doc_type}")
    
    def _get_document_type(self, file_path: str) -> str:
        """
        根据文件扩展名判断文档类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            文档类型: 'text' 或 'multimodal'
            
        Raises:
            ValueError: 不支持的文件格式
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.DOCUMENT_TYPE_MAP:
            supported_formats = list(self.DOCUMENT_TYPE_MAP.keys())
            raise ValueError(
                f"不支持的文件格式: {file_ext}. "
                f"支持的格式: {', '.join(supported_formats)}"
            )
        
        return self.DOCUMENT_TYPE_MAP[file_ext]['type']
    
    async def _process_text_document(
        self, 
        file_path: str, 
        title: Optional[str]
    ) -> DocumentContent:
        """
        处理文本类文档（TXT/MD）
        
        Args:
            file_path: 文件路径
            title: 可选的文档标题
            
        Returns:
            DocumentContent对象
            
        Raises:
            IOError: 文件读取失败
        """
        try:
            # 读取文件内容，尝试多种编码
            text_content = None
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text_content = f.read()
                    logger.info(f"成功使用 {encoding} 编码读取文件")
                    break
                except UnicodeDecodeError:
                    continue
            
            if text_content is None:
                raise IOError(f"无法读取文件，尝试了以下编码: {', '.join(encodings)}")
            
            # 获取文件信息
            file_ext = Path(file_path).suffix.lower()
            file_size = os.path.getsize(file_path)
            file_name = Path(file_path).name
            
            # 生成文档标识符
            doc_title = title or file_name
            doc_identifier = self._generate_document_identifier(doc_title, text_content[:200])
            
            # 构建文件信息
            file_info = {
                "name": doc_identifier,
                "path": file_path,
                "mime_type": self.DOCUMENT_TYPE_MAP[file_ext]['mime_type'],
                "size_bytes": file_size,
                "local_file": True
            }
            
            # 创建 DocumentContent 对象
            content = DocumentContent(
                file_info=file_info,
                title=doc_title,
                content_type="text",
                text_content=text_content
            )
            
            logger.info(f"文本文档处理完成: {doc_identifier}, 大小: {file_size} bytes")
            return content
            
        except Exception as e:
            logger.error(f"处理文本文档失败: {e}", exc_info=True)
            raise IOError(f"文件读取失败: {str(e)}")
    
    async def _process_multimodal_document(
        self, 
        file_path: str, 
        title: Optional[str]
    ) -> DocumentContent:
        """
        处理多模态文档（PDF/DOCX）
        
        Args:
            file_path: 文件路径
            title: 可选的文档标题
            
        Returns:
            DocumentContent对象
            
        Raises:
            IOError: 文件处理失败
        """
        try:
            # 延迟导入 PDFProcessor
            if self.pdf_processor is None:
                from reinvent_insight.infrastructure.media.pdf_processor import PDFProcessor
                self.pdf_processor = PDFProcessor()
            
            # 上传文件到 Gemini API
            file_info = await self.pdf_processor.upload_pdf(file_path)
            
            # 获取文件名作为默认标题
            file_name = Path(file_path).name
            doc_title = title or file_name
            
            # 创建 DocumentContent 对象
            content = DocumentContent(
                file_info=file_info,
                title=doc_title,
                content_type="multimodal",
                text_content=None
            )
            
            logger.info(f"多模态文档处理完成: {file_info['name']}")
            return content
            
        except Exception as e:
            logger.error(f"处理多模态文档失败: {e}", exc_info=True)
            raise IOError(f"文件处理失败: {str(e)}")
    
    def _generate_document_identifier(self, title: str, content_preview: str = "") -> str:
        """
        为文档生成唯一标识符
        
        Args:
            title: 文档标题
            content_preview: 内容预览（用于增强唯一性）
            
        Returns:
            唯一标识符
        """
        # 清理标题，移除特殊字符
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        clean_title = clean_title.strip().replace(' ', '_')[:50]
        
        # 生成内容哈希
        content_hash = hashlib.md5(
            (title + content_preview).encode('utf-8')
        ).hexdigest()[:8]
        
        return f"doc_{clean_title}_{content_hash}"


class UnsupportedFormatError(ValueError):
    """不支持的文件格式错误"""
    pass


class FileReadError(IOError):
    """文件读取错误"""
    pass
