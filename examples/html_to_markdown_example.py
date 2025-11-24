"""
HTML to Markdown Converter 使用示例

演示如何使用HTML到Markdown转换器。
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reinvent_insight.html_to_markdown import HTMLToMarkdownConverter


# 示例HTML
EXAMPLE_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>人工智能的未来发展</title>
    <script>
        // 这些JavaScript代码会被移除
        console.log('tracking code');
    </script>
    <style>
        /* 这些CSS样式会被移除 */
        .article { color: #333; }
    </style>
</head>
<body>
    <!-- 导航菜单 - 会被LLM过滤 -->
    <nav>
        <ul>
            <li><a href="/">首页</a></li>
            <li><a href="/about">关于</a></li>
        </ul>
    </nav>
    
    <!-- 主要内容 -->
    <article>
        <h1>人工智能的未来发展</h1>
        
        <div class="meta">
            <span class="author">作者：张三</span>
            <span class="date">2024-01-15</span>
        </div>
        
        <p>人工智能（AI）正在以前所未有的速度改变我们的世界。从自动驾驶汽车到智能助手，AI技术已经渗透到我们生活的方方面面。</p>
        
        <img src="/images/ai-future.jpg" alt="AI未来示意图" />
        
        <h2>技术突破</h2>
        
        <p>近年来，深度学习和神经网络技术取得了突破性进展。大型语言模型如GPT系列展示了令人惊叹的能力。</p>
        
        <h3>主要进展包括：</h3>
        <ul>
            <li>自然语言处理能力大幅提升</li>
            <li>计算机视觉识别准确率接近人类水平</li>
            <li>强化学习在复杂决策中的应用</li>
        </ul>
        
        <h2>应用场景</h2>
        
        <p>AI技术正在多个领域发挥重要作用：</p>
        
        <table>
            <tr>
                <th>领域</th>
                <th>应用</th>
            </tr>
            <tr>
                <td>医疗</td>
                <td>疾病诊断、药物研发</td>
            </tr>
            <tr>
                <td>金融</td>
                <td>风险评估、智能投顾</td>
            </tr>
            <tr>
                <td>教育</td>
                <td>个性化学习、智能辅导</td>
            </tr>
        </table>
        
        <img src="/images/ai-applications.jpg" alt="AI应用场景" />
        
        <h2>未来展望</h2>
        
        <p>展望未来，AI技术将继续快速发展。我们期待看到更多创新应用，同时也需要关注AI伦理和安全问题。</p>
        
        <blockquote>
            <p>"人工智能是我们这个时代最重要的技术之一。" - 某位专家</p>
        </blockquote>
    </article>
    
    <!-- 侧边栏广告 - 会被LLM过滤 -->
    <aside class="sidebar">
        <div class="ad">
            <h3>推广内容</h3>
            <p>购买我们的产品...</p>
        </div>
    </aside>
    
    <!-- 页脚 - 会被LLM过滤 -->
    <footer>
        <p>&copy; 2024 示例网站. 保留所有权利。</p>
    </footer>
</body>
</html>
"""


async def example_basic():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用")
    print("=" * 60)
    
    # 创建转换器
    converter = HTMLToMarkdownConverter()
    
    # 转换HTML
    result = await converter.convert_from_string(
        EXAMPLE_HTML,
        base_url="https://example.com"
    )
    
    # 打印结果
    print(f"\n标题: {result.content.title}")
    print(f"内容长度: {len(result.content.content)} 字符")
    print(f"图片数量: {len(result.content.images)}")
    print(f"元数据: {result.content.metadata}")
    
    print("\n生成的Markdown:")
    print("-" * 60)
    print(result.markdown[:500] + "..." if len(result.markdown) > 500 else result.markdown)
    print("-" * 60)


async def example_save_to_file():
    """保存到文件示例"""
    print("\n" + "=" * 60)
    print("示例2: 保存到文件")
    print("=" * 60)
    
    converter = HTMLToMarkdownConverter()
    
    # 转换并保存
    output_path = "downloads/summaries/example_article.md"
    result = await converter.convert_from_string(
        EXAMPLE_HTML,
        output_path=output_path,
        base_url="https://example.com"
    )
    
    print(f"\n✓ Markdown已保存到: {output_path}")
    print(f"  文件大小: {len(result.markdown)} 字节")


async def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("示例3: 错误处理")
    print("=" * 60)
    
    from src.reinvent_insight.html_to_markdown import (
        ContentExtractionError,
        HTMLParseError
    )
    
    converter = HTMLToMarkdownConverter()
    
    # 测试空HTML
    try:
        result = await converter.convert_from_string("")
    except HTMLParseError as e:
        print(f"\n✓ 正确捕获HTMLParseError: {e}")
    
    # 测试无内容HTML
    empty_html = "<html><body></body></html>"
    try:
        result = await converter.convert_from_string(empty_html)
    except ContentExtractionError as e:
        print(f"✓ 正确捕获ContentExtractionError: {e}")


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("HTML to Markdown Converter - 使用示例")
    print("=" * 60)
    
    try:
        # 示例1: 基本使用
        await example_basic()
        
        # 示例2: 保存到文件
        await example_save_to_file()
        
        # 示例3: 错误处理
        await example_error_handling()
        
        print("\n" + "=" * 60)
        print("✓ 所有示例运行完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
