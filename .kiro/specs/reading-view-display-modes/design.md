# Design Document

## Overview

本设计文档描述了 ReadingView 组件的三种显示模式功能的前端实现方案。该功能允许用户在"核心要点"、"精简摘要"和"完整解读"三种模式之间切换，以满足不同的阅读需求。设计遵循现有的组件架构和设计风格，确保与现有系统无缝集成。

## Architecture

### 组件结构

```
ReadingView (主组件)
├── ModeSelector (新增：模式选择器组件)
│   ├── 核心要点按钮
│   ├── 精简摘要按钮
│   └── 完整解读按钮
├── TOC Sidebar (现有：目录侧边栏 - 根据模式显示/隐藏)
└── Content Container (现有：内容容器 - 根据模式渲染不同内容)
    ├── CoreSummaryView (新增：核心要点视图 - 占位)
    ├── SimplifiedTextView (新增：精简摘要视图 - 占位)
    └── FullAnalysisView (现有：完整解读视图)
```

### 状态管理

使用 Vue 3 Composition API 的响应式状态管理：

```javascript
const displayMode = ref('full-analysis'); // 'core-summary' | 'simplified-text' | 'full-analysis'
const availableModes = [
  { id: 'core-summary', label: '核心要点', icon: '📌' },
  { id: 'simplified-text', label: '精简摘要', icon: '📝' },
  { id: 'full-analysis', label: '完整解读', icon: '📖' }
];
```

### 数据流

```
用户点击模式按钮
    ↓
ModeSelector 触发 @mode-change 事件
    ↓
ReadingView 更新 displayMode 状态
    ↓
Content Container 根据 displayMode 渲染对应视图
    ↓
TOC Sidebar 根据 displayMode 显示/隐藏
```

## Components and Interfaces

### 1. ModeSelector 组件

**职责**: 提供模式切换的UI控件

**Props**:
```javascript
{
  currentMode: {
    type: String,
    default: 'full-analysis',
    validator: (value) => ['core-summary', 'simplified-text', 'full-analysis'].includes(value)
  },
  modes: {
    type: Array,
    default: () => [
      { id: 'core-summary', label: '核心要点', icon: '📌' },
      { id: 'simplified-text', label: '精简摘要', icon: '📝' },
      { id: 'full-analysis', label: '完整解读', icon: '📖' }
    ]
  }
}
```

**Emits**:
```javascript
{
  'mode-change': (modeId: string) => void
}
```

**样式设计**:
- 使用 Tab 风格的按钮组
- 激活状态：渐变色底部边框 + 高亮文字颜色
- 非激活状态：灰色文字 + 透明背景
- Hover 效果：轻微背景色变化
- 响应式：移动端使用图标 + 缩写文字

### 2. CoreSummaryView 组件（占位）

**职责**: 显示核心要点模式的占位内容

**Props**:
```javascript
{
  // 预留后端数据接口
  summaryData: {
    type: Object,
    default: null
    // 预期格式：
    // {
    //   keyPoints: [
    //     { title: string, content: string, importance: 'high' | 'medium' | 'low' }
    //   ],
    //   mainTheme: string,
    //   tags: string[]
    // }
  }
}
```

