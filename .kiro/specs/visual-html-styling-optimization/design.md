# Design Document

## Overview

本设计文档旨在解决可视化解读（text2html）功能的两个核心问题：

1. **配色不一致问题**：当前生成的HTML使用AI自由选择的配色方案，与ReadingView组件的深色主题不匹配，导致可读性差
2. **CDN加载缓慢问题**：使用Google Fonts和国外CDN资源，在中国大陆访问缓慢或无法访问

解决方案的核心思路是：
- 在text2html.txt提示词中明确指定配色规范，确保AI生成的HTML与ReadingView主题一致
- 将所有外部CDN资源替换为国内可访问的镜像或使用系统字体栈
- 确保生成的HTML在无外部网络时仍能正常显示

## Architecture

### 系统组件关系

```
┌─────────────────────────────────────────────────────────────┐
│                    Visual Worker                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. 读取深度解读文章                                    │  │
│  │  2. 加载 text2html.txt 提示词                          │  │
│  │  3. 构建完整提示词（文章 + 提示词）                      │  │
│  │  4. 调用 AI 模型生成 HTML                              │  │
│  │  5. 清理和验证 HTML                                    │  │
│  │  6. 保存 HTML 文件                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  text2html.txt 提示词                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • 设计目标和风格指导                                   │  │
│  │  • 配色方案规范（新增）                                 │  │
│  │  • 技术规范（CDN链接）                                  │  │
│  │  • 输出要求                                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   生成的 HTML 文件                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • 使用统一配色方案                                     │  │
│  │  • 使用国内CDN或系统字体                                │  │
│  │  • 深色/浅色模式切换                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  ReadingView 组件                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • 加载并显示生成的 HTML                                │  │
│  │  • 提供一致的阅读体验                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

1. **输入**：深度解读Markdown文件（带YAML front matter）
2. **处理**：Visual Worker读取文章 → 加载提示词 → 调用AI生成HTML
3. **输出**：可视化HTML文件（与原文件同目录，命名为`{原文件名}_visual.html`）

## Components and Interfaces

### 1. text2html.txt 提示词文件

**职责**：指导AI生成符合设计规范的HTML

**修改内容**：

#### 1.1 配色方案规范（新增）

在提示词中添加明确的配色规范章节：

```markdown
**配色方案规范（必须严格遵守）：**

本网页必须使用以下配色方案，以确保与阅读界面的主题一致：

