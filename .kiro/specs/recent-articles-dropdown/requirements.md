# Requirements Document

## Introduction

本需求文档定义了在reinvent Insight应用中添加"近期解读"下拉菜单功能。该功能将在页面顶部AppHeader组件的"笔记库"按钮右侧添加一个新按钮，用户鼠标悬停时显示下拉列表，展示最近创建的文章，按时间倒序排列。

## Glossary

- **AppHeader**: 应用顶部导航栏组件，包含品牌标识、导航按钮和操作按钮
- **近期解读按钮**: 新增的导航按钮，位于"笔记库"按钮右侧
- **下拉列表**: 鼠标悬停在"近期解读"按钮上时显示的文章列表
- **文章**: 系统中已生成的摘要文档，包含标题、创建时间等元数据
- **时间倒序**: 按照创建时间从新到旧的排序方式
- **Frontend**: 前端Vue.js应用，负责用户界面展示
- **Backend API**: 后端FastAPI服务，提供数据接口

## Requirements

### Requirement 1

**User Story:** 作为一个用户，我想在页面顶部看到"近期解读"按钮，以便快速访问最新的文章

#### Acceptance Criteria

1. WHEN THE Frontend 加载完成，THE AppHeader SHALL 在"笔记库"按钮右侧显示"近期解读"按钮
2. THE "近期解读"按钮 SHALL 使用与"笔记库"按钮相同的视觉样式和尺寸
3. WHEN 用户处于移动端视图，THE "近期解读"按钮 SHALL 与其他导航按钮保持一致的响应式布局
4. THE "近期解读"按钮 SHALL 在桌面端和移动端都可见

### Requirement 2

**User Story:** 作为一个用户，我想通过鼠标悬停在"近期解读"按钮上看到下拉列表，以便浏览最新的文章

#### Acceptance Criteria

1. WHEN 用户将鼠标悬停在"近期解读"按钮上，THE Frontend SHALL 显示下拉列表
2. WHEN 用户将鼠标移出"近期解读"按钮和下拉列表区域，THE Frontend SHALL 在300毫秒延迟后隐藏下拉列表
3. THE 下拉列表 SHALL 显示在按钮正下方，与按钮左边缘对齐
4. THE 下拉列表 SHALL 具有科技风格的视觉效果，包括半透明背景、模糊效果和边框阴影
5. WHEN 下拉列表显示时，THE Frontend SHALL 播放平滑的淡入动画效果

### Requirement 3

**User Story:** 作为一个用户，我想在下拉列表中看到最近的文章，以便快速找到我感兴趣的内容

#### Acceptance Criteria

1. THE Backend API SHALL 提供获取最近文章列表的接口，返回按创建时间倒序排列的文章
2. THE 下拉列表 SHALL 显示最多10篇最近的文章
3. WHEN THE Backend API 返回文章数据，THE Frontend SHALL 按照modified_at字段进行时间倒序排序
4. THE 每个文章条目 SHALL 显示文章标题（优先显示title_cn，其次title_en）
5. THE 每个文章条目 SHALL 显示相对时间（例如："2小时前"、"3天前"）
6. WHEN 文章列表为空，THE 下拉列表 SHALL 显示"暂无近期解读"的提示信息

### Requirement 4

**User Story:** 作为一个用户，我想点击下拉列表中的文章条目，以便直接跳转到该文章的阅读页面

#### Acceptance Criteria

1. WHEN 用户点击下拉列表中的文章条目，THE Frontend SHALL 导航到该文章的阅读页面
2. WHEN 用户点击文章条目，THE 下拉列表 SHALL 立即关闭
3. THE 文章条目 SHALL 在鼠标悬停时显示高亮效果
4. THE 文章条目 SHALL 使用文章的hash值构建导航URL（格式：/d/{hash}）
5. WHEN 用户点击文章条目，THE Frontend SHALL 使用客户端路由进行页面跳转，避免页面刷新

### Requirement 5

**User Story:** 作为一个用户，我想在移动端也能使用"近期解读"功能，以便在不同设备上获得一致的体验

#### Acceptance Criteria

1. WHEN 用户在移动端点击"近期解读"按钮，THE Frontend SHALL 显示下拉列表
2. THE 移动端下拉列表 SHALL 适应屏幕宽度，最大宽度为屏幕宽度减去左右边距
3. WHEN 用户在移动端点击下拉列表外的区域，THE Frontend SHALL 关闭下拉列表
4. THE 移动端文章条目 SHALL 具有足够的触摸目标尺寸（最小44px高度）
5. THE 移动端下拉列表 SHALL 在小屏幕上保持良好的可读性和可用性
