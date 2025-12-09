"""大纲模型定义"""

from dataclasses import dataclass
from typing import List


class OutlineParseError(Exception):
    """大纲解析错误"""
    pass


@dataclass
class ChapterPlan:
    """章节规划"""
    index: int
    title: str
    depth_recommendation: 'DepthRecommendation'
    estimated_source_length: int  # 估计的原始内容长度（词数）
    source_coverage_percent: float  # 在原始内容中的覆盖百分比


@dataclass
class OutlinePlan:
    """大纲规划"""
    title_en: str
    title_cn: str
    introduction: str
    chapters: List[ChapterPlan]
    total_estimated_words: int
