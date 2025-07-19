"""
动态提示词生成器模块

该模块实现了基于长度目标的动态提示词生成功能，包括：
- 基础提示词模板系统
- 大纲生成提示词的动态调整
- 章节生成提示词的长度指导
- 结论生成提示词的深度调整
- 详细程度映射逻辑（简洁/适度/深度）
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from .adaptive_length import LengthTarget


@dataclass
class DetailLevel:
    """详细程度配置"""
    name: str  # 简洁/适度/深度
    description: str  # 描述
    chapter_instruction: str  # 章节指导
    outline_instruction: str  # 大纲指导
    conclusion_instruction: str  # 结论指导


class DynamicPromptGenerator:
    """动态提示词生成器，根据长度目标调整提示词内容"""
    
    def __init__(self, base_prompt: str, length_target: LengthTarget):
        """
        初始化动态提示词生成器
        
        Args:
            base_prompt: 基础提示词模板
            length_target: 长度目标配置
        """
        self.base_prompt = base_prompt
        self.length_target = length_target
        self.detail_level = self._determine_detail_level()
        
        logger.info(f"动态提示词生成器初始化完成: 目标长度={length_target.target_length}字, "
                   f"详细程度={self.detail_level.name}")
    
    def generate_outline_prompt(self, transcript: str) -> str:
        """
        生成大纲提示词
        
        Args:
            transcript: 视频字幕文本
            
        Returns:
            str: 调整后的大纲生成提示词
        """
        # 获取长度指导说明
        length_instruction = self._get_outline_length_instruction()
        
        # 获取章节数量指导
        chapter_instruction = self._get_chapter_count_instruction()
        
        # 获取详细程度指导
        detail_instruction = self.detail_level.outline_instruction
        
        # 构建动态提示词
        dynamic_prompt = f"""
{self.base_prompt}

## 长度与结构指导
{length_instruction}
{chapter_instruction}
{detail_instruction}

## 输入素材
- 完整英文字幕: 
{transcript}

---
## **【核心指令】**
你的**唯一任务**是根据上方提供的完整字幕，生成这份深度笔记的 **标题**、**引言** 和 **大纲索引 (TOC)**。

## 输出要求
1.  **标题**：直接输出标题正文，不要出现"标题"字眼。标题应高度概括视频核心内容。
2.  **引言**：概述视频的背景、主讲人、核心主题与价值。引言需要能够激发读者的阅读兴趣，并准确反映报告的整体内容。
3.  **大纲索引**：用 TOC 列出 {self.length_target.chapter_count} 个主要章节，确保每个章节标题都言之有物，能反映该部分的核心议题。
4.  **格式**：请严格按照以下 Markdown 格式输出，不要添加任何额外的解释、引言或章节内容，TOC中不要出现特殊字符导致TOC跳转可能失效的字符 (强制)。
5.  **纯文本要求**：每个章节标题都必须是纯文本，**严禁**包含任何 Markdown 链接格式或方括号 `[]()【】「」`。

## 输出格式示例
# [这里是生成的标题]

### 引言
[这里是引言内容]

### 主要目录
1. [第一章标题]
2. [第二章标题]
3. [第三章标题]
... (直到所有章节)

---
**请严格遵守上述指令，只输出标题、引言和大纲索引。**
"""
        
        logger.debug(f"大纲提示词生成完成，目标章节数: {self.length_target.chapter_count}")
        return dynamic_prompt
    
    def generate_chapter_prompt(self, chapter_index: int, chapter_title: str, 
                              outline: str, transcript: str) -> str:
        """
        生成章节提示词
        
        Args:
            chapter_index: 章节索引（从1开始）
            chapter_title: 章节标题
            outline: 完整大纲
            transcript: 视频字幕文本
            
        Returns:
            str: 调整后的章节生成提示词
        """
        # 计算当前章节的目标长度
        chapter_length_target = self._calculate_chapter_length_target(chapter_index)
        
        # 获取长度指导说明
        length_instruction = self._get_chapter_length_instruction(chapter_length_target)
        
        # 获取详细程度指导
        detail_instruction = self.detail_level.chapter_instruction
        
        # 构建动态提示词
        dynamic_prompt = f"""
{self.base_prompt}

## 长度与质量指导
{length_instruction}
{detail_instruction}

## 全局上下文
- **完整字幕**: {transcript}
- **完整大纲**: 
{outline}

---
## **【核心指令】**
你的任务是为上述 **完整大纲** 中的**特定一章**撰写详细内容。

