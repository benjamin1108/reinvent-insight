"""Document management schemas"""

from pydantic import BaseModel


class DeleteSummaryRequest(BaseModel):
    """Delete summary request"""
    filename: str
