"""文档元数据服务 - 处理Markdown元数据解析和文本提取"""

import re
import yaml
import logging
from typing import Dict
from zhon import hanzi

logger = logging.getLogger(__name__)


def parse_metadata_from_md(md_content: str) -> Dict:
    """从 Markdown 文件内容中解析 YAML front matter
    
    Args:
        md_content: Markdown文件内容
        
    Returns:
        解析出的元数据字典，解析失败返回空字典
    """
    try:
        # 使用正则表达式匹配 front matter
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', md_content, re.DOTALL)
        if match:
            front_matter_str = match.group(1)
            metadata = yaml.safe_load(front_matter_str)
            if isinstance(metadata, dict):
                return metadata
    except (yaml.YAMLError, IndexError) as e:
        logger.warning(f"解析 YAML front matter 失败: {e}")
    return {}


def extract_text_from_markdown(content: str) -> str:
    """从 Markdown 内容中提取纯文本，用于准确计算字数
    
    Args:
        content: Markdown内容
        
    Returns:
        提取的纯文本
    """
    # 移除代码块
    content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)
    content = re.sub(r'`[^`]+`', '', content)
    
    # 移除链接
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
    
    # 移除图片
    content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', content)
    
    # 移除标题标记
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
    
    # 移除粗体和斜体标记
    content = re.sub(r'\*{1,3}([^\*]+)\*{1,3}', r'\1', content)
    content = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', content)
    
    # 移除列表标记
    content = re.sub(r'^[\*\-\+]\s+', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\d+\.\s+', '', content, flags=re.MULTILINE)
    
    # 移除引用标记
    content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
    
    # 移除水平线
    content = re.sub(r'^[-\*_]{3,}$', '', content, flags=re.MULTILINE)
    
    # 移除表格分隔符
    content = re.sub(r'\|', '', content)
    
    # 移除多余的空白字符
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    
    # 去除首尾空白
    content = content.strip()
    
    return content


def clean_content_metadata(content: str, title: str = '') -> str:
    """清理内容中的元数据，返回干净的文本内容
    
    Args:
        content: 原始内容
        title: 文档标题（可选）
        
    Returns:
        清理后的内容
    """
    if not content:
        return ''
    
    cleaned_content = content
    
    # 使用yaml库安全地解析和移除YAML Front Matter
    if content.startswith('---'):
        try:
            # 使用更宽松的正则表达式匹配完整的YAML front matter块
            match = re.match(r'^---\s*\n(.*?)\n\s*---\s*\n', content, re.DOTALL)
            if match:
                # 验证YAML是否有效
                yaml_content = match.group(1)
                yaml.safe_load(yaml_content)  # 验证YAML语法
                
                # 移除YAML front matter，保留后面的内容
                cleaned_content = content[match.end():]
                logger.debug(f"成功移除YAML front matter，剩余内容长度: {len(cleaned_content)}")
            else:
                # 尝试另一种格式：没有结束标记的情况
                lines = content.split('\n')
                for i, line in enumerate(lines[1:], 1):
                    if line.strip().startswith('#') or (i > 1 and not line.strip() and i + 1 < len(lines) and ':' not in lines[i + 1]):
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
        escaped_title = re.escape(title)
        markdown_title_pattern = rf'^#+\s*{escaped_title}\s*[!！.。:：]?\s*$'
        cleaned_content = re.sub(
            markdown_title_pattern, 
            '', 
            cleaned_content, 
            count=1, 
            flags=re.MULTILINE | re.IGNORECASE
        ).lstrip()
    
    return cleaned_content


def count_toc_chapters(content: str) -> int:
    """统计 TOC 中的章节数量
    
    只统计「### 主要目录」或「### 目录」区域内的章节数量
    格式如：1. 章节标题、2. 章节标题 等
    
    Args:
        content: Markdown内容
        
    Returns:
        章节数量
    """
    # 先提取 TOC 区域
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
        return 0
    
    # 在 TOC 区域内统计编号列表项
    chapters = re.findall(r'^\d+\.\s+.+', toc_content, re.MULTILINE)
    return len(chapters)


def count_chinese_words(text: str) -> int:
    """统计中文字符和中文标点数量
    
    使用 zhon 库统计中文字符和中文标点
    
    Args:
        text: 文本内容
        
    Returns:
        中文字数
    """
    # 统计汉字 (不包含标点)
    hanzi_chars = re.findall(f'[{hanzi.characters}]', text)
    # 统计中文标点
    punctuation_chars = re.findall(f'[{hanzi.punctuation}]', text)
    return len(hanzi_chars) + len(punctuation_chars)


def discover_versions(source_identifier: str, output_dir, metadata_parser=None) -> list:
    """发现指定内容标识符的所有版本
    
    Args:
        source_identifier: 内容来源标识符（video_url 或 content_identifier）
        output_dir: 输出目录（Path对象）
        metadata_parser: 元数据解析函数，如果不提供则使用默认
        
    Returns:
        版本信息列表
    """
    versions = []
    
    if not output_dir.exists():
        return versions
    
    # 使用默认解析器如果未提供
    if metadata_parser is None:
        metadata_parser = parse_metadata_from_md
        
    # 扫描所有文件
    for md_file in output_dir.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            metadata = metadata_parser(content)
            
            # 检查是否是同一个内容（支持 content_identifier 和 video_url）
            file_source_id = metadata.get('content_identifier') or metadata.get('video_url')
            if file_source_id == source_identifier:
                version_info = {
                    'filename': md_file.name,
                    'version': metadata.get('version', 0),
                    'created_at': metadata.get('created_at', ''),
                    'title_cn': metadata.get('title_cn', ''),
                    'title_en': metadata.get('title_en', '')
                }
                versions.append(version_info)
        except Exception as e:
            logger.warning(f"检查文件 {md_file.name} 时出错: {e}")
    
    # 按版本号排序
    versions.sort(key=lambda x: x['version'])
    return versions
