# -*- coding: utf-8 -*-
"""
提示词模板模块

说明：
- 本模块定义特定任务的提示词模板和公共规则
- 按功能拆分为多个子模块：common, outline, chapter, conclusion, ultra
"""

from .common import (
    PDF_MULTIMODAL_GUIDE,
    ROLE_AND_STYLE_GUIDE,
    QUALITY_CONTROL_RULES,
    DEDUPLICATION_INSTRUCTION_WITH_PREVIOUS,
    DEDUPLICATION_INSTRUCTION_FIRST,
    PREVIOUS_CHAPTER_CONTEXT_TEMPLATE,
)

from .outline import OUTLINE_PROMPT_TEMPLATE

from .chapter import (
    CHAPTER_DEPTH_CONSTRAINT_TEMPLATE,
    CHAPTER_PROMPT_TEMPLATE,
)

from .conclusion import CONCLUSION_PROMPT_TEMPLATE

from .ultra import (
    MODE_CONFIGS,
    get_mode_config,
    get_outline_instructions,
    get_chapter_instructions,
    # 向后兼容
    DEEP_OUTLINE_INSTRUCTIONS,
    ULTRA_OUTLINE_INSTRUCTIONS,
    ULTRA_CHAPTER_INSTRUCTIONS,
)

from .subtitle import (
    SUBTITLE_TRANSLATION_PROMPT_WITH_CONTEXT,
    SUBTITLE_TRANSLATION_PROMPT_FALLBACK,
    build_translation_prompt,
)

__all__ = [
    # Common
    'PDF_MULTIMODAL_GUIDE',
    'ROLE_AND_STYLE_GUIDE',
    'QUALITY_CONTROL_RULES',
    'DEDUPLICATION_INSTRUCTION_WITH_PREVIOUS',
    'DEDUPLICATION_INSTRUCTION_FIRST',
    'PREVIOUS_CHAPTER_CONTEXT_TEMPLATE',
    # Outline
    'OUTLINE_PROMPT_TEMPLATE',
    # Chapter
    'CHAPTER_DEPTH_CONSTRAINT_TEMPLATE',
    'CHAPTER_PROMPT_TEMPLATE',
    # Conclusion
    'CONCLUSION_PROMPT_TEMPLATE',
    # Ultra / Deep
    'MODE_CONFIGS',
    'get_mode_config',
    'get_outline_instructions',
    'get_chapter_instructions',
    'DEEP_OUTLINE_INSTRUCTIONS',
    'ULTRA_OUTLINE_INSTRUCTIONS',
    'ULTRA_CHAPTER_INSTRUCTIONS',
    # Subtitle
    'SUBTITLE_TRANSLATION_PROMPT_WITH_CONTEXT',
    'SUBTITLE_TRANSLATION_PROMPT_FALLBACK',
    'build_translation_prompt',
]