- **当前需要你撰写的章节是**：第 `{chapter_index}` 章 - `{chapter_title}`

请基于**完整字幕**提供的上下文，并理解当前章节在**完整大纲**中的位置，为其撰写深入、详尽的内容。

## 风格与一致性要求
- **风格统一**: 你的写作风格、专业口吻和分析深度，必须与报告的其他部分保持高度一致。请把自己想象成正在撰写一部完整作品，而不是孤立的片段。
- **参考上下文**: 在动笔前，请再次审视上方提供的**完整大纲**，这有助于你理解当前章节的承上启下的作用。
- **术语一致**: 确保本章使用的所有专业术语，都与**完整字幕**和**基础提示词**中定义的标准保持一致。

## 章节内容结构要求
请严格遵循以下结构来组织内容，但不要机械地使用"章节摘要"、"关键论点"等字眼作为标题，应根据具体内容灵活命名：

1.  **章节摘要**：对该章节的核心内容进行全面、详细的概括。
2.  **关键论点/数据/案例**：精确引用视频中与本章相关的关键论点、数据和实例。
3.  **深入解读**：分析这部分内容为什么重要，它与现有认知有何不同，或带来了哪些补充。

## 输出要求
- **只输出** 你当前负责的第 `{chapter_index}` 章 **'{chapter_title}'** 的完整内容。
- **格式至关重要**：输出必须以 `### {chapter_index}. {chapter_title}` (Markdown H3 标题) 开头。这是确保最终报告结构正确的关键。
- 不需要包含引言、总结、其他章节或任何无关的文字。
在生成 Markdown 内容时，严格遵守以下加粗样式规则：
1. 加粗语法（`**...**`）中只允许纯中文字符（无标点）或纯英文字符（字母、数字）。
2. 禁止在加粗内容中包含任何引号（中文 `""`、英文 `""`）、括号（中文 `（）`、英文 `()`）或任何其他标点。
3. 如果原始内容包含引号或括号，将其移到加粗范围外，或重写句子以移除这些字符。
4. 确保加粗内容简洁，避免复杂结构，降低解析失败风险。
5. 示例：
   - 正确：`**控制平面**`、`**专家提示**`、`**LoadBalancingRouter**`
   - 错误：`**"控制平面"**`、`**控制平面（Control Plane）**`、`**"VPC路由"**`
6. 输出内容需兼容 CommonMark 规范，确保在 markdown-it 等渲染器中正确渲染为 `<strong>`。
---
**请开始撰写第 `{chapter_index}` 章 - `{chapter_title}` 的内容。**
"""
        
        logger.debug(f"章节提示词生成完成，章节{chapter_index}目标长度: {chapter_length_target}字")
        return dynamic_prompt
    
    def generate_conclusion_prompt(self, transcript: str, all_chapters: str) -> str:
        """
        生成结论提示词
        
        Args:
            transcript: 视频字幕文本
            all_chapters: 所有已生成的章节内容
            
        Returns:
            str: 调整后的结论生成提示词
        """
        # 获取结论深度指导
        depth_instruction = self._get_conclusion_depth_instruction()
        
        # 获取详细程度指导
        detail_instruction = self.detail_level.conclusion_instruction
        
        # 构建动态提示词
        dynamic_prompt = f"""
{self.base_prompt}

## 深度与质量指导
{depth_instruction}
{detail_instruction}

## 全局上下文
- **完整字幕**: {transcript}
- **已生成的全部正文内容**: 
{all_chapters}

---
## **【核心指令】**
你已经完成了报告所有正文章节的撰写。现在，你的任务是基于 **完整字幕** 和 **已生成的全部正文内容**，为整份报告撰写收尾部分。

## 具体任务
请生成以下两个部分：

1.  **洞见延伸**：结合行业趋势或学术前沿，给出不多于 10 条具有可操作性的启示。
2.  **金句&原声引用**：从字幕中挑选不多于 10 条有代表性的英文原句，并附上精准的中文翻译。

## 输出要求
- 输出"洞见延伸"、"金句&原声引用",要结合已生成的全部正文内容中所提到的内容，不要输出一个原字幕中有的但是再正文内容中没有提到的内容。
- 请严格按照"洞见延伸"、"金句&原声引用"的顺序和对应 Markdown 格式输出。
- 不要输出标题、大纲或任何正文内容。

