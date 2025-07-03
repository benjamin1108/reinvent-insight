"""
Text2HTML AI提示词模板系统

管理和优化用于生成HTML的AI提示词模板，支持模板变量替换、
动态内容注入和提示词版本管理。
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from . import config

logger = logging.getLogger(__name__)

class PromptTemplate:
    """AI提示词模板类"""
    
    def __init__(self, template_content: str, variables: Dict[str, Any] = None):
        self.template_content = template_content
        self.variables = variables or {}
        self.created_at = datetime.now()
    
    def render(self, context: Dict[str, Any]) -> str:
        """渲染模板，替换变量"""
        rendered = self.template_content
        
        # 合并默认变量和上下文变量
        all_variables = {**self.variables, **context}
        
        # 替换模板变量
        for key, value in all_variables.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in rendered:
                rendered = rendered.replace(placeholder, str(value))
        
        return rendered

class Text2HtmlPrompts:
    """Text2HTML提示词管理器"""
    
    # 基础HTML生成模板
    BASE_HTML_TEMPLATE = """你现在是我们网站 **{{brand_name}}** 的首席设计师兼高级前端工程师。你的使命是，将任何一篇高质量的技术文章，转化为符合我们品牌调性、且信息传达效率极高的网页。你既要维护品牌的一致性，又要展现每一篇文章的独特性。

# 设计系统与品牌规范 (必须严格遵守)

这是我们网站的视觉DNA。在生成任何页面时，都必须严格遵循以下所有规范。

## 色彩规范 (Color Palette)
- **背景 (Background):** `var(--bg-color): {{bg_color}};` (近黑)
- **卡片/浮层 (Surface):** `var(--surface-color): {{surface_color}};` (深灰)
- **主文本 (Primary Text):** `var(--text-color): {{text_color}};` (浅灰)
- **次要文本 (Secondary Text):** `var(--text-secondary): {{text_secondary}};` (中灰)
- **品牌强调色 (Accent):** `var(--primary-color): {{primary_color}};` (品牌色)
- **高亮/数据色 (Highlight):** `var(--highlight-color): {{highlight_color}};` (用于数据)

## 字体规范 (Typography)
- **字体族**: `{{font_family}}` (通过Google Fonts引入)
- **基础字号**: `{{base_font_size}}`
- **基础行高**: `{{line_height}}`
- **标题体系 (Scale)**: `h1 (3rem)`, `h2 (2.2rem)`, `h3 (1.6rem)`

## 布局与间距 (Layout & Spacing)
- **内容宽度**: 容器最大宽度 `{{container_width}}`
- **主要间距**: 所有顶级`<section>`上下 `padding` 统一为 `{{section_padding}}`

## 核心组件库 (Core Component Library)
这是我们预设的UI组件。你**必须**使用这些统一样式来渲染对应的元素。
- **`.card` (信息卡片)**: 用于承载核心原则、分点论述。样式：`background-color: var(--surface-color); padding: 30px; border-radius: 8px;`
- **`.data-highlight` (数据高亮)**: 用于展示关键数字。样式：`text-align: center;` 内含一个 `<div class="number">` (字体巨大，颜色为 `var(--highlight-color)`) 和一个 `<div class="description">`
- **`.analogy-box` (类比/洞察盒)**: 用于突出显示比喻或深刻见解。样式：`border: 1px dashed var(--primary-color); background-color: rgba({{primary_color_rgb}}, 0.05); padding: 25px;`
- **`blockquote` (引言)**: 用于引用人物原话。样式：`border-left: 4px solid var(--primary-color); padding-left: 20px; font-style: italic;`

# 内容解读与智能布局 (需要你发挥智能)

## 你的智能任务
作为信息架构师，你的核心任务是深入阅读和理解下面提供的文章，识别出其独特的**信息结构**和**关键亮点**。然后，从上述"核心组件库"中，策略性地选择最合适的组件来呈现这些信息。

