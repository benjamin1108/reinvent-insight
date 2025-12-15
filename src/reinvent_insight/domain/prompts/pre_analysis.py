# -*- coding: utf-8 -*-
"""
Pre分析提示词模板

在深度解读流程开始前，先对内容进行预分析，识别：
1. 内容类型（技术演讲、产品发布、访谈对话、理念阐述、操作指南等）
2. 内容风格（深度理论、实操导向、对话互动、叙事驱动等）
3. 目标受众（技术专家、产品经理、行业观察者、入门学习者等）
4. 建议的解读风格和侧重点

分析结果将注入后续的大纲生成和章节生成，使解读更贴合内容特性。
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PreAnalysisResult:
    """Pre分析结果数据类"""
    
    # 内容类型
    content_type: str  # 技术演讲/产品发布/访谈对话/理念阐述/操作指南/行业分析/案例解读等
    
    # 内容风格
    content_style: str  # 深度理论型/实操导向型/对话互动型/叙事驱动型/数据驱动型
    
    # 目标受众
    target_audience: str  # 技术专家/产品经理/行业观察者/入门学习者/决策层管理者
    
    # 内容深度级别
    depth_level: str  # 入门普及/进阶理解/专业深度/前沿探索
    
    # 核心价值主张
    core_value: str  # 内容的核心价值是什么
    
    # 解读风格建议
    interpretation_style: str  # 建议的解读风格描述
    
    # 章节设计建议
    chapter_design_hints: str  # 对章节设计的建议
    
    # 行文语气建议
    tone_guidance: str  # 行文语气的具体建议
    
    # 原始分析文本（完整保留AI输出）
    raw_analysis: str


# Pre分析提示词模板
PRE_ANALYSIS_PROMPT_TEMPLATE = """
## 任务背景

你是一位资深的内容策略专家，擅长分析不同类型内容的特点，并给出最佳的解读策略。

在深度解读一篇文章/视频/文档之前，我们需要先对内容进行"Pre分析"，以确定最适合的解读风格和策略。不同类型的内容需要不同的解读方式：

- **技术深度讲解**：需要注重原理拆解、代码示例、架构图解
- **产品发布会**：需要突出产品亮点、版本差异、商业价值
- **访谈对话**：需要保留对话的思想碰撞、观点交锋
- **理念阐述**：需要提炼核心思想、梳理逻辑链条
- **操作指南**：需要步骤清晰、可操作性强
- **行业分析**：需要数据支撑、趋势洞察、竞争分析

## 输入内容

- **内容类型**: {content_type}
- **内容概览**:
{content_preview}

---
## 分析任务

请仔细阅读上述内容，进行以下分析：

### 1. 内容类型识别

请从以下选项中选择最匹配的类型（可多选，但请标注主次）：

- **技术演讲/Deep Dive**：深入讲解技术原理、架构设计、实现细节
- **产品发布/Keynote**：发布新产品、新功能，强调商业价值和技术亮点
- **访谈对话/Interview**：两人或多人对话，思想交流，观点碰撞
- **理念阐述/Vision**：讲述愿景、战略方向、方法论、设计哲学
- **操作指南/Tutorial**：手把手教程，步骤式操作，实践导向
- **行业分析/Analysis**：市场分析、竞争格局、趋势预测，数据驱动
- **案例解读/Case Study**：真实项目经验、落地实践、问题解决过程

### 2. 内容风格判断

- **深度理论型**：重概念、重原理，适合想深入理解的读者
- **实操导向型**：重步骤、重实践，适合想动手尝试的读者
- **对话互动型**：保留对话感，展现思想碰撞
- **叙事驱动型**：故事化表达，有起承转合
- **数据驱动型**：大量数据、图表、定量分析

### 3. 目标受众画像

请判断这份内容最适合的读者群体：

- **技术专家**：有深厚技术背景，想了解前沿和细节
- **产品经理**：关注产品功能、用户价值、商业逻辑
- **行业观察者**：关注趋势、格局、战略方向
- **入门学习者**：刚接触该领域，需要清晰的入门解读
- **决策层管理者**：关注战略价值、ROI、风险评估

### 4. 解读风格建议

基于以上分析，给出具体的解读风格建议：

1. **标题风格**：应该偏产品化（带版本号、性能数据）还是偏理念化（概念+核心观点）？
2. **章节结构**：应该按时间线、按主题、按问题-解决方案、还是按深度递进？
3. **叙述语气**：应该更客观冷静、还是更有洞察锋芒？是专家视角还是观察者视角？
4. **内容侧重**：应该侧重 What（是什么）、Why（为什么）、还是 How（怎么做）？
5. **引用风格**：是多保留原声金句，还是以解读转述为主？

### 5. 特殊处理建议

如果内容有以下特点，请给出特殊处理建议：

