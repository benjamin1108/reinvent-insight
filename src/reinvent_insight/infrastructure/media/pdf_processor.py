"""PDF文件上传处理器"""
import logging
from typing import Dict, Any
from reinvent_insight.infrastructure.ai.model_config import get_model_client

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF处理器，负责文件上传和删除"""
    
    def __init__(self):
        """初始化模型客户端"""
        self.client = get_model_client("pdf_processing")
    
    async def upload_pdf(self, pdf_file_path: str) -> Dict[str, Any]:
        """
        将PDF文件上传到API
        
        Args:
            pdf_file_path: PDF文件路径
            
        Returns:
            包含文件信息的字典
        """
        return await self.client.upload_file(pdf_file_path)
    
    async def delete_file(self, file_id: str) -> bool:
        """
        删除上传的文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            删除是否成功
        """
        return await self.client.delete_file(file_id)