# 多格式文档支持

## 概述

Reinvent Insight 现已支持多种文档格式的深度分析，包括 TXT、MD、PDF 和 DOCX。系统采用统一的工作流处理不同格式的文档，根据文档类型自动选择最佳的处理策略。

## 支持的格式

### 文本文档（Text Documents）

#### TXT - 纯文本文件
- **文件扩展名**: `.txt`
- **最大文件大小**: 10MB（可配置）
- **编码支持**: UTF-8, GBK, GB2312, Latin-1
- **处理方式**: 文本注入（Text Injection）
- **适用场景**: 
  - 会议记录
  - 技术文档
  - 代码注释
  - 日志文件

#### MD - Markdown 文档
- **文件扩展名**: `.md`
- **最大文件大小**: 10MB（可配置）
- **编码支持**: UTF-8, GBK, GB2312, Latin-1
- **处理方式**: 文本注入（保留 Markdown 格式）
- **适用场景**:
  - 技术博客
  - 项目文档
  - README 文件
  - 知识库文章

### 多模态文档（Multimodal Documents）

#### PDF - PDF 文档
- **文件扩展名**: `.pdf`
- **最大文件大小**: 50MB（可配置）
- **处理方式**: 多模态分析（Multimodal Analysis）
- **特殊能力**:
  - 识别和分析图表
  - 理解架构图
  - 提取表格数据
  - 分析页面布局
- **适用场景**:
  - 技术白皮书
  - 研究报告
  - 产品手册
  - 演示文稿

#### DOCX - Word 文档
- **文件扩展名**: `.docx`
- **最大文件大小**: 50MB（可配置）
- **处理方式**: 多模态分析
- **特殊能力**:
  - 识别和分析图表
  - 理解文档结构
  - 提取表格数据
  - 分析嵌入对象
- **适用场景**:
  - 业务文档
  - 技术规范
  - 项目计划
  - 设计文档

## 处理策略

### 文本注入（Text Injection）

**适用格式**: TXT, MD

**工作原理**:
1. 读取文件内容为字符串
2. 将文本内容直接注入到 Prompt 中
3. 使用 Gemini API 的文本生成能力进行分析

**优势**:
- 处理速度快
- API 调用成本低
- 适合纯文本内容

**限制**:
- 无法处理图片和图表
- 不支持复杂的文档布局

### 多模态分析（Multimodal Analysis）

**适用格式**: PDF, DOCX

**工作原理**:
1. 上传文件到 Gemini API
2. 利用 Gemini 的多模态能力分析文档
3. 同时理解文本、图表、架构图等多种信息

**优势**:
- 全面理解文档内容
- 能够分析视觉元素
- 提取图表中的数据和洞察

**限制**:
- 处理时间较长
- API 调用成本较高
- 文件大小限制

## 使用方法

### 通过 API

```bash
curl -X POST "http://localhost:8001/analyze-document" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "title=可选的文档标题"
```

### 通过 Web 界面

1. 登录系统
2. 点击"上传文档"按钮
3. 选择要分析的文档文件
4. （可选）填写文档标题
5. 点击"开始分析"
6. 通过 WebSocket 实时查看分析进度

### 通过 Python SDK

```python
import asyncio
from src.reinvent_insight.document_processor import DocumentProcessor
from src.reinvent_insight.workflow import run_deep_summary_workflow
from src.reinvent_insight.downloader import VideoMetadata
from src.reinvent_insight.utils import generate_document_identifier

async def analyze_document(file_path: str, title: str = None):
    # 初始化处理器
    processor = DocumentProcessor()
    
    # 处理文档
    content = await processor.process_document(file_path, title)
    
    # 生成标识符
    doc_id = generate_document_identifier(
        content.title,
        content.text_content[:200] if content.text_content else "",
        "doc"
    )
    
    # 创建元数据
    metadata = VideoMetadata(
        title=content.title,
        upload_date="19700101",
        video_url=doc_id
    )
    
    # 运行工作流
    await run_deep_summary_workflow(
        task_id="test_task",
        model_name="Gemini",
        content=content,
        video_metadata=metadata
    )

# 运行
asyncio.run(analyze_document("/path/to/document.pdf", "测试文档"))
```

