import argparse
import re
from pathlib import Path


def slugify(text: str) -> str:
    """将标题文本转换为与前端相同的 slug"""
    # 小写
    text = text.lower()
    # 移除所有非 ascii 小写字母/数字、中文、空格、连字符的字符（保持与前端一致，排除上标²等）
    text = re.sub(r"[^a-z0-9\u4e00-\u9fa5\s-]", "", text)
    # 替换空白为连字符
    text = re.sub(r"\s+", "-", text)
    # 移除重复连字符
    text = re.sub(r"-+", "-", text)
    # 去除首尾连字符
    text = text.strip("-")
    return text


# 匹配 **"文本"** 或 **"文本"**（引号在粗体内需要移动）
QUOTE_BOLD_RE = re.compile(r'\*\*([""])(.+?)([""])\*\*')

# 通用粗体匹配
BOLD_RE = re.compile(r'\*\*(.+?)\*\*')

# 匹配 md 链接 [text](#anchor)
LINK_RE = re.compile(r'\[(.+?)\]\(#([^)]+)\)')

# 匹配各种标题行格式
HEADING_RE = re.compile(r'^(#+)\s+(.*)')

# 识别大纲列表项：例如 "1.  **标题**"，尚未包含链接
OUTLINE_RE = re.compile(r'^(\s*\d+[\.)]\s+)(\*\*(.+?)\*\*)(.*)$')

# 标准化章节标题格式 
CHAPTER_TITLE_RE = re.compile(r'^(#+)\s*\*?\*?(\d+)\.?\s*(.+?)\*?\*?\s*$')

# 匹配引言、大纲索引等特殊章节
SPECIAL_SECTIONS = ['引言', '大纲索引', '金句', '原声引用', '洞见延伸', '参考索引']


def fix_quotes(line: str) -> str:
    """修复 **"文本"** 这种格式，使引号在粗体外侧"""
    def _replace(match: re.Match) -> str:
        left_quote = match.group(1)
        content = match.group(2)
        right_quote = match.group(3)
        return f"{left_quote}**{content}**{right_quote}"

    return QUOTE_BOLD_RE.sub(_replace, line)


def fix_internal_punct(line: str) -> str:
    """将位于粗体内部的首尾引号移到粗体外部（保守处理）"""
    def _move(match: re.Match):
        inner = match.group(1)
        # 只处理引号的情况，不处理括号
        if not any(c in inner for c in '""\'\''):
            return match.group(0)
        
        prefix = ""
        suffix = ""
        QUOTES_LEFT = """'"""
        QUOTES_RIGHT = """'"""
        
        # 移动左侧标点
        while inner and inner[0] in QUOTES_LEFT:
            prefix += inner[0]
            inner = inner[1:]
        # 移动右侧标点
        while inner and inner[-1] in QUOTES_RIGHT:
            suffix = inner[-1] + suffix
            inner = inner[:-1]
        
        # 如果没有发生任何移动，返回原始内容
        if not prefix and not suffix:
            return match.group(0)
            
        return f"{prefix}**{inner}**{suffix}"

    return BOLD_RE.sub(_move, line)


def standardize_headings(line: str) -> str:
    """标准化标题格式"""
    # 处理章节标题
    chapter_match = CHAPTER_TITLE_RE.match(line)
    if chapter_match:
        level = chapter_match.group(1)
        num = chapter_match.group(2)
        title = chapter_match.group(3).strip()
        # 确保章节标题格式为: ### **1. 标题**
        return f"### **{num}. {title}**"
    
    # 处理其他标题格式
    heading_match = HEADING_RE.match(line)
    if heading_match:
        level = heading_match.group(1)
        content = heading_match.group(2).strip()
        
        # 特殊章节标题格式化
        for section in SPECIAL_SECTIONS:
            if section in content:
                # 确保特殊章节使用 ### **章节名** 格式
                if level in ['##', '###']:
                    # 处理金句&原声引用等组合标题
                    if '&' in content and ('金句' in content or '原声' in content):
                        return f"### **金句 & 原声引用**"
                    elif '金句' in content:
                        return f"### **金句 & 原声引用**"
                    elif '洞见' in content:
                        return f"### **洞见延伸**"
                    elif '参考' in content:
                        return f"### **参考索引**"
                    else:
                        clean_content = content.strip('*').strip()
                        return f"### **{clean_content}**"
                break
        
        # 小标题格式化（#### **标题**）
        if level == '####':
            if not content.startswith('**') or not content.endswith('**'):
                clean_content = content.strip('*').strip()
                return f"#### **{clean_content}**"
    
    return line


