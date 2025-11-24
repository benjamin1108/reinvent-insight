"""
手动测试脚本 - HTML to Markdown Converter

不依赖pytest，直接运行测试。
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """测试模块导入"""
    print("测试1: 模块导入...")
    try:
        from src.reinvent_insight.html_to_markdown import (
            HTMLToMarkdownConverter,
            ExtractedContent,
            ImageInfo,
            ConversionResult,
        )
        print("✓ 模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def test_preprocessor():
    """测试HTML预处理器"""
    print("\n测试2: HTML预处理器...")
    try:
        from src.reinvent_insight.html_to_markdown.preprocessor import HTMLPreprocessor
        
        html = """
        <html>
        <head>
            <script>console.log('test');</script>
            <style>.test { color: red; }</style>
        </head>
        <body>
            <h1>测试标题</h1>
            <p>测试内容</p>
        </body>
        </html>
        """
        
        preprocessor = HTMLPreprocessor()
        cleaned = preprocessor.preprocess(html)
        
        # 验证
        assert '<script>' not in cleaned, "script标签未被移除"
        assert '<style>' not in cleaned, "style标签未被移除"
        assert '测试标题' in cleaned, "内容丢失"
        assert '测试内容' in cleaned, "内容丢失"
        
        print("✓ HTML预处理器工作正常")
        return True
    except Exception as e:
        print(f"✗ HTML预处理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_url_processor():
    """测试URL处理器"""
    print("\n测试3: URL处理器...")
    try:
        from src.reinvent_insight.html_to_markdown.url_processor import URLProcessor
        
        processor = URLProcessor(base_url="https://example.com")
        
        # 测试相对路径转换
        result = processor.process_image_url("/images/test.jpg")
        assert result == "https://example.com/images/test.jpg", f"相对路径转换错误: {result}"
        
        # 测试绝对URL保留
        result = processor.process_image_url("https://other.com/image.jpg")
        assert result == "https://other.com/image.jpg", f"绝对URL处理错误: {result}"
        
        # 测试data URI保留
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA"
        result = processor.process_image_url(data_uri)
        assert result == data_uri, f"data URI处理错误: {result}"
        
        print("✓ URL处理器工作正常")
        return True
    except Exception as e:
        print(f"✗ URL处理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """测试数据模型"""
    print("\n测试4: 数据模型...")
    try:
        from src.reinvent_insight.html_to_markdown.models import (
            ImageInfo,
            ExtractedContent,
            ConversionResult
        )
        
        # 测试ImageInfo
        image = ImageInfo(
            url="https://example.com/image.jpg",
            alt="测试图片",
            caption="这是一张测试图片"
        )
        markdown = image.to_markdown()
        assert "![测试图片](https://example.com/image.jpg)" in markdown
        assert "*这是一张测试图片*" in markdown
        
        # 测试ExtractedContent
        content = ExtractedContent(
            title="测试标题",
            content="测试内容",
            images=[image],
            metadata={"author": "张三"}
        )
        data = content.to_dict()
        assert data["title"] == "测试标题"
        assert len(data["images"]) == 1
        
        print("✓ 数据模型工作正常")
        return True
    except Exception as e:
        print(f"✗ 数据模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("HTML to Markdown Converter - 基本功能测试")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_preprocessor,
        test_url_processor,
        test_models,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 60)
    
    if all(results):
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