**UI 设计**:
- 卡片式布局，每个要点一个卡片
- 使用图标标识重要程度
- 占位状态：显示友好的"即将推出"提示
- 配色：使用主题色 (#22d3ee) 的渐变背景

### 3. SimplifiedTextView 组件（占位）

**职责**: 显示精简摘要模式的占位内容

**Props**:
```javascript
{
  // 预留后端数据接口
  simplifiedContent: {
    type: String,
    default: ''
    // 预期格式：纯文本或简单 Markdown
  }
}
```

**UI 设计**:
- 简洁的文本布局，无复杂样式
- 较大字体（18px）和宽松行距（1.8）
- 占位状态：显示友好的"即将推出"提示
- 最大宽度限制（800px）以提升可读性

### 4. ReadingView 组件更新

**新增 Props**:
```javascript
{
  // 核心要点数据（预留）
  coreSummary: {
    type: Object,
    default: null
  },
  // 精简摘要数据（预留）
  simplifiedText: {
    type: String,
    default: ''
  },
  // 初始显示模式
  initialDisplayMode: {
    type: String,
    default: 'full-analysis'
  }
}
```

**新增 Emits**:
```javascript
{
  'display-mode-change': (mode: string) => void
}
```

**状态管理**:
```javascript
const displayMode = ref(props.initialDisplayMode);
const shouldShowToc = computed(() => displayMode.value === 'full-analysis');
```

## Data Models

### DisplayMode 枚举

```javascript
const DisplayMode = {
  CORE_SUMMARY: 'core-summary',
  SIMPLIFIED_TEXT: 'simplified-text',
  FULL_ANALYSIS: 'full-analysis'
};
```

### ModeConfig 接口

```javascript
interface ModeConfig {
  id: string;           // 模式ID
  label: string;        // 显示标签
  icon: string;         // 图标（emoji 或 icon class）
  showToc: boolean;     // 是否显示目录
  description: string;  // 模式描述
}
```

### CoreSummaryData 接口（预留）

```javascript
interface CoreSummaryData {
  keyPoints: Array<{
    title: string;
    content: string;
    importance: 'high' | 'medium' | 'low';
  }>;
  mainTheme: string;
  tags: string[];
  generatedAt: string;  // ISO 8601 时间戳
}
```

## Error Handling

### 模式切换失败

**场景**: 用户点击模式按钮但切换失败

**处理**:
1. 保持当前模式不变
2. 使用 Toast 组件显示错误提示："模式切换失败，请重试"
3. 记录错误日志到控制台
4. 不阻塞用户的其他操作

### 数据加载失败（预留）

**场景**: 后端数据加载失败

**处理**:
1. 显示占位内容或错误提示
2. 提供"重试"按钮
3. 允许用户切换到其他可用模式

### 浏览器兼容性

**场景**: 旧浏览器不支持某些 CSS 特性

**处理**:
1. 使用 CSS 降级方案（如移除过渡动画）
2. 确保核心功能可用
3. 在不支持的浏览器中显示简化版UI

## Testing Strategy

### 单元测试（可选）

**测试范围**:
- ModeSelector 组件的事件触发
- displayMode 状态的正确更新
- shouldShowToc 计算属性的逻辑

**测试工具**: Vitest + Vue Test Utils

### 集成测试（可选）

**测试场景**:
1. 用户点击模式按钮，内容容器正确切换
2. 模式切换时，目录侧边栏正确显示/隐藏
3. 模式状态在组件重新渲染后保持

### 手动测试

**必测场景**:
1. 三种模式的切换流畅性
2. 移动端响应式布局
3. 与现有功能（版本选择、目录滚动）的兼容性
4. 不同浏览器的兼容性（Chrome, Firefox, Safari, Edge）
5. 占位内容的视觉呈现

## UI/UX Design

### 模式选择器位置

**桌面端**: 
- 位置：文章标题上方，水平居中
- 布局：三个按钮横向排列
- 间距：按钮间距 8px

**移动端**:
- 位置：文章标题上方，占满宽度
- 布局：三个按钮横向排列，等宽分布
- 文字：使用图标 + 缩写（如"要点"、"摘要"、"全文"）

### 视觉过渡

**切换动画**:
```css
.content-fade-enter-active,
.content-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.content-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.content-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
```

**性能优化**:
- 使用 CSS transform 而非 position 变化
- 使用 will-change 提示浏览器优化
- 在低性能设备上禁用动画（通过 prefers-reduced-motion）

### 占位内容设计

**核心要点占位**:
```
┌─────────────────────────────────┐
│  📌 核心要点                     │
│                                 │
│  ┌───────────────────────────┐ │
│  │ 🚀 功能即将推出            │ │
│  │                           │ │
│  │ 我们正在开发核心要点提取   │ │
│  │ 功能，敬请期待！           │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
```

**精简摘要占位**:
```
┌─────────────────────────────────┐
│  📝 精简摘要                     │
│                                 │
│  功能即将推出                    │
│                                 │
│  我们正在开发精简摘要功能，      │
│  将为您提供简洁易读的文章概要。  │
│                                 │
│  敬请期待！                      │
└─────────────────────────────────┘
```

## Implementation Notes

### 文件结构

```
web/components/views/ReadingView/
├── ReadingView.js          # 主组件（更新）
├── ReadingView.html        # 模板（更新）
├── ReadingView.css         # 样式（更新）
├── ModeSelector.js         # 新增：模式选择器
├── ModeSelector.html       # 新增：模式选择器模板
├── ModeSelector.css        # 新增：模式选择器样式
├── CoreSummaryView.js      # 新增：核心要点视图
├── CoreSummaryView.html    # 新增：核心要点视图模板
├── CoreSummaryView.css     # 新增：核心要点视图样式
├── SimplifiedTextView.js   # 新增：精简摘要视图
├── SimplifiedTextView.html # 新增：精简摘要视图模板
└── SimplifiedTextView.css  # 新增：精简摘要视图样式
```

### 代码组织原则

1. **关注点分离**: 每个视图模式独立组件
2. **可扩展性**: 预留清晰的数据接口
3. **向后兼容**: 不破坏现有功能
4. **渐进增强**: 占位内容 → 真实数据

### 与现有系统集成

**app.js 更新**:
```javascript
// 在 ReadingView 的数据中添加新字段
data() {
  return {
    // ... 现有字段
    displayMode: 'full-analysis',
    coreSummary: null,
    simplifiedText: ''
  }
}
```

**事件处理**:
```javascript
methods: {
  handleDisplayModeChange(mode) {
    this.displayMode = mode;
    // 后续可在此处触发后端数据加载
  }
}
```

## Performance Considerations

### 渲染优化

1. **条件渲染**: 使用 `v-if` 而非 `v-show` 避免不必要的 DOM 渲染
2. **懒加载**: 仅在切换到对应模式时渲染内容
3. **虚拟滚动**: 如果核心要点数量很多，考虑使用虚拟滚动

### 内存管理

1. **组件卸载**: 切换模式时正确清理事件监听器
2. **数据缓存**: 缓存已加载的模式数据，避免重复请求

### 动画性能

1. **GPU 加速**: 使用 transform 和 opacity 触发 GPU 加速
2. **降级方案**: 在低性能设备上禁用动画
3. **帧率监控**: 确保动画保持 60fps

## Accessibility

### 键盘导航

- Tab 键可聚焦到模式选择器
- 左右箭头键可在模式间切换
- Enter/Space 键激活选中的模式

### 屏幕阅读器

- 为模式按钮添加 `aria-label`
- 使用 `aria-current` 标识当前激活模式
- 模式切换时通过 `aria-live` 区域通知用户

### 对比度

- 确保文字与背景的对比度符合 WCAG AA 标准（至少 4.5:1）
- 激活状态的视觉标识不仅依赖颜色

## Future Enhancements

### 后端集成（Phase 2）

1. 添加 API 端点获取核心要点和精简摘要数据
2. 实现数据加载状态和错误处理
3. 添加数据缓存机制

### 高级功能（Phase 3）

1. 用户偏好记忆：记住用户最后选择的模式
2. 模式对比：并排显示两种模式的内容
3. 自定义模式：允许用户配置显示内容

### 性能优化（Phase 4）

1. 预加载：在用户可能切换前预加载数据
2. 增量渲染：大内容分批渲染
3. Service Worker：离线缓存模式数据