def collect_headings(lines):
    """收集所有标题，生成slug映射"""
    headings = {}
    for line in lines:
        # 先标准化标题格式再处理
        normalized_line = standardize_headings(line)
        m = HEADING_RE.match(normalized_line)
        if not m:
            continue
        text = m.group(2)
        # 去除 **
        text_plain = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        anchor = slugify(text_plain)
        headings[anchor] = True
    return headings


def fix_links(line: str, headings):
    """修复链接锚点"""
    def _link_replace(match: re.Match):
        text = match.group(1)
        anchor = match.group(2)
        # 去除内部强调
        text_plain = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        new_anchor = slugify(text_plain)
        if new_anchor in headings and new_anchor != anchor:
            return f"[{text}](#{new_anchor})"
        return match.group(0)

    return LINK_RE.sub(_link_replace, line)


def fix_outline(line: str, headings):
    """将未加链接的大纲列表项转为带锚点链接，并移除多余粗体"""
    # 如果已存在链接，仍可能需要去掉粗体并规范间距
    if LINK_RE.search(line):
        return line  # 交由后续 normalize_outline_item 处理
    m = OUTLINE_RE.match(line)
    if not m:
        return line

    prefix = m.group(1)  # "1.  " 
    # m.group(2) 是包含 ** ** 的粗体版本，我们改为使用不带粗体的文字
    title_text = m.group(3)  # 去掉 ** 的文字
    rest = m.group(4)

    # 从prefix中提取序号
    num_match = re.match(r'^\s*(\d+)', prefix)
    if num_match:
        num = num_match.group(1)
        # 构造完整的标题文本，包含序号但没有空格（匹配实际标题格式）
        full_title = f"{num}.{title_text}"
        slug = slugify(full_title)
        # 检查 slug
        if slug in headings:
            link_text = title_text  # 不使用粗体
            linked = f"[{link_text}](#{slug})"
            return f"{num}. {linked}{rest}"

    # 尝试不带序号的 slug
    slug = slugify(title_text)
    if slug in headings:
        link_text = title_text
        linked = f"[{link_text}](#{slug})"
        # 使用 prefix "1." 后面标准一个空格
        num_match = re.match(r'^\s*(\d+)', prefix)
        num_part = num_match.group(1) if num_match else prefix.strip()
        return f"{num_part}. {linked}{rest}"

    return line  # 找不到对应的标题


def normalize_outline_item(line: str) -> str:
    """规范大纲索引单行格式：去除粗体，保证数字后只有一个空格"""
    # 匹配诸如 "1.  [**标题**](#slug)" 或 "1. [标题](#slug)"
    m = re.match(r'^(\s*)(\d+)\.\s+\[(.*?)\]\(#([^)]+)\)(.*)$', line)
    if not m:
        return line

    indent = m.group(1)
    num = m.group(2)
    link_text = m.group(3)
    anchor = m.group(4)
    tail = m.group(5)

    # 移除粗体星号
    link_text = re.sub(r'^\*\*(.+?)\*\*$', r'\1', link_text)
    # 再次移除可能存在的粗体内部星号
    link_text = re.sub(r'\*\*(.+?)\*\*', r'\1', link_text)

    # 重新生成 slug，确保包含章节号，避免遗漏数字或特殊字符问题
    new_slug = slugify(f"{num}. {link_text}")
    return f"{indent}{num}. [{link_text}](#{new_slug}){tail}"


def standardize_outline_section(lines, start_idx):
    """标准化大纲索引部分的格式"""
    result = []
    i = start_idx
    
    # 添加标准化的大纲索引标题
    result.append("### **大纲索引**\n")
    i += 1
    
    # 跳过空行
    while i < len(lines) and lines[i].strip() == '':
        result.append(lines[i])
        i += 1
    
    # 处理大纲项
    while i < len(lines):
        line = lines[i]
        # 如果遇到下一个章节，停止
        if re.match(r'^#{1,3}\s+', line):
            break
        # 如果是空行，保留
        if line.strip() == '':
            result.append(line)
            i += 1
            continue
        # 如果是大纲项，处理格式
        if re.match(r'^\s*\d+\.\s+', line):
            result.append(line)
        else:
            result.append(line)
        i += 1
    
    return result, i


