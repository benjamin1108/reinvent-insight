# -*- coding: utf-8 -*-
"""
章节内容生成 Prompt（v2 重构版 - 含 CoT）

结构化的 Chain-of-Thought 引导，确保：
1. 准确理解章节定位
2. 遵守边界约束避免重复
3. 生成高质量叙事内容
"""

from ._base import get_base_context, get_quality_rules

# ============================================================
# 章节生成 Prompt 模板
# ============================================================

CHAPTER_PROMPT_TEMPLATE = """
{base_context}

---

# 任务目标

为深度解读文章的**第 {chapter_number} 章**撰写完整内容。

---

# 全局上下文

## 原始内容
<source_content>
{full_content}
</source_content>

## 完整大纲
<outline>
{full_outline}
</outline>

{previous_context}

---

# 当前章节信息

**章节序号**：第 {chapter_number} 章
**章节标题**：{chapter_title}

## 子章节结构
{subsections_structure}

## 必须包含的内容
{must_include_list}

## 禁止涉及的内容（已在其他章节覆盖）
{must_exclude_list}

## 内容指导
{content_guidance}

---

# 思考过程（Chain-of-Thought）

请按以下步骤逐步思考，确保章节质量：

## 步骤 1：定位分析

回答以下问题：
1. 这一章在整体大纲中的位置是什么？（开场/核心/过渡/收尾）
2. 前一章讲了什么？本章需要如何衔接？
3. 后一章将讲什么？本章需要为其铺垫什么？

## 步骤 2：边界确认

**严格检查 must_exclude 列表**：
- 列出本章绝对不能涉及的内容
- 如果写作过程中发现想提及这些内容，改用引用式表达："这一点在第X章已详细分析"

## 步骤 3：素材定位

从原始内容中定位本章需要使用的素材：
- 哪些段落/数据直接支撑本章论点？
- 哪些引用/案例必须包含？
- 有没有原文中的"金句"可以使用？

## 步骤 4：叙事结构设计

按以下结构组织内容：

### Scene Setting（起）
- 用一个事实、一个数字或一个冲突直接把读者拽进场景
- 画面感 > 概念定义
- **禁止**："在本章中，我们将探讨..."

### Connect the Dots（承/转）
- 把离散的数据点连成线
- 解释它是如何从 A 推导到 B 的
- 展示因果链条，而非并列罗列

### Insight（合）
- 给出这章的"灵魂总结"
- 这不是复述，是透视——告诉读者"这意味着什么"
- 可以适当引入反面视角或未解决的问题

## 步骤 5：开场三句测试

写完开头三句后，检查：
- 这三个句子能否无缝替换到任何一篇科技报道中？
- 如果能，说明太"AI"了——重写，直到带有本章独有的信息密度和画面感

## 步骤 6：摩擦力检查

本章是否只写了成功和优点？
- 如果是，找出至少一个"代价"、"质疑"或"失败尝试"
- 技术突破背后的 trade-off 是什么？

---

# 输出要求

## 格式要求
- 输出必须以 `### {chapter_number}. {chapter_title}` 开头（Markdown H3 标题）
- 标题后直接用事实、数据、观点开始正文
- 可以使用小标题帮助阅读理解，但避免机械的"章节摘要"类标题

## 内容要求
- 充分展开每个子章节，每个论点需有具体案例或数据支撑
- 技术细节要解释清楚，不要一句话带过
- 所有论述必须有原文支撑，不要编造

## 禁止事项
- ❌ "上一章我们谈到..."、"接下来我们将..."
- ❌ "演讲开场"、"演讲伊始"、"在最开始"
- ❌ "从...说起"、"首先让我们..."
- ❌ 在概念后添加括号英文注释
- ❌ 涉及 must_exclude 中列出的任何内容

---

{quality_rules}

---

**现在，请开始撰写第 {chapter_number} 章 - {chapter_title} 的内容：**
"""

# ============================================================
# 上下文构建辅助
# ============================================================

PREVIOUS_CHAPTER_CONTEXT = """
## 上一章节内容（避免重复）
**第 {prev_index} 章 - {prev_title}**

{prev_content}
"""

PREVIOUS_CHAPTERS_SUMMARY = """
## 已生成章节摘要（绝对不能重复这些内容）

{summaries}
"""

