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
        "chapter_range": "10-20",
        "chapter_min": 10,
        "chapter_max": 20,
        "subsection_range": "1-3",
        "depth_mode": "adaptive",  # brief/moderate/detailed 根据内容自适应
        "depth_mode_desc": "根据原文内容量自适应选择 brief/moderate/detailed",
        "word_targets": {
            "brief": 2000,
            "moderate": 3000,
            "detailed": 5000
        },
        "expansion_strategy": "conservative",
        "expansion_desc": "基于原文事实，不过度扩展；原文简略则输出简短"
    },
    "ultra": {
        "chapter_range": "18-20",
        "chapter_min": 18,
        "chapter_max": 20,
        "subsection_range": "2-4",
        "depth_mode": "all_detailed",  # 全部使用 detailed
        "depth_mode_desc": "所有章节统一标注为 detailed，确保深度一致",
        "word_targets": {
            "detailed": 6000
        },
        "expansion_strategy": "aggressive",
        "expansion_desc": "充分展开，可补充技术背景、行业上下文和相关案例类比"
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
- **must_exclude**：**强制负向约束** - 绝对禁止包含的内容，这是防止内容撞车的最强防火墙
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
## 字数与扩展要求

**目标字数**：约{target_words}字
**扩展策略**：{expansion_desc}

**生成要求**：
1. **严格遵守深度建议**：
   - brief（简洁）：快速概括核心要点，不展开细节，约2000字
   - moderate（适度）：适度展开关键论点和案例，约3000字
   - detailed（详细）：深入分析并提供详细解读，约5000字以上

2. **防止过度扩展**：
   - 如果原文内容稀少(sparse)，绝对不要为了凑字数而编造或过度推测
   - 如果原文只是简单提及某个点，你的解读也应该简短
   - 宁可生成较短但准确的内容，也不要生成冗长但偏离原文的内容

3. **基于原文事实**：
   - 所有论述必须有原文支撑
   - 不要添加原文中没有的案例、数据或观点
"""


def get_chapter_instructions(is_ultra: bool, generation_depth: str = "detailed") -> str:
    """获取章节生成指令
    
    Args:
        is_ultra: 是否为 Ultra 模式
        generation_depth: 生成深度 (brief/moderate/detailed)
    """
    config = get_mode_config(is_ultra)
    
    # Ultra 模式固定使用 detailed 的字数目标
    if is_ultra:
        target_words = config["word_targets"]["detailed"]
    else:
        target_words = config["word_targets"].get(generation_depth, 3000)
    
    return CHAPTER_DEPTH_INSTRUCTIONS.format(
        target_words=target_words,
        expansion_desc=config["expansion_desc"]
    )


# ========================================
# 向后兼容（保留旧变量名，逐步废弃）
# ========================================

# 这些变量保留用于过渡期，新代码应使用 get_outline_instructions() 和 get_chapter_instructions()
DEEP_OUTLINE_INSTRUCTIONS = get_outline_instructions(is_ultra=False)
ULTRA_OUTLINE_INSTRUCTIONS = get_outline_instructions(is_ultra=True)
ULTRA_CHAPTER_INSTRUCTIONS = get_chapter_instructions(is_ultra=True)