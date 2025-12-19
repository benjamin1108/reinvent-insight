# -*- coding: utf-8 -*-
"""
大纲生成 Prompt（v2 重构版 - 含 CoT）

结构化的 Chain-of-Thought 引导，确保：
1. 准确识别内容类型
2. 合理设计章节结构
3. 防止并发生成时的内容重复
"""

from ._base import get_base_context, get_quality_rules

# ============================================================
# 模式配置
# ============================================================

MODE_CONFIGS = {
    "deep": {
        "chapter_range": "8-10",
        "chapter_min": 5,
        "chapter_max": 15,
        "subsection_min": 3,
        "description": "精炼深度模式，适合 30-60 分钟内容"
    },
    "ultra": {
        "chapter_range": "12-20",
        "chapter_min": 10,
        "chapter_max": 25,
        "subsection_min": 4,
        "description": "全面深度模式，适合 1-2 小时或复杂文档"
    }
}


def get_mode_config(mode: str = "deep") -> dict:
    """获取模式配置"""
    return MODE_CONFIGS.get(mode, MODE_CONFIGS["deep"])


# ============================================================
# 大纲生成 Prompt 模板
# ============================================================

OUTLINE_PROMPT_TEMPLATE = """
{base_context}

---

# 任务目标

根据提供的原始内容，生成一份深度解读文章的**中文标题**、**英文标题**、**引言**和**章节大纲**。

---

# 输入内容

<source_content>
{full_content}
</source_content>

---

# 思考过程（Chain-of-Thought）

请按以下步骤逐步思考，确保大纲设计的质量：

## 步骤 1：内容类型识别

首先判断原文属于以下哪种类型，这决定了后续的章节设计策略：

| 类型 | 特征 | 章节策略 |
|------|------|----------|
| **产品发布会/Keynote** | 混合型：产品发布+战略理念+客户案例 | 按内容属性匹配标题风格 |
| **技术深度解读** | 深入剖析某个技术/产品的设计与实现 | 问题导向，层次递进 |
| **长篇访谈/对话** | 问答式结构，话题跳跃性较大 | 主题聚类，观点提炼 |
| **行业分析报告** | 趋势洞察、战略分析、未来预测 | 概念化标题，横向对比 |
| **技术教程** | 聚焦技术细节、操作步骤 | 技术层级，步骤清晰 |

**请输出你的判断**：这份内容属于哪种类型？为什么？

## 步骤 2：核心概念归属分配

识别文章涉及的所有核心概念，并为每个概念指定**唯一归属章节**：

```
核心概念归属表：
- "[概念A]" → 第X章独占，其他章节禁止重述
- "[概念B]" → 第Y章独占，第Z章仅允许引用式提及
...
```

这是防止并发生成时内容重复的**核心机制**。

## 步骤 3：叙事结构重构

你是**导演，不是剪辑师**。评估原文结构，决定是否需要重构：

1. **钩子开场**：第一章是否能在 30 秒内抓住读者？
2. **权重分配**：哪些内容值得 5000 字深入？哪些 500 字即可？
3. **逻辑闭环**：是否形成「问题 → 分析 → 解决方案 → 验证」的完整链条？

**允许的重构操作**：
- 合并分散但主题相同的内容
- 拆分过于臃肿的段落
- 调整顺序形成更好的逻辑链

**禁止的操作**：
- 凭空添加原文没有的内容

## 步骤 4：章节框架设计

为每个章节设计详细框架，包含：

1. **章节标题**：根据内容类型选择对应风格
   - 产品类：`[产品名 + 版本] + [核心亮点] + [关键参数]`
   - 理念类：接地气表达 + 实效洞察（拒绝宏大叙事）
   - 案例类：`[客户名称] + [应用场景] + [关键成果]`

2. **子章节结构**：每章至少 {subsection_min} 个子章节，每个子章节明确 key_points

3. **边界约束**：
   - `must_include`：必须包含的关键数据/案例
   - `must_exclude`：绝对禁止涉及的内容（已在其他章节覆盖）

## 步骤 5：自我验证

在输出前检查：

- [ ] 章节数量是否在 {chapter_min}-{chapter_max} 范围内？
- [ ] 每个章节的边界是否清晰？
- [ ] `must_exclude` 是否覆盖了所有潜在重复点？
- [ ] 第一章是否足够有冲击力？
- [ ] 是否避免了平均主义（每章长度相近）？

---

# 章节标题设计指南

## 产品发布类
✅ 「Trainium 2 芯片正式商用：AI 训练性能提升4倍，成本降低40%」
✅ 「Aurora DSQL：全球首个无服务器分布式 SQL 数据库」

## 理念/方法论类（拒绝宏大叙事，选择接地气表达）
风格选项：
- **口语+真相**：别发火：发脾气是本能，压下去是本事
- **动作+收益**：关掉手机：专注一小时，顶你磨洋工一天
- **比喻+场景**：烂尾楼心态：钱都花了，非得把这顿难吃的饭吃完？
- **吐槽+纠正**：瞎忙活：感动了自己，却没有任何产出

✅ 「消除 AI 幻觉：自动化推理检查的工程实践」
✅ 「开发者优先：从 API 设计到工具链的完整思考」

## 客户案例类
✅ 「Apple Intelligence 案例：支撑全球10亿设备的云端算力架构」
✅ 「Netflix 流媒体：每日处理 PB 级数据的实时分析架构」

## 需要避免的表达
❌ 模糊版本：「新一代 AI 芯片」（应明确 Trainium 2）
❌ 缺失参数：「性能大幅提升」（应明确「提升4倍」）
❌ 主观修辞：「震撼发布」「颠覆性创新」（让数据说话）
❌ 理念量化：「工程文化提升50%」（文化无法量化）

---

# 输出格式

**只输出 JSON，不要输出任何其他内容**

```json
{{
  "content_type": "[识别的内容类型]",
  "content_type_rationale": "[为什么判断为这个类型]",
  "concept_ownership": {{
    "[核心概念1]": "第X章独占",
    "[核心概念2]": "第Y章独占，第Z章仅引用"
  }},
  "title_en": "[英文标题]",
  "title_cn": "[中文标题]",
  "introduction": "[200-400字引言，激发读者兴趣，自然融入内容来源信息]",
  "chapters": [
    {{
      "index": 1,
      "title": "[章节标题]",
      "subsections": [
        {{
          "subtitle": "[子章节标题]",
          "key_points": ["核心论点1", "核心论点2", "核心论点3"]
        }}
      ],
      "must_include": ["必须包含的关键数据点", "必须引用的案例"],
      "must_exclude": ["绝对禁止涉及的内容"],
      "content_guidance": "[自然语言描述本章内容范围、重点和注意事项]"
    }}
  ]
}}
```

---

# 约束条件

## 章节数量约束
- **目标范围**：{chapter_range} 个章节
- **硬性下限**：不少于 {chapter_min} 章
- **硬性上限**：不超过 {chapter_max} 章

## 子章节约束
- 每章至少 {subsection_min} 个子章节
- 每个子章节 2-3 个 key_points
- 核心章节可增加子章节数量，边缘章节可减少

## 格式约束
- 章节标题必须是纯文本，禁止包含 Markdown 链接格式或方括号
- JSON 中如有引号，使用中文书名号「」替代
- 确保 JSON 格式合法，可被标准解析器解析

## 内容约束
- 禁止凭空添加原文没有的内容
- 禁止为了凑数而强行拆分或合并章节
- `must_exclude` 是防止内容撞车的最强防火墙，必须认真填写

---

{quality_rules}

---

**现在，请根据上述指引，输出大纲 JSON：**
"""


def build_outline_prompt(
    full_content: str,
    mode: str = "deep"
) -> str:
    """
    构建大纲生成 prompt
    
    Args:
        full_content: 原始内容
        mode: "deep" 或 "ultra"
        
    Returns:
        格式化后的 prompt
    """
    config = get_mode_config(mode)
    
    return OUTLINE_PROMPT_TEMPLATE.format(
        base_context=get_base_context(),
        quality_rules=get_quality_rules(),
        full_content=full_content,
        chapter_range=config["chapter_range"],
        chapter_min=config["chapter_min"],
        chapter_max=config["chapter_max"],
        subsection_min=config["subsection_min"]
    )


# ============================================================
# 向后兼容导出
# ============================================================

def get_outline_instructions(is_ultra: bool = False) -> str:
    """向后兼容：获取大纲指令片段"""
    mode = "ultra" if is_ultra else "deep"
    config = get_mode_config(mode)
    
    return f"""
## 章节规划约束

**章节数量**：{config["chapter_range"]}个章节（不可少于{config["chapter_min"]}章，不可超过{config["chapter_max"]}章）
**子章节数**：每章至少 {config["subsection_min"]} 个子章节
"""
