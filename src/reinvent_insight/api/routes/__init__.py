"""API Routes - FastAPI route handlers"""

from .auth import router as auth_router
from .analysis import router as analysis_router
from .documents import router as documents_router
from .trash import router as trash_router
from .versions import router as versions_router
from .downloads import router as downloads_router
from .tts_generate import router as tts_generate_router
from .tts_cache import router as tts_cache_router
from .tts_pregenerate import router as tts_pregenerate_router
from .system import router as system_router
from .visual import router as visual_router
from .ultra_deep import router as ultra_deep_router
from .tasks import router as tasks_router

__all__ = [
    "auth_router",
    "analysis_router",
    "documents_router",
    "trash_router",
    "versions_router",
    "downloads_router",
    "tts_generate_router",
    "tts_cache_router",
    "tts_pregenerate_router",
    "system_router",
    "visual_router",
    "ultra_deep_router",
    "tasks_router",
]
