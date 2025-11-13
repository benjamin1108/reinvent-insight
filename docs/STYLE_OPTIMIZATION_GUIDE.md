# HTML样式优化指南

## 优化目标
将"看起来像纯文本"的HTML转变为层次分明、视觉舒适的专业页面。

## 核心问题分析

### 问题1：段落文本颜色过淡
**之前**: `p { color: var(--text-secondary); }` (#B0B0B0 - 中灰色)
**优化**: `p { color: var(--text-color); }` (#E0E0E0 - 浅灰色)
**原因**: 次要色应该用于辅助信息，主要内容应该使用主文本色

### 问题2：缺少文本强调
**之前**: 所有文字一视同仁，没有视觉重点
**优化**: 关键词用 `<strong>` 标签，样式为品牌色
```html
<!-- 之前 -->
<p>微软的战略核心是信任，而非单纯的技术优势。</p>

<!-- 优化后 -->
<p>微软的战略核心是<strong>信任</strong>，而非单纯的技术优势。</p>
```

### 问题3：专业术语不突出
**之前**: 技术名词混在普通文本中
**优化**: 使用 `<code>` 标签，添加背景色和品牌色
```html
<!-- 之前 -->
<p>通过 Azure API 访问 OpenAI 模型。</p>

<!-- 优化后 -->
<p>通过 <code>Azure API</code> 访问 <code>OpenAI</code> 模型。</p>
```

### 问题4：列表项颜色过淡
**之前**: `ol li { color: var(--text-secondary); }` 
**优化**: `ol li { color: var(--text-color); }`

## 完整CSS样式规范

```css
/* 段落 - 使用主文本色 */
p {
    margin-bottom: 1.5rem;
    color: var(--text-color);  /* #E0E0E0 */
    line-height: 1.8;
}

/* 强调文本 - 品牌色 + 适中字重 */
strong {
    color: var(--primary-color);  /* #00BFFF */
    font-weight: 600;
}

/* 专业术语 - 微妙背景 + 品牌色 */
code {
    background: rgba(0, 191, 255, 0.1);
    color: var(--primary-color);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.95em;
}

/* 列表 - 主文本色 */
ol li, ul li {
    margin-bottom: 1rem;
    color: var(--text-color);
    line-height: 1.7;
}

/* 列表中的强调 */
ol li strong, ul li strong {
    color: var(--primary-color);
}

/* 引言 - 更大字号 + 主文本色 */
blockquote {
    border-left: 4px solid var(--primary-color);
    padding-left: 20px;
    font-style: italic;
    margin: 2rem 0;
    font-size: 1.2rem;
    color: var(--text-color);  /* 不是次要色 */
}

/* 链接悬停效果 */
a {
    color: var(--primary-color);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.3s ease;
}
a:hover {
    border-bottom-color: var(--primary-color);
}

/* 卡片内文本 */
.card p {
    color: var(--text-color);
}

/* 类比盒内文本 */
.analogy-box p {
    color: var(--text-color);
}
```

## 内容标记原则

### 何时使用 `<strong>`
- 核心概念：战略、原则、方法论
- 关键结论：最终答案、核心发现
- 重要数据：百分比、倍数（非纯数字展示时）
- 对比重点：A vs B 中的关键差异点

### 何时使用 `<code>`
- 技术产品名：Azure、OpenAI、GitHub Copilot
- API/接口名：REST API、GraphQL
- 技术术语：tokens-per-dollar、COGS
- 代码相关：函数名、变量名

### 何时使用 `.data-highlight`
- 震撼性数字：10x、500万、40倍
- 关键指标：增长率、市场份额
- 对比数据：4% vs 50%

## 视觉层次金字塔

```
标题 (h1, h2, h3)
    ↓ 最醒目
数据高亮 (.data-highlight)
    ↓
引言 (blockquote)
    ↓
强调文本 (<strong>)
    ↓
专业术语 (<code>)
    ↓
普通段落 (p) - 主文本色
    ↓
辅助信息 - 次要文本色
```

## 实际应用示例

### 优化前
```html
<p>微软每18至24个月将AI训练能力提升10倍。这需要在数据中心建设、
模型架构和软件优化之间找到平衡。纳德拉认为，真正的护城河在于
tokens-per-dollar-per-watt这个核心效率指标。</p>
```

### 优化后
```html
<p>微软每18至24个月将AI训练能力提升<strong>10倍</strong>。这需要在数据中心建设、
模型架构和软件优化之间找到平衡。纳德拉认为，真正的护城河在于
<code>tokens-per-dollar-per-watt</code>这个<strong>核心效率指标</strong>。</p>
```

## 检查清单

生成HTML后，检查以下项目：
- [ ] 所有段落 `<p>` 使用主文本色（#E0E0E0）
- [ ] 关键概念已用 `<strong>` 标记
- [ ] 技术术语已用 `<code>` 标记
- [ ] 列表项使用主文本色
- [ ] 引言字体大小为 1.2rem
- [ ] 卡片和类比盒内的文本颜色正确
- [ ] 链接有悬停效果
- [ ] 数据高亮使用了 `.data-highlight` 组件

## 总结

核心原则：**让重要的信息看起来重要，让普通的文本易于阅读**

- 主文本色用于主要内容
- 次要色仅用于辅助信息（如时间戳、元数据）
- 品牌色用于强调和交互元素
- 通过语义标签（strong, code）而非纯CSS来标记重要内容
