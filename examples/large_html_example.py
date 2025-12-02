"""
处理大型 HTML 文件示例

演示如何使用 html_to_markdown 处理 5MB+ 的大型 HTML 文件。
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reinvent_insight.html_to_markdown import HTMLToMarkdownConverter


async def process_large_html_file(html_path: str, output_path: str = None):
    """处理大型 HTML 文件
    
    Args:
        html_path: HTML 文件路径
        output_path: 输出 Markdown 路径（可选）
    """
    html_path = Path(html_path)
    
    if not html_path.exists():
        print(f"❌ 文件不存在: {html_path}")
        return
    
    # 获取文件大小
    file_size = html_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    
    print("=" * 80)
    print(f"📄 处理大型 HTML 文件")
    print("=" * 80)
    print(f"文件路径: {html_path}")
    print(f"文件大小: {file_size_mb:.2f} MB ({file_size:,} bytes)")
    print()
    
    # 确定输出路径
    if not output_path:
        output_path = html_path.with_suffix('.md')
    
    print(f"输出路径: {output_path}")
    print()
    
    # 创建转换器（启用调试模式）
    print("🔧 创建转换器（调试模式已启用）...")
    converter = HTMLToMarkdownConverter(debug=True)
    
    try:
        print("⚙️  开始转换...")
        print("-" * 80)
        
        # 转换
        result = await converter.convert_from_file(
            html_path,
            output_path=output_path,
            base_url="https://example.com"  # 根据实际情况修改
        )
        
        print("-" * 80)
        print()
        print("✅ 转换完成！")
        print()
        
        # 显示结果统计
        print("📊 转换结果统计:")
        print(f"  • 标题: {result.content.title}")
        print(f"  • 正文长度: {len(result.content.content):,} 字符")
        print(f"  • Markdown 大小: {len(result.markdown):,} 字符")
        print(f"  • 图片数量: {len(result.content.images)}")
        
        if result.content.metadata:
            print(f"  • 元数据: {result.content.metadata}")
        
        print()
        print(f"💾 Markdown 已保存到: {output_path}")
        
        # 如果启用了调试模式，提示查看调试文件
        debug_dir = Path(output_path).parent / "debug"
        if debug_dir.exists():
            print()
            print(f"🔍 调试文件位于: {debug_dir}")
            print("   包含:")
            print("   - 原始 HTML")
            print("   - 预处理后的 HTML")
            print("   - 各分段的 HTML、提取结果、Markdown")
            print("   - 合并后的最终内容")
        
        # 显示前 500 字符的预览
        print()
        print("📖 内容预览 (前 500 字符):")
        print("-" * 80)
        preview = result.markdown[:500]
        print(preview)
        if len(result.markdown) > 500:
            print("...")
        print("-" * 80)
        
    except Exception as e:
        print()
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()


async def process_large_html_string():
    """演示处理大型 HTML 字符串"""
    print("=" * 80)
    print("📝 处理大型 HTML 字符串示例")
    print("=" * 80)
    print()
    
    # 生成一个大型 HTML（模拟长文章）
    print("🔨 生成模拟大型 HTML...")
    
    html_parts = ['<html><body><article>']
    html_parts.append('<h1>这是一篇非常长的技术文章</h1>')
    
    # 添加 100 个段落
    for i in range(100):
        html_parts.append(f'<h2>第 {i+1} 章节</h2>')
        html_parts.append(f'<p>这是第 {i+1} 个段落的内容。' + '内容详情... ' * 100 + '</p>')
        
        # 每 10 段添加一张图片
        if i % 10 == 0:
            html_parts.append(f'<img src="/images/image_{i}.jpg" alt="图片 {i}" />')
    
    html_parts.append('</article></body></html>')
    large_html = ''.join(html_parts)
    
    html_size_mb = len(large_html) / (1024 * 1024)
    print(f"生成的 HTML 大小: {html_size_mb:.2f} MB ({len(large_html):,} 字符)")
    print()
    
    # 转换
    converter = HTMLToMarkdownConverter(debug=False)
    
    print("⚙️  开始转换...")
    try:
        result = await converter.convert_from_string(
            large_html,
            base_url="https://example.com"
        )
        
        print("✅ 转换完成！")
        print()
        print("📊 转换结果:")
        print(f"  • 标题: {result.content.title}")
        print(f"  • 正文长度: {len(result.content.content):,} 字符")
        print(f"  • 图片数量: {len(result.content.images)}")
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="处理大型 HTML 文件")
    parser.add_argument(
        'html_file',
        nargs='?',
        help='HTML 文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出 Markdown 文件路径'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='运行演示（生成模拟大 HTML）'
    )
    
    args = parser.parse_args()
    
    if args.demo:
        # 运行演示
        await process_large_html_string()
    elif args.html_file:
        # 处理指定文件
        await process_large_html_file(args.html_file, args.output)
    else:
        # 显示帮助
        print("大型 HTML 文件转换工具")
        print()
        print("用法:")
        print("  1. 处理文件:")
        print("     python large_html_example.py <html_file> [-o output.md]")
        print()
        print("  2. 运行演示:")
        print("     python large_html_example.py --demo")
        print()
        print("示例:")
        print("  python large_html_example.py article.html")
        print("  python large_html_example.py article.html -o output.md")
        print("  python large_html_example.py --demo")


if __name__ == "__main__":
    asyncio.run(main())
