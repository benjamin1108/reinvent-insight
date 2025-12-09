"""TTS (Text-to-Speech) schemas"""

from typing import Optional, List
from pydantic import BaseModel


class TTSRequest(BaseModel):
    """TTS generation request"""
    article_hash: str
    text: str
    voice: Optional[str] = None
    language: Optional[str] = None
    use_cache: bool = True
    skip_code_blocks: bool = True


class TTSResponse(BaseModel):
    """TTS generation response"""
    audio_url: str
    duration: float
    cached: bool
    voice: str
    language: str


class TTSStreamRequest(BaseModel):
    """TTS streaming request"""
    article_hash: str
    text: str
    voice: Optional[str] = None
    language: Optional[str] = None
    use_cache: bool = True
    skip_code_blocks: bool = True


class TTSStatusResponse(BaseModel):
    """Audio status query response"""
    has_audio: bool
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    status: str  # "ready", "processing", "none"
    voice: Optional[str] = None
    generated_at: Optional[str] = None
    # Progressive playback related
    has_partial: bool = False
    partial_url: Optional[str] = None
    partial_duration: Optional[float] = None
    chunks_generated: int = 0
    total_chunks: int = 0
    progress_percent: int = 0


class TTSQueueStatsResponse(BaseModel):
    """TTS queue statistics response"""
    queue_size: int
    total_tasks: int
    pending: int
    processing: int
    completed: int
    failed: int
    skipped: int
    is_running: bool


class TTSTaskInfo(BaseModel):
    """TTS task information"""
    task_id: str
    article_hash: str
    source_file: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    audio_hash: Optional[str] = None


class TTSTaskListResponse(BaseModel):
    """TTS task list response"""
    tasks: List[TTSTaskInfo]
    total: int


class TTSPregenerateRequest(BaseModel):
    """Manual trigger pregeneration request"""
    filename: Optional[str] = None
    article_hash: Optional[str] = None
    text: Optional[str] = None


class TTSPregenerateResponse(BaseModel):
    """Manual trigger pregeneration response"""
    task_id: Optional[str] = None
    status: str
    message: str
