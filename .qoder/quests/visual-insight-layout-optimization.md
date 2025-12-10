# Visual Insight 长图布局优化说明

## 优化时间
2024-12-10

## 问题描述

用户反馈 Visual Insight HTML 在转换为长图时存在布局问题：
1. **控件宽度不一致**：同一页面中，部分卡片网格使用 3 列，部分使用 4 列，导致卡片宽度不统一
2. **视觉不协调**：不同区域的间距、内边距不一致，影响整体美观
3. **两侧留白不均**：部分内容过宽，导致截图后两侧留白差异大

## 解决方案

### 修改文件
`prompt/text2html.txt` - Visual Insight HTML 生成提示词

### 新增规范：长图优化布局规范（第 3 节）

#### 1. 全局宽度控制
```
所有内容必须包裹在一个主容器中：
<div class="max-w-6xl mx-auto px-6">
  <!-- 所有内容 -->
</div>
```

**作用**：
- 确保内容宽度统一
- 避免部分内容过宽导致两侧留白不一致
- 在长图场景下呈现更紧凑、协调的视觉效果

#### 2. 卡片等宽原则

**规则**：
- **同层级卡片必须等宽**：同一网格容器内的所有卡片使用相同的 Grid 列数配置
- **禁止混合布局**：避免在同一视觉区域混用不同的网格配置（如一处用 3 列，另一处用 4 列）
- **统一 Grid 配置**：推荐全局使用 `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`

**示例**：

✅ **正确做法**（所有卡片网格保持一致）：
```html
<!-- 第一个章节 -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div>卡片 1</div>
  <div>卡片 2</div>
  <div>卡片 3</div>
</div>

<!-- 第二个章节 -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div>卡片 4</div>
  <div>卡片 5</div>
  <div>卡片 6</div>
</div>
```

❌ **错误做法**（网格配置不一致）：
```html
<!-- 第一个章节 - 3 列 -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div>卡片 1</div>
  <div>卡片 2</div>
  <div>卡片 3</div>
</div>

<!-- 第二个章节 - 4 列（错误！） -->
<div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
  <div>卡片 4</div>
  <div>卡片 5</div>
  <div>卡片 6</div>
  <div>卡片 7</div>
</div>
```

#### 3. 间距统一

**规则**：
- 所有卡片之间的间距（`gap`）必须统一
- 推荐使用 `gap-6` 或 `gap-8`

**作用**：
- 避免部分区域间距大、部分区域间距小
- 营造统一的视觉节奏

#### 4. 内边距一致

**规则**：
- 同类型卡片的内边距（`padding`）必须一致
- 主卡片统一使用 `p-8` 或 `p-10`
- 迷你卡片统一使用 `p-6`

#### 5. 垂直节奏

**规则**：
- 使用统一的垂直间距（`mb-12` 或 `mb-16`）分隔不同章节
- 营造良好的阅读节奏

#### 6. 避免绝对定位

**规则**：
- 除非必要（如固定背景效果），禁止使用 `absolute` 定位
- 优先使用 Flexbox 和 Grid 确保布局可控

**原因**：
- 绝对定位在长图场景下容易导致元素重叠或错位
- Flexbox/Grid 更适合响应式布局，确保在不同视口宽度下都能正确显示

## 预期效果

应用此优化后，AI 生成的 Visual Insight HTML 将具备：

1. **统一的视觉宽度**
   - 所有内容宽度一致
   - 两侧留白均匀

2. **协调的卡片布局**
   - 所有卡片网格使用相同配置
   - 每行卡片宽度完全一致

3. **一致的间距节奏**
   - 卡片间距统一
   - 章节间距统一
   - 内边距统一

4. **更佳的长图效果**
   - 适合移动端分享（1080px 宽度）
   - 高清显示（2x 分辨率）
   - 视觉紧凑、美观

## 使用建议

### 对于新生成的 Visual Insight

直接生成即可，AI 会自动应用新规范：

```bash
# API 调用
POST /api/article/{hash}/visual
```

### 对于已有的 Visual Insight

建议重新生成以应用新的布局规范：

```bash
# 1. 删除旧的 Visual HTML
rm downloads/summaries/{filename}_visual.html

# 2. 重新生成
POST /api/article/{hash}/visual

# 3. 重新生成长图
POST /api/article/{hash}/visual/to-image?force_regenerate=true
```

## 技术细节

### Tailwind CSS Grid 配置说明

| 断点 | 屏幕宽度 | 列数 | 说明 |
|-----|---------|------|------|
| `grid-cols-1` | < 768px | 1 列 | 移动端 |
| `md:grid-cols-2` | ≥ 768px | 2 列 | 平板端 |
| `lg:grid-cols-3` | ≥ 1024px | 3 列 | 桌面端 |

### 推荐的容器宽度

| 容器类 | 最大宽度 | 适用场景 |
|-------|---------|---------|
| `max-w-6xl` | 1152px | 推荐（长图优化） |
| `max-w-7xl` | 1280px | 备选（桌面端宽屏） |
| `max-w-5xl` | 896px | 备选（移动端优先） |

## 验证方法

### 1. 检查宽度统一性

查看生成的 HTML，所有内容应包裹在主容器中：

```html
<body class="bg-black min-h-screen">
  <div class="max-w-6xl mx-auto px-6">
    <!-- 所有内容 -->
  </div>
</body>
```

### 2. 检查 Grid 配置一致性

搜索所有 `grid` 类，确认配置统一：

```bash
grep -o 'grid-cols-[0-9]' {filename}_visual.html | sort | uniq -c
```

应该只看到一种配置（如 `grid-cols-1`），而不是多种混合。

### 3. 检查间距一致性

搜索所有 `gap` 类：

```bash
grep -o 'gap-[0-9]' {filename}_visual.html | sort | uniq -c
```

应该只看到一到两种间距值（如 `gap-6` 和 `gap-8`）。

## 后续优化方向

1. **自适应宽度**：根据内容复杂度动态调整容器宽度
2. **智能列数**：根据卡片数量智能选择最佳列数
3. **间距算法**：根据视口宽度自动调整间距大小
4. **响应式优化**：针对不同设备提供更精细的布局控制

## 相关文档

- [Visual Insight 功能设计](/home/benjamin/reinvent-insight/.qoder/quests/visual-insight-to-long-image.md)
- [长图生成快速开始](/home/benjamin/reinvent-insight/.qoder/quests/visual-insight-to-long-image-QUICKSTART.md)
- [text2html 提示词](/home/benjamin/reinvent-insight/prompt/text2html.txt)

## 更新记录

| 日期 | 版本 | 变更内容 |
|-----|------|---------|
| 2024-12-10 | v1.0 | 初始版本，添加长图优化布局规范 |
