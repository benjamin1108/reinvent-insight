# Requirements Document

## Introduction

本需求文档定义了扩展现有PDF工作流以支持多种文档格式（TXT、MD、WORD等）的功能。系统当前已具备完整的PDF多模态分析能力，需要以最小修改方案扩展支持其他常见文档格式，同时保持现有的处理流程、模型参数和代码架构不变。

## Glossary

- **System**: 指reinvent_insight文档分析系统
- **Text_Document**: 指TXT和MD格式的纯文本文档
- **Binary_Document**: 指PDF和WORD等需要多模态解析的二进制文档
- **Multimodal_Analysis**: 指使用Gemini API的多模态能力处理包含文字、图表、架构图等多种信息的文档
- **Text_Injection**: 指将文本内容直接注入到Prompt中进行分析的处理方式
- **Workflow**: 指现有的run_deep_summary_workflow工作流程
- **Document_Processor**: 指处理文档上传和内容提取的处理器组件

## Requirements

### Requirement 1: 支持TXT格式文档分析

**User Story:** 作为系统用户，我希望能够上传TXT格式的文档进行深度分析，以便获得与PDF文档相同质量的分析报告

#### Acceptance Criteria

1. WHEN 用户上传TXT格式文件，THE System SHALL 接受该文件并创建分析任务
2. WHEN 处理TXT文档时，THE System SHALL 读取文件内容并将其作为文本直接注入到Prompt中
3. WHEN 生成TXT文档的分析报告时，THE System SHALL 使用与PDF文档相同的工作流程和输出格式
4. THE System SHALL 支持UTF-8编码的TXT文件
5. THE System SHALL 为TXT文档生成唯一的文档标识符

### Requirement 2: 支持MD格式文档分析

**User Story:** 作为系统用户，我希望能够上传Markdown格式的文档进行深度分析，以便分析技术文档和说明文档

#### Acceptance Criteria

1. WHEN 用户上传MD格式文件，THE System SHALL 接受该文件并创建分析任务
2. WHEN 处理MD文档时，THE System SHALL 读取文件内容并保留Markdown格式标记
3. WHEN 将MD内容注入Prompt时，THE System SHALL 保持Markdown语法结构完整
4. THE System SHALL 支持UTF-8编码的MD文件
5. THE System SHALL 为MD文档生成唯一的文档标识符

### Requirement 3: 支持WORD格式文档分析

**User Story:** 作为系统用户，我希望能够上传WORD格式的文档进行深度分析，以便处理常见的办公文档

#### Acceptance Criteria

1. WHEN 用户上传DOCX格式文件，THE System SHALL 接受该文件并创建分析任务
2. WHEN 处理WORD文档时，THE System SHALL 使用多模态分析方式处理文档内容
3. THE System SHALL 支持DOCX格式（Office 2007及以上版本）
4. WHEN WORD文档包含图表和图片时，THE System SHALL 通过多模态分析提取视觉信息
5. THE System SHALL 为WORD文档生成唯一的文档标识符

### Requirement 4: 统一的文档处理接口

**User Story:** 作为开发者，我希望有一个统一的文档处理接口，以便系统能够透明地处理不同格式的文档

#### Acceptance Criteria

1. THE System SHALL 提供统一的文档上传API端点接受多种格式
2. WHEN 接收到文档上传请求时，THE System SHALL 根据文件扩展名识别文档类型
3. THE System SHALL 将文档类型信息传递给Document_Processor
4. THE Document_Processor SHALL 根据文档类型选择合适的处理策略（文本注入或多模态分析）
5. THE System SHALL 复用现有的Workflow而不修改其核心逻辑

### Requirement 5: 最小化代码修改

**User Story:** 作为开发者，我希望以最小的代码修改实现多格式支持，以便降低引入bug的风险并保持代码稳定性

#### Acceptance Criteria

1. THE System SHALL 复用现有的PDFContent数据模型结构
2. THE System SHALL 复用现有的run_deep_summary_workflow工作流
3. THE System SHALL 不修改现有的模型参数配置
4. THE System SHALL 不修改现有的Prompt模板核心逻辑
5. WHEN 添加新格式支持时，THE System SHALL 通过扩展而非修改现有代码实现功能

### Requirement 6: 文档内容提取

**User Story:** 作为系统，我需要能够从不同格式的文档中提取内容，以便进行统一的分析处理

#### Acceptance Criteria

1. WHEN 处理Text_Document时，THE System SHALL 直接读取文件内容为字符串
2. WHEN 处理Binary_Document时，THE System SHALL 上传文件到Gemini API获取文件引用
3. THE System SHALL 在DocumentContent对象中标识内容类型（text或multimodal）
4. WHEN 内容类型为text时，THE Workflow SHALL 使用文本注入方式调用Summarizer
5. WHEN 内容类型为multimodal时，THE Workflow SHALL 使用多模态方式调用Summarizer

### Requirement 7: 错误处理和文件验证

**User Story:** 作为系统用户，我希望在上传不支持的文件或损坏的文件时能够收到清晰的错误提示

#### Acceptance Criteria

1. WHEN 用户上传不支持格式的文件时，THE System SHALL 返回明确的错误消息
2. THE System SHALL 验证上传文件的大小不超过配置的最大限制
3. WHEN 文件读取失败时，THE System SHALL 记录详细的错误日志
4. THE System SHALL 在文件处理失败后清理临时文件
5. THE System SHALL 向用户返回友好的错误提示信息

### Requirement 8: 文档标识符生成

**User Story:** 作为系统，我需要为每个文档生成唯一的标识符，以便进行版本管理和文件追踪

#### Acceptance Criteria

1. THE System SHALL 为每种格式的文档生成唯一的标识符
2. WHEN 文档有标题时，THE System SHALL 在标识符中包含清理后的标题
3. WHEN 文档无标题时，THE System SHALL 使用文件名生成标识符
4. THE System SHALL 在标识符中包含文件哈希值以确保唯一性
5. THE System SHALL 使用与现有PDF文档相同的标识符生成逻辑
