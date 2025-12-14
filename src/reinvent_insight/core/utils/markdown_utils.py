"""Markdown 文本处理工具"""

import re
import logging
from typing import List, Optional, Tuple
from zhon import hanzi

logger = logging.getLogger(__name__)


def create_anchor(text: str) -> str:
    """根据给定的标题文本创建一个 Markdown 锚点链接。
    
    Args:
        text: 标题文本
        
    Returns:
        锚点链接字符串
        
    Examples:
        >>> create_anchor("第一章：简介")
        "第一章-简介"
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
    """
    移除文本中的"中文（英文）"格式
    
    这是一个后处理函数，用于清理模型生成的内容中不必要的英文注释。
    这是提示词优化的补充保险措施，确保即使模型偶尔犯错也能自动修正。
    
    Examples:
        "目标（goals）" -> "目标"
        "**方法**（methods）" -> "**方法**"
        "超人级表现（superhuman performance）" -> "超人级表现"
        "OpenAI 是一家公司" -> "OpenAI 是一家公司"  # 无括号，保持不变
    
    Args:
        text: 待处理的文本
        
    Returns:
        清理后的文本
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
    """根据章节列表生成带锚点链接的 Markdown 目录。
    
    Args:
        chapters: 章节标题列表
        
    Returns:
        带链接的目录 Markdown 文本
    """
    toc_md_lines = ["### 主要目录"]
    for i, chapter_title in enumerate(chapters):
        # 最终报告中的标题格式是 "1. Chapter Title"
        heading_for_anchor = f"{i + 1}. {chapter_title}"
        anchor = create_anchor(heading_for_anchor)
        toc_md_lines.append(f"{i + 1}. [{chapter_title}](#{anchor})")
    return "\n".join(toc_md_lines)


def parse_outline(content: str) -> Tuple[Optional[str], Optional[List[str]], Optional[str]]:
    """从Markdown文本中解析标题、引言和章节列表
    
    Args:
        content: Markdown 格式的大纲内容
        
    Returns:
        (title, chapters, introduction) 元组
        - title: 标题（从 # 标题 提取）
        - chapters: 章节列表（从 1. 章节 提取）
        - introduction: 引言（从 ### 引言 部分提取）
    """
    
    title_match = re.search(r"^#\s*(.*)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else None

    # 解析引言
    introduction_match = re.search(r"###\s*引言\s*\n(.*?)(?=\n###|$)", content, re.DOTALL)
    introduction = introduction_match.group(1).strip() if introduction_match else None

    chapters = re.findall(r"^\d+\.\s*(.*)", content, re.MULTILINE)
    
    if not title or not chapters:
        logger.warning(f"无法从内容中解析出完整的标题和章节: {content[:500]}")
        return None, None, None
        
    return title, chapters, introduction


def extract_titles_from_outline(outline_content: str) -> Tuple[Optional[str], Optional[str]]:
    """
    从outline内容中提取中英文标题
    
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


def clean_content_metadata(content: str, title: str = '') -> str:
    """清理内容中的元数据，返回干净的文本内容
    
    Args:
        content: 原始内容
        title: 文档标题（用于去重）
        
    Returns:
        清理后的内容
    """
    import yaml
    
    if not content:
        return ''
    
    cleaned_content = content
    
    # 使用yaml库安全地解析和移除YAML Front Matter
    if content.startswith('---'):
        try:
            # 使用更宽松的正则表达式匹配完整的YAML front matter块
            # 允许结束标记前有空行
            match = re.match(r'^---\s*\n(.*?)\n\s*---\s*\n', content, re.DOTALL)
            if match:
                # 验证YAML是否有效
                yaml_content = match.group(1)
                yaml.safe_load(yaml_content)  # 验证YAML语法
                
                # 移除YAML front matter，保留后面的内容
                cleaned_content = content[match.end():]
                logger.debug(f"成功移除YAML front matter，剩余内容长度: {len(cleaned_content)}")
            else:
                # 尝试另一种格式：没有结束标记的情况（用户展示的错误格式）
                # 这种情况下，假设从第一个标题行开始是正文
                lines = content.split('\n')
                for i, line in enumerate(lines[1:], 1):  # 跳过第一行的 ---
                    # 如果遇到 Markdown 标题（# 开头）或者空行后的非 YAML 格式内容
                    if line.strip().startswith('#') or (i > 1 and not line.strip() and i + 1 < len(lines) and not ':' in lines[i + 1]):
                        cleaned_content = '\n'.join(lines[i:])
                        logger.debug(f"检测到不完整的YAML front matter，从第{i}行开始提取内容")
                        break
                else:
                    logger.warning("检测到---开头但无法确定YAML front matter的结束位置")
        except yaml.YAMLError as e:
            logger.warning(f"YAML front matter解析失败，保留原始内容: {e}")
        except Exception as e:
            logger.error(f"处理YAML front matter时发生错误: {e}")
    
    # 清理开头的空行
    cleaned_content = cleaned_content.lstrip()
    
    # 可选：如果标题存在，去除可能重复的H1标题
    if title and cleaned_content:
        # 处理可能的标题变体（考虑空格、标点等）
        escaped_title = re.escape(title)
        # 匹配 # 标题 或 ## 标题 等，允许标题后有标点符号
        markdown_title_pattern = rf'^#+\s*{escaped_title}\s*[!！.。:：]?\s*$'
        cleaned_content = re.sub(markdown_title_pattern, '', cleaned_content, count=1, flags=re.MULTILINE | re.IGNORECASE).lstrip()
    
    return cleaned_content


def count_toc_chapters(content: str) -> int:
    """统计 TOC 中的章节数量
    
    只统计「### 主要目录」或「### 目录」区域内的章节数量
    格式如：1. 章节标题、2. 章节标题 等
    
    Args:
        content: Markdown 内容
        
    Returns:
        章节数量
    """
    # 先提取 TOC 区域（从 ### 主要目录 或 ### 目录 到下一个 ### 标题之间）
    toc_patterns = [
        r'###\s*主要目录\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
        r'###\s*目录\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
        r'###\s*Table of Contents\s*\n(.*?)(?=\n###[^#]|\n##[^#]|$)',
    ]
    
    toc_content = ""
    for pattern in toc_patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            toc_content = match.group(1)
            break
    
    if not toc_content:
        # 如果没找到TOC区域，返回0
        return 0
    
    # 在 TOC 区域内统计编号列表项
    chapters = re.findall(r'^\d+\.\s+.+', toc_content, re.MULTILINE)
    return len(chapters)
