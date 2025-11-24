# HTML to Markdown Converter

智能的网页内容提取和转换模块，能够将HTML网页转换为格式化的Markdown文档。

## 特性

- **代码预处理**：快速去除JavaScript、CSS、注释等冗余内容
- **LLM智能提取**：使用Gemini模型智能识别正文、标题、相关图片
- **广告过滤**：自动过滤广告和无关内容
- **URL处理**：自动转换相对路径为绝对路径
- **Markdown生成**：生成格式化的标准Markdown文档

## 安装依赖

```bash
pip install beautifulsoup4 lxml httpx
```

## 快速开始

### 基本使用

```python
import asyncio
from reinvent_insight.html_to_markdown import HTMLToMarkdownConverter

async def main():
    # 创建转换器
    converter = HTMLToMarkdownConverter()
    
    # 从HTML字符串转换
    html = """
    <html>
        <body>
            <h1>文章标题</h1>
            <p>文章内容...</p>
        </body>
    </html>
    """
    
    result = await converter.convert_from_string(
        html,
        base_url="https://example.com"
    )
    
    print(result.markdown)
    print(f"标题: {result.content.title}")
    print(f"图片数量: {len(result.content.images)}")

# 运行
asyncio.run(main())
```

### 从文件转换

```python
import asyncio
from reinvent_insight.html_to_markdown import HTMLToMarkdownConverter

async def main():
    converter = HTMLToMarkdownConverter()
    
    # 从HTML文件转换并保存
    result = await converter.convert_from_file(
        "article.html",
        output_path="article.md",
        base_url="https://example.com"
    )
    
    print(f"转换完成！Markdown已保存到 article.md")

asyncio.run(main())
```

### 从URL转换

```python
import asyncio
from reinvent_insight.html_to_markdown import HTMLToMarkdownConverter

async def main():
    converter = HTMLToMarkdownConverter()
    
    # 从URL获取并转换
    result = await converter.convert_from_url(
        "https://example.com/article",
        output_path="article.md"
    )
    
    print(f"转换完成！")
    print(f"标题: {result.content.title}")
    print(f"内容长度: {len(result.content.content)} 字符")

asyncio.run(main())
```

## API 文档

### HTMLToMarkdownConverter

主转换器类，协调各组件完成转换。

#### 方法

##### `__init__(task_type: str = "html_to_markdown")`

初始化转换器。

**参数：**
- `task_type`: 任务类型，用于从配置文件加载模型配置

##### `async convert_from_string(html: str, output_path: Optional[Path] = None, base_url: Optional[str] = None) -> ConversionResult`

从HTML字符串转换为Markdown。

**参数：**
- `html`: HTML字符串
- `output_path`: 输出文件路径（可选）
- `base_url`: 网页的基础URL，用于图片路径转换（可选）

**返回：**
- `ConversionResult`: 包含Markdown文本和提取的内容

##### `async convert_from_file(html_path: Path, output_path: Optional[Path] = None, base_url: Optional[str] = None) -> ConversionResult`

从HTML文件转换为Markdown。

**参数：**
- `html_path`: HTML文件路径
- `output_path`: 输出文件路径（可选）
- `base_url`: 网页的基础URL（可选）

**返回：**
- `ConversionResult`: 包含Markdown文本和提取的内容

##### `async convert_from_url(url: str, output_path: Optional[Path] = None) -> ConversionResult`

从URL获取HTML并转换为Markdown。

**参数：**
- `url`: 网页URL
- `output_path`: 输出文件路径（可选）

**返回：**
- `ConversionResult`: 包含Markdown文本和提取的内容

### 数据模型

#### ConversionResult

转换结果对象。

**属性：**
- `markdown: str` - 生成的Markdown文本
- `content: ExtractedContent` - 提取的内容对象
- `stats: Dict[str, Any]` - 统计信息

**方法：**
- `save(path: Path)` - 保存Markdown到文件

#### ExtractedContent

提取的内容对象。

**属性：**
- `title: str` - 文章标题
- `content: str` - 正文内容（Markdown格式）
- `images: List[ImageInfo]` - 相关图片列表
- `metadata: Dict[str, Any]` - 元数据（作者、日期等）

#### ImageInfo

图片信息对象。

**属性：**
- `url: str` - 图片URL
- `alt: str` - alt文本
- `caption: Optional[str]` - 图片说明
- `position: Optional[int]` - 在文章中的位置

**方法：**
- `to_markdown() -> str` - 转换为Markdown图片语法

## 配置

模块使用统一的模型配置系统。配置位于 `config/model_config.yaml`：

```yaml
tasks:
  html_to_markdown:
    provider: gemini
    model_name: gemini-3-pro-preview
    api_key_env: GEMINI_API_KEY
    
    generation:
      temperature: 0.5
      top_p: 0.9
      top_k: 40
      max_output_tokens: 16000
    
    rate_limit:
      interval: 0.5
      max_retries: 3
      retry_backoff_base: 2.0
```

确保设置环境变量 `GEMINI_API_KEY`。

## 错误处理

模块定义了以下异常类型：

- `HTMLToMarkdownError` - 基础异常类
- `HTMLParseError` - HTML解析错误
- `ContentExtractionError` - 内容提取错误
- `LLMProcessingError` - LLM处理错误
- `URLProcessingError` - URL处理错误
- `MarkdownGenerationError` - Markdown生成错误

示例：

```python
from reinvent_insight.html_to_markdown import (
    HTMLToMarkdownConverter,
    ContentExtractionError
)

async def main():
    converter = HTMLToMarkdownConverter()
    
    try:
        result = await converter.convert_from_string(html)
    except ContentExtractionError as e:
        print(f"内容提取失败: {e}")
    except Exception as e:
        print(f"转换失败: {e}")
```

## 工作原理

转换流程分为4个步骤：

1. **HTML预处理** - 使用BeautifulSoup去除JavaScript、CSS、注释等冗余内容
2. **LLM内容提取** - 使用Gemini模型智能识别标题、正文、图片，过滤广告
3. **URL处理** - 将相对路径转换为绝对URL
4. **Markdown生成** - 格式化输出为标准Markdown文档

## 限制

- HTML长度限制：约50KB（超出部分会被截断）
- 需要有效的Gemini API密钥
- 最适合处理文章类网页（新闻、博客、技术文档等）
- 对于JavaScript动态加载的内容，需要提供完整渲染后的HTML

## 示例

完整示例请参考 `tests/manual_test_html_to_markdown.py`。

## 许可证

与项目主许可证相同。
