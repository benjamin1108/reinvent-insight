#!/usr/bin/env python3
"""
Visual HTML 转 Reveal.js 演示文稿工具

将 visual_worker 生成的 HTML 转换为可演示的 Reveal.js 幻灯片格式。

使用方式:
    python src/reinvent_insight/tools/visual_to_reveal.py
    python src/reinvent_insight/tools/visual_to_reveal.py <input_file>
    
功能:
    - 无参数: 自动遍历 output/visual/ 下所有 *_visual.html 文件并转换
    - 指定文件: 只转换指定文件
    - 输出目录: 项目根目录下的 out/ 目录
"""

import os
import sys
import argparse
from pathlib import Path
from bs4 import BeautifulSoup


def clean_html_content(soup_element):
    """清理 HTML 中的动画类，保留布局"""
    if not soup_element:
        return ""
    for tag in soup_element.find_all(True):
        if 'class' in tag.attrs:
            # 移除 fade-in 动画类
            tag['class'] = [
                c for c in tag['class'] 
                if 'fade-in' not in c and 'delay-' not in c
            ]
    return soup_element.decode_contents()


def extract_title(soup) -> str:
    """从 HTML 中提取标题"""
    # 尝试从 title 标签获取
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    
    # 尝试从 h1 获取
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)
    
    return "Visual Presentation"


def extract_brand_color(soup) -> str:
    """从 HTML 中提取品牌色"""
    # 尝试从 CSS 变量中提取
    for style in soup.find_all('style'):
        content = style.string or ""
        if '--brand-color:' in content:
            import re
            match = re.search(r'--brand-color:\s*(#[0-9a-fA-F]{6})', content)
            if match:
                return match.group(1)
    return "#4285F4"  # 默认 Google Blue


