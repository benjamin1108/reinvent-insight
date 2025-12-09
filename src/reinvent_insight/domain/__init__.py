"""
领域层（Domain Layer）

包含核心业务实体、领域模型和业务规则。
领域层应该是无外部依赖的，只包含纯粹的业务逻辑。
"""

from .models import DocumentContent, ChapterPlan, OutlinePlan, OutlineParseError
from .workflows import AnalysisWorkflow
from . import prompts

__all__ = [
    'DocumentContent',
    'ChapterPlan',
    'OutlinePlan',
    'OutlineParseError',
    'AnalysisWorkflow',
    'prompts',
]
