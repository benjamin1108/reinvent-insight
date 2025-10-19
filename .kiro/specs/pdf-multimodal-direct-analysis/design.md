# Design Document

## Overview

本设计文档描述了PDF多模态直接解析功能的技术方案。核心思路是让大模型直接使用多模态能力分析PDF文件，就像处理视频一样，避免中间的文本提取步骤导致的信息丢失。

### 当前问题

现有流程：
```
PDF文件 → extract_pdf_content() → 提取纯文本 → run_deep_summary_workflow() → 最终报告
```

问题：
- `extract_pdf_content()` 只提取文本，丢失了架构图、流程图、数据图表等视觉信息
- 视觉信息对于技术文档的理解至关重要
- 增加了一次不必要的API调用

### 目标方案

新流程：
```
PDF文件 → run_deep_summary_workflow() (使用PDF专用提示词) → 最终报告
```

优势：
- 直接多模态分析，保留所有视觉信息
- 减少API调用次数
- 复用成熟的视频分析工作流
- 提高分析质量和准确性

## Architecture

### 核心组件关系

```
PDFAnalysisRequest
       ↓
pdf_analysis_worker_async
       ↓
run_deep_summary_workflow (使用PDF适配的提示词)
       ↓
DeepSummaryWorkflow
   ├── _generate_outline (使用PDF多模态提示词)
   ├── _generate_chapters_parallel (使用PDF多模态提示词)
   └── _generate_conclusion
       ↓
最终报告
```

### 提示词适配策略


使用两种方式适配提示词：

1. **方案A（推荐）**: 修改 `prompts.py`，将视频相关的提示词改为通用的"内容分析"提示词
   - 优点：代码简洁，统一处理
   - 缺点：需要确保提示词对两种输入都适用

2. **方案B**: 创建PDF专用的提示词模板
   - 优点：可以针对PDF特性优化
   - 缺点：代码重复，维护成本高

**选择方案A**，因为视频字幕和PDF文档本质上都是"需要深度分析的内容"，可以用统一的提示词处理。

## Components and Interfaces

### 1. PDF Worker 模块 (`pdf_worker.py`)

#### 修改点

**移除**：
- `extract_pdf_content()` 函数 - 不再需要文本提取

**修改**：
- `pdf_analysis_worker_async()` 函数
  - 移除文本提取步骤
  - 直接将PDF文件信息传递给工作流
  - 创建特殊的"transcript"对象，包含PDF文件引用

#### 新接口设计

```python
async def pdf_analysis_worker_async(
    req: PDFAnalysisRequest, 
    task_id: str, 
    file_path: str
):
    """
    处理PDF分析请求，直接使用多模态工作流
    """
    # 1. 上传PDF到Gemini
    processor = PDFProcessor()
    pdf_file_info = await processor.upload_pdf(file_path)
    
    # 2. 创建PDF内容对象（包含文件引用）
    pdf_content = PDFContent(
        file_info=pdf_file_info,
        title=clean_title,
        content_type="pdf"
    )
    
    # 3. 直接运行工作流
    await run_deep_summary_workflow(
        task_id=task_id,
        model_name=config.PREFERRED_MODEL,
        content=pdf_content,  # 传递PDF内容对象而非文本
        video_metadata=metadata
    )
```

### 2. Workflow 模块 (`workflow.py`)

#### 修改点

**新增**：
- `PDFContent` 数据类 - 封装PDF文件信息
- 内容类型检测逻辑

**修改**：
- `DeepSummaryWorkflow.__init__()` - 接受通用的content参数
- `_generate_outline()` - 根据内容类型选择处理方式
- `_generate_single_chapter()` - 根据内容类型选择处理方式
- `_generate_conclusion()` - 根据内容类型选择处理方式

#### 新数据结构