## 关键信息识别与布局指南
请遵循以下指南来分析文章并决定布局：
- **全文核心论点 (Thesis)**: 找到文章最核心的、唯一的"Aha!"时刻或最终结论，将其放在网页顶部的**英雄区域 (Hero Section)**
- **关键原则/支柱论点 (Pillars)**: 如果文章有几个并列的关键原则或设计哲学，使用多个 **`.card`** 组件来分别阐述
- **震撼性数据 (Impactful Data)**: 当你发现一个极具说服力的数字或指标时，使用 **`.data-highlight`** 组件来给予它最强的视觉冲击力
- **绝妙的比喻或类比 (Analogies)**: 如果作者用了巧妙的比喻来解释复杂概念，将其放入 **`.analogy-box`** 中，让读者能轻松理解
- **步骤、演进或流程 (Processes)**: 如果文章描述了一个时间线、技术演进过程或分步指南，请使用有序列表 (`<ol>`) 或一系列带 `<h3>` 标题的子章节来清晰地呈现其逻辑
- **专家或人物引言 (Quotes)**: 如果文中直接引用了某人的话，使用 **`blockquote`** 组件

**你的"自由发挥"体现在：判断"什么信息"应该被赋予"哪种样式"，以及这些组件的"组织顺序"。**

# 技术与交付要求

- **交付物**: 一个独立的、所有CSS都内联在`<head>`部分`<style>`标签内的HTML文件
- **代码质量**: 使用语义化HTML5标签，确保代码整洁，并实现完全的响应式布局
- **CSS变量**: 必须使用CSS变量系统，确保品牌一致性
- **响应式**: 完美适配桌面、平板和移动设备

---

# 文章信息
- **标题**: {{article_title}}
- **字数**: {{word_count}}
- **预计阅读时间**: {{reading_time}}分钟
- **生成时间**: {{generation_time}}

# 待处理文章内容
{{article_content}}

请严格按照上述设计系统和布局指南，生成完整的HTML文件。
"""

    # 增强版HTML生成模板（基于新的三步转化法）
    ENHANCED_HTML_TEMPLATE = """### 角色与使命

你是一位顶级的数字体验架构师，名为"Reinvent Insight"。你的核心使命是将任何一篇深度、复杂的文本（源文本）转化为一个极致精美、信息丰富、重点突出的单页式"数字洞察"体验。你不仅是信息的转述者，更是叙事的重塑者、美学的创造者和用户注意力的引导者。

---

### 核心工作流：三步转化法

你必须严格遵循以下三步法，将源文本转化为最终的数字杰作：

**第一步：解构与提炼 (Deconstruction & Synthesis)**
1.  **深度阅读**：通读并理解源文本，识别出其核心论点、关键原则、支撑案例、关键数据、精妙比喻和演进脉络。
2.  **信息分类**：将提炼出的信息归类到以下几个核心类别中，为第二步的布局映射做准备：
    * **核心主旨 (The Thesis)**：文章最引人入胜、统领全局的核心思想。
    * **设计哲学/原则 (The Pillars)**：支撑核心思想的几个并行关键原则或信条。
    * **关键数据 (The Data Points)**：最具冲击力、最能体现规模与成果的数字。
    * **创新案例/轶事 (The Innovations/Anecdotes)**：具体的、引人入胜的技术或流程创新故事。
    * **演进过程 (The Process)**：具有明确时间线或步骤感的叙事，如技术发展历程。

**第二步：架构映射 (Architectural Mapping)**
这是将信息转化为视觉结构的关键一步。你必须将上一步分类好的信息，智能地映射到以下两种核心布局上：

1.  **Bento Grid (便当盒网格布局)**：作为页面的主体，用于展示核心、高影响力的非线性信息。
    * **核心主旨** -> 映射到最大、最醒目的 `Hero Tile`。
    * **关键数据** -> 映射到小而精的 `Data Tile`。
    * **设计哲学/原则** -> 映射到中等尺寸的 `Philosophy Tile`。
    * **创新案例/轶事** -> 映射到内容丰富、图文并茂的 `Innovation Tile`。

