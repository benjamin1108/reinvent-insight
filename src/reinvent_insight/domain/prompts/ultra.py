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
        "chapter_min": 8,
        "chapter_max": 10,
        "subsection_range": "1-2",  # 子章节较少
        "depth_mode": "all_detailed",
        "depth_mode_desc": "所有章节统一标注为 detailed，确保深度一致",
        # 字数配置：精炼版
        "word_targets": {
            "detailed": 4000,
            "min_detailed": 3000  # 硬性最低字数
        },
        "expansion_strategy": "balanced",
        "expansion_desc": "适度展开核心论点，避免过度扩展",
        # 洞见配置
        "insights_count": "5-6"
    },
    "ultra": {
        # 章节规模：全面深度，适合 1-2 小时或复杂文档
        "chapter_range": "12-16",  # 从 18-20 降到 12-16，减少碎片化
        "chapter_min": 12,
        "chapter_max": 16,
        "subsection_range": "2-4",  # 子章节较多
        "depth_mode": "all_detailed",
        "depth_mode_desc": "所有章节统一标注为 detailed，确保深度一致",
        # 字数配置：详尽版
        "word_targets": {
            "detailed": 5000,
            "min_detailed": 4000  # 硬性最低字数
        },
        "expansion_strategy": "aggressive",
        "expansion_desc": "充分展开，可补充技术背景、行业上下文和相关案例类比",
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
**子章节数**：每章规划{subsection_range}个子章节，每个子章节聚焦一个核心论点
**深度模式**：{depth_mode_desc}

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
      "subtitle": "子章节标题（可选，用于章节内部分段）",
      "key_points": ["该子章节必须覆盖的核心论点1", "核心论点2"]
    }}}}
  ],
  "opening_hook": "该章节的起始引子/切入点描述（如何开篇，用什么事实或数据引入）",
  "closing_transition": "该章节的结尾/过渡描述（如何收尾，与下一章如何衔接）",
  "must_include": ["必须包含的关键数据点", "必须引用的案例"],
  "must_exclude": ["绝对禁止涉及的内容（已在其他章节覆盖）"],
  "prev_chapter_link": "与上一章的逻辑关系",
  "next_chapter_link": "与下一章的逻辑关系"
}}}}
```

### 子章节设计原则

- **subsections 数组**：每章规划{subsection_range}个子章节，每个子章节聚焦一个核心论点
- **key_points 清晰**：明确列出每个子章节必须覆盖的论点，避免遗漏或重复
- **顺序逻辑**：子章节之间应有递进或并列的逻辑关系

### 章节边界与连接

- **opening_hook**：设计每章独特的开篇方式，避免所有章节都以类似方式开始
- **closing_transition**：规划与下一章的自然过渡，确保阅读连贯性
  - ⚠️ **禁止使用以下模板化过渡**：
    * "在确立了X之后，AWS开始..."
    * "解决了X问题后，接下来面临的挑战是..."
    * "这为X奠定了基础，下一章将探讨..."
  - ✅ **推荐过渡方式**：
    * 悬念式：提出一个新问题
    * 对比式：暗示不同视角
    * 静默式：直接结束，不刻意过渡（技术章节推荐）
- **must_exclude**：**强制负向约束** - 绝对禁止包含的内容，这是防止内容撞车的最强防火墙
  - ⚠️ 即使你认为再提一次很有必要，也必须遵守
  - ⚠️ 如需引用已覆盖内容，使用"这一点在第X章已详细分析"的引用式表达
- **prev_chapter_link / next_chapter_link**：建立章节间的逻辑链条
"""


def get_outline_instructions(is_ultra: bool) -> str:
    """获取大纲生成指令"""
    config = get_mode_config(is_ultra)
    return OUTLINE_MODE_INSTRUCTIONS.format(
        chapter_range=config["chapter_range"],
        chapter_min=config["chapter_min"],
        chapter_max=config["chapter_max"],
        subsection_range=config["subsection_range"],
        depth_mode_desc=config["depth_mode_desc"]
    )


# ========================================
# 统一章节深度指令模板
# ========================================

CHAPTER_DEPTH_INSTRUCTIONS = """
## 字数硬性要求（强制执行）

**最低字数**：{min_words} 字（低于此数视为任务未完成）
**目标字数**：{target_words} 字
**扩展策略**：{expansion_desc}

⚠️ **字数警告**：
- 如果你的输出少于 {min_words} 字，说明内容展开不充分
- 宁可超出目标 20%，也绝不能低于最低字数
- 每个子章节至少 800 字，不要一两句话就跳到下一个小节

**字数不足时的补救措施**（按优先级）：
1. 为每个论点补充具体案例或数据佐证
2. 展开技术原理的详细解释
3. 添加「为什么重要」「意味着什么」的分析
4. 补充行业背景或历史演进
5. 增加对比分析（与竞品/前代/替代方案）

**生成深度说明**：
- brief（简洁）：约 2000-2500 字，快速概括核心要点
- moderate（适度）：约 3000-3500 字，适度展开关键论点
- detailed（详细）：约 {target_words} 字，深入分析并详细解读

**防止注水**：
- 如果原文内容稀少(sparse)，绝对不要为了凑字数而编造
- 宁可写得少但准确，也不要冗长但偏离原文
- 所有论述必须有原文支撑
"""


def get_chapter_instructions(is_ultra: bool, generation_depth: str = "detailed") -> str:
    """获取章节生成指令
    
    Args:
        is_ultra: 是否为 Ultra 模式
        generation_depth: 生成深度 (brief/moderate/detailed)
    """
    config = get_mode_config(is_ultra)
    
    # 获取目标字数和最低字数
    target_words = config["word_targets"].get("detailed", 5000)
    min_words = config["word_targets"].get("min_detailed", 3000)
    
    return CHAPTER_DEPTH_INSTRUCTIONS.format(
        target_words=target_words,
        min_words=min_words,
        expansion_desc=config["expansion_desc"]
    )


# ========================================
# 向后兼容（保留旧变量名，逐步废弃）
# ========================================

# 这些变量保留用于过渡期，新代码应使用 get_outline_instructions() 和 get_chapter_instructions()
DEEP_OUTLINE_INSTRUCTIONS = get_outline_instructions(is_ultra=False)
ULTRA_OUTLINE_INSTRUCTIONS = get_outline_instructions(is_ultra=True)
ULTRA_CHAPTER_INSTRUCTIONS = get_chapter_instructions(is_ultra=True)