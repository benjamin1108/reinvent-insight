# 桌面端隐藏目录时的宽度优化

## 问题描述

在修复 iPad Chrome 半屏问题后，PC 端隐藏目录时文章变成全宽，在大屏幕上阅读体验很差，从左到右阅读时眼睛移动距离过长。

## 原因分析

移动端的 CSS 样式没有正确闭合在 `@media (max-width: 768px)` 块内，导致以下样式影响了桌面端：

```css
.reading-view__article-wrapper {
  max-width: 100% !important; /* 这行影响了桌面端 */
}
```

## 解决方案

### 1. 修复 CSS 作用域

确保移动端的样式都在 `@media (max-width: 768px)` 块内，不影响桌面端。

### 2. 优化桌面端宽度策略

根据不同屏幕尺寸，提供最佳阅读宽度：

```css
/* 小屏幕（769px - 1200px）：充满屏幕 */
@media (min-width: 769px) and (max-width: 1200px) {
  .reading-view__content--no-toc .reading-view__article-wrapper {
    max-width: 100%;
  }
}

/* 中等屏幕（1201px - 1600px）：限制为 80% 宽度 */
@media (min-width: 1201px) and (max-width: 1600px) {
  .reading-view__content--no-toc .reading-view__article-wrapper {
    max-width: 80%;
  }
}

/* 大屏幕（> 1600px）：固定最大宽度 1200px */
@media (min-width: 1601px) {
  .reading-view__content--no-toc .reading-view__article-wrapper {
    max-width: 1200px;
  }
}
```

## 阅读体验优化原理

### 为什么要限制宽度？

根据排版学研究，最佳阅读行长度为：
- **理想值**：50-75 个字符（约 600-900px）
- **可接受范围**：45-90 个字符（约 500-1200px）
- **超过 90 个字符**：阅读效率显著下降

### 不同屏幕的策略

1. **小屏幕（769-1200px）**：
   - 屏幕本身不够宽，充满屏幕不会导致行过长
   - 使用 100% 宽度，最大化内容显示

2. **中等屏幕（1201-1600px）**：
   - 屏幕较宽，但不是超宽屏
   - 限制为 80% 宽度，留出适当边距
   - 约 960-1280px，在最佳阅读范围内

3. **大屏幕（>1600px）**：
   - 超宽屏幕，如果不限制会导致行过长
   - 固定最大宽度 1200px
   - 确保最佳阅读体验

## 测试场景

### 桌面端测试

1. **小屏幕测试（1024px）**：
   - 隐藏目录
   - 内容应该充满屏幕
   - 行长度适中

2. **中等屏幕测试（1440px）**：
   - 隐藏目录
   - 内容宽度约为屏幕的 80%
   - 左右有适当边距

3. **大屏幕测试（1920px+）**：
   - 隐藏目录
   - 内容宽度固定为 1200px
   - 居中显示，左右有较大边距

4. **超宽屏测试（2560px+）**：
   - 隐藏目录
   - 内容宽度仍为 1200px
   - 不会过宽，保持最佳阅读体验

### 移动端测试

确保修复没有影响移动端：
- iPad（768px）：内容应该充满屏幕
- 手机（<768px）：内容应该充满屏幕

## 视觉效果

### 修复前（大屏幕）
```
┌─────────────────────────────────────────────────────────────┐
│ 文章内容从左到右充满整个屏幕，行长度过长，阅读困难          │
│ 眼睛需要移动很长距离才能从行首读到行尾                      │
└─────────────────────────────────────────────────────────────┘
```

### 修复后（大屏幕）
```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│        ┌─────────────────────────────────┐                  │
│        │ 文章内容居中显示，宽度适中     │                  │
│        │ 行长度在最佳阅读范围内         │                  │
│        │ 阅读体验舒适                   │                  │
│        └─────────────────────────────────┘                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 相关文件

- `web/components/views/ReadingView/ReadingView.css` - CSS 修复

## 参考资料

- [Optimal Line Length for Reading](https://baymard.com/blog/line-length-readability)
- [Typography Best Practices](https://practicaltypography.com/line-length.html)
- [Web Content Accessibility Guidelines (WCAG)](https://www.w3.org/WAI/WCAG21/Understanding/visual-presentation.html)
