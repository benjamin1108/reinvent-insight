# Reinvent Insight 提示词系统完整文档

> 版本: 2.0 (2025-12-17)  
> 重构说明: 删除字数控制机制，改为基于子章节结构的约束

---

## 目录

- [核心架构](#核心架构)
- [模式配置](#模式配置)
- [公共规则](#公共规则)
- [Outline 生成](#outline-生成)
- [Chapter 生成](#chapter-生成)
- [Conclusion 生成](#conclusion-生成)
- [约束机制对比](#约束机制对比)

---

## 核心架构

### 生成流程

```
Outline 阶段
    ↓
生成 JSON 元数据（包含 subsections/must_include/must_exclude/content_guidance）
    ↓
Chapter 阶段（并发/顺序）
    ↓
基于 subsections 的结构化约束生成章节内容
    ↓
Conclusion 阶段
    ↓
生成洞见延伸和金句
```

### 文件结构

```
domain/prompts/
├── __init__.py         # 导出所有模板
├── common.py           # 公共规则（角色定义、质量控制）
├── outline.py          # Outline 生成提示词
├── chapter.py          # Chapter 生成提示词
├── conclusion.py       # Conclusion 生成提示词
└── ultra.py            # Deep/Ultra 模式配置
```

---

## 模式配置

### 配置参数（ultra.py）

```python
MODE_CONFIGS = {
    "deep": {
        "chapter_range": "8-10",
        "chapter_min": 8,
        "chapter_max": 10,
        "subsection_min": 3,      # 每章至少 3 个子章节
        "insights_count": "5-6"
    },
    "ultra": {
        "chapter_range": "12-20",
        "chapter_min": 12,
        "chapter_max": 16,
        "subsection_min": 3,      # 每章至少 3 个子章节
        "insights_count": "8-10"
    }
}
```

### 核心设计理念

1. **不控制字数**：AI 无法精确计数，字数要求徒劳
2. **结构化约束**：通过子章节数量和论点数控制内容密度
3. **下限引导**：设置最小值（3个子章节），不设上限
4. **自然展开**：要求 AI "尽可能详细"，而非"写 5000 字"

---

## 公共规则

### 角色定位（common.py）

```
角色：科技媒体资深主编
风格参考：《晚点LatePost》等一线科技媒体
```

**文风特征**：
- 专业但不晦涩
- 深度但不冗长
- 客观但有洞察
- 流畅且有节奏
- 数据驱动

**禁止事项**：
- ❌ 中文（英文）混排
- ❌ 套话开场（"众所周知"、"值得注意"）
- ❌ 过度修饰（"惊人的"、"史诗级"）
- ❌ 生硬过渡（"上一章我们谈到..."）

### 质量控制规则

**1. 术语一致性**
- 专有名词统一：OpenAI（不能出现 Open AI）
- 人名拼写一致：Sarah Friar（不能出现 Sarah Frier）

**2. 事实准确性**
- 数据精确：与原文 100% 一致
- 引用准确：逐字核对，不得有拼写错误

**3. 格式规范**
- 中文全角标点：，。？！
- 英文半角标点：, . ? !
- 空格规则：中英之间、中数之间需空格，数字与单位间不空格（130亿美元）

**4. 语言纯净**
- 禁止中英混排：人机结合 ✅ / 人机结合（Human-Machine Integration）❌
- 删除情绪形容词：指数级爆发 → 快速增长
- 直述风格：直接陈述事实，不用套话铺垫

---

## Outline 生成

### 输出格式（纯 JSON）

```json
{
  "title_en": "AI Scaling Laws and 2030 Predictions",
  "title_cn": "AI 扩展定律与 2030 年预测",
  "introduction": "200-400字引言，必须透出内容来源...",
  "chapters": [
    {
      "index": 1,
      "title": "Trainium 2 芯片正式商用：AI 训练性能提升4倍",
      "subsections": [
        {
          "subtitle": "架构升级：从 Trainium 1 到 Trainium 2",
          "key_points": [
            "FP8 精度支持带来的训练速度提升",
            "HBM3 内存带宽翻倍的影响",
            "芯片间互连从 NeuronLink v1 到 v2 的演进"
          ]
        },
        {
          "subtitle": "性能基准测试：与竞品对比",
          "key_points": [
            "GPT-3 模型训练时间从 X 降至 Y",
            "成本降低 40% 的具体计算方式"
          ]
        },
        {
          "subtitle": "商用时间表与客户采用情况",
          "key_points": [
            "2024 Q4 正式商用计划",
            "Apple 等客户的早期测试反馈"
          ]
        }
      ],
      "must_include": [
        "4倍性能提升的具体测试数据",
        "40%成本降低的计算逻辑",
        "与 Trainium 1 的对比"
      ],
      "must_exclude": [
        "Trainium 3 的路线图（第3章覆盖）",
        "Apple 的具体使用案例（第4章覆盖）"
      ],
      "content_guidance": "本章聚焦 Trainium 2 的技术规格和商用时间表，强调性能提升的具体数据支撑。不涉及未来路线图和客户案例细节，保持在产品本身的层面。"
    }
  ]
}
```

### 关键字段说明

**subsections**（核心约束）：
- 每章至少 3 个子章节
- 每个子章节必须明确 2-3 个 `key_points`
- AI 会严格按照子章节结构展开

**must_include**（正向约束）：
- 必须包含的数据点、案例、论点
- 避免遗漏关键信息

**must_exclude**（负向约束，最强防火墙）：
- **绝对禁止**涉及的内容（已在其他章节覆盖）
- 即使 AI 认为有必要，也必须遵守
- 如需引用，使用"这一点在第X章已详细分析"

**content_guidance**（自然语言指导）：
- 描述内容范围、重点、注意事项
- 不使用机械标签（如 `source_content_amount: rich`）

### 章节设计原则

**内容类型识别**：
1. **Keynote 发布会**：产品发布 + 理念讲解 + 客户案例
2. **技术深度解读**：问题导向，层次递进
3. **长篇访谈**：主题聚类，观点提炼
4. **行业分析报告**：趋势洞察，横向对比
5. **技术教程**：技术层级，步骤清晰

**标题策略**（以 Keynote 为例）：
- **产品发布章节**：`[产品名 + 版本] + [核心亮点]`
  - 示例："Trainium 2 芯片正式商用：AI 训练性能提升4倍"
- **理念/方法论章节**：`[核心理念] + [关键观点]`
  - 示例："云原生时代的长期主义：AWS 的基础设施承诺"
- **客户案例章节**：`[客户名称] + [应用场景] + [关键成果]`
  - 示例："Apple Intelligence 案例：支撑全球10亿设备的云端算力架构"

**叙事重构原则**：
- 打破原文顺序：问题前置、方案后置
- 识别叙事缺陷：流水账 → 起承转合
- 主题聚类：将分散的对话按主题重组
- **禁止**凭空添加原文没有的内容

---

## Chapter 生成

### 约束模板（chapter.py）

```
## 当前章节生成要求

**子章节结构**（至少 3 个，根据内容可增加）：
1. **架构升级：从 Trainium 1 到 Trainium 2**
   核心论点：
   - FP8 精度支持带来的训练速度提升
   - HBM3 内存带宽翻倍的影响
   - 芯片间互连从 NeuronLink v1 到 v2 的演进

2. **性能基准测试：与竞品对比**
   核心论点：
   - GPT-3 模型训练时间从 X 降至 Y
   - 成本降低 40% 的具体计算方式

3. **商用时间表与客户采用情况**
   核心论点：
   - 2024 Q4 正式商用计划
   - Apple 等客户的早期测试反馈

**必须包含的内容**：
- 4倍性能提升的具体测试数据
- 40%成本降低的计算逻辑
- 与 Trainium 1 的对比

**禁止涉及的内容**：
- Trainium 3 的路线图（第3章覆盖）
- Apple 的具体使用案例（第4章覆盖）

**内容指导**：
本章聚焦 Trainium 2 的技术规格和商用时间表，强调性能提升的具体数据支撑。不涉及未来路线图和客户案例细节，保持在产品本身的层面。

---

## 生成规则

1. **充分展开每个子章节**
   - 每个论点需有具体案例或数据支撑
   - 技术细节要解释清楚，不要一句话带过
   - 宁可写得详细，也不要为了简洁而省略重要内容

2. **基于原文事实**
   - 所有论述必须有原文支撑
   - 不要编造原文中没有的案例或数据

3. **避免重复**
   - 严格遵守"禁止涉及的内容"
   - 如需引用其他章节内容，使用"这一点在第X章已详细分析"

**提示**：如果某个论点内容特别丰富，可以拆分为多个段落深入展开
```

### 去重机制

**并发模式**（基于大纲）：
- 依赖 `must_exclude` 防止内容重复
- 每个章节在大纲阶段就明确边界

**顺序模式**（基于已生成章节）：
- 传递已生成章节的摘要
- 强制检查核心论点、数据、案例去重
- 禁止重复引用同一个原文金句

---

## Conclusion 生成

### 任务定义

**洞见延伸**（超越正文的独立思考）：
- **定义**：基于正文事实进行**外延推理**，提供正文未明确提及的新视角
- **数量**：不多于 10 条

**禁止**：
- ❌ 复述正文已详细论述的观点
- ❌ 以"文章提到..."或"正如第X章所述..."开头
- ❌ 纯粹的事实还原（如"AWS通过风冷设计降低了TCO"）

**必须**：
- ✅ 基于正文事实，推导出正文未直接阐述的结论
- ✅ 每条洞见包含**新视角**或**外延启示**

**示例对照**：
- 正文讲"AWS用风冷降成本" → 洞见延伸："这种策略对中小云厂商的启示"
- 正文讲"Trainium3支持MoE" → 洞见延伸："MoE架构对芯片设计范式的长期影响"

**金句&原声引用**：
- 从原文中挑选有代表性的原句
- 附中文翻译
- 数量不多于 10 条

---

## 约束机制对比

### 1.0 版本（已废弃）

**字数控制机制**：
```python
# 密度参数（5处定义，3个参数）
source_content_amount: "rich" / "moderate" / "sparse"
information_density: "high" / "medium" / "low"
generation_depth: "detailed" / "moderate" / "brief"

# 字数目标
word_targets = {
    "detailed": 5000,
    "moderate": 3000,
    "brief": 2000
}

# 字数指令
"目标约 5000 字，充分展开论述"
```

**问题**：
1. AI 无法精确计数字数（基于 token 生成）
2. 指令冲突：同一约束定义 3 次，值不一致
3. 参数过度细化：3 个密度参数，只有 1 个真正被用
4. AI 倾向注水凑字数，而非充实内容

---

### 2.0 版本（当前）

**结构化约束机制**：
```json
{
  "subsections": [
    {
      "subtitle": "子章节标题",
      "key_points": ["论点1", "论点2", "论点3"]
    }
  ],
  "must_include": ["必须包含的数据点"],
  "must_exclude": ["绝对禁止的内容"],
  "content_guidance": "自然语言描述内容范围"
}
```

**优势**：
1. **可验证性**：AI 可以检查是否覆盖所有 key_points
2. **结构清晰**：子章节数量直接控制内容粒度
3. **灵活性**：设置下限（3个），不设上限
4. **自然展开**：AI 根据论点丰富度自然决定长度

**核心理念转变**：
- **从量化控制到结构控制**：不要求"5000字"，要求"3个子章节，每个覆盖2-3个论点"
- **从机械标签到自然语言**：用 `content_guidance` 描述内容重点，而非 `source_content_amount: rich`
- **从上限约束到下限引导**："至少3个"而非"3-4个"

---

## 使用示例

### 调用 Outline 生成

```python
from reinvent_insight.domain import prompts

# 获取模式配置
config = prompts.get_mode_config(is_ultra=True)

# 获取大纲生成指令
mode_instructions = prompts.get_outline_instructions(is_ultra=True)

# 构建完整提示词
prompt = prompts.OUTLINE_PROMPT_TEMPLATE.format(
    role_and_style=prompts.ROLE_AND_STYLE_GUIDE,
    base_prompt="基础提示词...",
    content_type="完整英文字幕",
    content_description="完整字幕",
    full_content="[字幕内容]",
    mode_instructions=mode_instructions,
    quality_control_rules=prompts.QUALITY_CONTROL_RULES
)
```

### 调用 Chapter 生成

```python
# 从 outline JSON 提取元数据
chapter_meta = outline_json["chapters"][0]

# 构建子章节结构字符串
subsections = chapter_meta.get("subsections", [])
subsections_structure = ""
for i, sub in enumerate(subsections, 1):
    subtitle = sub.get("subtitle", "")
    key_points = sub.get("key_points", [])
    subsections_structure += f"\n{i}. **{subtitle}**\n"
    if key_points:
        subsections_structure += "   核心论点：\n"
        for point in key_points:
            subsections_structure += f"   - {point}\n"

# 提取其他约束
must_include = chapter_meta.get("must_include", [])
must_include_list = "\n".join([f"- {item}" for item in must_include]) if must_include else "(无)"

must_exclude = chapter_meta.get("must_exclude", [])
must_exclude_list = "\n".join([f"- {item}" for item in must_exclude]) if must_exclude else "(无)"

content_guidance = chapter_meta.get("content_guidance", "请基于原文充分展开")

# 构建约束模板
chapter_constraint = prompts.CHAPTER_CONTENT_CONSTRAINT_TEMPLATE.format(
    subsections_structure=subsections_structure,
    must_include_list=must_include_list,
    must_exclude_list=must_exclude_list,
    content_guidance=content_guidance
)

# 构建完整提示词
prompt = prompts.CHAPTER_PROMPT_TEMPLATE.format(
    role_and_style=prompts.ROLE_AND_STYLE_GUIDE,
    base_prompt="基础提示词...",
    content_type="完整英文字幕",
    content_description="完整字幕",
    full_content="[字幕内容]",
    full_outline="[大纲内容]",
    previous_chapters_context="[前序章节上下文]",
    chapter_content_constraint=chapter_constraint,
    chapter_number=1,
    current_chapter_title="Trainium 2 芯片正式商用：AI 训练性能提升4倍",
    deduplication_instruction=prompts.DEDUPLICATION_INSTRUCTION_FIRST,
    quality_control_rules=prompts.QUALITY_CONTROL_RULES
)
```

---

## 重构历史

### 2025-12-17 重构记录

**删除的内容**：
1. ❌ 3 个密度参数（`source_content_amount`, `information_density`, `generation_depth`）
2. ❌ 字数配置（`word_targets: {detailed: 5000}`）
3. ❌ 字数硬性要求指令（"目标约 5000 字"）
4. ❌ 过度设计的字段（`opening_hook`, `closing_transition`, `prev_chapter_link`, `next_chapter_link`, `rationale`）
5. ❌ `CHAPTER_DEPTH_INSTRUCTIONS` 整个模板
6. ❌ `get_chapter_instructions()` 函数

**保留/新增的内容**：
1. ✅ `subsections` + `key_points`（核心约束）
2. ✅ `must_include` + `must_exclude`（正负向约束）
3. ✅ `content_guidance`（自然语言指导）
4. ✅ `subsection_min: 3`（最小子章节数）
5. ✅ "宁可写得详细，也不要为了简洁而省略重要内容"（新生成规则）

**影响的文件**：
- `outline.py` - 简化 JSON schema
- `chapter.py` - 重命名模板，删除字数指导
- `ultra.py` - 删除 word_targets
- `youtube_workflow.py` - 重写章节生成逻辑
- `base.py` - 简化元数据缓存
- `__init__.py` - 更新导出

---

## 附录：完整提示词模板

### common.py - 角色定义

```
## 角色定位与文风要求

**你的角色**：科技媒体资深主编

**行文风格参考**：一线科技媒体的深度解读文章

**文风特征**：
1. **专业但不晦涩**：使用准确的专业术语，但要确保普通读者也能理解
2. **深度但不冗长**：挖掘深层逻辑和趋势，但避免无意义的堆砌
3. **客观但有洞察**：基于事实陈述，但针对值得深度挖掘的内容提供独到的分析视角
4. **流畅且有节奏**：逻辑清晰，阅读体验流畅
5. **数据驱动**：善用具体数字、案例和引用来支撑观点

**禁止使用的开篇方式**：
- ❌ 生硬的承上启下："上一章我们谈到..." "在上文中..." "接下来我们将..."
- ❌ 演讲实录式："演讲开场" "演讲伊始" "在最开始" "开篇" "首先"
- ❌ 刻意的引入："从...说起" "让我们从...开始"

**推荐的表达方式**：
- ✅ 直接切入核心内容：用事实、数据、观点直接开始，不需要铺垫
- ✅ 自然过渡：通过内容本身的逻辑关联实现衔接

**中英文混排的严格规范**：
- ❌ 绝对禁止：中文（英文）格式
- ✅ 唯一允许：专有名词本身就是英文（OpenAI、ChatGPT）
```

### ultra.py - 模式配置

```python
MODE_CONFIGS = {
    "deep": {
        "chapter_range": "8-10",
        "chapter_min": 8,
        "chapter_max": 10,
        "subsection_min": 3,
        "insights_count": "5-6"
    },
    "ultra": {
        "chapter_range": "12-20",
        "chapter_min": 12,
        "chapter_max": 16,
        "subsection_min": 3,
        "insights_count": "8-10"
    }
}
```

### outline.py - 大纲生成核心指令

```
## 章节框架详细规划（核心要求）

为了避免并发生成时章节间的内容重复与逻辑割裂，**每个章节必须包含详细的内部框架**：

{
  "index": 1,
  "title": "章节标题",
  "subsections": [
    {
      "subtitle": "子章节标题",
      "key_points": ["该子章节必须覆盖的核心论点1", "核心论点2", "核心论点3"]
    }
  ],
  "must_include": ["必须包含的关键数据点", "必须引用的案例"],
  "must_exclude": ["绝对禁止涉及的内容（已在其他章节覆盖）"],
  "content_guidance": "自然语言描述：本章内容范围、重点论述方向、需要特别注意的点"
}

### 子章节设计原则

- **subsections 数组**：每章至少 3 个子章节，每个子章节聚焦一个核心论点
- **key_points 清晰**：明确列出每个子章节必须覆盖的论点（每个子章节 2-3 个 key_points）
- **顺序逻辑**：子章节之间应有递进或并列的逻辑关系
- **灵活性**：如果内容特别丰富，可以增加子章节数量，不要强求每章都是相同数量

### 章节边界与连接

- **must_exclude**：**强制负向约束** - 绝对禁止包含的内容，这是防止内容撞车的最强防火墙
  - ⚠️ 即使你认为再提一次很有必要，也必须遵守
  - ⚠️ 如需引用已覆盖内容，使用"这一点在第X章已详细分析"的引用式表达
- **content_guidance**：用自然语言描述内容范围和重点，而非机械标签
```

### chapter.py - 章节生成约束

```
## 生成规则

1. **充分展开每个子章节**
   - 每个论点需有具体案例或数据支撑
   - 技术细节要解释清楚，不要一句话带过
   - 宁可写得详细，也不要为了简洁而省略重要内容

2. **基于原文事实**
   - 所有论述必须有原文支撑
   - 不要编造原文中没有的案例或数据

3. **避免重复**
   - 严格遵守"禁止涉及的内容"
   - 如需引用其他章节内容，使用"这一点在第X章已详细分析"

**提示**：如果某个论点内容特别丰富，可以拆分为多个段落深入展开
```

---

**文档结束**
