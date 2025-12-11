"""Analysis task schemas"""

from typing import Optional
from pydantic import BaseModel, HttpUrl


class SummarizeRequest(BaseModel):
    """YouTube video analysis request"""
    url: HttpUrl
    task_id: Optional[str] = None


class SummarizeResponse(BaseModel):
    """Analysis task response"""
    task_id: Optional[str] = None
    message: str
    status: str  # "created", "reconnected", "exists", "in_progress"
    # 重复检测相关字段
    exists: Optional[bool] = None
    doc_hash: Optional[str] = None
    title: Optional[str] = None
    redirect_url: Optional[str] = None
    in_progress: Optional[bool] = None
    in_queue: Optional[bool] = None


class PDFAnalysisRequest(BaseModel):
    """PDF document analysis request"""
    title: Optional[str] = None  # 可选的标题，如果为None则由AI生成


class DocumentAnalysisRequest(BaseModel):
    """Generic document analysis request"""
    title: Optional[str] = None  # 可选的标题