SUMMARY_ITEM = """**第 {index} 章 - {title}**：
{summary}

---
"""


def format_subsections(subsections: list) -> str:
    """格式化子章节结构"""
    if not subsections:
        return "（无子章节信息）"
    
    lines = []
    for i, sub in enumerate(subsections, 1):
        subtitle = sub.get("subtitle", f"子章节 {i}")
        key_points = sub.get("key_points", [])
        
        lines.append(f"### {i}. {subtitle}")
        if key_points:
            for point in key_points:
                lines.append(f"   - {point}")
        lines.append("")
    
    return "\n".join(lines)


def format_list(items: list, default: str = "（无）") -> str:
    """格式化列表"""
    if not items:
        return default
    return "\n".join(f"- {item}" for item in items)


def build_previous_context(
    previous_chapter: dict = None,
    previous_summaries: list = None
) -> str:
    """
    构建前序章节上下文
    
    Args:
        previous_chapter: 上一章节信息 {"index": 1, "title": "...", "content": "..."}
        previous_summaries: 已生成章节摘要列表 [{"index": 1, "title": "...", "summary": "..."}]
    
    Returns:
        格式化的上下文字符串
    """
    parts = []
    
    # 上一章节完整内容
    if previous_chapter:
        parts.append(PREVIOUS_CHAPTER_CONTEXT.format(
            prev_index=previous_chapter.get("index", ""),
            prev_title=previous_chapter.get("title", ""),
            prev_content=previous_chapter.get("content", "")
        ))
    
    # 已生成章节摘要
    if previous_summaries:
        summaries_text = ""
        for item in previous_summaries:
            summaries_text += SUMMARY_ITEM.format(
                index=item.get("index", ""),
                title=item.get("title", ""),
                summary=item.get("summary", "")
            )
        parts.append(PREVIOUS_CHAPTERS_SUMMARY.format(summaries=summaries_text))
    
    return "\n".join(parts) if parts else ""


def build_chapter_prompt(
    full_content: str,
    full_outline: str,
    chapter_number: int,
    chapter_title: str,
    subsections: list = None,
    must_include: list = None,
    must_exclude: list = None,
    content_guidance: str = "",
    previous_chapter: dict = None,
    previous_summaries: list = None
) -> str:
    """
    构建章节生成 prompt
    
    Args:
        full_content: 原始内容
        full_outline: 完整大纲
        chapter_number: 章节序号
        chapter_title: 章节标题
        subsections: 子章节列表
        must_include: 必须包含的内容
        must_exclude: 禁止涉及的内容
        content_guidance: 内容指导
        previous_chapter: 上一章节信息
        previous_summaries: 已生成章节摘要
        
    Returns:
        格式化后的 prompt
    """
    return CHAPTER_PROMPT_TEMPLATE.format(
        base_context=get_base_context(),
        quality_rules=get_quality_rules(),
        full_content=full_content,
        full_outline=full_outline,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        subsections_structure=format_subsections(subsections or []),
        must_include_list=format_list(must_include or [], "（无特定要求）"),
        must_exclude_list=format_list(must_exclude or [], "（无特定约束）"),
        content_guidance=content_guidance or "（无特定指导）",
        previous_context=build_previous_context(previous_chapter, previous_summaries)
    )


# ============================================================
# 去重指令（用于顺序生成模式）
# ============================================================

DEDUPLICATION_INSTRUCTION_SEQUENTIAL = """
## 顺序生成模式去重检查（重要）

你已经生成了前面的所有章节，在写作本章节之前，请仔细审查：

1. **核心论点去重**：已生成章节中讲过的主要观点、案例、数据，本章节绝对不能重复
2. **数据和案例去重**：检查前序章节中已用过的数字、百分比、客户案例
3. **结构差异化**：如果前序章节开篇用了某种方式，本章节应使用不同的开篇方式
4. **衔接而非重复**：与上一章保持逻辑上的衔接，但绝对不能重复已讲述的内容

**禁止事项**：
- 不要使用"上一章我们谈到..."、"前文提到"等表达
- 不要重复引用同一个原文金句
- 不要重新解释前序章节已详细解释过的概念
"""