- 如果是**多个演讲者**的内容，如何处理不同声音？
- 如果**内容跨度大**（多主题），如何保持连贯性？
- 如果**专业术语密集**，如何平衡专业性和可读性？
- 如果**案例丰富**，如何选取和组织案例？

## 输出格式

请严格按以下 JSON 格式输出：

```json
{{{{
  "content_type": "[主类型] + [次类型，如有]",
  "content_style": "[核心风格特征]",
  "target_audience": "[主要目标读者]",
  "depth_level": "[入门普及/进阶理解/专业深度/前沿探索]",
  "core_value": "[这份内容能给读者带来的核心价值，一句话概括]",
  "interpretation_style": "[详细的解读风格建议，100-200字]",
  "chapter_design_hints": "[章节设计的具体建议，100-200字]",
  "tone_guidance": "[行文语气的具体建议，50-100字]"
}}}}
```

**注意**：
- 所有字段都必须填写，不要留空
- interpretation_style、chapter_design_hints、tone_guidance 需要详细具体，将用于指导后续的大纲和章节生成
- 请确保 JSON 格式正确，可被解析
"""


# 将Pre分析结果注入到大纲生成的指令模板
PRE_ANALYSIS_INJECTION_FOR_OUTLINE = """
## 内容解读策略指导（基于Pre分析）

**内容类型**：{content_type}
**目标受众**：{target_audience}  
**内容深度**：{depth_level}
**核心价值**：{core_value}

### 解读风格要求

{interpretation_style}

### 章节设计指导

{chapter_design_hints}

### 行文语气

{tone_guidance}

---
**重要**：请将以上解读策略融入你的大纲设计中，确保章节结构、标题风格、内容侧重都与目标受众和内容特性相匹配。
"""


# 将Pre分析结果注入到章节生成的指令模板
PRE_ANALYSIS_INJECTION_FOR_CHAPTER = """
## 内容解读策略（基于Pre分析）

**内容类型**：{content_type}
**目标受众**：{target_audience}
**深度级别**：{depth_level}

### 本章写作风格要求

{interpretation_style}

### 行文语气

{tone_guidance}

---
**重要**：请在撰写本章节时贯彻以上解读策略，确保风格统一、受众明确。
"""


def format_pre_analysis_for_outline(result: PreAnalysisResult) -> str:
    """将Pre分析结果格式化为大纲生成的注入指令
    
    Args:
        result: Pre分析结果
        
    Returns:
        格式化后的指令字符串
    """
    return PRE_ANALYSIS_INJECTION_FOR_OUTLINE.format(
        content_type=result.content_type,
        target_audience=result.target_audience,
        depth_level=result.depth_level,
        core_value=result.core_value,
        interpretation_style=result.interpretation_style,
        chapter_design_hints=result.chapter_design_hints,
        tone_guidance=result.tone_guidance
    )


def format_pre_analysis_for_chapter(result: PreAnalysisResult) -> str:
    """将Pre分析结果格式化为章节生成的注入指令
    
    Args:
        result: Pre分析结果
        
    Returns:
        格式化后的指令字符串
    """
    return PRE_ANALYSIS_INJECTION_FOR_CHAPTER.format(
        content_type=result.content_type,
        target_audience=result.target_audience,
        depth_level=result.depth_level,
        interpretation_style=result.interpretation_style,
        tone_guidance=result.tone_guidance
    )


def parse_pre_analysis_response(response: str) -> Optional[PreAnalysisResult]:
    """解析AI返回的Pre分析结果
    
    Args:
        response: AI返回的原始响应
        
    Returns:
        解析后的PreAnalysisResult，解析失败返回None
    """
    import json
    import re
    
    try:
        # 尝试提取JSON块
        json_match = re.search(r'```json\s*([\s\S]*?)```', response)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # 尝试直接匹配JSON对象
            json_match = re.search(r'\{[\s\S]*"content_type"[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                return None
        
        data = json.loads(json_str)
        
        return PreAnalysisResult(
            content_type=data.get('content_type', '未识别'),
            content_style=data.get('content_style', '综合型'),
            target_audience=data.get('target_audience', '通用读者'),
            depth_level=data.get('depth_level', '进阶理解'),
            core_value=data.get('core_value', ''),
            interpretation_style=data.get('interpretation_style', ''),
            chapter_design_hints=data.get('chapter_design_hints', ''),
            tone_guidance=data.get('tone_guidance', ''),
            raw_analysis=response
        )
    except (json.JSONDecodeError, KeyError) as e:
        # 解析失败，返回一个带有原始响应的默认结果
        return PreAnalysisResult(
            content_type='未识别',
            content_style='综合型',
            target_audience='通用读者',
            depth_level='进阶理解',
            core_value='',
            interpretation_style='',
            chapter_design_hints='',
            tone_guidance='',
            raw_analysis=response
        )
