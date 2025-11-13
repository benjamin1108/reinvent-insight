# Requirements Document

## Introduction

本需求文档描述了将 ReadingView 组件中的 Quick Insight（可视化解读）展示方式从直接 HTML 注入改为 iframe 隔离的功能需求。当前实现使用 `v-html` 直接注入 HTML 内容，导致可视化解读的样式与主应用的样式相互污染。使用 iframe 可以完全隔离样式环境，同时保持布局和用户体验的一致性。

## Glossary

- **ReadingView**: 文章阅读视图组件，负责展示文章内容和可视化解读
- **Quick Insight**: 可视化解读模式，通过图表和可视化元素展示文章内容
- **Deep Insight**: 深度解读模式，展示完整的文章文本内容
- **Visual HTML**: 后端生成的包含完整样式和脚本的可视化 HTML 内容
- **CSS Pollution**: CSS 样式污染，指不同来源的样式相互影响导致显示异常
- **iframe**: HTML 内联框架元素，提供独立的浏览上下文和样式隔离

## Requirements

### Requirement 1

**User Story:** 作为用户，我希望在 Quick Insight 模式下看到的可视化内容样式完全独立，不受主应用样式影响，以便获得最佳的视觉体验。

#### Acceptance Criteria

1. WHEN 用户切换到 Quick Insight 模式，THE ReadingView SHALL 使用 iframe 元素加载可视化 HTML 内容
2. WHEN 可视化 HTML 在 iframe 中加载，THE ReadingView SHALL 确保 iframe 内的样式与主应用样式完全隔离
3. WHEN 可视化内容在 iframe 中渲染，THE ReadingView SHALL 保持与当前实现相同的布局位置和尺寸
4. WHEN iframe 加载可视化内容，THE ReadingView SHALL 确保 iframe 内的 JavaScript 脚本正常执行
5. WHEN 用户在 Quick Insight 模式下滚动，THE ReadingView SHALL 提供流畅的滚动体验

### Requirement 2

**User Story:** 作为用户，我希望在 Quick Insight 和 Deep Insight 模式之间切换时，布局保持一致且过渡平滑，以便获得连贯的使用体验。

#### Acceptance Criteria

1. WHEN 用户从 Deep Insight 切换到 Quick Insight，THE ReadingView SHALL 保持模式切换器在相同的视觉位置
2. WHEN 用户从 Quick Insight 切换到 Deep Insight，THE ReadingView SHALL 平滑过渡到文章内容视图
3. WHEN 模式切换发生，THE ReadingView SHALL 在 300 毫秒内完成视觉过渡
4. WHEN Quick Insight 模式激活，THE ReadingView SHALL 隐藏目录侧边栏
5. WHEN Deep Insight 模式激活，THE ReadingView SHALL 根据用户设置显示或隐藏目录侧边栏

### Requirement 3

**User Story:** 作为用户，我希望 iframe 能够自动适应内容高度，避免出现双重滚动条，以便获得更好的阅读体验。

#### Acceptance Criteria

1. WHEN 可视化内容加载到 iframe 中，THE ReadingView SHALL 自动调整 iframe 高度以匹配内容高度
2. WHEN iframe 内容高度变化，THE ReadingView SHALL 动态更新 iframe 高度
3. WHEN iframe 高度超过视口高度，THE ReadingView SHALL 仅在外部容器显示滚动条
4. WHEN 用户调整浏览器窗口大小，THE ReadingView SHALL 重新计算并调整 iframe 高度
5. IF iframe 内容加载失败，THEN THE ReadingView SHALL 显示友好的错误提示信息

### Requirement 4

**User Story:** 作为用户，我希望在移动设备上查看 Quick Insight 时，布局能够自适应屏幕尺寸，以便在小屏幕上也能获得良好的体验。

#### Acceptance Criteria

1. WHEN 用户在移动设备上访问 Quick Insight，THE ReadingView SHALL 确保 iframe 宽度适应屏幕宽度
2. WHEN 移动设备方向改变，THE ReadingView SHALL 重新调整 iframe 布局
3. WHEN 用户在移动设备上滚动，THE ReadingView SHALL 提供原生滚动体验
4. WHEN 模式切换器在移动设备上显示，THE ReadingView SHALL 确保按钮大小适合触摸操作
5. WHEN iframe 在移动设备上加载，THE ReadingView SHALL 优化加载性能以减少等待时间

### Requirement 5

**User Story:** 作为开发者，我希望 iframe 实现能够复用现有的可视化内容加载逻辑，以便减少代码重复和维护成本。

#### Acceptance Criteria

1. WHEN 实现 iframe 方案，THE ReadingView SHALL 复用现有的 `checkVisualStatus` 方法检查可视化状态
2. WHEN 实现 iframe 方案，THE ReadingView SHALL 复用现有的 `visualHtmlUrl` 计算逻辑
3. WHEN 实现 iframe 方案，THE ReadingView SHALL 保持现有的版本切换逻辑不变
4. WHEN 实现 iframe 方案，THE ReadingView SHALL 保持现有的错误处理机制
5. WHEN 实现 iframe 方案，THE ReadingView SHALL 移除不再需要的 `loadVisualHtml` 和 `visualHtmlContent` 相关代码
