"""
Markdown 后处理模块

这个模块提供了各种 Markdown 文档的后处理功能，包括：
1. 在大章节之间添加分隔符
2. 修复粗体格式的空格问题
"""

import logging
from pathlib import Path
from typing import Tuple, List

logger = logging.getLogger(__name__)

class MarkdownProcessor:
    """Markdown 文档后处理器"""
    
    def __init__(self):
        pass
    
    def clean_duplicate_separators(self, content: str) -> Tuple[str, int]:
        """
        清理重复的分隔符
        
        Args:
            content: Markdown 文档内容
            
        Returns:
            处理后的内容和清理的重复分隔符数量
        """
        lines = content.split('\n')
        cleaned_lines = []
        removals_count = 0
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 如果当前行是分隔符
            if line in ['---', '***', '___']:
                cleaned_lines.append(lines[i])
                i += 1
                
                # 跳过后续连续的分隔符和空行
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line in ['---', '***', '___']:
                        # 发现重复的分隔符，跳过
                        removals_count += 1
                        i += 1
                    elif next_line == '':
                        # 空行，保留一个
                        if not cleaned_lines or cleaned_lines[-1].strip() != '':
                            cleaned_lines.append(lines[i])
                        i += 1
                    else:
                        # 非空行，结束跳过
                        break
            else:
                cleaned_lines.append(lines[i])
                i += 1
        
        return '\n'.join(cleaned_lines), removals_count
    
    def add_section_separators(self, content: str) -> Tuple[str, int]:
        """
        在大章节（### 标题）之间添加分隔符
        
        Args:
            content: Markdown 文档内容
            
        Returns:
            处理后的内容和添加的分隔符数量
        """
        lines = content.split('\n')
        section_lines = self._find_section_lines(lines)
        
        if len(section_lines) <= 1:
            return content, 0
        
        # 从后往前处理，避免行号变化的问题
        additions_count = 0
        for i in reversed(range(1, len(section_lines))):
            line_num = section_lines[i]
            
            # 检查这个标题前面是否已经有分隔符了
            has_separator = self._has_separator_before(lines, line_num)
            if has_separator:
                continue  # 已经有分隔符了，跳过
            
            # 检查前面是否有空行，如果没有则先加一个空行
            insert_pos = line_num
            prev_line_idx = line_num - 1
            if prev_line_idx >= 0 and lines[prev_line_idx].strip():
                # 前面不是空行，先插入空行再插入分隔符
                lines.insert(insert_pos, '')
                lines.insert(insert_pos + 1, '---')
                lines.insert(insert_pos + 2, '')
                additions_count += 1
            else:
                # 前面已经是空行，直接插入分隔符
                lines.insert(insert_pos, '---')
                lines.insert(insert_pos + 1, '')
                additions_count += 1
        
        return '\n'.join(lines), additions_count
    
    def _find_section_lines(self, lines: List[str]) -> List[int]:
        """找出所有大章节（### 标题）的行号"""
        section_lines = []
        
        for i, line in enumerate(lines):
            # 匹配以 ### 开头的标题（大章节）
            if line.strip().startswith('### ') and not line.strip().startswith('#### '):
                section_lines.append(i)
        
        return section_lines
    
    def _has_separator_before(self, lines: List[str], line_num: int) -> bool:
        """检查指定行之前是否已经有分隔符"""
        # 从当前行往前查找，跳过空行，看是否有分隔符
        separator_found = False
        non_empty_lines_count = 0
        
        for i in range(line_num - 1, -1, -1):
            line = lines[i].strip()
            if not line:  # 空行，继续查找
                continue
            
            non_empty_lines_count += 1
            if line in ['---', '***', '___']:  # 找到分隔符
                separator_found = True
                break
            elif non_empty_lines_count >= 2:  # 已经检查了2行非空内容，没必要继续
                break
        
        return separator_found
    
    def process_file(self, file_path: Path, add_separators: bool = True, clean_duplicates: bool = True) -> bool:
        """
        处理单个 Markdown 文件
        
        Args:
            file_path: 文件路径
            add_separators: 是否添加章节分隔符
            clean_duplicates: 是否清理重复分隔符
            
        Returns:
            处理是否成功
        """
        try:
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return False
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modifications_made = False
            
            # 清理重复的分隔符
            if clean_duplicates:
                content, duplicates_removed = self.clean_duplicate_separators(content)
                if duplicates_removed > 0:
                    logger.info(f"为文件 {file_path.name} 清理了 {duplicates_removed} 个重复分隔符")
                    modifications_made = True
            
            # 添加章节分隔符
            if add_separators:
                content, separators_added = self.add_section_separators(content)
                if separators_added > 0:
                    logger.info(f"为文件 {file_path.name} 添加了 {separators_added} 个章节分隔符")
                    modifications_made = True
            
            # 如果有修改，写回文件
            if modifications_made:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"已更新文件: {file_path.name}")
                return True
            else:
                logger.debug(f"文件无需修改: {file_path.name}")
                return True
                
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时发生错误: {e}")
            return False

# 全局实例
markdown_processor = MarkdownProcessor()

def process_markdown_file(file_path: Path, add_separators: bool = True, clean_duplicates: bool = True) -> bool:
    """
    便捷函数：处理单个 Markdown 文件
    
    Args:
        file_path: 文件路径
        add_separators: 是否添加章节分隔符
        clean_duplicates: 是否清理重复分隔符
        
    Returns:
        处理是否成功
    """
    return markdown_processor.process_file(file_path, add_separators, clean_duplicates) 