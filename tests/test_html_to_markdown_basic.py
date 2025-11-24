"""
基本功能测试 - HTML to Markdown Converter

测试核心转换功能是否正常工作。
"""

import pytest
import asyncio


# 简单的HTML示例
SIMPLE_HTML = """
<html>
<head>
    <title>测试文章</title>
    <script>console.log('test');</script>
    <style>.test { color: red; }</style>
</head>
<body>
    <h1>人工智能的未来</h1>
    <p>人工智能正在改变我们的世界。</p>
    <img src="/images/ai.jpg" alt="AI示意图">
    <h2>技术发展</h2>
    <p>近年来，AI技术取得了突破性进展。</p>
</body>
</html>
"""


def test_imports():
    """测试模块导入"""
    from reinvent_insight.html_to_markdown import (
        HTMLToMarkdownConverter,
        ExtractedContent,
        ImageInfo,
        ConversionResult,
    )
    
    assert HTMLToMarkdownConverter is not None
    assert ExtractedContent is not None
    assert ImageInfo is not None
    assert ConversionResult is not None


def test_preprocessor():
    """测试HTML预处理器"""
    from reinvent_insight.html_to_markdown.preprocessor import HTMLPreprocessor
    
    preprocessor = HTMLPreprocessor()
    cleaned = preprocessor.preprocess(SIMPLE_HTML)
    
    # 验证script和style被移除
    assert '<script>' not in cleaned
    assert '<style>' not in cleaned
    assert 'console.log' not in cleaned
    assert '.test { color: red; }' not in cleaned
    
    # 验证内容保留
    assert '人工智能的未来' in cleaned
    assert '人工智能正在改变我们的世界' in cleaned


def test_url_processor():
    """测试URL处理器"""
    from reinvent_insight.html_to_markdown.url_processor import URLProcessor
    
    processor = URLProcessor(base_url="https://example.com")
    
    # 测试相对路径转换
    result = processor.process_image_url("/images/test.jpg")
    assert result == "https://example.com/images/test.jpg"
    
    # 测试绝对URL保留
    result = processor.process_image_url("https://other.com/image.jpg")
    assert result == "https://other.com/image.jpg"
    
    # 测试data URI保留
    data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA"
    result = processor.process_image_url(data_uri)
    assert result == data_uri


def test_image_info_to_markdown():
    """测试ImageInfo转Markdown"""
    from reinvent_insight.html_to_markdown.models import ImageInfo
    
    image = ImageInfo(
        url="https://example.com/image.jpg",
        alt="测试图片",
        caption="这是一张测试图片"
    )
    
    markdown = image.to_markdown()
    assert "![测试图片](https://example.com/image.jpg)" in markdown
    assert "*这是一张测试图片*" in markdown


def test_extracted_content_to_dict():
    """测试ExtractedContent序列化"""
    from reinvent_insight.html_to_markdown.models import ExtractedContent, ImageInfo
    
    content = ExtractedContent(
        title="测试标题",
        content="测试内容",
        images=[
            ImageInfo(url="https://example.com/img.jpg", alt="图片")
        ],
        metadata={"author": "张三"}
    )
    
    data = content.to_dict()
    assert data["title"] == "测试标题"
    assert data["content"] == "测试内容"
    assert len(data["images"]) == 1
    assert data["metadata"]["author"] == "张三"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
