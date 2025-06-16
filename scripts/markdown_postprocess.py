import argparse
import re
from pathlib import Path


def slugify(text: str) -> str:
    """将标题文本转换为与前端相同的 slug"""
    # 小写
    text = text.lower()
    # 移除所有非中英文字符、数字、空格、连字符的字符（与前端保持一致）
    text = re.sub(r"[^\w\u4e00-\u9fa5\s-]", "", text)
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

# 匹配标题行，例如 ### 标题
HEADING_RE = re.compile(r'^(#+)\s+(.*)')

# 识别大纲列表项：例如 "1.  **标题**"，尚未包含链接
OUTLINE_RE = re.compile(r'^(\s*\d+[\.)]\s+)(\*\*(.+?)\*\*)(.*)$')

# 定义左右标点符号
PUNCT_LEFT = """（(【『「"'"""
PUNCT_RIGHT = """）)】』」"'"""


def fix_quotes(line: str) -> str:
    """修复 **"文本"** 这种格式，使引号在粗体外侧"""
    def _replace(match: re.Match) -> str:
        left_quote = match.group(1)
        content = match.group(2)
        right_quote = match.group(3)
        return f"{left_quote}**{content}**{right_quote}"

    return QUOTE_BOLD_RE.sub(_replace, line)


def fix_internal_punct(line: str) -> str:
    """将位于粗体内部的首尾引号移到粗体外部（暂时不处理括号）"""

    def _move(match: re.Match):
        inner = match.group(1)
        # 只处理引号的情况，不处理括号
        if not any(c in inner for c in '""\''):
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


def collect_headings(lines):
    headings = {}
    for l in lines:
        m = HEADING_RE.match(l)
        if not m:
            continue
        text = m.group(2)
        # 去除 **
        text_plain = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        anchor = slugify(text_plain)
        headings[anchor] = True
    return headings


def fix_links(line: str, headings):
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
    """将未加链接的大纲列表项转为带锚点链接"""
    if LINK_RE.search(line):
        return line  # 已有链接
    m = OUTLINE_RE.match(line)
    if not m:
        return line

    prefix = m.group(1)  # "1.  " 
    bold = m.group(2)  # 包含 ** **
    title_text = m.group(3)  # 去掉 ** 的文字
    rest = m.group(4)

    slug = slugify(title_text)
    
    # 首先尝试直接匹配
    if slug in headings:
        linked = f"[{bold}](#{slug})"
        return f"{prefix}{linked}{rest}"
    
    # 如果直接匹配失败，尝试添加序号前缀
    # 从prefix中提取序号
    num_match = re.match(r'^\s*(\d+)', prefix)
    if num_match:
        num = num_match.group(1)
        slug_with_num = slugify(f"{num}. {title_text}")
        if slug_with_num in headings:
            linked = f"[{bold}](#{slug_with_num})"
            return f"{prefix}{linked}{rest}"
    
    return line  # 找不到对应标题，不替换


def process_file(path: Path):
    original = path.read_text(encoding="utf-8").splitlines(keepends=True)
    headings = collect_headings(original)

    new_lines = []
    for line in original:
        # 保留原始行的换行符
        line_content = line.rstrip('\n\r')
        line_ending = line[len(line_content):]
        
        # 处理行内容
        processed = line_content
        processed = fix_quotes(processed)
        processed = fix_internal_punct(processed)
        processed = fix_links(processed, headings)
        processed = fix_outline(processed, headings)
        
        # 重新加上换行符
        new_lines.append(processed + line_ending)

    path.write_text("".join(new_lines), encoding="utf-8")
    print(f"Processed {path}")


def main():
    parser = argparse.ArgumentParser(description="Post-process markdown files to fix bold quotes and anchors")
    parser.add_argument("targets", nargs="+", help="Markdown file(s) or directory(ies) to process")
    args = parser.parse_args()

    for tgt in args.targets:
        p = Path(tgt)
        if p.is_dir():
            for md in p.rglob("*.md"):
                process_file(md)
        elif p.is_file():
            process_file(p)
        else:
            print(f"Path not found: {p}")


if __name__ == "__main__":
    main() 