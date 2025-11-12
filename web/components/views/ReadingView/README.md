# ReadingView 显示模式功能

## 概述

ReadingView 组件现在支持三种显示模式，用户可以根据需求选择不同的内容呈现方式：

1. **核心要点** (core-summary) - 显示文章的关键信息和核心观点
2. **精简摘要** (simplified-text) - 显示简洁易读的文章概要
3. **完整解读** (full-analysis) - 显示完整的文章内容（默认模式）

## 组件结构

```
ReadingView/
├── ReadingView.js          # 主组件（包含内联子组件定义）
├── ReadingView.html        # 主模板
├── ReadingView.css         # 主样式（包含所有子组件样式）
└── README.md              # 本文档
```

**注意**: CoreSummaryView 和 SimplifiedTextView 作为内联组件定义在 ReadingView.js 中，无需单独的文件。

## 使用方法

### 基本用法

```html
<reading-view
  :content="readingContent"
  :document-title="documentTitle"
  :document-title-en="documentTitleEn"
  :initial-display-mode="displayMode"
  :core-summary="coreSummary"
  :simplified-text="simplifiedText"
  @display-mode-change="handleDisplayModeChange">
</reading-view>
```

### Props

#### 显示模式相关

- `initialDisplayMode` (String, 默认: 'full-analysis')
  - 初始显示模式
  - 可选值: 'core-summary' | 'simplified-text' | 'full-analysis'

- `coreSummary` (Object, 默认: null)
  - 核心要点数据
  - 数据格式见下方"数据格式"部分

- `simplifiedText` (String, 默认: '')
  - 精简摘要内容
  - 支持纯文本或简单 Markdown

#### 其他 Props

- `content` (String) - 完整文章内容（HTML）
- `documentTitle` (String) - 文档标题（中文）
- `documentTitleEn` (String) - 文档标题（英文）
- `loading` (Boolean) - 加载状态
- `error` (String) - 错误信息
- `versions` (Array) - 版本列表
- `currentVersion` (Number) - 当前版本
- `initialShowToc` (Boolean) - 初始目录显示状态
- `initialTocWidth` (Number) - 初始目录宽度

### Events

- `display-mode-change` - 显示模式切换事件
  - 参数: `mode` (String) - 新的显示模式

- `toc-toggle` - 目录切换事件
- `toc-resize` - 目录调整大小事件
- `article-click` - 文章点击事件
- `version-change` - 版本切换事件

## 数据格式

### CoreSummary 数据格式

```javascript
{
  keyPoints: [
    {
      title: string,        // 要点标题
      content: string,      // 要点内容
      importance: 'high' | 'medium' | 'low'  // 重要程度
    }
  ],
  mainTheme: string,        // 主题
  tags: string[],           // 标签
  generatedAt: string       // ISO 8601 时间戳
}
```

### SimplifiedText 数据格式

```javascript
// 纯文本或简单 Markdown
"本文介绍了...\n\n主要观点包括：\n1. ...\n2. ...\n\n结论：..."
```

## 后端集成指南

### 当前状态

目前核心要点和精简摘要模式显示占位内容。后端数据接口已预留，需要实现以下 API：

### 需要实现的 API

#### 1. 获取核心要点

```
GET /api/public/doc/{docHash}/summary
```

响应格式：
```json
{
  "keyPoints": [
    {
      "title": "要点标题",
      "content": "要点内容",
      "importance": "high"
    }
  ],
  "mainTheme": "文章主题",
  "tags": ["标签1", "标签2"],
  "generatedAt": "2024-01-01T00:00:00Z"
}
```

#### 2. 获取精简摘要

```
GET /api/public/doc/{docHash}/simplified
```

响应格式：
```json
{
  "content": "精简摘要内容..."
}
```

### 集成步骤

1. 在 `app.js` 中取消注释 `loadCoreSummary` 和 `loadSimplifiedText` 方法
2. 在 `handleDisplayModeChange` 中取消注释数据加载逻辑
3. 实现后端 API 端点
4. 测试数据加载和错误处理

## 样式定制

### 主题色

组件使用以下主题色：
- 主色: `#22d3ee` (青色)
- 辅助色: `#3b82f6` (蓝色)
- 强调色: `#8b5cf6` (紫色)

### 响应式断点

- 桌面端: > 768px
- 移动端: ≤ 768px
- 极小屏幕: ≤ 480px

### 自定义样式

可以通过覆盖 CSS 变量来自定义样式：

```css
.reading-view {
  --primary-color: #22d3ee;
  --secondary-color: #3b82f6;
  --accent-color: #8b5cf6;
}
```

## 无障碍支持

- 键盘导航: Tab 键聚焦，左右箭头切换模式
- 屏幕阅读器: 使用 `aria-label` 和 `aria-current` 属性
- 高对比度模式: 自动适配系统设置
- 减少动画: 支持 `prefers-reduced-motion`

## 性能优化

- 使用 `v-if` 条件渲染，避免不必要的 DOM
- CSS 动画使用 GPU 加速（transform + opacity）
- 懒加载：仅在切换到对应模式时加载数据
- 数据缓存：避免重复请求

## 浏览器兼容性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 已知问题

无

## 未来计划

1. 添加用户偏好记忆功能
2. 支持模式对比（并排显示）
3. 添加自定义模式配置
4. 实现预加载优化
5. 添加离线缓存支持

## 更新日志

### v1.0.0 (2024-01-01)

- ✨ 新增三种显示模式切换功能
- ✨ 新增 ModeSelector 组件
- ✨ 新增 CoreSummaryView 占位组件
- ✨ 新增 SimplifiedTextView 占位组件
- 🎨 优化模式切换动画
- 📱 完善移动端响应式布局
- ♿ 添加无障碍支持
- 📝 添加完整文档
