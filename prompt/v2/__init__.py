# -*- coding: utf-8 -*-
"""
Prompt v2 模块

重构版本的 prompt 模板，采用标准化结构：
- 角色定义（Role Definition）
- 任务目标（Task Objective）
- 输入规范（Input Specification）
- 思考过程（Chain-of-Thought）
- 输出格式（Output Format）
- 约束条件（Constraints）

目录结构：
- deep_ultra/: Deep/Ultra 流程的 prompt
"""

from .deep_ultra import (
    # 主要构建函数
    build_outline_prompt,
    build_chapter_prompt,
    build_conclusion_prompt,
    
    # 辅助函数
    get_mode_config,
    get_outline_instructions,
    
    # 配置
    MODE_CONFIGS,
)

__all__ = [
    "build_outline_prompt",
    "build_chapter_prompt",
    "build_conclusion_prompt",
    "get_mode_config",
    "get_outline_instructions",
    "MODE_CONFIGS",
]
