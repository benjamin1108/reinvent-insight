# -*- coding: utf-8 -*-
"""
DeepInsight 模式提示词（统一架构）

Deep 和 Ultra 使用同一套核心逻辑，通过配置参数控制差异：
- 章节数量范围
- 子章节数量
- 深度模式
- 字数目标
- 扩展策略
"""

# ========================================
# 模式配置（核心差异抽象为参数）
# ========================================

MODE_CONFIGS = {
    "deep": {
        # 章节规模：精炼深度，适合 30-60 分钟内容
        "chapter_range": "8-10",
        "chapter_min": 5,
        "chapter_max": 20,
        "subsection_min": 3,  # 每章至少 3 个子章节
        # 洞见配置
        "insights_count": "5-6"
    },
    "ultra": {
        # 章节规模：全面深度，适合 1-2 小时或复杂文档
        "chapter_range": "12-20",
        "chapter_min": 10,
        "chapter_max": 20,
        "subsection_min": 4,  # 每章至少 3 个子章节
        # 洞见配置
        "insights_count": "8-10"
    }
}


def get_mode_config(is_ultra: bool) -> dict:
    """获取模式配置"""
    return MODE_CONFIGS["ultra"] if is_ultra else MODE_CONFIGS["deep"]


# ========================================
# 统一大纲指令模板
# ========================================

OUTLINE_MODE_INSTRUCTIONS = """
## 章节规划约束

**章节数量**：{chapter_range}个章节（不可少于{chapter_min}章，不可超过{chapter_max}章）
**子章节数**：每章至少 {subsection_min} 个子章节，根据内容丰富程度可适当增加，不设上限

## 叙事重构原则（Narrative Re-engineering）

**你是架构师，不是速记员**。你的任务是重新设计内容的叙事结构，而非照搬原文顺序。

- 如果原文先讲解决方案后讲问题，应将问题前置、方案后置
- 如果原文话题跳跃、缺乏逻辑链条，应按主题重新聚类
- 目标是形成「问题 → 分析 → 解决方案 → 验证」的完整逻辑闭环
- 允许合并分散但主题相同的内容，允许拆分过于臃肿的段落
- **禁止**凭空添加原文没有的内容

## 章节框架详细规划（核心要求）

为了避免并发生成时章节间的内容重复与逻辑割裂，**每个章节必须包含详细的内部框架**：

```json
{{{{
  "index": 1,
  "title": "章节标题",
  "subsections": [
    {{{{
      "subtitle": "子章节标题",
      "key_points": ["该子章节必须覆盖的核心论点1", "核心论点2", "核心论点3"]
    }}}}
  ],
  "must_include": ["必须包含的关键数据点", "必须引用的案例"],
  "must_exclude": ["绝对禁止涉及的内容（已在其他章节覆盖）"],
  "content_guidance": "自然语言描述：本章内容范围、重点论述方向、需要特别注意的点"
}}}}
```

### 子章节设计原则

- **subsections 数组**：每章至少 {subsection_min} 个子章节，每个子章节聚焦一个核心论点
- **key_points 清晰**：明确列出每个子章节必须覆盖的论点（每个子章节 2-3 个 key_points）
- **顺序逻辑**：子章节之间应有递进或并列的逻辑关系
- **灵活性**：如果内容特别丰富，可以增加子章节数量，不要强求每章都是相同数量

### 章节边界与连接

- **must_exclude**：**强制负向约束** - 绝对禁止包含的内容，这是防止内容撞车的最强防火墙
  - ⚠️ 即使你认为再提一次很有必要，也必须遵守
  - ⚠️ 如需引用已覆盖内容，使用“这一点在第X章已详细分析”的引用式表达
- **content_guidance**：用自然语言描述内容范围和重点，而非机械标签
"""


def get_outline_instructions(is_ultra: bool) -> str:
    """获取大纲生成指令"""
    config = get_mode_config(is_ultra)
    return OUTLINE_MODE_INSTRUCTIONS.format(
        chapter_range=config["chapter_range"],
        chapter_min=config["chapter_min"],
        chapter_max=config["chapter_max"],
        subsection_min=config["subsection_min"]
    )


# ========================================
# 向后兼容（保留旧变量名，逐步废弃）
# ========================================

# 这些变量保留用于过渡期，新代码应使用 get_outline_instructions()
DEEP_OUTLINE_INSTRUCTIONS = get_outline_instructions(is_ultra=False)
ULTRA_OUTLINE_INSTRUCTIONS = get_outline_instructions(is_ultra=True)