def generate_reveal_html(input_file: str, output_file: str) -> bool:
    """
    将 Visual HTML 转换为 Reveal.js 演示文稿
    
    Args:
        input_file: 输入的 Visual HTML 文件路径
        output_file: 输出的 Reveal.js HTML 文件路径
        
    Returns:
        是否转换成功
    """
    if not os.path.exists(input_file):
        print(f"❌ 错误：找不到文件 '{input_file}'")
        return False

    print(f"📖 正在读取 {input_file} ...")
    with open(input_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 提取元信息
    title = extract_title(soup)
    brand_color = extract_brand_color(soup)
    print(f"📝 标题: {title}")
    print(f"🎨 品牌色: {brand_color}")
    
    # --- 1. 提取原文件中的 CSS ---
    custom_styles = []
    for style in soup.find_all('style'):
        custom_styles.append(style.decode_contents())
    custom_css_block = "\n".join(custom_styles)

    # --- 2. 提取全局背景层 ---
    bg_layers = []
    if soup.body:
        for div in soup.body.find_all('div', recursive=False):
            classes = div.get('class', [])
            # 提取背景装饰层 (通常包含 fixed/absolute 且内容很少)
            if ('fixed' in classes or 'absolute' in classes) and len(div.get_text(strip=True)) < 20:
                bg_layers.append(str(div))
                
    print(f"✨ 提取到 {len(bg_layers)} 个背景层")

    slides = []

    # --- 3. 处理封面 ---
    header = soup.find('header')
    if header:
        content = clean_html_content(header)
        slide_html = f"""
        <section data-background-color="transparent">
            <div class="native-scroll-container">
                <div class="scale-container max-w-5xl mx-auto py-20 px-6 relative z-10">
                    {content}
                </div>
            </div>
        </section>
        """
        slides.append(slide_html)

    # --- 4. 处理章节 ---
    chapters = soup.find_all('section', id=lambda x: x and x.startswith('chapter-'))
    print(f"🔍 找到 {len(chapters)} 个章节")

    for chapter in chapters:
        content = clean_html_content(chapter)
        slide_html = f"""
        <section data-background-color="transparent">
            <div class="native-scroll-container">
                <div class="scale-container max-w-5xl mx-auto py-12 px-6 relative z-10">
                    {content}
                </div>
            </div>
        </section>
        """
        slides.append(slide_html)

    # --- 5. 处理结论/footer ---
    footer = soup.find('footer')
    if footer:
        # 提取核心洞见和金句部分
        for section in footer.find_all('section', class_='main-card'):
            content = clean_html_content(section)
            slide_html = f"""
            <section data-background-color="transparent">
                <div class="native-scroll-container">
                    <div class="scale-container max-w-5xl mx-auto py-12 px-6 relative z-10">
                        {content}
                    </div>
                </div>
            </section>
            """
            slides.append(slide_html)

    # --- 6. 组装最终 HTML ---
    final_html = f"""<!doctype html>
<html lang="zh-CN" class="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    
    <!-- Reveal.js -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.0.4/reveal.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.0.4/reset.min.css">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        'brand': '{brand_color}',
                        'tech-dark': '#0a0a0a',
                    }},
                    fontFamily: {{
                        mono: ['"Fira Code"', 'monospace'],
                        sans: ['Inter', 'system-ui', 'sans-serif'],
                    }}
                }}
            }},
            corePlugins: {{ preflight: false }}
        }}
    </script>

    <style>
        /* --- 原文件样式 --- */
        {custom_css_block}

        /* --- 全局黑底白字 --- */
        html, body {{
            background-color: #000000 !important;
            color: #e4e4e7 !important;
            width: 100%; height: 100%;
            overflow: hidden;
        }}

        /* --- 盒模型修复 --- */
        *, ::before, ::after {{
            box-sizing: border-box;
            border-width: 0;
            border-style: solid;
            border-color: #3f3f46;
        }}

        /* --- Reveal 容器透明 --- */
        .reveal {{
            background-color: transparent !important;
            width: 100vw !important; height: 100vh !important;
            z-index: 10;
        }}
        .reveal .slides {{
            text-align: left;
            width: 100% !important; height: 100% !important;
            inset: 0 !important; transform: none !important;
        }}
        .reveal .slides > section {{
            top: 0 !important; left: 0 !important;
            width: 100% !important; height: 100% !important;
            padding: 0 !important; margin: 0 !important;
            transform: none !important;
        }}

        /* --- 滚动容器 --- */
        .native-scroll-container {{
            width: 100%; height: 100%;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            overflow: hidden;
        }}
        
        /* --- 内容容器（用于缩放） --- */
        .scale-container {{
            transform-origin: top center;
            transition: transform 0.3s ease;
        }}

        /* --- 全局背景层 --- */
        #global-bg-layer {{
            position: fixed; top: 0; left: 0; 
            width: 100vw; height: 100vh;
            z-index: 0;
            pointer-events: none;
            background-color: #000000;
        }}
        
        /* --- 字体颜色修正 --- */
        h1, h2, h3, h4, h5, h6 {{ color: inherit !important; margin: 0; font-weight: inherit; }}
        
        /* --- 控制按钮样式 --- */
        .reveal .controls {{ color: {brand_color} !important; }}
        .reveal .progress {{ background: rgba(255,255,255,0.1); height: 4px; }}
        .reveal .progress span {{ background: {brand_color}; }}
    </style>
</head>
<body class="bg-black text-zinc-200 antialiased">
    
    <!-- 全局背景层 -->
    <div id="global-bg-layer">
        {"".join(bg_layers)}
    </div>

    <!-- Reveal.js 主体 -->
    <div class="reveal">
        <div class="slides">
            {"".join(slides)}
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.0.4/reveal.min.js"></script>
    <script>
        // 自动缩放每页内容以适配屏幕高度
        function scaleSlides() {{
            const viewportHeight = window.innerHeight;
            const slides = document.querySelectorAll('.scale-container');
            
            slides.forEach(container => {{
                // 重置缩放以获取真实高度
                container.style.transform = 'scale(1)';
                const contentHeight = container.scrollHeight;
                
                if (contentHeight > viewportHeight) {{
                    // 内容超出屏幕，需要缩小
                    const scale = (viewportHeight - 40) / contentHeight; // 留 40px 边距
                    container.style.transform = `scale(${{Math.max(scale, 0.5)}})`;
                }} else {{
                    container.style.transform = 'scale(1)';
                }}
            }});
        }}
        
        // 初始化 Reveal.js
        Reveal.initialize({{
            width: "100%", 
            height: "100%",
            margin: 0, 
            minScale: 1, 
            maxScale: 1,
            disableLayout: true,
            controls: true, 
            progress: true, 
            hash: true,
            transition: 'slide',
            mouseWheel: false,
            keyboard: {{
                27: null,  // 禁用 ESC 退出全屏
            }}
        }});
        
        // 页面加载后缩放
        Reveal.on('ready', scaleSlides);
        
        // 切换幻灯片后重新缩放
        Reveal.on('slidechanged', scaleSlides);
        
        // 窗口大小变化时重新缩放
        window.addEventListener('resize', scaleSlides);
    </script>
</body>
</html>
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"✅ 转换完成！")
    print(f"📄 输出文件: {output_file}")
    print(f"📊 共 {len(slides)} 页幻灯片")
    return True


def get_project_root() -> Path:
    """获取项目根目录"""
    # 从当前文件位置向上找到项目根目录
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / 'pyproject.toml').exists():
            return parent
    # 回退到当前工作目录
    return Path.cwd()


def find_visual_files(visual_dir: Path) -> list:
    """查找所有 visual HTML 文件"""
    patterns = ['*_visual.html', '*visual*.html']
    files = []
    for pattern in patterns:
        files.extend(visual_dir.glob(pattern))
    # 去重并排除已转换的文件
    unique_files = []
    seen = set()
    for f in files:
        if f.name not in seen and '_reveal' not in f.name:
            seen.add(f.name)
            unique_files.append(f)
    return sorted(unique_files)


def main():
    parser = argparse.ArgumentParser(
        description="将 Visual HTML 转换为 Reveal.js 演示文稿",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                               # 自动遍历并转换所有 visual HTML
  %(prog)s input.html                    # 只转换指定文件
        """
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default=None,
        help="输入的 Visual HTML 文件路径（可选，不指定则自动遍历）"
    )
    
    args = parser.parse_args()
    
    project_root = get_project_root()
    out_dir = project_root / 'out'
    out_dir.mkdir(exist_ok=True)
    
    print(f"📁 项目根目录: {project_root}")
    print(f"📂 输出目录: {out_dir}")
    
    if args.input_file:
        # 单文件模式
        input_path = Path(args.input_file)
        output_path = out_dir / f"{input_path.stem}_reveal.html"
        success = generate_reveal_html(str(input_path), str(output_path))
        sys.exit(0 if success else 1)
    else:
        # 批量模式 - 搜索多个可能的目录
        possible_dirs = [
            project_root / 'downloads' / 'summaries',
            project_root / 'output' / 'visual',
            project_root / 'downloads',
        ]
        
        visual_dir = None
        for d in possible_dirs:
            if d.exists():
                visual_dir = d
                break
        
        if not visual_dir:
            print(f"❌ 未找到 visual 目录")
            sys.exit(1)
        
        files = find_visual_files(visual_dir)
        if not files:
            print(f"⚠️  未找到 visual HTML 文件")
            sys.exit(0)
        
        print(f"\n🔍 找到 {len(files)} 个 visual HTML 文件:\n")
        
        success_count = 0
        for f in files:
            print(f"{'='*60}")
            output_path = out_dir / f"{f.stem}_reveal.html"
            if generate_reveal_html(str(f), str(output_path)):
                success_count += 1
            print()
        
        print(f"{'='*60}")
        print(f"\n🎉 完成！成功转换 {success_count}/{len(files)} 个文件")
        print(f"📂 输出目录: {out_dir}")
        sys.exit(0 if success_count == len(files) else 1)


if __name__ == "__main__":
    main()
