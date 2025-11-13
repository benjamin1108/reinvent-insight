# Requirements Document

## Introduction

本规范旨在优化可视化解读（text2html）功能的两个核心问题：
1. 生成的HTML配色与网站主题不匹配，导致可读性问题
2. 外部CDN资源加载缓慢，影响用户体验

## Glossary

- **Visual Interpretation System**: 可视化解读系统，负责将Markdown深度解读转换为HTML可视化页面
- **ReadingView Component**: 阅读视图组件，用于展示可视化解读的前端组件
- **Text2HTML Prompt**: text2html.txt提示词文件，指导AI生成HTML的规范文档
- **Model Client**: 模型客户端，负责与AI模型通信的接口
- **CDN Resources**: 内容分发网络资源，包括CSS框架、字体和图标库

## Requirements

### Requirement 1: 配色方案适配

**User Story:** 作为用户，我希望可视化解读页面的配色与网站主题一致，以便在深色背景下清晰阅读内容

#### Acceptance Criteria

1. WHEN Visual Interpretation System生成HTML时，THE System SHALL使用与ReadingView Component一致的配色方案
2. THE Visual Interpretation System SHALL在Text2HTML Prompt中明确指定主题色为#22d3ee（cyan）、#3b82f6（blue）和#8b5cf6（purple）的渐变组合
3. THE Visual Interpretation System SHALL确保深色模式下文本颜色为#e5e7eb，背景色为#111827和#0f172a
4. THE Visual Interpretation System SHALL确保浅色模式下文本颜色为#1a1a1a，背景色为#ffffff
5. WHEN用户在ReadingView Component中查看可视化解读时，THE System SHALL保证文本与背景对比度符合WCAG AA标准（至少4.5:1）

### Requirement 2: CDN资源本地化

**User Story:** 作为中国大陆用户，我希望可视化解读页面快速加载，不受国外CDN限制影响

#### Acceptance Criteria

1. THE Visual Interpretation System SHALL将Tailwind CSS、Font Awesome和Google Fonts替换为国内可访问的CDN或本地资源
2. WHERE外部资源必须使用CDN，THE System SHALL优先使用国内CDN服务（如staticfile.org、bootcdn.cn或unpkg.com）
3. WHERE字体资源无法通过国内CDN访问，THE System SHALL使用系统字体栈作为fallback，不依赖Google Fonts
4. THE Visual Interpretation System SHALL在Text2HTML Prompt中更新所有CDN链接为国内可访问地址
5. THE Visual Interpretation System SHALL确保生成的HTML在无外部网络访问时仍能正常显示（使用内联样式或本地资源）