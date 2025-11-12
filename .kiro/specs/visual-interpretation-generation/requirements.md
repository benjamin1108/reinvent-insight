# Requirements Document

## Introduction

本功能为文章深度解读添加可视化解读生成能力。系统将在深度解读完成后，使用 AI 将文章内容转换为高度可视化的网页形式，并在 ReadingView 中提供原文与可视化解读的切换功能。可视化解读基于 text2html.txt 中定义的设计系统和布局规范生成。

## Glossary

- **Visual Interpretation**: 可视化解读，指使用特定设计系统将文章内容转换为高度可视化的网页形式
- **Deep Analysis**: 深度解读，指系统生成的完整文章分析内容（现有功能）
- **Text2HTML Prompt**: text2html.txt 文件中定义的提示词，用于指导 AI 生成可视化网页
- **Background Task**: 后台任务，指在用户阅读深度解读时，系统在后台异步生成可视化解读的任务
- **Generation Worker**: 生成工作器，负责调用 AI 模型生成可视化 HTML 的后端组件
- **Display Mode Toggle**: 显示模式切换，指用户在原文和可视化解读之间切换的 UI 控件
- **HTML Content Storage**: HTML 内容存储，指保存生成的可视化 HTML 内容的存储机制

## Requirements

### Requirement 1

**User Story:** 作为系统，我希望在深度解读完成后自动启动可视化解读生成任务，以便为用户提供可视化内容而不影响其阅读体验

#### Acceptance Criteria

1. WHEN 深度解读生成完成，THE System SHALL 自动启动可视化解读生成的后台任务
2. THE Background Task SHALL 不阻塞用户查看深度解读内容
3. THE System SHALL 将生成任务添加到任务队列中进行异步处理
4. THE System SHALL 记录任务状态（pending, processing, completed, failed）
5. IF 生成任务失败，THEN THE System SHALL 记录错误日志并支持重试机制

### Requirement 2

**User Story:** 作为系统，我希望使用 text2html.txt 中的提示词调用 AI 生成可视化 HTML，以便生成符合设计规范的高质量可视化内容

#### Acceptance Criteria

1. THE Generation Worker SHALL 读取 text2html.txt 文件作为系统提示词
2. THE Generation Worker SHALL 将深度解读的完整文本作为用户输入传递给 AI 模型
3. THE Generation Worker SHALL 使用 Gemini API 调用 AI 模型生成 HTML 内容
4. THE System SHALL 验证生成的 HTML 内容格式正确且包含必要的 CSS 样式
5. THE System SHALL 将生成的 HTML 内容保存到存储系统中

### Requirement 3

**User Story:** 作为系统，我希望将生成的可视化 HTML 与对应的文章关联存储，以便用户访问时能够快速加载

#### Acceptance Criteria

1. THE System SHALL 为每篇文章的可视化解读分配唯一的存储路径
2. THE System SHALL 将生成的 HTML 内容保存为独立文件
3. THE System SHALL 在文章元数据中记录可视化解读的生成状态和文件路径
4. THE System SHALL 支持可视化解读的版本管理（如果深度解读重新生成）
5. THE System SHALL 在文件系统中使用合理的目录结构组织可视化 HTML 文件

### Requirement 4

**User Story:** 作为用户，我希望在可视化解读生成完成后看到切换控件，以便我可以选择查看原文或可视化解读

#### Acceptance Criteria

1. WHEN 可视化解读生成完成，THE ReadingView SHALL 显示显示模式切换控件
2. THE Display Mode Toggle SHALL 提供两个选项："Deep Insight"（完整解读）和"Quick Insight"（可视化解读）
3. THE ReadingView SHALL 默认显示 Deep Insight 模式
4. WHERE 可视化解读尚未生成，THE ReadingView SHALL 隐藏切换控件或显示"生成中"状态
5. THE Display Mode Toggle SHALL 使用与现有设计风格一致的视觉样式

### Requirement 5

**User Story:** 作为用户，我希望能够在 Deep Insight 和 Quick Insight 之间流畅切换，以便根据需求选择不同的阅读方式

#### Acceptance Criteria

1. WHEN 用户点击"Quick Insight"选项，THE ReadingView SHALL 加载并显示生成的可视化 HTML 内容
2. WHEN 用户点击"Deep Insight"选项，THE ReadingView SHALL 显示原始的深度解读内容
3. THE ReadingView SHALL 在模式切换时提供平滑的视觉过渡效果
4. THE ReadingView SHALL 在 Quick Insight 模式下隐藏目录侧边栏
5. WHEN 切换到 Deep Insight 模式，THE ReadingView SHALL 自动退出全屏模式（如果处于全屏状态）

### Requirement 6

**User Story:** 作为用户，我希望 Quick Insight 模式提供沉浸式的全屏阅读体验，以便专注于可视化内容

#### Acceptance Criteria

1. WHEN 用户切换到 Quick Insight 模式且使用桌面设备，THE ReadingView SHALL 自动进入全屏模式
2. THE ReadingView SHALL 在 Quick Insight 模式下使用 iframe 或隔离的容器渲染 HTML 内容
3. THE System SHALL 确保可视化 HTML 的样式不与主应用样式冲突
4. THE ReadingView SHALL 在全屏模式下显示明显的退出按钮
5. WHERE 用户使用移动设备，THE ReadingView SHALL 不自动进入全屏模式，仅显示可视化内容