## 配置选项

在 `.env` 文件中可以配置以下选项：

```bash
# 文本文件最大大小（字节）
MAX_TEXT_FILE_SIZE=10485760  # 10MB

# 二进制文件最大大小（字节）
MAX_BINARY_FILE_SIZE=52428800  # 50MB
```

## 输出格式

所有格式的文档分析都会生成统一的 Markdown 报告，包含：

1. **YAML Front Matter**
   - 文档标题（中英文）
   - 创建时间
   - 文档标识符
   - 文档类型

2. **引言**
   - 文档概述
   - 核心主题

3. **目录**
   - 带锚点链接的章节列表

4. **章节内容**
   - 详细的分析内容
   - 结构化的子章节

5. **洞见延伸**
   - 核心洞察
   - 实践建议

6. **金句 & 原声引用**
   - 关键观点
   - 重要引用

## 最佳实践

### 文档准备

1. **文本文档**:
   - 确保使用 UTF-8 编码
   - 保持文档结构清晰
   - 避免过多的格式标记

2. **PDF 文档**:
   - 确保文本可选择（非扫描版）
   - 图表清晰可读
   - 避免过度加密

3. **Word 文档**:
   - 使用 .docx 格式（Office 2007+）
   - 保持文档结构清晰
   - 图表嵌入而非链接

### 性能优化

1. **文件大小**:
   - 尽量控制在推荐大小以内
   - 大文件可能导致处理超时

2. **内容质量**:
   - 清晰的文档结构有助于生成更好的分析
   - 避免过多的冗余内容

3. **批量处理**:
   - 建议分批处理大量文档
   - 避免同时处理过多大文件

## 故障排除

### 常见问题

**Q: 上传文件时提示"不支持的文件格式"**
A: 请确保文件扩展名为 .txt, .md, .pdf 或 .docx

**Q: 文件上传失败，提示"文件大小超过限制"**
A: 请检查文件大小是否超过配置的限制（文本文件 10MB，二进制文件 50MB）

**Q: PDF 文档分析结果不准确**
A: 请确保 PDF 是文本格式而非扫描版，图表清晰可读

**Q: 文本文件编码错误**
A: 系统会自动尝试多种编码，建议使用 UTF-8 编码保存文件

**Q: 分析进度卡住不动**
A: 可能是网络问题或 API 限流，请稍后重试

### 错误代码

- `400`: 不支持的文件格式或参数错误
- `413`: 文件大小超过限制
- `500`: 服务器内部错误（文件读取失败、API 调用失败等）

## 技术架构

### 核心组件

1. **DocumentProcessor**
   - 统一的文档处理入口
   - 格式识别和策略选择
   - 文件读取和内容提取

2. **DocumentContent**
   - 统一的文档内容数据模型
   - 支持文本和多模态两种类型
   - 向后兼容 PDFContent

3. **Workflow**
   - 统一的分析工作流
   - 根据内容类型自动选择处理方式
   - 生成标准化的分析报告

4. **DocumentWorker**
   - 异步任务处理
   - 进度实时推送
   - 错误处理和资源清理

### 数据流

```
文档上传 → DocumentProcessor → DocumentContent → Workflow → 分析报告
                ↓                      ↓              ↓
           格式识别              内容提取        AI 分析
                ↓                      ↓              ↓
           策略选择              数据封装        报告生成
```

## 未来计划

- [ ] 支持更多格式（RTF、HTML、EPUB）
- [ ] 批量文档处理
- [ ] 文档格式转换
- [ ] 增强的文本处理（代码高亮、公式识别）
- [ ] 文档对比和版本管理
- [ ] 自定义分析模板

## 参考资料

- [Gemini API 文档](https://ai.google.dev/docs)
- [Markdown 语法指南](https://www.markdownguide.org/)
- [PDF 格式规范](https://www.adobe.com/devnet/pdf/pdf_reference.html)
- [Office Open XML 规范](https://docs.microsoft.com/en-us/openspecs/office_standards/)