def clean_markdown_artifacts(line: str) -> str:
    """清理大模型幻觉产生的markdown格式问题"""
    # 移除多余的星号
    line = re.sub(r'\*{3,}', '**', line)
    
    # 清理不正确的引用格式
    line = re.sub(r'^>\s*\*\*', '> **', line)
    
    # 清理列表项格式
    line = re.sub(r'^(\s*)-\s*\*\*(.+?)\*\*\s*:', r'\1- **\2**:', line)
    
    # 标准化特殊标题格式
    line = re.sub(r'^#+\s*\*\*引言\*\*\s*$', '### **引言**', line)
    line = re.sub(r'^#+\s*引言\s*$', '### **引言**', line)
    line = re.sub(r'^#+\s*\*\*大纲索引\*\*\s*$', '### **大纲索引**', line)
    line = re.sub(r'^#+\s*大纲索引\s*$', '### **大纲索引**', line)
    
    # 清理多余的空格
    line = re.sub(r'\s+$', '', line)  # 去除行尾空格
    line = re.sub(r'^\s*#+\s+', lambda m: re.sub(r'\s+', ' ', m.group(0)), line)  # 标题格式
    
    # 清理引用中的格式问题
    line = re.sub(r'^>\s+>', '> ', line)
    
    return line


def fix_content_structure(lines):
    """修复内容结构问题"""
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip('\n\r')
        
        # 检查是否是需要特殊处理的章节
        if re.match(r'^#+\s*(大纲索引|引言)', line):
            # 标准化标题
            if '大纲索引' in line:
                result.append('### **大纲索引**\n')
            elif '引言' in line:
                result.append('### **引言**\n')
            i += 1
            continue
        
        # 处理金句部分的多种变体
        if re.match(r'^#+\s*(金句|原声|引用)', line):
            result.append('### **金句 & 原声引用**\n')
            i += 1
            continue
            
        # 处理洞见延伸的多种变体  
        if re.match(r'^#+\s*(洞见|延伸)', line):
            result.append('### **洞见延伸**\n')
            i += 1
            continue
            
        # 处理参考索引
        if re.match(r'^#+\s*(参考|索引)', line):
            result.append('### **参考索引**\n')
            i += 1
            continue
        
        result.append(lines[i])
        i += 1
    
    return result


def fix_bold_spacing(line: str) -> str:
    """确保粗体标记 ** 与中文/英文单词之间至少有一个空格。避免 ** 被原样渲染。"""
    # 在左侧缺失空格的情况插入空格：汉字/字母/数字紧邻 **
    line = re.sub(r'([\u4e00-\u9fa5A-Za-z0-9])\*\*(\S)', r'\1 **\2', line)
    # 在右侧缺失空格的情况插入空格：** 紧邻 汉字/字母/数字
    line = re.sub(r'(\S)\*\*([\u4e00-\u9fa5A-Za-z0-9])', r'\1** \2', line)
    return line


def process_file(path: Path):
    """处理单个markdown文件"""
    original = path.read_text(encoding="utf-8").splitlines(keepends=True)
    
    # 第一遍：修复内容结构
    structured_lines = fix_content_structure(original)
    
    # 第二遍：标准化标题格式，用于正确收集headings
    normalized_lines = []
    for line in structured_lines:
        line_content = line.rstrip('\n\r')
        processed = standardize_headings(line_content)
        processed = clean_markdown_artifacts(processed)
        normalized_lines.append(processed)
    
    # 收集标题信息
    headings = collect_headings(normalized_lines)
    
    # 第三遍：完整处理
    new_lines = []
    for i, line in enumerate(structured_lines):
        # 保留原始行的换行符
        line_content = line.rstrip('\n\r')
        line_ending = line[len(line_content):]
        
        # 处理行内容
        processed = line_content
        processed = standardize_headings(processed)
        processed = clean_markdown_artifacts(processed)
        processed = fix_quotes(processed)
        processed = fix_internal_punct(processed)
        processed = fix_bold_spacing(processed)
        processed = fix_links(processed, headings)
        processed = fix_outline(processed, headings)
        processed = normalize_outline_item(processed)
        
        # 重新加上换行符
        new_lines.append(processed + line_ending)

    path.write_text("".join(new_lines), encoding="utf-8")
    print(f"Processed {path}")


def main():
    parser = argparse.ArgumentParser(description="Post-process markdown files to standardize format and fix issues")
    parser.add_argument("targets", nargs="+", help="Markdown file(s) or directory(ies) to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    args = parser.parse_args()

    for tgt in args.targets:
        p = Path(tgt)
        if p.is_dir():
            for md in p.rglob("*.md"):
                if args.dry_run:
                    print(f"Would process: {md}")
                else:
                    process_file(md)
        elif p.is_file():
            if args.dry_run:
                print(f"Would process: {p}")
            else:
                process_file(p)
        else:
            print(f"Path not found: {p}")


if __name__ == "__main__":
    main() 