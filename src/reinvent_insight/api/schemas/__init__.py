"""API Schemas - Pydantic models for request/response validation"""

from .auth import LoginRequest, LoginResponse
from .analysis import (
    SummarizeRequest,
    SummarizeResponse,
    PDFAnalysisRequest,
    DocumentAnalysisRequest,
)
from .tts import (
    TTSRequest,
    TTSResponse,
    TTSStreamRequest,
    TTSStatusResponse,
    TTSPregenerateRequest,
    TTSPregenerateResponse,
    TTSQueueStatsResponse,
    TTSTaskInfo,
    TTSTaskListResponse,
)
from .document import DeleteSummaryRequest

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    # Analysis
    "SummarizeRequest",
    "SummarizeResponse",
    "PDFAnalysisRequest",
    "DocumentAnalysisRequest",
    # TTS
    "TTSRequest",
    "TTSResponse",
    "TTSStreamRequest",
    "TTSStatusResponse",
    "TTSPregenerateRequest",
    "TTSPregenerateResponse",
    "TTSQueueStatsResponse",
    "TTSTaskInfo",
    "TTSTaskListResponse",
    # Document
    "DeleteSummaryRequest",
]
