"""Analysis task schemas"""

from typing import Optional
from pydantic import BaseModel, HttpUrl


class SummarizeRequest(BaseModel):
    """YouTube video analysis request"""
    url: HttpUrl
    task_id: Optional[str] = None


class SummarizeResponse(BaseModel):
    """Analysis task response"""
    task_id: str
    message: str
    status: str  # "created", "reconnected"


class PDFAnalysisRequest(BaseModel):
    """PDF document analysis request"""
    title: Optional[str] = None  # 可选的标题，如果为None则由AI生成


class DocumentAnalysisRequest(BaseModel):
    """Generic document analysis request"""
    title: Optional[str] = None  # 可选的标题
