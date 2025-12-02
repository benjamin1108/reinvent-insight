"""
TTS 文本预处理器

将 Markdown 文章转换为适合 TTS 朗读的纯文本。
遵循设计文档中的预处理规则，优化朗读节奏和抑扬顿挫。
"""

import re
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingResult:
    """预处理结果"""
    text: str                    # 处理后的文本
    article_hash: str           # 文章哈希值
    title_cn: str               # 中文标题
    original_length: int        # 原文长度
    processed_length: int       # 处理后长度
    sections_removed: list      # 移除的章节


class TTSTextPreprocessor:
    """TTS 文本预处理器
    
    功能：
    1. 去除英文标题，保留中文标题
    2. 去除目录（TOC）
    3. 去除洞见与金句
    4. 清理 Markdown 格式
    5. 优化段落节奏
    """
    
    def __init__(self):
        """初始化预处理器"""
        # 需要移除的章节标题模式
        self.remove_sections = [
            r'###\s*目录',
            r'###\s*Table of Contents',
            r'###\s*TOC',
            r'###\s*核心洞见',
            r'###\s*洞见',
            r'###\s*Insights?',
            r'###\s*Key Takeaways?',
            r'###\s*金句',
            r'###\s*Quotes?',
            r'###\s*名言',
        ]
        
        # 特殊符号替换表
        self.symbol_replacements = {
            '→': '到',
            '←': '来自',
            '⇒': '推导出',
            '≈': '约等于',
            '×': '乘以',
            '÷': '除以',
            '±': '正负',
            '≥': '大于等于',
            '≤': '小于等于',
            '≠': '不等于',
            '∞': '无穷',
            '√': '平方根',
            '∑': '求和',
            '∏': '连乘',
            '∫': '积分',
            '∂': '偏导',
            '∇': '梯度',
            '∆': '变化量',
            '∈': '属于',
            '∉': '不属于',
            '⊂': '真子集',
            '⊆': '子集',
            '∪': '并集',
            '∩': '交集',
            '∅': '空集',
            '°C': '摄氏度',
            '°F': '华氏度',
            '%': '百分之',
            '‰': '千分之',
            '•': '，',
            '·': '点',
            '…': '等等',
            '—': '，',
            '–': '至',
            '"': '',
            '"': '',
            ''': '',
            ''': '',
            '「': '',
            '」': '',
            '『': '',
            '』': '',
        }
        
        # 列表序号词
        self.list_ordinals = [
            '第一', '第二', '第三', '第四', '第五',
            '第六', '第七', '第八', '第九', '第十',
            '第十一', '第十二', '第十三', '第十四', '第十五',
            '第十六', '第十七', '第十八', '第十九', '第二十',
        ]
    
    def calculate_article_hash(
        self,
        video_url: str = "",
        title: str = "",
        upload_date: str = ""
    ) -> str:
        """计算文章哈希值
        
        Args:
            video_url: 视频URL
            title: 标题
            upload_date: 上传日期
            
        Returns:
            16 字符的哈希字符串
        """
        content = f"{video_url}|{title}|{upload_date}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        return hash_obj.hexdigest()[:16]
    
    def extract_yaml_metadata(self, content: str) -> Tuple[dict, str]:
        """提取 YAML 元数据
        
        Args:
            content: Markdown 内容
            
        Returns:
            (元数据字典, 去除元数据后的内容)
        """
        metadata = {}
        remaining_content = content
        
        # 匹配 YAML front matter
        yaml_pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(yaml_pattern, content, re.DOTALL)
        
        if match:
            yaml_content = match.group(1)
            remaining_content = content[match.end():]
            
            # 简单解析 YAML（仅支持基本键值对）
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"\'')
        
        return metadata, remaining_content
    
    def extract_chinese_title(self, content: str) -> Tuple[str, str]:
        """提取中文标题（去除英文部分）
        
        Args:
            content: Markdown 内容
            
        Returns:
            (中文标题, 去除标题后的内容)
        """
        # 匹配一级标题
        title_pattern = r'^#\s+(.+?)$'
        match = re.search(title_pattern, content, re.MULTILINE)
        
        if not match:
            return "", content
        
        title_line = match.group(1)
        
        # 去除英文部分（假设格式为 "English Title 中文标题" 或 "中文标题 English Title"）
        # 优先保留中文
        chinese_part = re.findall(r'[\u4e00-\u9fa5]+[^\u4e00-\u9fa5]*[\u4e00-\u9fa5]*', title_line)
        
        if chinese_part:
            # 取最长的中文片段
            title_cn = max(chinese_part, key=len).strip()
        else:
            # 如果没有中文，保留整个标题
            title_cn = title_line.strip()
        
        # 移除标题行
        remaining_content = content[:match.start()] + content[match.end():]
        
        return title_cn, remaining_content
    
    def remove_toc_section(self, content: str) -> Tuple[str, bool]:
        """移除目录章节
        
        Args:
            content: Markdown 内容
            
        Returns:
            (处理后的内容, 是否移除了 TOC)
        """
        removed = False
        
        # 匹配"主要目录"或"目录"章节（从章节标题到下一个同级或更高级标题）
        # 匹配模式：### 主要目录 或 ### 目录 或 ### TOC
        patterns = [
            r'###\s*主要目录.*?(?=\n###[^#]|\Z)',  # ### 主要目录 到下一个 ### 或文件结尾
            r'###\s*目录.*?(?=\n###[^#]|\Z)',      # ### 目录
            r'###\s*Table of Contents.*?(?=\n###[^#]|\Z)',  # ### Table of Contents
            r'###\s*TOC.*?(?=\n###[^#]|\Z)',       # ### TOC
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
                content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
                removed = True
                logger.debug(f"移除了 TOC 章节")
        
        return content, removed
    
    def remove_insights_and_quotes(self, content: str) -> Tuple[str, list]:
        """移除洞见和金句章节
        
        Args:
            content: Markdown 内容
            
        Returns:
            (处理后的内容, 移除的章节列表)
        """
        removed_sections = []
        
        # 匹配洞见和金句章节（从文末开始）
        for section_pattern in self.remove_sections[3:]:  # 洞见和金句的模式
            pattern = rf'{section_pattern}.*?(?=\n###|\Z)'
            matches = list(re.finditer(pattern, content, re.DOTALL))
            
            if matches:
                # 移除最后一个匹配（通常在文末）
                last_match = matches[-1]
                section_title = re.search(r'###\s*(.+?)\n', last_match.group(0))
                if section_title:
                    removed_sections.append(section_title.group(1))
                
                content = content[:last_match.start()] + content[last_match.end():]
                logger.debug(f"移除了章节: {section_pattern}")
        
        return content, removed_sections
    
    def clean_markdown_syntax(self, content: str) -> str:
        """清理 Markdown 语法
        
        Args:
            content: Markdown 内容
            
        Returns:
            清理后的文本
        """
        # 1. 移除代码块
        content = re.sub(r'```[\s\S]*?```', '', content)
        
        # 2. 移除行内代码
        content = re.sub(r'`[^`]+`', '', content)
        
        # 3. 移除图片
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', content)
        
        # 4. 处理链接（保留文本）
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        
        # 5. 移除粗体和斜体标记
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        content = re.sub(r'__([^_]+)__', r'\1', content)
        content = re.sub(r'\*([^*]+)\*', r'\1', content)
        content = re.sub(r'_([^_]+)_', r'\1', content)
        
        # 6. 移除分隔线
        content = re.sub(r'^[-*_]{3,}\s*$', '', content, flags=re.MULTILINE)
        
        # 7. 移除引用标记
        content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
        
        return content
    
    def optimize_headings(self, content: str) -> str:
        """优化标题格式，增加停顿
        
        Args:
            content: 文本内容
            
        Returns:
            优化后的文本
        """
        # 一级标题后添加长停顿
        content = re.sub(r'^#\s+(.+?)$', r'\1。\n\n', content, flags=re.MULTILINE)
        
        # 二级标题后添加中等停顿
        content = re.sub(r'^##\s+(.+?)$', r'\1。\n', content, flags=re.MULTILINE)
        
        # 三级标题后添加短停顿
        content = re.sub(r'^###\s+(.+?)$', r'\1。', content, flags=re.MULTILINE)
        
        # 四级及以下标题（添加分号标记，后面的 optimize_lists 会识别并跳过）
        content = re.sub(r'^#{4,}\s+(.+?)$', r'\1；', content, flags=re.MULTILINE)
        
        return content
    
    def optimize_lists(self, content: str) -> str:
        """优化列表格式
        
        Args:
            content: 文本内容
            
        Returns:
            优化后的文本
        """
        lines = content.split('\n')
        result_lines = []
        list_counter = 0
        in_list = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 跳过已经处理过的标题（以句号或分号结尾）
            if stripped.endswith('。') or stripped.endswith('；'):
                # 这些是标题，不是列表项
                if in_list:
                    in_list = False
                    list_counter = 0
                result_lines.append(line)
                continue
            
            # 跳过以逗号结尾且没有列表标记的行（可能是标题或普通文本）
            if stripped.endswith('，') and not re.match(r'^\s*[-*+\d]', stripped):
                if in_list:
                    in_list = False
                    list_counter = 0
                result_lines.append(line)
                continue
            
            # 无序列表（只匹配以 - * + 开头的）
            unordered_match = re.match(r'^\s*[-*+]\s+(.+)$', line)
            if unordered_match:
                # 检查上一行是否为空行或文本（确认这是列表开始）
                if not in_list:
                    list_counter = 0
                    in_list = True
                
                ordinal = self.list_ordinals[list_counter] if list_counter < len(self.list_ordinals) else f"第{list_counter + 1}"
                result_lines.append(f"{ordinal}，{unordered_match.group(1)}；")
                list_counter += 1
                continue
            
            # 有序列表（但要排除已经处理过的标题）
            ordered_match = re.match(r'^\s*(\d+)\.\s+(.+)$', line)
            if ordered_match:
                content_part = ordered_match.group(2)
                
                # 检查是否是标题或单独的段落标题：
                # 1. 以句号或分号结尾
                # 2. 很长（超过 50 字符）
                # 3. 不在列表上下文中（上一行是空行或文本，下一行也是）
                is_likely_heading = (
                    content_part.endswith('。') or 
                    content_part.endswith('；') or 
                    len(content_part) > 50
                )
                
                # 检查上下文：如果不在列表中，且上一行不是列表项，可能是单独的标题
                if not in_list:
                    # 检查上一行
                    prev_line_empty_or_text = (i == 0 or 
                                               not lines[i-1].strip() or 
                                               not re.match(r'^\s*[-*+\d]', lines[i-1]))
                    # 检查下一行
                    next_line_empty_or_text = (i >= len(lines)-1 or 
                                               not lines[i+1].strip() or 
                                               not re.match(r'^\s*[-*+\d]', lines[i+1]))
                    
                    if is_likely_heading or (prev_line_empty_or_text and next_line_empty_or_text):
                        # 这是标题或单独的段落标题，不是列表项
                        result_lines.append(line)
                        continue
                
                # 如果在列表中但是明显是标题，也要跳过
                if in_list and is_likely_heading:
                    in_list = False
                    list_counter = 0
                    result_lines.append(line)
                    continue
                
                # 这是真正的列表项
                if not in_list:
                    list_counter = 0
                    in_list = True
                
                ordinal = self.list_ordinals[list_counter] if list_counter < len(self.list_ordinals) else f"第{list_counter + 1}"
                result_lines.append(f"{ordinal}，{content_part}；")
                list_counter += 1
                continue
            
            # 非列表行
            if in_list and line.strip():
                in_list = False
                list_counter = 0
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def replace_special_symbols(self, content: str) -> str:
        """替换特殊符号
        
        Args:
            content: 文本内容
            
        Returns:
            替换后的文本
        """
        # 先处理百分号（需要特殊处理，避免 "40%" 变成 "40百分之"）
        # 匹配 "数字%" 并转换为 "百分之数字"
        content = re.sub(r'(\d+)%', r'百分之\1', content)
        
        # 然后处理其他符号（排除百分号）
        for symbol, replacement in self.symbol_replacements.items():
            if symbol != '%':  # 跳过百分号，已经处理过了
                content = content.replace(symbol, replacement)
        
        return content
    
    def normalize_whitespace(self, content: str) -> str:
        """规范化空白字符
        
        Args:
            content: 文本内容
            
        Returns:
            规范化后的文本
        """
        # 移除连续的空行（保留段落间的单个空行）
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 移除行首行尾空白
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        # 移除多余的空格
        content = re.sub(r' {2,}', ' ', content)
        
        return content
    
    def validate_result(self, text: str) -> bool:
        """验证处理结果
        
        Args:
            text: 处理后的文本
            
        Returns:
            是否通过验证
        """
        # 检查文本长度
        if len(text) < 50:
            logger.warning("处理后文本过短")
            return False
        
        # 检查是否有中文
        if not re.search(r'[\u4e00-\u9fa5]', text):
            logger.warning("处理后文本不包含中文")
            return False
        
        # 检查是否还有 Markdown 语法残留
        if re.search(r'```|`|!\[.*?\]\(', text):
            logger.warning("处理后文本仍包含 Markdown 语法")
            return False
        
        return True
    
    def preprocess(
        self,
        markdown_content: str,
        video_url: str = "",
        title: str = "",
        upload_date: str = ""
    ) -> Optional[PreprocessingResult]:
        """预处理 Markdown 文章
        
        Args:
            markdown_content: Markdown 内容
            video_url: 视频 URL（用于计算哈希）
            title: 标题（用于计算哈希）
            upload_date: 上传日期（用于计算哈希）
            
        Returns:
            预处理结果，失败返回 None
        """
        try:
            original_length = len(markdown_content)
            sections_removed = []
            
            # 1. 提取 YAML 元数据
            metadata, content = self.extract_yaml_metadata(markdown_content)
            logger.debug(f"提取元数据: {metadata}")
            
            # 使用元数据中的信息（如果有）
            if not video_url:
                video_url = metadata.get('video_url', '')
            if not title:
                title = metadata.get('title', '')
            if not upload_date:
                upload_date = metadata.get('upload_date', '')
            
            # 2. 提取中文标题
            title_cn, content = self.extract_chinese_title(content)
            logger.debug(f"提取中文标题: {title_cn}")
            
            # 3. 移除目录
            content, toc_removed = self.remove_toc_section(content)
            if toc_removed:
                sections_removed.append('目录')
            
            # 4. 移除洞见和金句
            content, removed = self.remove_insights_and_quotes(content)
            sections_removed.extend(removed)
            
            # 5. 清理 Markdown 语法（只移除标记符号，不改变内容结构）
            content = self.clean_markdown_syntax(content)
            
            # 6. 移除标题标记（#），但保持原文格式
            content = re.sub(r'^#{1,6}\s+(.+?)$', r'\1', content, flags=re.MULTILINE)
            
            # 7. 清理多余空白
            content = re.sub(r'\n{3,}', '\n\n', content)
            lines = [line.strip() for line in content.split('\n')]
            content = '\n'.join(lines)
            content = re.sub(r' {2,}', ' ', content)
            
            # 10. 添加标题到开头
            if title_cn:
                content = f"{title_cn}。\n\n{content}"
            
            # 11. 验证结果
            if not self.validate_result(content):
                logger.error("文本验证失败")
                return None
            
            # 12. 计算文章哈希
            article_hash = self.calculate_article_hash(video_url, title, upload_date)
            
            processed_length = len(content)
            logger.info(
                f"预处理完成: 原文 {original_length} 字符 -> 处理后 {processed_length} 字符, "
                f"移除章节: {', '.join(sections_removed) if sections_removed else '无'}"
            )
            
            return PreprocessingResult(
                text=content,
                article_hash=article_hash,
                title_cn=title_cn,
                original_length=original_length,
                processed_length=processed_length,
                sections_removed=sections_removed
            )
            
        except Exception as e:
            logger.error(f"预处理失败: {e}", exc_info=True)
            return None
    
    def save_to_file(self, result: PreprocessingResult, output_dir: Path) -> Optional[Path]:
        """保存预处理结果到文件
        
        Args:
            result: 预处理结果
            output_dir: 输出目录
            
        Returns:
            保存的文件路径，失败返回 None
        """
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"{result.article_hash}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.text)
            
            logger.info(f"TTS 文本已保存到: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}", exc_info=True)
            return None