### Requirement 7

**User Story:** 作为用户，我希望能够方便地退出 Quick Insight 的全屏模式，以便快速切换到其他任务

#### Acceptance Criteria

1. WHEN 用户在 Quick Insight 全屏模式下按下 ESC 键，THE ReadingView SHALL 退出全屏模式
2. THE ReadingView SHALL 在全屏模式下显示明显的退出按钮（位于屏幕右上角或其他显眼位置）
3. WHEN 用户点击退出按钮，THE ReadingView SHALL 退出全屏模式
4. WHEN 用户切换到 Deep Insight 模式，THE ReadingView SHALL 自动退出全屏模式
5. THE ReadingView SHALL 在退出全屏后保持在当前选择的显示模式（除非用户主动切换）

### Requirement 8

**User Story:** 作为系统，我希望监控可视化解读生成任务的进度，以便向用户提供实时反馈

#### Acceptance Criteria

1. THE System SHALL 通过 WebSocket 或 SSE 向前端推送生成任务的状态更新
2. THE ReadingView SHALL 在可视化解读生成过程中显示进度指示器
3. WHEN 生成完成，THE System SHALL 通知前端更新 UI 显示切换控件
4. IF 生成失败，THEN THE System SHALL 向用户显示错误提示和重试选项
5. THE System SHALL 记录生成任务的开始时间、完成时间和耗时

### Requirement 9

**User Story:** 作为开发者，我希望可视化解读生成功能具有良好的错误处理和重试机制，以便提高系统的可靠性

#### Acceptance Criteria

1. THE System SHALL 在 AI API 调用失败时自动重试最多 3 次
2. THE System SHALL 在重试之间使用指数退避策略
3. IF 所有重试失败，THEN THE System SHALL 记录详细错误信息并标记任务为失败状态
4. THE System SHALL 提供手动重新生成可视化解读的接口
5. THE System SHALL 在生成过程中处理超时情况（设置合理的超时时间）

### Requirement 10

**User Story:** 作为系统，我希望可视化解读生成功能复用现有的模型配置，以便保持配置的一致性和简洁性

#### Acceptance Criteria

1. THE System SHALL 使用与深度解读相同的 AI 模型配置生成可视化解读
2. THE System SHALL 复用现有的 API 密钥和模型参数配置
3. THE System SHALL 支持通过配置文件设置可视化 HTML 的存储路径
4. THE System SHALL 使用与深度解读相同的任务队列和工作器机制
5. THE System SHALL 在现有配置文件中添加可视化解读相关的简单开关（启用/禁用）

### Requirement 11

**User Story:** 作为用户，我希望可视化解读的内容质量高且符合设计规范，以便获得良好的阅读体验

#### Acceptance Criteria

1. THE Generated HTML SHALL 严格遵循 text2html.txt 中定义的设计系统（色彩、字体、布局）
2. THE Generated HTML SHALL 包含完整的内联 CSS 样式
3. THE Generated HTML SHALL 使用语义化的 HTML5 标签
4. THE Generated HTML SHALL 正确识别文章的信息结构并使用合适的组件呈现
5. THE Generated HTML SHALL 在不同屏幕尺寸下保持良好的响应式布局

### Requirement 11

**User Story:** 作为用户，我希望可视化解读的内容质量高且符合设计规范，以便获得良好的阅读体验

#### Acceptance Criteria

1. THE Generated HTML SHALL 严格遵循 text2html.txt 中定义的设计系统（色彩、字体、布局）
2. THE Generated HTML SHALL 包含完整的内联 CSS 样式
3. THE Generated HTML SHALL 使用语义化的 HTML5 标签
4. THE Generated HTML SHALL 正确识别文章的信息结构并使用合适的组件呈现
5. THE Generated HTML SHALL 在不同屏幕尺寸下保持良好的响应式布局

### Requirement 12

**User Story:** 作为系统，我希望优化可视化解读的加载性能，以便用户能够快速查看内容

#### Acceptance Criteria

1. THE System SHALL 在用户打开文章时预加载可视化解读的元数据
2. THE System SHALL 仅在用户切换到 Quick Insight 模式时加载完整的 HTML 内容
3. THE System SHALL 缓存已加载的可视化 HTML 内容避免重复请求
4. THE System SHALL 压缩存储的 HTML 文件以减少传输大小
5. THE System SHALL 在 HTTP 响应中设置适当的缓存头

### Requirement 13

**User Story:** 作为用户，我希望在可视化解读生成失败时仍能正常阅读深度解读原文，以便不影响我的使用体验

#### Acceptance Criteria

1. WHERE 可视化解读生成失败，THE ReadingView SHALL 继续正常显示 Deep Insight 模式
2. THE System SHALL 向用户显示友好的错误提示（如"Quick Insight 生成失败"）
3. THE ReadingView SHALL 提供"重新生成"按钮允许用户手动触发生成
4. THE System SHALL 不因可视化解读生成失败而影响其他功能
5. THE System SHALL 记录失败原因以便后续分析和改进