2.  **Timeline (时间轴布局)**：作为Bento Grid中的一个特殊"大模块"或独立章节，用于清晰地展示线性的"演进过程"。
    * **演进过程** -> 映射到垂直的 `Timeline Tile` 内部，按步骤或时间顺序排列。

**第三步：视觉构建 (Visual Construction)**
使用你脑中的"设计法典"和"组件库"，将映射好的结构构建成一个独立的、自包含的HTML文件。

---

### 设计法典 (The Design Codex) - 视觉的绝对真理

这是我们品牌的DNA，必须像素级地严格遵守。

* **布局 (Layout)**：
    * **主结构**: `Bento Grid`，采用CSS Grid实现，确保网格的健壮性与对齐。
    * **辅助结构**: `Timeline`，作为Bento Grid的一部分或紧随其后。
    * **响应式**: 在中小型设备上，Bento Grid应能优雅地堆叠。

* **色彩规范 (Color Palette)**：
    * **背景 (Background)**: `#121212`
    * **浮层/卡片 (Surface)**: `rgba(30, 30, 30, 0.65)` (玻璃拟态)
    * **主文本 (Primary Text)**: `#F5F5F7`
    * **次要文本 (Secondary Text)**: `#A1A1A6`
    * **主强调色 (Primary Accent)**: `#FF9900` (如：AWS Orange)
    * **高亮色 (Highlight Accent)**: `#00BFFF` (如：数据、图标)
    * **边框 (Border)**: `rgba(255, 153, 0, 0.2)`

* **字体规范 (Typography)**：
    * **字体族**: `'Noto Sans SC', sans-serif` (通过Google Fonts引入)。
    * **层级**: 使用不同的字重 (300, 400, 500, 700) 和字号来构建清晰的视觉层级。
    * **行高**: `1.8`，保证阅读舒适性。

* **动效与交互 (Animation & Interaction)**：
    * **入场动效**: 所有核心元素（网格项、时间轴节点）都必须有优雅的、基于滚动的淡入动画 (`Fade-in-up`)。
    * **背景**: 必须包含一个流动的、微妙的动画渐变背景，营造高级感和呼吸感。
    * **数据动画**: `Data Tile` 中的数字必须有从0滚动到目标值的动画效果。
    * **悬浮效果**: Bento Grid的网格项在鼠标悬浮时应有轻微的辉光或上浮效果，以增强交互感。

---

### 组件库 (Component Library) - 你的构建模块

* `.bento-grid`: 布局的容器。
* `.bento-item`: 网格项的基础样式，必须实现玻璃拟态效果 (`backdrop-filter: blur(16px);`)。
    * `.hero-tile`: 用于核心主旨，通常占据最大空间。
    * `.data-tile`: 用于关键数据，设计应简洁、醒目。
    * `.philosophy-tile`: 用于设计原则，内容精炼。
    * `.innovation-tile`: 用于创新案例，可包含图标或更丰富的描述。
    * `.timeline-tile`: 用于容纳时间轴组件。
* `.timeline`: 垂直时间轴的容器。
    * `.timeline-item`: 时间轴上的每一个事件节点。

---

### 交付要求与约束

1.  **交付物**: 一个独立的、所有CSS和JavaScript都内联在`<style>`和`<script>`标签中的 **HTML文件**。
2.  **代码质量**: 使用语义化HTML5标签，确保代码整洁、可读，并实现完全的响应式布局。
3.  **引用规范**: 这是一个绝对的、不可违反的约束。任何源自"源文本"的信息，在其所在的句子或短语末尾，都**必须**严格按照 `<cite data-ref="{{article_title}}">{{引用内容}}</cite>` 的格式进行标记。

---

### 任务开始

请严格遵循以上三步转化法、设计法典和组件库，开始处理下面的文章。

