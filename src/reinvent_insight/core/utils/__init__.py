"""工作流相关的工具函数"""

import re
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def create_anchor(text: str) -> str:
    """根据给定的标题文本创建一个 Markdown 锚点链接
    
    Args:
        text: 标题文本
        
    Returns:
        锚点链接（小写、去标点、空格转连字符）
        
    Examples:
        "1. AWS 服务架构" -> "1-aws-服务架构"
        "### 引言" -> "引言"
    """
    # 转换为小写
    text = text.lower()
    # 移除 Markdown 标题标记, e.g., '### '
    text = text.strip().lstrip('#').strip()
    # 移除大部分标点符号, 但保留连字符. \w 匹配字母、数字、下划线.
    # 添加了中文字符范围 \u4e00-\u9fa5
    text = re.sub(r'[^\w\s\-\u4e00-\u9fa5]', '', text, flags=re.UNICODE)
    # 将一个或多个空格替换为单个连字符
    text = re.sub(r'\s+', '-', text)
    return text


def remove_parenthetical_english(text: str) -> str:
    """移除文本中的"中文（英文）"格式
    
    这是一个后处理函数，用于清理模型生成的内容中不必要的英文注释。
    这是提示词优化的补充保险措施，确保即使模型偶尔犯错也能自动修正。
    
    Args:
        text: 待处理的文本
        
    Returns:
        清理后的文本
        
    Examples:
        "目标（goals）" -> "目标"
        "**方法**（methods）" -> "**方法**"
        "超人级表现（superhuman performance）" -> "超人级表现"
        "OpenAI 是一家公司" -> "OpenAI 是一家公司"  # 无括号，保持不变
    """
    # 匹配模式：中文（可能包含加粗标记**）后跟括号，括号内是英文
    # 支持：中文（英文）、**中文**（英文）、中文 (英文) 等格式
    # [\u4e00-\u9fa5*]+ 匹配中文字符和星号（用于加粗）
    pattern = r'([\u4e00-\u9fa5*]+)[\s]*[\(（]([a-zA-Z\s\-]+)[\)）]'
    
    def replace_func(match):
        chinese_part = match.group(1)
        # 直接返回中文部分，去掉括号和英文
        return chinese_part
    
    # 执行替换
    cleaned_text = re.sub(pattern, replace_func, text)
    
    # 记录清理情况
    if cleaned_text != text:
        removed_count = len(re.findall(pattern, text))
        logger.info(f"后处理清理：移除了 {removed_count} 处不必要的英文注释")
    
    return cleaned_text


def generate_toc_with_links(chapters: List[str]) -> str:
    """根据章节列表生成带锚点链接的 Markdown 目录
    
    Args:
        chapters: 章节标题列表
        
    Returns:
        Markdown格式的目录，带锚点链接
        
    Example:
        chapters = ["AWS 服务架构", "网络配置", "安全最佳实践"]
        返回：
        ```
        ### 主要目录
        1. [AWS 服务架构](#1-aws-服务架构)
        2. [网络配置](#2-网络配置)
        3. [安全最佳实践](#3-安全最佳实践)
        ```
    """
    toc_md_lines = ["### 主要目录"]
    for i, chapter_title in enumerate(chapters):
        # 最终报告中的标题格式是 "1. Chapter Title"
        heading_for_anchor = f"{i + 1}. {chapter_title}"
        anchor = create_anchor(heading_for_anchor)
        toc_md_lines.append(f"{i + 1}. [{chapter_title}](#{anchor})")
    return "\n".join(toc_md_lines)


