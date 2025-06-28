# 前端组件样式依赖文档

## 概述

本文档记录了 reinvent-insight 项目前端组件的样式架构和依赖关系。我们采用了**基础样式 + 组件特定样式**的分层架构，确保样式的一致性和可维护性。

## 样式架构

### 1. 基础样式层 (`/web/css/base/`)

基础样式提供了全局可复用的样式定义，所有组件都可以直接使用这些样式类。

#### **typography.css** - 字体系统
- **作用**：定义全局字体栈和字体变量
- **主要内容**：
  ```css
  --font-primary: 'JetBrains Mono', 'Consolas', ...
  --font-code: 'SFMono-Regular', 'Consolas', ...
  --font-ui: 'PingFang SC', 'Helvetica Neue', ...
  ```
- **使用方式**：组件自动继承，无需额外引入

#### **effects.css** - 视觉效果
- **作用**：定义通用的视觉效果类
- **主要样式类**：
  - `.tech-gradient` - 科技感渐变背景
  - `.tech-gradient-dark` - 深色渐变变体
  - `.glow-effect` - 发光效果
  - `.glow-effect-subtle` - 柔和发光
  - `.glow-effect-strong` - 强烈发光
  - `.is-dragging-toc` - 拖拽状态
- **使用方式**：在组件HTML中直接添加类名

#### **content.css** - 内容展示
- **作用**：定义文章内容的展示样式
- **主要样式类**：
  - `.prose-tech` - 科技风格的文章内容样式
- **使用方式**：在文章内容容器上添加该类

### 2. 组件样式层 (`/web/components/`)

每个组件只定义自身特有的样式，通过组合基础样式类来实现完整效果。

## 样式引用策略

### 原则

1. **DRY原则**：不要重复定义基础样式
2. **单一职责**：组件CSS只负责组件特有样式
3. **组合优于继承**：通过组合基础样式类实现效果

### 实施方式

#### ✅ 正确的做法
```html
<!-- 使用基础样式类 -->
<div class="modal-content tech-gradient glow-effect">
  <!-- 组件内容 -->
</div>
```

```css
/* 组件CSS只定义特有样式 */
.modal-content {
  position: relative;
  border-radius: 12px;
  padding: 2rem;
}
```

#### ❌ 错误的做法
```css
/* 不要在组件中重复定义基础样式 */
.modal-content {
  background: linear-gradient(...); /* 错误：重复定义tech-gradient */
  box-shadow: 0 0 20px ...; /* 错误：重复定义glow-effect */
}
```

## 组件样式依赖清单

### 基础组件 (Shared)

| 组件 | 依赖的基础样式 | 说明 |
|-----|---------------|------|
| TechButton | 无 | 完全独立，自定义按钮样式系统 |
| ProgressBar | 无 | 完全独立 |
| VersionSelector | 无 | 完全独立 |

### 通用组件 (Common)

| 组件 | 依赖的基础样式 | 说明 |
|-----|---------------|------|
| LoginModal | `tech-gradient`, `glow-effect` | 模态框背景效果 |
| SummaryCard | `tech-gradient`, `glow-effect` | 卡片背景和悬停效果 |
| Filter | 无 | 自定义渐变效果 |
| VideoPlayer | 无 | 自定义样式 |
| TableOfContents | 无 | 完全独立 |
| AppHeader | 无 | 完全独立 |
| Toast | 无 | 完全独立 |

### 视图组件 (Views)

| 组件 | 依赖的基础样式 | 说明 |
|-----|---------------|------|
| HeroSection | 无 | 自定义渐变动画 |
| CreateView | `prose-tech` | 文章内容预览 |
| LibraryView | `glow-effect`* | 通过子组件继承 |
| ReadingView | `prose-tech` | 文章内容显示 |

*注：LibraryView 本身不直接使用，但其子组件 SummaryCard 使用了这些样式

## 样式加载机制

### ComponentLoader 自动注入

ComponentLoader 在加载组件时会自动：
1. 加载组件的 CSS 文件
2. 将样式注入到 `<head>` 中
3. 使用 `data-component-style` 属性防止重复加载

### 基础样式引入

基础样式需要在主页面中手动引入：
```html
<!-- 在 index.html 或测试页面中 -->
<link rel="stylesheet" href="/css/base/typography.css">
<link rel="stylesheet" href="/css/base/effects.css">
<link rel="stylesheet" href="/css/base/content.css">
```

## 最佳实践

### 1. 创建新组件时

- 优先使用基础样式类
- 只定义组件特有的布局和修饰
- 在组件CSS顶部注明依赖的基础样式

```css
/* MyComponent 组件样式 */
/* 
 * 样式策略：
 * - 使用全局基础样式类（tech-gradient, glow-effect）
 * - 组件只定义布局和特有样式
 */
```

### 2. 修改样式时

- 基础效果修改 → 编辑 `/css/base/` 下的文件
- 组件特有样式修改 → 编辑组件自身的 CSS 文件
- 避免在组件中覆盖基础样式

### 3. 样式隔离

- 使用具体的类名选择器，避免影响其他组件
- 合理使用CSS作用域
- 避免使用 `!important`（除非必要）

## 待优化事项

1. **CSS变量系统**：考虑将颜色、间距等提取为CSS变量
2. **样式工具类**：考虑引入更多原子化的工具类
3. **CSS预处理器**：评估是否需要引入 SCSS 或 Less
4. **CSS Modules**：评估是否需要更严格的样式隔离

## 维护指南

- 定期检查组件中是否有重复的样式定义
- 新增基础样式时更新此文档
- 组件样式变更时同步更新依赖清单
- 保持样式命名的一致性和语义化

---

最后更新：2024年（组件化重构完成后） 