在生成 Markdown 内容时，严格遵守以下加粗样式规则：
1. 加粗语法（`**...**`）中只允许纯中文字符（无标点）或纯英文字符（字母、数字）。
2. 禁止在加粗内容中包含任何引号（中文 `""`、英文 `""`）、括号（中文 `（）`、英文 `()`）或任何其他标点。
3. 如果原始内容包含引号或括号，将其移到加粗范围外，或重写句子以移除这些字符。
4. 确保加粗内容简洁，避免复杂结构，降低解析失败风险。
5. 示例：
   - 正确：`**控制平面**`、`**专家提示**`、`**LoadBalancingRouter**`
   - 错误：`**"控制平面"**`、`**控制平面（Control Plane）**`、`**"VPC路由"**`
6. 输出内容需兼容 CommonMark 规范，确保在 markdown-it 等渲染器中正确渲染为 `<strong>`。
---
**请开始生成洞见延伸和金句。**
"""
        
        logger.debug("结论提示词生成完成")
        return dynamic_prompt
    
    def _determine_detail_level(self) -> DetailLevel:
        """
        根据目标长度确定详细程度
        
        Returns:
            DetailLevel: 详细程度配置
        """
        target_length = self.length_target.target_length
        
        if target_length < 15000:
            return DetailLevel(
                name="简洁",
                description="重点突出核心观点，保持内容精炼",
                chapter_instruction="""
## 内容详细程度：简洁精炼
- **核心要求**：重点突出核心观点，避免冗余描述
- **章节结构**：每个部分都要言简意赅，直击要点
- **论证深度**：提供关键论证，但避免过度展开
- **案例使用**：选择最具代表性的案例，简洁说明
""",
                outline_instruction="""
## 大纲结构指导：简洁版
- **章节设计**：每个章节都应该聚焦一个核心主题，避免内容分散
- **标题要求**：章节标题要精准概括核心内容，便于快速理解
- **逻辑关系**：章节间要有清晰的逻辑递进关系
- **段落长度控制**：每个段落控制在100-150字之间，确保内容紧凑
""",
                conclusion_instruction="""
## 结论深度：精选要点
- **洞见延伸**：选择5-7条最具实用价值的启示，每条150-200字
- **金句选择**：挑选5-7条最具代表性和冲击力的原声引用
- **质量优先**：宁缺毋滥，确保每条内容都有独特价值
"""
            )
        elif target_length < 30000:
            return DetailLevel(
                name="适度",
                description="平衡深度与可读性，包含关键论证和案例",
                chapter_instruction="""
## 内容详细程度：适度详细
- **核心要求**：在保持可读性的前提下，提供充分的论证和分析
- **章节结构**：每个部分都要有完整的论证链条，包含必要的背景和案例
- **论证深度**：提供关键论证和支撑数据，适度展开分析
- **案例使用**：结合多个相关案例，增强说服力
""",
                outline_instruction="""
## 大纲结构指导：标准版
- **章节设计**：每个章节既要有独立价值，又要与整体形成有机联系
- **标题要求**：章节标题要准确反映内容深度和广度
- **逻辑关系**：章节间要有清晰的逻辑递进和相互呼应
- **段落长度控制**：每个段落控制在100-150字之间，确保内容紧凑
""",
                conclusion_instruction="""
## 结论深度：全面总结
- **洞见延伸**：提供8-10条具有可操作性的启示，每条180-250字
- **金句选择**：挑选8-10条有代表性的原声引用，涵盖不同维度
- **深度平衡**：既要有理论高度，又要有实践指导价值
"""
            )
        else:
            return DetailLevel(
                name="深度",
                description="全面展开论述和分析，提供深度洞察",
                chapter_instruction="""
## 内容详细程度：深度详细
- **核心要求**：全面展开论述，提供深度分析和多维度思考
- **章节结构**：每个部分都要有完整的理论框架和详细的实证分析
- **论证深度**：提供全面的论证链条，包含背景、现状、趋势和影响
- **案例使用**：结合多个层次的案例，从不同角度验证观点
- **延伸思考**：在核心内容基础上，提供相关的延伸思考和关联分析
""",
                outline_instruction="""
## 大纲结构指导：深度版
- **章节设计**：每个章节都要有丰富的内容层次，形成完整的知识体系
- **标题要求**：章节标题要体现内容的深度和复杂性
- **逻辑关系**：章节间要有复杂的逻辑关系，包含递进、并列、对比等多种关系
- **段落长度控制**：每个段落控制在100-150字之间，确保内容紧凑
""",
                conclusion_instruction="""