```python
from dataclasses import dataclass
from typing import Union, Dict, Any

@dataclass
class PDFContent:
    """PDF内容封装"""
    file_info: Dict[str, Any]  # PDF文件信息
    title: str  # 文档标题
    content_type: str = "pdf"  # 内容类型标识

class DeepSummaryWorkflow:
    def __init__(
        self, 
        task_id: str, 
        model_name: str, 
        content: Union[str, PDFContent],  # 支持字符串或PDF对象
        video_metadata: VideoMetadata
    ):
        self.task_id = task_id
        self.model_name = model_name
        self.content = content
        self.is_pdf = isinstance(content, PDFContent)
        self.metadata = video_metadata
        # ...
```

### 3. Prompts 模块 (`prompts.py`)

#### 修改点

将所有提示词中的"视频"、"字幕"等词汇改为通用表述：

**修改前**：
```
## 输入素材
- 内容来源：YouTube（科普 / 访谈 / 发布演讲，自动判别）
- 提供材料：{英文字幕}
```

**修改后**：
```
## 输入素材
- 内容来源：{content_source}
- 提供材料：{content_description}
```

#### 新增多模态分析指导

在提示词中添加针对PDF的多模态分析指导：

```python
PDF_MULTIMODAL_GUIDE = """
## 多模态分析指南（针对PDF文档）

### 文本分析重点：
- 核心概念和技术术语
- 业务价值和技术优势
- 问题描述和解决方案

### 视觉元素分析重点：
- **架构图**: 系统组件、数据流、部署结构
- **流程图**: 业务流程、操作步骤、决策树
- **数据图表**: 性能指标、趋势分析、对比数据
- **截图**: UI设计、配置示例、代码片段

### 关联分析：
- 文本中提到的概念如何在图中体现
- 图表数据如何支撑文本论述
- 架构设计如何解决文本中的问题

**重要**: 你正在分析的是PDF文档，请充分利用多模态能力，
不仅要理解文字内容，更要深入解读其中的图表、架构图等视觉信息。
```

### 4. Summarizer 模块 (`summarizer.py`)

#### 修改点

**新增方法**：
- `generate_content_with_pdf()` - 支持PDF文件作为输入

```python
async def generate_content_with_pdf(
    self, 
    prompt: str, 
    pdf_file_info: Dict[str, Any]
) -> str:
    """
    使用PDF文件生成内容
    
    Args:
        prompt: 提示词
        pdf_file_info: PDF文件信息（包含file_id或本地路径）
    
    Returns:
        生成的内容
    """
```

## Data Models

### PDFContent

```python
@dataclass
class PDFContent:
    """PDF内容封装类"""
    file_info: Dict[str, Any]  # Gemini文件信息
    title: str  # 文档标题
    content_type: str = "pdf"  # 固定为"pdf"
    
    @property
    def file_id(self) -> str:
        """获取文件ID"""
        return self.file_info.get("name", "")
    
    @property
    def is_local(self) -> bool:
        """是否为本地文件"""
        return self.file_info.get("local_file", False)
```

### ContentWrapper (可选的统一接口)

```python
from typing import Union

ContentType = Union[str, PDFContent]

def is_pdf_content(content: ContentType) -> bool:
    """判断是否为PDF内容"""
    return isinstance(content, PDFContent)

def get_content_description(content: ContentType) -> str:
    """获取内容描述"""
    if is_pdf_content(content):
        return f"PDF文档: {content.title}"
    else:
        return f"文本内容 ({len(content)} 字符)"
```

## Error Handling

### 错误场景

1. **PDF上传失败**
   - 原因：网络问题、文件格式不支持
   - 处理：重试3次，失败后返回错误信息

2. **多模态分析失败**
   - 原因：API限制、PDF内容无法解析
   - 处理：降级到文本提取模式（保留原有逻辑作为fallback）

3. **文件引用失效**
   - 原因：Gemini文件过期
   - 处理：重新上传文件

### 错误处理策略

```python
async def pdf_analysis_worker_async(...):
    try:
        # 尝试多模态分析
        await run_deep_summary_workflow(...)
    except MultimodalAnalysisError as e:
        logger.warning(f"多模态分析失败，降级到文本提取: {e}")
        # Fallback: 使用原有的文本提取逻辑
        pdf_content = await extract_pdf_content(...)
        await run_deep_summary_workflow(
            content=pdf_content,  # 传递文本
            ...
        )
```

## Testing Strategy

