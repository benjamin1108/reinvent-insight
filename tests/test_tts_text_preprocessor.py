"""
TTS 文本预处理器单元测试
"""

import pytest
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reinvent_insight.services.tts_text_preprocessor import (
    TTSTextPreprocessor,
    PreprocessingResult
)


class TestTTSTextPreprocessor:
    """TTS 文本预处理器测试"""
    
    @pytest.fixture
    def preprocessor(self):
        """创建预处理器实例"""
        return TTSTextPreprocessor()
    
    @pytest.fixture
    def sample_markdown(self):
        """示例 Markdown 文章"""
        return """---
title: AWS re:Invent 2024 - AI 创新
video_url: https://www.youtube.com/watch?v=test123
upload_date: 2024-11-20
---

# Advancing AI Innovation AWS 人工智能创新

### 引言

本文介绍 AWS re:Invent 2024 大会上的 AI 创新。

### 目录

- [第一章节](#section1)
- [第二章节](#section2)
- [核心洞见](#insights)

### 第一章节

这是**重要内容**，包含`代码示例`和[链接](https://example.com)。

```python
def hello():
    print("Hello World")
```

列表示例：
- 第一项内容
- 第二项内容
- 第三项内容

### 第二章节

这里有特殊符号 → × ÷ 等。

### 核心洞见

1. 洞见一：AI 发展迅速
2. 洞见二：云计算至关重要

### 金句

> "创新是永恒的主题"
> "技术改变世界"
"""
    
    def test_extract_yaml_metadata(self, preprocessor, sample_markdown):
        """测试提取 YAML 元数据"""
        metadata, content = preprocessor.extract_yaml_metadata(sample_markdown)
        
        assert 'title' in metadata
        assert 'video_url' in metadata
        assert metadata['title'] == 'AWS re:Invent 2024 - AI 创新'
        assert 'Advancing AI Innovation' in content
        assert '---' not in content
    
    def test_extract_chinese_title(self, preprocessor):
        """测试提取中文标题"""
        content = "# Advancing AI Innovation AWS 人工智能创新\n\n正文内容"
        title_cn, remaining = preprocessor.extract_chinese_title(content)
        
        assert '人工智能创新' in title_cn
        assert '正文内容' in remaining
        assert '# Advancing' not in remaining
    
    def test_remove_toc_section(self, preprocessor, sample_markdown):
        """测试移除目录章节"""
        content, removed = preprocessor.remove_toc_section(sample_markdown)
        
        assert removed is True
        assert '### 目录' not in content
        assert '[第一章节]' not in content
    
    def test_remove_insights_and_quotes(self, preprocessor, sample_markdown):
        """测试移除洞见和金句"""
        content, removed_sections = preprocessor.remove_insights_and_quotes(sample_markdown)
        
        assert len(removed_sections) > 0
        assert '核心洞见' not in content
        assert '金句' not in content
        assert '创新是永恒的主题' not in content
    
    def test_clean_markdown_syntax(self, preprocessor):
        """测试清理 Markdown 语法"""
        content = """这是**粗体**和*斜体*文本。

```python
code block
```

这是`行内代码`和[链接](url)和![图片](img.png)。
"""
        cleaned = preprocessor.clean_markdown_syntax(content)
        
        assert '**' not in cleaned
        assert '*' not in cleaned
        assert '```' not in cleaned
        assert '`' not in cleaned
        assert 'code block' not in cleaned
        assert '[链接]' not in cleaned
        assert '![图片]' not in cleaned
        assert '粗体' in cleaned
        assert '斜体' in cleaned
        assert '链接' in cleaned
    
    def test_optimize_headings(self, preprocessor):
        """测试优化标题格式"""
        content = """# 一级标题

## 二级标题

### 三级标题

#### 四级标题
"""
        optimized = preprocessor.optimize_headings(content)
        
        assert '一级标题。\n\n' in optimized
        assert '二级标题。\n' in optimized
        assert '三级标题。' in optimized
        assert '四级标题，' in optimized
    
    def test_optimize_lists(self, preprocessor):
        """测试优化列表格式"""
        content = """正文内容

- 第一项
- 第二项
- 第三项

继续正文
"""
        optimized = preprocessor.optimize_lists(content)
        
        assert '第一，第一项；' in optimized
        assert '第二，第二项；' in optimized
        assert '第三，第三项；' in optimized
    
    def test_replace_special_symbols(self, preprocessor):
        """测试替换特殊符号"""
        content = "A → B × C ÷ D ≈ E"
        replaced = preprocessor.replace_special_symbols(content)
        
        assert '→' not in replaced
        assert '×' not in replaced
        assert '÷' not in replaced
        assert '到' in replaced
        assert '乘以' in replaced
        assert '除以' in replaced
    
    def test_normalize_whitespace(self, preprocessor):
        """测试规范化空白字符"""
        content = """  行首空格  


多个空行


   
正文内容  多个空格  继续
"""
        normalized = preprocessor.normalize_whitespace(content)
        
        assert '  行首空格' not in normalized
        assert '\n\n\n' not in normalized
        assert '多个空格  继续' not in normalized
        assert '行首空格' in normalized
        assert '正文内容 多个空格 继续' in normalized
    
    def test_validate_result(self, preprocessor):
        """测试验证结果"""
        # 有效文本
        valid_text = "这是一段包含中文的有效文本，长度足够，没有 Markdown 语法残留。"
        assert preprocessor.validate_result(valid_text) is True
        
        # 文本过短
        short_text = "短文本"
        assert preprocessor.validate_result(short_text) is False
        
        # 没有中文
        no_chinese = "This is English text without Chinese characters for testing."
        assert preprocessor.validate_result(no_chinese) is False
        
        # 有 Markdown 残留
        markdown_text = "这是包含中文的文本，但有```代码块```残留，长度也足够长来通过长度检查。"
        assert preprocessor.validate_result(markdown_text) is False
    
    def test_preprocess_complete_workflow(self, preprocessor, sample_markdown):
        """测试完整预处理流程"""
        result = preprocessor.preprocess(
            sample_markdown,
            video_url="https://www.youtube.com/watch?v=test123",
            title="AWS re:Invent 2024",
            upload_date="2024-11-20"
        )
        
        assert result is not None
        assert isinstance(result, PreprocessingResult)
        assert len(result.text) > 0
        assert len(result.article_hash) == 16
        assert '人工智能创新' in result.title_cn
        assert result.processed_length < result.original_length
        assert '目录' in result.sections_removed or '核心洞见' in result.sections_removed
        
        # 验证内容清理
        assert '---' not in result.text  # 无 YAML
        assert '### 目录' not in result.text  # 无目录
        assert '核心洞见' not in result.text  # 无洞见
        assert '金句' not in result.text  # 无金句
        assert '```' not in result.text  # 无代码块
        assert '**' not in result.text  # 无 Markdown 格式
        assert '[链接]' not in result.text  # 无链接语法
    
    def test_calculate_article_hash(self, preprocessor):
        """测试计算文章哈希"""
        hash1 = preprocessor.calculate_article_hash(
            "https://example.com/video1",
            "标题一",
            "2024-01-01"
        )
        
        hash2 = preprocessor.calculate_article_hash(
            "https://example.com/video1",
            "标题一",
            "2024-01-01"
        )
        
        hash3 = preprocessor.calculate_article_hash(
            "https://example.com/video2",
            "标题二",
            "2024-01-02"
        )
        
        assert len(hash1) == 16
        assert hash1 == hash2  # 相同输入产生相同哈希
        assert hash1 != hash3  # 不同输入产生不同哈希
    
    def test_save_to_file(self, preprocessor, tmp_path):
        """测试保存到文件"""
        result = PreprocessingResult(
            text="测试文本内容",
            article_hash="a1b2c3d4e5f6g7h8",
            title_cn="测试标题",
            original_length=1000,
            processed_length=500,
            sections_removed=["目录", "核心洞见"]
        )
        
        output_path = preprocessor.save_to_file(result, tmp_path)
        
        assert output_path is not None
        assert output_path.exists()
        assert output_path.name == "a1b2c3d4e5f6g7h8.txt"
        
        # 验证文件内容
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == "测试文本内容"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
