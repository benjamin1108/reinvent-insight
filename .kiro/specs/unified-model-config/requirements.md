# Requirements Document

## Introduction

本文档定义了统一模型配置系统的需求。当前系统中存在多处硬编码的模型调用逻辑，不同模块使用不同的模型版本和参数配置，导致维护困难且配置不一致。本需求旨在建立一个统一的、可配置的模型管理系统，支持按任务类型配置不同的模型和参数。

## Glossary

- **Model Configuration System**: 模型配置系统，负责管理所有 AI 模型的配置信息
- **Task Type**: 任务类型，指系统中不同的业务功能，如视频摘要、PDF处理、可视化生成等
- **Model Provider**: 模型提供商，如 Gemini、XAI、Alibaba 等
- **Generation Config**: 生成配置，包括 temperature、max_tokens 等模型参数
- **Model Client**: 模型客户端，封装了与特定模型提供商交互的逻辑

## Requirements

### Requirement 1

**User Story:** 作为系统管理员，我希望能够在配置文件中统一管理所有任务类型的模型配置，以便于维护和调整

#### Acceptance Criteria

1. WHEN 系统启动时，THE Model Configuration System SHALL 从配置文件加载所有任务类型的模型配置
2. THE Model Configuration System SHALL 支持为每个任务类型指定不同的模型提供商和模型名称
3. THE Model Configuration System SHALL 支持为每个任务类型配置独立的生成参数（temperature、max_tokens等）
4. WHERE 配置文件不存在或格式错误，THE Model Configuration System SHALL 使用默认配置并记录警告日志

### Requirement 2

**User Story:** 作为开发者，我希望通过统一的接口获取模型客户端，而不需要关心底层的模型提供商实现细节

#### Acceptance Criteria

1. THE Model Configuration System SHALL 提供工厂方法根据任务类型返回对应的模型客户端
2. THE Model Client SHALL 提供统一的 generate_content 接口用于文本生成
3. THE Model Client SHALL 提供统一的 generate_content_with_file 接口用于多模态生成
4. WHEN 请求的任务类型不存在时，THE Model Configuration System SHALL 返回默认配置的模型客户端

### Requirement 3

**User Story:** 作为开发者，我希望所有模块都使用统一的模型配置系统，消除硬编码的模型调用逻辑

#### Acceptance Criteria

1. THE summarizer module SHALL 通过 Model Configuration System 获取模型客户端
2. THE pdf_processor module SHALL 通过 Model Configuration System 获取模型客户端
3. THE visual_worker module SHALL 通过 Model Configuration System 获取模型客户端
4. THE System SHALL NOT 包含任何硬编码的模型名称或 API 配置

### Requirement 4

**User Story:** 作为系统管理员，我希望能够通过环境变量覆盖配置文件中的模型配置，以便于在不同环境中灵活调整

#### Acceptance Criteria

1. WHERE 环境变量定义了任务类型的模型配置，THE Model Configuration System SHALL 优先使用环境变量的值
2. THE Model Configuration System SHALL 支持通过环境变量配置 API Key
3. THE Model Configuration System SHALL 支持通过环境变量配置模型名称
4. THE Model Configuration System SHALL 支持通过环境变量配置生成参数

### Requirement 5

**User Story:** 作为开发者，我希望模型配置系统支持速率限制和重试机制，确保 API 调用的稳定性

#### Acceptance Criteria

1. THE Model Client SHALL 实现全局速率限制，控制 API 调用频率
2. WHEN API 调用失败时，THE Model Client SHALL 自动重试最多3次
3. THE Model Client SHALL 在重试时使用指数退避策略
4. THE Model Client SHALL 记录所有 API 调用的日志和错误信息

### Requirement 6

**User Story:** 作为系统管理员，我希望配置文件采用易读的格式，并包含清晰的注释说明

#### Acceptance Criteria

1. THE Model Configuration System SHALL 使用 YAML 格式存储配置
2. THE configuration file SHALL 包含每个配置项的注释说明
3. THE configuration file SHALL 提供所有任务类型的配置示例
4. THE configuration file SHALL 包含默认配置的推荐值