*   **主题色：**
    *   Cyan: #22d3ee（主要强调色，用于链接、按钮、高亮）
    *   Blue: #3b82f6（次要强调色，用于渐变和装饰）
    *   Purple: #8b5cf6（辅助强调色，用于渐变和特殊元素）
    *   渐变组合：linear-gradient(135deg, #22d3ee, #3b82f6, #8b5cf6)

*   **深色模式（默认）：**
    *   背景色：#111827（主背景）、#0f172a（次要背景）
    *   文本色：#e5e7eb（主文本，透明度87%）、#f3f4f6（标题）
    *   边框色：#374151
    *   卡片背景：rgba(15, 23, 42, 0.6) 到 rgba(30, 41, 59, 0.4) 的渐变
    *   代码背景：#0f172a
    *   引用块背景：rgba(34, 211, 238, 0.05)
    *   引用块边框：#22d3ee

*   **浅色模式：**
    *   背景色：#ffffff（主背景）、#f9fafb（次要背景）
    *   文本色：#1a1a1a（主文本）、#111827（标题）
    *   边框色：#e5e7eb
    *   卡片背景：#ffffff
    *   代码背景：#f3f4f6
    *   引用块背景：rgba(34, 211, 238, 0.1)
    *   引用块边框：#22d3ee

*   **对比度要求：**
    *   所有文本与背景的对比度必须符合 WCAG AA 标准（至少 4.5:1）
    *   深色模式下，主文本使用 rgba(229, 231, 235, 0.87)
    *   浅色模式下，主文本使用 #1a1a1a

*   **禁止使用的颜色：**
    *   不要使用其他主题色（如红色、绿色、黄色等作为主色调）
    *   不要使用过于鲜艳或刺眼的颜色
    *   不要使用与主题色冲突的配色方案
```

#### 1.2 CDN资源替换

将现有的CDN链接替换为国内可访问的镜像：

**当前配置：**
```
Font Awesome: https://cdn.staticfile.org/font-awesome/6.4.0/css/all.min.css
Tailwind CSS: https://cdn.staticfile.org/tailwindcss/2.2.19/tailwind.min.css
Google Fonts: https://fonts.googleapis.com/css2?family=Noto+Serif+SC:...
```

**优化后配置：**
```markdown
**技术规范（必须严格遵守）：**

*   **CSS框架和图标库：**
    *   Font Awesome: https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/font-awesome/6.0.0/css/all.min.css
    *   Tailwind CSS: https://lf6-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css
    *   备用CDN: https://cdn.bootcdn.net/ 或 https://unpkg.com/

*   **字体方案：**
    *   禁止使用 Google Fonts（在中国大陆访问不稳定）
    *   使用系统字体栈，确保跨平台兼容性：
    ```css
    font-family: 'Inter', 'PingFang SC', 'SF Pro Text', 'Hiragino Sans GB', 
                 'Microsoft YaHei', 'Segoe UI', sans-serif;
    ```
    *   标题字体栈：
    ```css
    font-family: 'Outfit', 'PingFang SC', 'SF Pro Display', 'Hiragino Sans GB', 
                 'Microsoft YaHei', sans-serif;
    ```
    *   代码字体栈：
    ```css
    font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', 
                 'SFMono-Regular', Menlo, monospace;
    ```

*   **JavaScript库：**
    *   如需使用图表库，使用 ECharts（国内CDN）：
    *   https://lf26-cdn-tos.bytecdntp.com/cdn/expire-1-M/echarts/5.3.0/echarts.min.js
    *   禁止使用 Mermaid.js（已在原提示词中禁止）

*   **降级策略：**
    *   所有外部资源必须有 fallback 方案
    *   关键样式应内联到 HTML 中，确保无网络时也能正常显示
    *   使用 `<link>` 标签的 `onerror` 事件处理CDN加载失败
```

#### 1.3 深色/浅色模式实现规范

在提示词中添加模式切换的实现要求：

```markdown
**深色/浅色模式切换实现：**

*   默认跟随系统设置：使用 `prefers-color-scheme` 媒体查询
*   提供手动切换按钮，状态保存到 localStorage
*   切换时使用平滑过渡动画（transition: all 0.3s ease）
*   确保所有元素在两种模式下都清晰可读
*   模式切换代码示例：
```javascript
// 检测系统主题
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
// 读取用户偏好
const savedTheme = localStorage.getItem('theme');
const theme = savedTheme || (prefersDark ? 'dark' : 'light');
document.documentElement.setAttribute('data-theme', theme);
```
```

### 2. Visual Worker (visual_worker.py)

**职责**：协调整个可视化生成流程

**当前实现**：已经完善，无需修改

**关键方法**：
- `_load_text2html_prompt()`: 加载提示词文件
- `_build_prompt()`: 构建完整提示词（提示词 + 文章内容）
- `_generate_html()`: 调用AI生成HTML
- `_clean_html()`: 清理AI输出（移除markdown代码块标记等）
- `_validate_html()`: 验证HTML格式
- `_save_html()`: 保存HTML文件

**不需要修改的原因**：
- Visual Worker只是加载和传递提示词，不关心提示词的具体内容
- 所有配色和CDN的控制都在提示词层面完成
- Worker的职责是流程控制，不涉及内容生成逻辑

### 3. ReadingView 组件

**职责**：展示生成的可视化HTML

**当前实现**：已经使用统一的配色方案（#22d3ee, #3b82f6, #8b5cf6）

**不需要修改的原因**：
- ReadingView只是加载和显示HTML iframe
- 生成的HTML是独立的文档，有自己的样式
- 只要生成的HTML使用相同的配色方案，就能保证视觉一致性

## Data Models

### 提示词结构

```
text2html.txt
├── 角色定义
├── 设计目标
├── 设计指导
│   ├── 整体风格
│   ├── Hero模块
│   ├── 排版
│   ├── 配色方案（新增详细规范）
│   ├── 布局
│   ├── 调性
│   └── 数据可视化
├── 技术规范（更新CDN链接）
│   ├── CSS框架和图标库
│   ├── 字体方案（新增系统字体栈）
│   ├── JavaScript库
│   └── 降级策略（新增）
├── 深色/浅色模式实现（新增）
├── 额外加分项
└── 输出要求
```

### HTML输出结构

生成的HTML应包含：

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文章标题</title>
    
    <!-- 外部CSS资源（国内CDN） -->
    <link rel="stylesheet" href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css">
    
    <!-- 内联关键样式（确保无网络时也能显示） -->
    <style>
        :root {
            --color-cyan: #22d3ee;
            --color-blue: #3b82f6;
            --color-purple: #8b5cf6;
            --gradient-primary: linear-gradient(135deg, #22d3ee, #3b82f6, #8b5cf6);
        }
        
        [data-theme="dark"] {
            --bg-primary: #111827;
            --bg-secondary: #0f172a;
            --text-primary: rgba(229, 231, 235, 0.87);
            --text-heading: #f3f4f6;
            --border-color: #374151;
        }
        
        [data-theme="light"] {
            --bg-primary: #ffffff;
            --bg-secondary: #f9fafb;
            --text-primary: #1a1a1a;
            --text-heading: #111827;
            --border-color: #e5e7eb;
        }
        
        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Inter', 'PingFang SC', 'SF Pro Text', sans-serif;
            transition: all 0.3s ease;
        }
        
        /* 更多样式... */
    </style>
</head>
<body>
    <!-- 主题切换按钮 -->
    <button id="theme-toggle" aria-label="切换主题">
        <i class="fas fa-moon"></i>
    </button>
    
    <!-- 文章内容 -->
    <article>
        <!-- AI生成的内容 -->
    </article>
    
    <!-- 主题切换脚本 -->
    <script>
        // 主题切换逻辑
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const savedTheme = localStorage.getItem('theme');
        const theme = savedTheme || (prefersDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', theme);
        
        document.getElementById('theme-toggle').addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    </script>
</body>
</html>
```

## Error Handling

### 1. CDN加载失败处理

**问题**：外部CDN可能加载失败

**解决方案**：
- 在提示词中要求AI添加CDN失败的fallback逻辑
- 关键样式内联到HTML中
- 使用多个CDN备选方案

**实现示例**：
```html
<link rel="stylesheet" 
      href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/font-awesome/6.0.0/css/all.min.css"
      onerror="this.onerror=null; this.href='https://cdn.bootcdn.net/ajax/libs/font-awesome/6.0.0/css/all.min.css'">
```

### 2. AI生成配色不符合规范

**问题**：AI可能忽略配色规范，使用其他颜色

**解决方案**：
- 在提示词中多次强调配色规范的重要性
- 使用"必须严格遵守"等强调性语言
- 在"禁止使用的颜色"章节明确列出不允许的配色

**验证方案**（可选，未来优化）：
- 在Visual Worker中添加HTML内容验证
- 检查生成的HTML是否包含指定的颜色代码
- 如果不符合，可以重新生成或记录警告

### 3. 字体加载失败

**问题**：系统可能缺少某些字体

**解决方案**：
- 使用完整的字体栈，包含多个fallback选项
- 优先使用系统自带字体（PingFang SC, Microsoft YaHei等）
- 不依赖外部字体CDN

## Testing Strategy

### 1. 提示词验证测试

**目标**：确保修改后的提示词能生成符合规范的HTML

**测试步骤**：
1. 选择3-5篇不同类型的深度解读文章
2. 使用修改后的提示词生成可视化HTML
3. 检查生成的HTML是否符合以下标准：
   - 使用指定的配色方案（#22d3ee, #3b82f6, #8b5cf6）
   - 使用国内CDN或系统字体
   - 包含深色/浅色模式切换功能
   - 文本对比度符合WCAG AA标准

**验证方法**：
- 视觉检查：在浏览器中打开生成的HTML，检查配色是否一致
- 代码检查：搜索HTML源码中的颜色代码，确认使用了指定颜色
- 网络检查：使用浏览器开发者工具，确认没有加载Google Fonts
- 对比度检查：使用对比度检查工具（如WebAIM Contrast Checker）

### 2. CDN可用性测试

**目标**：确保使用的CDN在中国大陆可访问

**测试步骤**：
1. 在中国大陆网络环境下访问生成的HTML
2. 检查所有外部资源是否成功加载
3. 测试CDN加载速度

**验证方法**：
- 使用浏览器开发者工具的Network面板
- 检查所有资源的加载状态和时间
- 确认没有404或超时错误

### 3. 降级功能测试

**目标**：确保在无网络或CDN失败时，HTML仍能正常显示

**测试步骤**：
1. 在浏览器中打开生成的HTML
2. 使用开发者工具阻止所有外部资源加载
3. 检查页面是否仍然可读

**验证方法**：
- 页面布局应保持基本结构
- 文本应清晰可读
- 配色应符合规范（通过内联样式）

### 4. 主题切换测试

**目标**：确保深色/浅色模式切换正常工作

**测试步骤**：
1. 打开生成的HTML
2. 点击主题切换按钮
3. 检查页面配色是否正确切换
4. 刷新页面，检查主题是否保持

**验证方法**：
- 深色模式：背景#111827，文本#e5e7eb
- 浅色模式：背景#ffffff，文本#1a1a1a
- localStorage中应保存用户选择

### 5. 对比度测试

**目标**：确保文本对比度符合无障碍标准

**测试工具**：
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Chrome DevTools Lighthouse

**测试步骤**：
1. 使用对比度检查工具测试主要文本元素
2. 确保所有文本与背景的对比度 ≥ 4.5:1（WCAG AA标准）

**关键对比度**：
- 深色模式：rgba(229, 231, 235, 0.87) on #111827 ≈ 12.5:1 ✓
- 浅色模式：#1a1a1a on #ffffff ≈ 16.1:1 ✓
- 链接色：#22d3ee on #111827 ≈ 8.2:1 ✓

### 6. 跨浏览器测试

**目标**：确保在不同浏览器中显示一致

**测试浏览器**：
- Chrome/Edge（Chromium内核）
- Firefox
- Safari（如果可用）
- 移动端浏览器（iOS Safari, Chrome Mobile）

**测试内容**：
- 配色显示
- 字体渲染
- 主题切换功能
- 响应式布局

## Implementation Notes

### 修改优先级

1. **高优先级**：修改text2html.txt提示词
   - 添加配色方案规范
   - 更新CDN链接
   - 添加深色/浅色模式实现规范

2. **中优先级**：测试和验证
   - 生成测试HTML
   - 验证配色和CDN
   - 检查对比度

3. **低优先级**（可选）：Visual Worker增强
   - 添加HTML内容验证
   - 添加配色检查逻辑
   - 添加错误报告

### 向后兼容性

- 修改只影响新生成的HTML文件
- 已生成的HTML文件不受影响
- 用户可以选择重新生成旧文章的可视化版本

### 性能考虑

- 使用国内CDN可以显著提升加载速度
- 内联关键样式可以减少首屏渲染时间
- 系统字体栈避免了字体下载时间

### 维护性

- 所有配色规范集中在提示词中，易于维护
- CDN链接统一管理，便于批量更新
- 提示词使用清晰的章节结构，便于理解和修改
