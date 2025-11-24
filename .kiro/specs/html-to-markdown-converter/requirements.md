# Requirements Document

## Introduction

本文档定义了HTML到Markdown转换器模块的需求。该模块能够智能地从HTML网页中提取核心内容（标题、正文、相关图片），过滤无关信息（广告、推广链接等），并利用大模型生成格式化的Markdown文档。

## Glossary

- **HTML Parser**: 解析HTML文档结构的组件
- **Content Extractor**: 从HTML中提取核心内容的组件
- **LLM Processor**: 使用大语言模型处理和格式化内容的组件
- **Markdown Generator**: 生成最终Markdown文档的组件
- **Model Config**: 统一的模型配置系统，用于调用不同的AI模型
- **Gemini**: Google的大语言模型，用于内容处理和格式化

## Requirements

### Requirement 1

**User Story:** 作为用户，我希望能够读取HTML网页内容，以便提取其中的有价值信息

#### Acceptance Criteria

1. WHEN 用户提供HTML文件路径或URL THEN HTML Parser SHALL 成功读取并解析HTML内容
2. WHEN HTML内容包含各种编码格式 THEN HTML Parser SHALL 正确识别并处理字符编码
3. WHEN HTML文件损坏或格式不正确 THEN HTML Parser SHALL 返回明确的错误信息
4. WHEN 读取远程URL THEN HTML Parser SHALL 在30秒内完成请求或超时

### Requirement 2

**User Story:** 作为用户，我希望系统能够预处理HTML去除冗余内容，以便为大模型提供干净的输入

#### Acceptance Criteria

1. WHEN HTML包含内嵌的script标签 THEN HTML Preprocessor SHALL 移除所有JavaScript代码
2. WHEN HTML包含内嵌的style标签或style属性 THEN HTML Preprocessor SHALL 移除所有CSS样式代码
3. WHEN HTML包含注释内容 THEN HTML Preprocessor SHALL 移除所有HTML注释
4. WHEN HTML包含SVG或Canvas元素 THEN HTML Preprocessor SHALL 移除这些复杂的图形元素
5. WHEN 预处理完成 THEN HTML Preprocessor SHALL 保留HTML的基本结构和文本内容

### Requirement 3

**User Story:** 作为用户，我希望大模型能够智能提取文章的标题、正文和相关图片，以便获得高质量的内容

#### Acceptance Criteria

1. WHEN 预处理后的HTML传递给LLM THEN LLM Processor SHALL 识别并提取文章的主标题
2. WHEN HTML包含多个标题候选 THEN LLM Processor SHALL 选择最相关的标题作为主标题
3. WHEN HTML包含正文内容 THEN LLM Processor SHALL 提取完整的文章正文并保持段落结构
4. WHEN HTML包含图片元素 THEN LLM Processor SHALL 判断哪些图片与正文内容相关
5. WHEN 图片具有alt文本或周围有说明文字 THEN LLM Processor SHALL 保留这些描述信息

### Requirement 4

**User Story:** 作为用户，我希望大模型能够智能过滤广告和无关内容，以便获得纯净的文章内容

#### Acceptance Criteria

1. WHEN LLM分析HTML内容 THEN LLM Processor SHALL 识别并排除广告区域
2. WHEN HTML包含导航菜单、页脚、侧边栏 THEN LLM Processor SHALL 排除这些非正文区域
3. WHEN HTML包含推广链接或营销内容 THEN LLM Processor SHALL 过滤这些元素
4. WHEN HTML包含社交媒体分享按钮或评论区 THEN LLM Processor SHALL 排除这些交互元素
5. WHEN 提取的正文内容为空或过短 THEN LLM Processor SHALL 返回错误提示

### Requirement 5

**User Story:** 作为用户，我希望系统使用统一的模型配置方案调用Gemini模型，以便保持系统的一致性

#### Acceptance Criteria

