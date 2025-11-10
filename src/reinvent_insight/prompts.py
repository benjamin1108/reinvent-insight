# -*- coding: utf-8 -*-
"""
提示词模板模块

说明：
- 本模块现在使用 PromptManager 进行统一管理
- 所有 prompt 定义在 ./prompt/ 目录下
- 本模块提供向后兼容的接口，但建议使用新的 PromptManager API

迁移指南：
- 旧方式: prompts.PDF_MULTIMODAL_GUIDE
- 新方式: get_prompt_manager().get_prompt('pdf_multimodal_guide')
"""

import os
from loguru import logger
from .prompt_manager import get_prompt_manager, PromptManager

logger = logger.bind(name=__name__)

# ============================================
# 全局 PromptManager 实例
# ============================================

# 检查是否在开发模式（通过环境变量）
_enable_hot_reload = os.getenv('PROMPT_HOT_RELOAD', 'false').lower() == 'true'

try:
    _manager = get_prompt_manager(enable_hot_reload=_enable_hot_reload)
    logger.info(f"PromptManager initialized (hot_reload={_enable_hot_reload})")
except Exception as e:
    logger.error(f"Failed to initialize PromptManager: {e}")
    _manager = None


# ============================================
# 向后兼容的常量和模板
# ============================================

def _get_with_deprecation_warning(key: str, var_name: str) -> str:
    """
    获取 prompt 并记录弃用警告
    
    Args:
        key: prompt key
        var_name: 变量名（用于警告信息）
        
    Returns:
        prompt 内容
    """
    logger.warning(
        f"Accessing '{var_name}' directly is deprecated. "
        f"Please use: get_prompt_manager().get_prompt('{key}') or format_prompt('{key}', ...)"
    )
    
    if _manager is None:
        logger.error("PromptManager not initialized, returning empty string")
        return ""
    
    try:
        return _manager.get_prompt(key)
    except Exception as e:
        logger.error(f"Failed to get prompt '{key}': {e}")
        return ""


# 使用 __getattr__ 实现动态属性访问
def __getattr__(name: str):
    """
    动态属性访问，提供向后兼容性
    
    支持的旧常量：
    - PDF_MULTIMODAL_GUIDE
    - MARKDOWN_BOLD_RULES
    - OUTLINE_PROMPT_TEMPLATE
    - CHAPTER_PROMPT_TEMPLATE
    - CONCLUSION_PROMPT_TEMPLATE
    """
    # 映射旧常量名到新的 prompt key
    _legacy_mapping = {
        'PDF_MULTIMODAL_GUIDE': 'pdf_multimodal_guide',
        'MARKDOWN_BOLD_RULES': 'markdown_bold_rules',
        'OUTLINE_PROMPT_TEMPLATE': 'outline_template',
        'CHAPTER_PROMPT_TEMPLATE': 'chapter_template',
        'CONCLUSION_PROMPT_TEMPLATE': 'conclusion_template',
    }
    
    if name in _legacy_mapping:
        key = _legacy_mapping[name]
        return _get_with_deprecation_warning(key, name)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# ============================================
# 新的推荐 API
# ============================================

def get_prompt(key: str, raw: bool = False) -> str:
    """
    获取 prompt 内容（推荐使用）
    
    Args:
        key: prompt 标识符
        raw: 是否返回原始内容（不进行片段组合）
        
    Returns:
        prompt 内容字符串
        
    Example:
        >>> base_prompt = get_prompt('youtube_deep_summary_base')
        >>> markdown_rules = get_prompt('markdown_bold_rules')
    """
    if _manager is None:
        raise RuntimeError("PromptManager not initialized")
    
    return _manager.get_prompt(key, raw=raw)


def format_prompt(key: str, **params) -> str:
    """
    格式化 prompt 模板（推荐使用）
    
    Args:
        key: prompt 标识符
        **params: 模板参数
        
    Returns:
        格式化后的 prompt 字符串
        
    Example:
        >>> outline_prompt = format_prompt(
        ...     'outline_template',
        ...     content_type='完整英文字幕',
        ...     content_description='完整字幕',
        ...     full_content=transcript
        ... )
    """
    if _manager is None:
        raise RuntimeError("PromptManager not initialized")
    
    return _manager.format_prompt(key, **params)


def list_available_prompts() -> list:
    """
    列出所有可用的 prompt
    
    Returns:
        PromptConfig 对象列表
    """
    if _manager is None:
        raise RuntimeError("PromptManager not initialized")
    
    return _manager.list_prompts()


def reload_prompts() -> None:
    """
    重新加载所有 prompt（用于开发模式）
    """
    if _manager is None:
        raise RuntimeError("PromptManager not initialized")
    
    _manager.reload_prompts()


# ============================================
# 导出的公共 API
# ============================================

__all__ = [
    'get_prompt',
    'format_prompt',
    'list_available_prompts',
    'reload_prompts',
    'get_prompt_manager',
]