---

# 文章信息
- **标题**: {{article_title}}
- **字数**: {{word_count}}
- **预计阅读时间**: {{reading_time}}分钟
- **生成时间**: {{generation_time}}

# 待处理文章内容
{{article_content}}

---"""

    # 简化版模板（适用于短文章）
    SIMPLE_HTML_TEMPLATE = """你是 **{{brand_name}}** 的设计师，需要将这篇文章转换为简洁美观的HTML网页。

# 设计系统规范
## 色彩系统
- **背景色**: `var(--bg-color): {{bg_color}};`
- **卡片色**: `var(--surface-color): {{surface_color}};`
- **主文本**: `var(--text-color): {{text_color}};`
- **次要文本**: `var(--text-secondary): {{text_secondary}};`
- **品牌色**: `var(--primary-color): {{primary_color}};`
- **高亮色**: `var(--highlight-color): {{highlight_color}};`

## 字体系统
- **字体**: {{font_family}}
- **基础字号**: {{base_font_size}}
- **行高**: {{line_height}}

## 布局系统
- **容器宽度**: {{container_width}}
- **区域间距**: {{section_padding}}

# 组件使用指南
- **`.card`**: 核心观点和原则
- **`.data-highlight`**: 重要数据和数字
- **`.analogy-box`**: 精彩比喻和类比
- **`blockquote`**: 权威引言和观点

# 文章信息
- **标题**: {{article_title}}
- **字数**: {{word_count}}
- **预计阅读时间**: {{reading_time}}分钟
- **生成时间**: {{generation_time}}

# 待处理文章内容
{{article_content}}