1. WHEN 需要调用LLM处理内容 THEN LLM Processor SHALL 使用现有的Model Config系统
2. WHEN 配置指定使用Gemini模型 THEN LLM Processor SHALL 正确初始化Gemini客户端
3. WHEN Model Config不可用 THEN LLM Processor SHALL 返回配置错误信息
4. WHEN API调用失败 THEN LLM Processor SHALL 实施重试机制（最多3次）
5. WHEN 重试全部失败 THEN LLM Processor SHALL 返回详细的错误信息

### Requirement 6

**User Story:** 作为用户，我希望大模型能够将提取的内容转换为格式化的Markdown，以便生成高质量的文档

#### Acceptance Criteria

1. WHEN LLM提取内容后 THEN LLM Processor SHALL 将内容转换为标准的Markdown格式
2. WHEN 转换内容 THEN LLM Processor SHALL 保持原文的语义、段落结构和关键信息
3. WHEN 内容包含列表、表格等结构 THEN LLM Processor SHALL 转换为对应的Markdown语法
4. WHEN 内容包含代码块 THEN LLM Processor SHALL 使用正确的Markdown代码块格式并标注语言
5. WHEN 内容包含图片 THEN LLM Processor SHALL 使用标准的Markdown图片语法并包含alt文本

### Requirement 7

**User Story:** 作为用户，我希望生成的Markdown文档格式精美且结构清晰，以便阅读和使用

#### Acceptance Criteria

1. WHEN 生成Markdown文档 THEN Markdown Generator SHALL 包含清晰的标题层级
2. WHEN 文档包含图片 THEN Markdown Generator SHALL 使用标准的Markdown图片语法
3. WHEN 文档包含链接 THEN Markdown Generator SHALL 确保链接格式正确且可访问
4. WHEN 文档生成完成 THEN Markdown Generator SHALL 保存到指定的输出路径
5. WHEN 输出路径已存在同名文件 THEN Markdown Generator SHALL 提供覆盖或重命名选项

### Requirement 8

**User Story:** 作为开发者，我希望模块具有清晰的API接口，以便集成到现有系统中

#### Acceptance Criteria

1. WHEN 调用转换功能 THEN 系统 SHALL 提供简单的函数接口接受HTML输入和配置参数
2. WHEN 转换过程中 THEN 系统 SHALL 提供进度回调或日志输出
3. WHEN 转换完成 THEN 系统 SHALL 返回Markdown内容和元数据（标题、图片数量等）
4. WHEN 发生错误 THEN 系统 SHALL 抛出明确的异常类型和错误消息
5. WHEN 模块被导入 THEN 系统 SHALL 不产生副作用或自动执行操作

### Requirement 9

**User Story:** 作为用户，我希望系统能够正确处理图片URL，以便在Markdown中引用可访问的图片

#### Acceptance Criteria

1. WHEN 图片使用相对路径 THEN URL Processor SHALL 将其转换为绝对URL
2. WHEN 提供了源网页的base URL THEN URL Processor SHALL 使用该URL作为基准进行转换
3. WHEN 图片URL包含查询参数 THEN URL Processor SHALL 保留这些参数
4. WHEN 图片URL是data URI THEN URL Processor SHALL 保留原始的data URI
5. WHEN 图片URL无效或格式错误 THEN URL Processor SHALL 记录警告并跳过该图片

### Requirement 10

**User Story:** 作为用户，我希望系统能够处理各种类型的网页，以便适应不同的使用场景

#### Acceptance Criteria

1. WHEN 处理新闻文章网页 THEN 系统 SHALL 正确提取文章内容和相关图片
2. WHEN 处理博客文章 THEN 系统 SHALL 识别并提取博客正文和作者信息
3. WHEN 处理技术文档页面 THEN 系统 SHALL 保留代码示例、表格和技术细节
4. WHEN 处理包含多语言内容的页面 THEN 系统 SHALL 正确处理中文、英文等各种语言字符
5. WHEN 输入的HTML是静态快照 THEN 系统 SHALL 成功处理已渲染的HTML内容
