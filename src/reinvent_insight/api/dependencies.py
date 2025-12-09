"""API dependencies - dependency injection for FastAPI routes"""

from reinvent_insight.services.document import document_service
from reinvent_insight.services.analysis import get_analysis_service


def get_document_service():
    """获取文档服务依赖"""
    return document_service


def get_analysis_service_dep():
    """获取分析服务依赖"""
    return get_analysis_service()
