# Requirements Document

## Introduction

本项目需要重构当前分散的 prompt 管理系统，实现单一数据源原则，避免 prompt 内容的重复定义和维护困难。当前系统中 prompt 分散在多个文件中（`prompt/` 目录下的文本文件和 `src/reinvent_insight/prompts.py` 中的模板），导致修改一处时需要同步更新多处，容易出现不一致的问题。

## Glossary

- **Prompt System**: 提示词系统，用于管理和组织所有 AI 模型的输入提示词
- **Base Prompt**: 基础提示词，定义 AI 的角色、风格和核心要求
- **Template Prompt**: 模板提示词，包含占位符的提示词模板，用于动态生成具体任务的提示词
- **Single Source of Truth**: 单一数据源，确保每个数据只在一个地方定义和维护
- **Prompt Manager**: 提示词管理器，负责加载、缓存和提供提示词的模块

## Requirements

### Requirement 1: 统一 Prompt 存储位置

**User Story:** 作为开发者，我希望所有 prompt 定义都存储在一个统一的位置，这样我只需要在一个地方修改就能生效

#### Acceptance Criteria

1. WHEN 系统启动时，THE Prompt System SHALL 从单一的配置目录加载所有 prompt 定义
2. THE Prompt System SHALL 支持将 prompt 定义存储为独立的文本文件或 YAML 配置文件
3. THE Prompt System SHALL NOT 在 Python 代码中硬编码任何完整的 prompt 内容
4. WHERE prompt 需要在代码中引用时，THE Prompt System SHALL 通过标识符（key）来引用，而非直接嵌入内容

### Requirement 2: Prompt 模板化和组合

**User Story:** 作为开发者，我希望能够灵活组合不同的 prompt 片段，避免重复定义相同的规则

#### Acceptance Criteria

1. THE Prompt System SHALL 支持将 prompt 拆分为可复用的片段（fragments）
2. WHEN 生成最终 prompt 时，THE Prompt System SHALL 能够组合多个 prompt 片段
3. THE Prompt System SHALL 支持 prompt 片段的继承和覆盖机制
4. WHERE 多个任务共享相同的规则时，THE Prompt System SHALL 允许定义公共规则片段并在多处引用

### Requirement 3: Prompt 版本管理和验证

**User Story:** 作为开发者，我希望系统能够验证 prompt 的完整性，并在 prompt 缺失或格式错误时给出明确提示

#### Acceptance Criteria

1. WHEN 系统加载 prompt 时，THE Prompt System SHALL 验证所有必需的 prompt 是否存在
2. IF prompt 文件缺失或格式错误，THEN THE Prompt System SHALL 记录详细的错误信息并抛出异常
3. THE Prompt System SHALL 支持为 prompt 添加版本标识
4. THE Prompt System SHALL 在日志中记录当前使用的 prompt 版本信息

### Requirement 4: 动态 Prompt 参数替换

**User Story:** 作为开发者，我希望能够在 prompt 模板中使用占位符，并在运行时动态替换为实际值

#### Acceptance Criteria

1. THE Prompt System SHALL 支持在 prompt 模板中使用占位符语法（如 `{variable_name}`）
2. WHEN 生成最终 prompt 时，THE Prompt System SHALL 将占位符替换为提供的实际值
3. IF 必需的参数未提供，THEN THE Prompt System SHALL 抛出明确的错误信息
4. THE Prompt System SHALL 支持可选参数，当参数未提供时使用默认值或空字符串

### Requirement 5: Prompt 热重载支持

**User Story:** 作为开发者，我希望在开发环境中修改 prompt 后无需重启服务即可生效

#### Acceptance Criteria

1. WHERE 系统运行在开发模式时，THE Prompt System SHALL 支持热重载 prompt 配置
2. WHEN prompt 文件被修改时，THE Prompt System SHALL 在下次使用时自动重新加载
3. THE Prompt System SHALL 提供手动刷新 prompt 缓存的接口
4. WHERE 系统运行在生产模式时，THE Prompt System SHALL 在启动时加载 prompt 并缓存，不进行热重载

### Requirement 6: 向后兼容性

**User Story:** 作为开发者，我希望重构后的系统能够与现有代码兼容，避免大规模修改现有业务逻辑

#### Acceptance Criteria

1. THE Prompt System SHALL 提供与现有 `prompts.py` 模块兼容的接口
2. WHEN 现有代码调用旧的 prompt 常量时，THE Prompt System SHALL 返回正确的 prompt 内容
3. THE Prompt System SHALL 在过渡期内同时支持新旧两种访问方式
4. THE Prompt System SHALL 在使用旧接口时记录弃用警告
