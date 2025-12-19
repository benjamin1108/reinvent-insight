# -*- coding: utf-8 -*-
"""
Deep/Ultra Prompt 模块（v2 重构版）

提供结构化的 Chain-of-Thought prompt，用于：
- 大纲生成
- 章节内容生成
- 结论生成

使用示例：
```python
from prompt.v2.deep_ultra import (
    build_outline_prompt,
    build_chapter_prompt,
    build_conclusion_prompt,
    get_mode_config
)

# 构建大纲 prompt
outline_prompt = build_outline_prompt(content, mode="deep")

# 构建章节 prompt
chapter_prompt = build_chapter_prompt(
    full_content=content,
    full_outline=outline,
    chapter_number=1,
    chapter_title="章节标题",
    subsections=[...],
    must_include=[...],
    must_exclude=[...]
)

# 构建结论 prompt
conclusion_prompt = build_conclusion_prompt(content, chapters)
```
"""

# 大纲生成
from .outline import (
    build_outline_prompt,
    get_outline_instructions,
    get_mode_config,
    MODE_CONFIGS,
)

# 章节生成
from .chapter import (
    build_chapter_prompt,
    build_previous_context,
    format_subsections,
    DEDUPLICATION_INSTRUCTION_SEQUENTIAL,
)

# 结论生成
from .conclusion import (
    build_conclusion_prompt,
)

# 基础定义
from ._base import (
    ROLE_DEFINITION,
    WRITING_STYLE_GUIDE,
    LANGUAGE_PURIFICATION_RULES,
    TRANSITION_RULES,
    FORMATTING_RULES,
    QUALITY_CHECKLIST,
    ARCHITECT_PERSPECTIVE,
    get_base_context,
    get_quality_rules,
)

__all__ = [
    # 主要构建函数
    "build_outline_prompt",
    "build_chapter_prompt",
    "build_conclusion_prompt",
    
    # 辅助函数
    "get_mode_config",
    "get_outline_instructions",
    "build_previous_context",
    "format_subsections",
    "get_base_context",
    "get_quality_rules",
    
    # 配置
    "MODE_CONFIGS",
    
    # 基础定义（供高级用途）
    "ROLE_DEFINITION",
    "WRITING_STYLE_GUIDE",
    "LANGUAGE_PURIFICATION_RULES",
    "TRANSITION_RULES",
    "FORMATTING_RULES",
    "QUALITY_CHECKLIST",
    "ARCHITECT_PERSPECTIVE",
    "DEDUPLICATION_INSTRUCTION_SEQUENTIAL",
]