请生成完整的HTML文件，包含内联CSS样式和CSS变量系统。
"""

    def __init__(self):
        self.templates = {
            "base": PromptTemplate(self.BASE_HTML_TEMPLATE),
            "enhanced": PromptTemplate(self.ENHANCED_HTML_TEMPLATE),
            "simple": PromptTemplate(self.SIMPLE_HTML_TEMPLATE)
        }
        
        # 加载外部模板文件（如果存在）
        self._load_external_template()
    
    def _load_external_template(self):
        """加载外部的text2html.txt模板文件"""
        external_template_file = config.PROJECT_ROOT / "prompt" / "text2html.txt"
        
        if external_template_file.exists():
            try:
                with open(external_template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 将外部模板注册为"external"版本
                self.templates["external"] = PromptTemplate(content)
                logger.info("成功加载外部text2html模板")
                
            except Exception as e:
                logger.warning(f"加载外部模板失败: {e}")
    
    def get_template(self, template_name: str = "base") -> Optional[PromptTemplate]:
        """获取指定的模板"""
        return self.templates.get(template_name)
    
    def list_templates(self) -> list:
        """列出所有可用的模板"""
        return list(self.templates.keys())
    
    def create_generation_prompt(self, 
                                content: str, 
                                metadata: Dict[str, Any],
                                brand_config: Dict[str, Any],
                                template_name: str = "base") -> str:
        """
        创建完整的AI生成提示词
        
        Args:
            content: 文章内容
            metadata: 文章元数据
            brand_config: 品牌配置
            template_name: 模板名称
            
        Returns:
            str: 完整的提示词
        """
        template = self.get_template(template_name)
        if not template:
            logger.warning(f"模板不存在: {template_name}，使用默认模板")
            template = self.get_template("base")
        
        # 准备模板变量
        context = self._prepare_template_context(content, metadata, brand_config)
        
        # 渲染模板
        return template.render(context)
    
    def _prepare_template_context(self, 
                                content: str, 
                                metadata: Dict[str, Any],
                                brand_config: Dict[str, Any]) -> Dict[str, Any]:
        """准备模板上下文变量"""
        
        # 从品牌配置中提取颜色值
        colors = brand_config.get('colors', {})
        fonts = brand_config.get('fonts', {})
        layout = brand_config.get('layout', {})
        
        # 处理RGB颜色值（用于rgba函数）
        primary_color = colors.get('primary', '#00BFFF')
        primary_color_rgb = self._hex_to_rgb(primary_color)
        
        return {
            # 品牌信息
            'brand_name': brand_config.get('name', 'Reinvent Insight'),
            
            # 新设计法典颜色系统
            'bg_color': colors.get('bg', '#121212'),
            'surface_color': colors.get('surface', 'rgba(30, 30, 30, 0.65)'),
            'text_color': colors.get('text', '#F5F5F7'),
            'text_secondary': colors.get('text_secondary', '#A1A1A6'),
            'primary_color': colors.get('primary', '#FF9900'),
            'highlight_color': colors.get('highlight', '#00BFFF'),
            'border_color': colors.get('border', 'rgba(255, 153, 0, 0.2)'),
            'primary_color_rgb': self._hex_to_rgb(colors.get('primary', '#FF9900')),
            
            # 新设计法典字体系统
            'font_family': fonts.get('main', "'Noto Sans SC', sans-serif"),
            'base_font_size': fonts.get('base_size', '16px'),
            'line_height': fonts.get('line_height', '1.8'),
            
            # 布局系统保持不变
            'container_width': layout.get('container_width', '1200px'),
            'section_padding': layout.get('section_padding', '3rem 0'),
            
            # 文章信息
            'article_title': metadata.get('title', '未知标题'),
            'word_count': metadata.get('word_count', 0),
            'reading_time': metadata.get('estimated_reading_time', 1),
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'article_content': content
        }
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """将十六进制颜色转换为RGB值字符串"""
        try:
            # 移除#号
            hex_color = hex_color.lstrip('#')
            
            # 转换为RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            return f"{r}, {g}, {b}"
        except (ValueError, IndexError):
            logger.warning(f"无效的颜色值: {hex_color}")
            return "255, 153, 0"  # 默认橙色
    
    def auto_select_template(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        根据文章内容自动选择最合适的模板
        
        Args:
            content: 文章内容
            metadata: 文章元数据
            
        Returns:
            str: 推荐的模板名称
        """
        # 优先使用外部模板（如果存在）
        if "external" in self.templates:
            return "external"
            
        word_count = metadata.get('word_count', len(content))
        
        # 根据文章长度选择模板
        if word_count < 1000:
            return "simple"
        elif word_count > 5000:
            return "enhanced"
        else:
            return "base"
    
    def add_custom_template(self, name: str, template_content: str, variables: Dict[str, Any] = None):
        """添加自定义模板"""
        self.templates[name] = PromptTemplate(template_content, variables)
        logger.info(f"已添加自定义模板: {name}")
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """获取模板信息"""
        template = self.get_template(template_name)
        if not template:
            return {}
        
        return {
            "name": template_name,
            "created_at": template.created_at.isoformat(),
            "content_length": len(template.template_content),
            "variables_count": len(template.variables),
            "available_variables": list(template.variables.keys()) if template.variables else []
        }

# 全局提示词管理器实例
prompts_manager = Text2HtmlPrompts()

def get_prompts_manager() -> Text2HtmlPrompts:
    """获取全局提示词管理器实例"""
    return prompts_manager

def create_html_prompt(content: str, 
                      metadata: Dict[str, Any],
                      brand_config: Dict[str, Any],
                      template_name: str = None) -> str:
    """
    便捷函数：创建HTML生成提示词
    
    Args:
        content: 文章内容
        metadata: 文章元数据  
        brand_config: 品牌配置
        template_name: 模板名称，None则自动选择
        
    Returns:
        str: 完整的AI提示词
    """
    manager = get_prompts_manager()
    
    # 自动选择模板
    if not template_name:
        template_name = manager.auto_select_template(content, metadata)
        logger.info(f"自动选择模板: {template_name}")
    
    return manager.create_generation_prompt(content, metadata, brand_config, template_name) 