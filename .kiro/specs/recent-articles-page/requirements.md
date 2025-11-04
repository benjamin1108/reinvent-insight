# Requirements Document

## Introduction

本功能旨在将当前错误地放置在 Hero 区域的"最近文章时间轴"功能重构为一个独立的页面视图。用户登录后将默认进入这个最近文章页面，而不是笔记库页面。同时，需要恢复 Hero 区域和 Header 的原始设计，移除不合理的时间轴展示。

## Glossary

- **Hero Section**: 应用首页的英雄区域，用于展示欢迎信息和登录引导
- **Recent Timeline**: 最近文章时间轴组件，以时间轴形式展示最近更新的文章
- **Library View**: 笔记库视图，展示所有文章的分类列表
- **Recent View**: 新增的最近文章视图，作为独立页面展示最近文章时间轴
- **App Header**: 应用顶部导航栏组件
- **View Router**: 应用的视图路由系统，控制不同页面的显示

## Requirements

### Requirement 1

**User Story:** 作为已登录用户，我希望登录后默认看到最近文章页面，以便快速访问最新更新的内容

#### Acceptance Criteria

1. WHEN 用户成功登录，THE View Router SHALL 将 currentView 设置为 'recent'
2. WHEN 用户访问根路径 '/' 且已认证，THE View Router SHALL 显示 Recent View
3. THE Recent View SHALL 展示最近更新的文章时间轴
4. THE Recent View SHALL 支持点击文章跳转到阅读视图

### Requirement 2

**User Story:** 作为用户，我希望在导航栏中看到"最近文章"和"笔记库"两个独立的导航选项，以便在两个视图之间切换

#### Acceptance Criteria

1. THE App Header SHALL 在导航栏中显示"最近文章"按钮
2. THE App Header SHALL 在导航栏中显示"笔记库"按钮
3. WHEN 用户点击"最近文章"按钮，THE View Router SHALL 切换到 Recent View
4. WHEN 用户点击"笔记库"按钮，THE View Router SHALL 切换到 Library View
5. THE App Header SHALL 高亮显示当前激活的导航按钮

### Requirement 3

**User Story:** 作为开发者，我希望 Hero Section 恢复到原始设计，不再包含最近文章时间轴，以保持首页的简洁性

#### Acceptance Criteria

1. THE Hero Section SHALL 移除 recent-timeline 组件的引用
2. THE Hero Section SHALL 移除 recentArticles 和 recentLoading 属性
3. THE Hero Section SHALL 移除文章点击事件处理
4. THE Hero Section SHALL 仅在未登录状态下显示欢迎信息和登录按钮
5. WHEN 用户已登录，THE Hero Section SHALL 不再显示

### Requirement 4

**User Story:** 作为用户，我希望最近文章页面有清晰的标题和说明，以便理解页面的用途

#### Acceptance Criteria

1. THE Recent View SHALL 在页面顶部显示"最近文章"标题
2. THE Recent View SHALL 显示副标题说明页面用途
3. THE Recent View SHALL 使用与其他视图一致的样式设计
4. THE Recent View SHALL 在加载时显示加载状态指示器

### Requirement 5

**User Story:** 作为开发者，我希望创建一个新的 RecentView 组件，以便将最近文章功能独立管理

#### Acceptance Criteria

1. THE System SHALL 创建 RecentView 组件文件（JS、HTML、CSS）
2. THE RecentView SHALL 接收 articles 和 loading 属性
3. THE RecentView SHALL 发出 article-click 事件
4. THE RecentView SHALL 复用现有的 RecentTimeline 组件
5. THE System SHALL 在 app.js 中注册 RecentView 组件

### Requirement 6

**User Story:** 作为用户，我希望在最近文章页面看到更多文章（不限于6篇），以便浏览更多最近更新的内容

#### Acceptance Criteria

1. THE Recent View SHALL 显示至少 10 篇最近文章
2. THE RecentTimeline SHALL 接受 maxItems 属性控制显示数量
3. WHEN maxItems 未指定，THE RecentTimeline SHALL 显示所有文章
4. THE Recent View SHALL 在没有文章时显示友好的空状态提示

### Requirement 7

**User Story:** 作为开发者，我希望移除 app.js 中与 Hero Section 时间轴相关的调试代码，以保持代码整洁

#### Acceptance Criteria

1. THE System SHALL 从 app.js 移除 recentArticles 状态变量
2. THE System SHALL 从 app.js 移除 recentLoading 状态变量
3. THE System SHALL 从 app.js 移除 loadRecentArticles 方法
4. THE System SHALL 保留文章数据加载逻辑在 loadSummaries 方法中
5. THE Recent View SHALL 直接使用 summaries 数据源