## 结论深度：深度洞察
- **洞见延伸**：提供10条具有前瞻性和深度的启示，每条250-300字
- **金句选择**：挑选10条最具思想深度和启发价值的原声引用
- **思想高度**：既要有理论深度，又要有实践指导，还要有未来展望
"""
            )
    
    def _get_outline_length_instruction(self) -> str:
        """获取大纲长度指导说明"""
        return f"""
### 目标文章规格
- **总体目标长度**：{self.length_target.target_length:,} 字（范围：{self.length_target.min_length:,}-{self.length_target.max_length:,} 字）
- **章节数量**：{self.length_target.chapter_count} 个章节
- **平均章节长度**：约 {self.length_target.avg_chapter_length:,} 字/章节
- **详细程度**：{self.detail_level.name}（{self.detail_level.description}）
"""
    
    def _get_chapter_count_instruction(self) -> str:
        """获取章节数量指导说明"""
        return f"""
### 章节规划要求
- **精确章节数**：必须生成 {self.length_target.chapter_count} 个章节，不多不少
- **内容分布**：确保每个章节都有足够的内容支撑，避免内容过于分散或集中
- **逻辑完整**：{self.length_target.chapter_count} 个章节要形成完整的逻辑链条，覆盖视频的所有核心内容
"""
    
    def _calculate_chapter_length_target(self, chapter_index: int) -> int:
        """
        计算特定章节的目标长度
        
        Args:
            chapter_index: 章节索引（从1开始）
            
        Returns:
            int: 该章节的目标长度
        """
        # 基础长度
        base_length = self.length_target.avg_chapter_length
        
        # 根据章节位置进行微调
        if chapter_index == 1:
            # 第一章通常需要更多背景介绍
            return int(base_length * 1.1)
        elif chapter_index == self.length_target.chapter_count:
            # 最后一章可能需要更多总结
            return int(base_length * 1.05)
        else:
            # 中间章节保持标准长度
            return base_length
    
    def _get_chapter_length_instruction(self, chapter_length_target: int) -> str:
        """获取章节长度指导说明"""
        min_length = int(chapter_length_target * 0.8)
        max_length = int(chapter_length_target * 1.2)
        
        return f"""
### 当前章节长度目标
- **目标长度**：{chapter_length_target:,} 字
- **允许范围**：{min_length:,} - {max_length:,} 字
- **段落长度控制**：每个段落控制在100-150字之间，避免生成过长的段落
- **段落结构要求**：每个段落包含3-5个句子，确保内容紧凑且易读
- **质量要求**：在满足长度要求的同时，确保内容质量和逻辑完整性
- **结构完整**：必须包含章节摘要、关键论点/案例、深入解读三个完整部分
"""
    
    def _get_conclusion_depth_instruction(self) -> str:
        """获取结论深度指导说明"""
        if self.detail_level.name == "简洁":
            insight_count = "5-7"
            quote_count = "5-7"
        elif self.detail_level.name == "适度":
            insight_count = "8-10"
            quote_count = "8-10"
        else:
            insight_count = "10"
            quote_count = "10"
        
        return f"""
### 结论部分规格要求
- **洞见延伸数量**：{insight_count} 条
- **金句引用数量**：{quote_count} 条
- **内容深度**：{self.detail_level.name}级别（{self.detail_level.description}）
- **总体长度**：结论部分应占全文的 8-12%
"""


def load_base_prompt_template(template_path: str = "prompt/youtbe-deep-summary.txt") -> str:
    """
    加载基础提示词模板
    
    Args:
        template_path: 模板文件路径
        
    Returns:
        str: 基础提示词内容
    """
    try:
        template_file = Path(template_path)
        if template_file.exists():
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"成功加载基础提示词模板: {template_path}")
                return content
        else:
            logger.warning(f"提示词模板文件不存在: {template_path}")
            return ""
    except Exception as e:
        logger.error(f"加载提示词模板失败: {e}")
        return ""


def create_dynamic_prompt_generator(length_target: LengthTarget, 
                                  template_path: str = "prompt/youtbe-deep-summary.txt") -> DynamicPromptGenerator:
    """
    创建动态提示词生成器的便捷函数
    
    Args:
        length_target: 长度目标配置
        template_path: 基础模板路径
        
    Returns:
        DynamicPromptGenerator: 动态提示词生成器实例
    """
    base_prompt = load_base_prompt_template(template_path)
    return DynamicPromptGenerator(base_prompt, length_target)