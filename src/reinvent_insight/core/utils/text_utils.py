"""Text utility functions"""

import re
from zhon import hanzi


def extract_text_from_markdown(content: str) -> str:
    """从 Markdown 内容中提取纯文本，用于准确计算字数
    
    Args:
        content: Markdown 内容
        
    Returns:
        纯文本内容
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


def count_chinese_words(text: str) -> int:
    """使用 zhon 库统计中文字符和中文标点
    
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