### 单元测试

1. **PDFContent 类测试**
   - 测试数据封装
   - 测试属性访问

2. **提示词生成测试**
   - 测试PDF提示词生成
   - 测试视频提示词生成
   - 验证提示词格式正确

3. **内容类型检测测试**
   - 测试 `is_pdf_content()` 函数
   - 测试类型判断逻辑

### 集成测试

1. **PDF工作流测试**
   - 使用真实PDF文件
   - 验证完整流程
   - 检查输出格式

2. **多模态分析测试**
   - 测试包含图表的PDF
   - 验证视觉信息是否被正确解读
   - 对比文本提取模式的输出差异

3. **降级测试**
   - 模拟多模态分析失败
   - 验证fallback机制
   - 确保系统稳定性

### 性能测试

1. **API调用次数对比**
   - 对比新旧流程的API调用次数
   - 验证是否减少至少50%

2. **处理时间对比**
   - 测量端到端处理时间
   - 对比新旧流程的效率

3. **质量评估**
   - 人工评估分析报告质量
   - 对比是否包含更多视觉信息洞察

## Implementation Phases

### Phase 1: 基础架构 (核心功能)
- 创建 `PDFContent` 数据类
- 修改 `DeepSummaryWorkflow` 支持PDF内容
- 修改提示词为通用表述

### Phase 2: PDF处理优化 (核心功能)
- 修改 `pdf_worker.py` 移除文本提取
- 实现直接传递PDF文件到工作流
- 添加PDF多模态分析指导

### Phase 3: Summarizer适配 (核心功能)
- 在 `summarizer.py` 中添加PDF支持
- 实现 `generate_content_with_pdf()` 方法
- 处理本地文件和远程文件两种情况

### Phase 4: 错误处理和降级 (可选)
- 实现错误捕获和重试机制
- 添加fallback到文本提取模式
- 完善日志和监控

### Phase 5: 测试和验证 (可选)
- 编写单元测试
- 进行集成测试
- 性能和质量评估

## Migration Strategy

### 向后兼容

保留原有的 `extract_pdf_content()` 函数作为fallback：

```python
# 在 pdf_worker.py 中
USE_MULTIMODAL_ANALYSIS = True  # 配置开关

if USE_MULTIMODAL_ANALYSIS:
    # 新流程：直接多模态分析
    await run_deep_summary_workflow(content=pdf_content, ...)
else:
    # 旧流程：文本提取
    text = await extract_pdf_content(...)
    await run_deep_summary_workflow(content=text, ...)
```

### 渐进式部署

1. **阶段1**: 新旧流程并行，通过配置开关控制
2. **阶段2**: 默认使用新流程，保留旧流程作为fallback
3. **阶段3**: 完全移除旧流程（在验证稳定后）

## Performance Considerations

### API调用优化

- **当前**: 2次主要调用（文本提取 + 大纲生成）
- **优化后**: 1次主要调用（直接大纲生成）
- **预期节省**: 50% API调用

### 内存使用

- PDF文件会上传到Gemini，不占用本地内存
- 工作流中只保存文件引用，不保存完整内容
- 内存占用与当前视频处理相当

### 并发处理

- 保持现有的章节并行生成机制
- PDF文件引用可以在多个请求中复用
- 不影响现有的并发能力

## Security Considerations

### 文件安全

- PDF文件上传到Gemini后自动加密
- 文件有过期时间，自动清理
- 本地临时文件及时删除

### 数据隐私

- 不在日志中记录PDF内容
- 文件ID不暴露给前端
- 遵循现有的安全策略

## Future Enhancements

1. **支持更多文件格式**
   - Word文档 (.docx)
   - PowerPoint (.pptx)
   - 图片文件 (.png, .jpg)

2. **增强视觉分析**
   - 专门的图表识别和解读
   - OCR文字识别
   - 表格数据提取

3. **交互式分析**
   - 用户可以指定关注的章节或图表
   - 支持追问和深入分析
   - 生成针对性的洞察

4. **批量处理**
   - 同时分析多个PDF
   - 生成对比分析报告
   - 知识图谱构建
