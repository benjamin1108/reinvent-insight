# RecentArticlesDropdown 组件

显示最近文章的下拉列表组件。

## 功能特性

- 显示最近10篇文章
- 按修改时间倒序排列
- 绝对日期显示（如"2024-11-02"）
- 支持鼠标悬停和键盘导航
- 响应式设计，适配移动端
- 科技风格UI设计

## Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| visible | Boolean | false | 是否显示下拉列表 |
| articles | Array | [] | 文章列表数据 |
| loading | Boolean | false | 加载状态 |

## Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| article-click | article | 文章被点击时触发 |
| mouseenter | - | 鼠标进入下拉区域时触发 |
| mouseleave | - | 鼠标离开下拉区域时触发 |

## 使用示例

```html
<recent-articles-dropdown
  :visible="showDropdown"
  :articles="recentArticles"
  :loading="loading"
  @article-click="handleArticleClick"
  @mouseenter="handleMouseEnter"
  @mouseleave="handleMouseLeave">
</recent-articles-dropdown>
```

## 文章数据结构

```javascript
{
  hash: String,           // 文章hash，用于导航
  title_cn: String,       // 中文标题
  title_en: String,       // 英文标题
  modified_at: Number,    // 修改时间戳（秒）
  is_pdf: Boolean,        // 是否为PDF文档
  content_type: String    // 内容类型
}
```

## 样式定制

组件使用科技风格设计，主要颜色：
- 主色：#22d3ee (青色)
- 背景：渐变半透明深色
- 文字：#e5e7eb (浅灰)

可以通过覆盖CSS变量或类名来定制样式。