def extract_titles_from_outline(outline_content: str) -> Tuple[Optional[str], Optional[str]]:
    """从outline内容中提取中英文标题
    
    Args:
        outline_content: outline.md的完整内容
        
    Returns:
        (title_en, title_cn) 元组，如果提取失败则返回(None, None)
    """
    import json
    
    title_en = None
    title_cn = None
    
    # 方法1: 尝试提取JSON格式的标题信息
    try:
        # 使用更健壮的JSON提取方法：查找第一个{，然后匹配括号平衡
        json_str = None
        start_idx = outline_content.find('{')
        if start_idx != -1:
            brace_count = 0
            for i in range(start_idx, len(outline_content)):
                if outline_content[i] == '{':
                    brace_count += 1
                elif outline_content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = outline_content[start_idx:i+1]
                        break
        
        if json_str:
            title_data = json.loads(json_str)
            title_en = title_data.get('title_en', '').strip()
            title_cn = title_data.get('title_cn', '').strip()
            
            if title_en and title_cn:
                logger.info(f"成功从JSON格式提取标题 - EN: {title_en}, CN: {title_cn}")
                return title_en, title_cn
            else:
                logger.warning(f"JSON中标题字段为空 - EN: {title_en}, CN: {title_cn}")
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败: {e}")
    except Exception as e:
        logger.warning(f"提取JSON标题时出错: {e}")
    
    # 方法2: 从Markdown标题中提取中文标题
    title_match = re.search(r"^#\s*(.*)", outline_content, re.MULTILINE)
    if title_match:
        title_cn = title_match.group(1).strip()
        logger.info(f"从Markdown提取中文标题: {title_cn}")
    else:
        logger.warning("无法从Markdown中提取标题")
    
    # 如果没有英文标题，记录警告
    if not title_en:
        logger.warning("未能提取英文标题，将在后续使用后备方案")
    
    return title_en, title_cn


def parse_outline(content: str) -> Tuple[Optional[str], Optional[List[str]], Optional[str]]:
    """从大纲JSON中解析标题、引言和章节列表
    
    Args:
        content: outline内容（JSON格式）
        
    Returns:
        (title, chapters, introduction) 元组
    """
    import json
    
    try:
        # 提取 JSON 块
        json_match = re.search(r'```json\s*([\s\S]*?)```', content)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_match = re.search(r'\{[\s\S]*"chapters"[\s\S]*\}', content)
            if json_match:
                json_str = json_match.group(0)
            else:
                logger.warning("未找到JSON内容")
                return None, None, None
        
        outline_json = json.loads(json_str)
        
        title = outline_json.get('title_cn') or outline_json.get('title')
        introduction = outline_json.get('introduction')
        chapters_data = outline_json.get('chapters', [])
        chapters = [ch.get('title', '') for ch in chapters_data if ch.get('title')]
        
        if not title or not chapters:
            logger.warning(f"解析大纲失败: title={title}, chapters={len(chapters) if chapters else 0}")
            return None, None, None
        
        logger.info(f"解析大纲成功: 标题={title[:30]}..., 章节数={len(chapters)}")
        return title, chapters, introduction
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败: {e}")
        return None, None, None
    except Exception as e:
        logger.warning(f"解析大纲失败: {e}")
        return None, None, None


def count_toc_chapters(toc_content: str) -> int:
    """统计 TOC 中的章节数量
    
    只统计「### 主要目录」或「### 目录」区域内的章节数量
    格式如：1. 章节标题1...2
    
    Args:
        toc_content: 目录内容
        
    Returns:
        章节数量
    """
    # 先提取 TOC 区域（从 ### 主要目录 或 ### 目录 到下一个 ### 标题之间）
    toc_patterns = [
        r'###\s*主要目录\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
        r'###\s*目录\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
        r'###\s*Table of Contents\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
    ]
    
    toc_area = ""
    for pattern in toc_patterns:
        match = re.search(pattern, toc_content, re.DOTALL | re.IGNORECASE)
        if match:
            toc_area = match.group(1)
            break
    
    if not toc_area:
        # 如果没找到TOC区域，返回0
        return 0
    
    # 在 TOC 区域内统计编号列表项
    chapters = re.findall(r'^\d+\.\s+.+', toc_area, re.MULTILINE)
    return len(chapters)
