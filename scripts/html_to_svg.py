#!/usr/bin/env python3
"""
HTML to SVG 转换脚本

使用 Playwright 将 HTML 文件转换为 SVG 格式。
SVG 中嵌入 base64 编码的 PNG 图像，保证高保真渲染。

用法:
    python scripts/html_to_svg.py <input.html> [output.svg]
    python scripts/html_to_svg.py <input.html> --width 1200 --scale 2
    
示例:
    python scripts/html_to_svg.py downloads/summaries/article_visual.html
    python scripts/html_to_svg.py page.html output.svg --width 1400 --scale 1.5
"""

import argparse
import asyncio
import base64
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("错误: 请先安装 playwright")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)


async def html_to_svg(
    input_path: str,
    output_path: str | None = None,
    width: int = 1200,
    scale: float = 2.0,
    full_page: bool = True,
) -> str:
    """
    将 HTML 文件转换为 SVG
    
    Args:
        input_path: 输入 HTML 文件路径
        output_path: 输出 SVG 文件路径（可选，默认同名 .svg）
        width: 视口宽度（像素）
        scale: 缩放比例（用于高清截图）
        full_page: 是否截取完整页面
        
    Returns:
        输出文件路径
    """
    input_file = Path(input_path).resolve()
    
    if not input_file.exists():
        raise FileNotFoundError(f"文件不存在: {input_file}")
    
    if not input_file.suffix.lower() in ['.html', '.htm']:
        raise ValueError(f"不是 HTML 文件: {input_file}")
    
    # 确定输出路径
    if output_path:
        output_file = Path(output_path).resolve()
    else:
        output_file = input_file.with_suffix('.svg')
    
    print(f"📄 输入文件: {input_file}")
    print(f"📐 视口宽度: {width}px, 缩放: {scale}x")
    
    async with async_playwright() as p:
        # 启动浏览器
        print("🚀 启动浏览器...")
        browser = await p.chromium.launch()
        
        # 创建页面，设置视口
        page = await browser.new_page(
            viewport={'width': width, 'height': 800},
            device_scale_factor=scale
        )
        
        # 加载 HTML 文件
        print("📖 加载 HTML...")
        await page.goto(f'file://{input_file}', wait_until='networkidle')
        
        # 等待动画完成（fade-in-up 等）
        await page.wait_for_timeout(1000)
        
        # 获取页面实际尺寸
        dimensions = await page.evaluate('''() => ({
            width: Math.max(
                document.body.scrollWidth,
                document.documentElement.scrollWidth
            ),
            height: Math.max(
                document.body.scrollHeight,
                document.documentElement.scrollHeight
            )
        })''')
        
        page_width = dimensions['width']
        page_height = dimensions['height']
        print(f"📏 页面尺寸: {page_width} x {page_height}px")
        
        # 调整视口高度以匹配内容
        await page.set_viewport_size({
            'width': width,
            'height': page_height
        })
        
        # 截图为 PNG
        print("📸 截取页面...")
        png_bytes = await page.screenshot(
            full_page=full_page,
            type='png'
        )
        
        await browser.close()
    
    # 将 PNG 转为 base64
    png_base64 = base64.b64encode(png_bytes).decode('utf-8')
    
    # 计算实际图像尺寸（考虑缩放）
    img_width = int(page_width * scale)
    img_height = int(page_height * scale)
    
    # 生成 SVG（使用原始尺寸，图像会自动缩放）
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{page_width}" 
     height="{page_height}"
     viewBox="0 0 {page_width} {page_height}">
  <title>Generated from {input_file.name}</title>
  <image 
    width="{page_width}" 
    height="{page_height}"
    xlink:href="data:image/png;base64,{png_base64}"
    preserveAspectRatio="xMidYMid meet"/>
</svg>
'''
    
    # 写入文件
    output_file.write_text(svg_content, encoding='utf-8')
    
    # 统计信息
    svg_size = output_file.stat().st_size
    svg_size_mb = svg_size / (1024 * 1024)
    
    print(f"✅ 转换完成!")
    print(f"📁 输出文件: {output_file}")
    print(f"📊 文件大小: {svg_size_mb:.2f} MB")
    
    return str(output_file)


async def html_to_png(
    input_path: str,
    output_path: str | None = None,
    width: int = 1200,
    scale: float = 2.0,
) -> str:
    """
    将 HTML 文件转换为 PNG（额外提供）
    """
    input_file = Path(input_path).resolve()
    
    if not input_file.exists():
        raise FileNotFoundError(f"文件不存在: {input_file}")
    
    if output_path:
        output_file = Path(output_path).resolve()
    else:
        output_file = input_file.with_suffix('.png')
    
    print(f"📄 输入文件: {input_file}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={'width': width, 'height': 800},
            device_scale_factor=scale
        )
        
        await page.goto(f'file://{input_file}', wait_until='networkidle')
        await page.wait_for_timeout(1000)
        
        await page.screenshot(path=str(output_file), full_page=True, type='png')
        await browser.close()
    
    print(f"✅ PNG 输出: {output_file}")
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description='HTML to SVG 转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s article.html                    # 输出 article.svg
  %(prog)s article.html output.svg         # 指定输出路径
  %(prog)s article.html --width 1400       # 自定义宽度
  %(prog)s article.html --scale 3          # 高清 3x 缩放
  %(prog)s article.html --png              # 输出 PNG 格式
        '''
    )
    
    parser.add_argument('input', help='输入 HTML 文件路径')
    parser.add_argument('output', nargs='?', help='输出文件路径（可选）')
    parser.add_argument('--width', type=int, default=1200, help='视口宽度，默认 1200')
    parser.add_argument('--scale', type=float, default=2.0, help='缩放比例，默认 2.0')
    parser.add_argument('--png', action='store_true', help='输出 PNG 而非 SVG')
    
    args = parser.parse_args()
    
    try:
        if args.png:
            output = args.output
            if output and not output.endswith('.png'):
                output = output.rsplit('.', 1)[0] + '.png'
            asyncio.run(html_to_png(
                args.input,
                output,
                width=args.width,
                scale=args.scale
            ))
        else:
            asyncio.run(html_to_svg(
                args.input,
                args.output,
                width=args.width,
                scale=args.scale
            ))
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
