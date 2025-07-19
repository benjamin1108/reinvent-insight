# -*- coding: utf-8 -*-

from typing import Dict, Any
from pathlib import Path
from loguru import logger

# 基础角色和通用指令，将从 youtbe-deep-summary.txt 加载
BASE_PROMPT_TEMPLATE = ""
# 步骤一：生成大纲和标题的提示词模板
OUTLINE_PROMPT_TEMPLATE = """
{base_prompt}

## 输入素材
- 完整英文字幕: 
{full_transcript}

---
## **【核心指令】**
你的**唯一任务**是根据上方提供的完整字幕，生成这份深度笔记的 **标题**、**引言** 和 **大纲索引 (TOC)**。

## 输出要求
1.  **标题**：直接输出标题正文，不要出现"标题"字眼。标题应高度概括视频核心内容。
2.  **引言**：概述视频的背景、主讲人、核心主题与价值。引言需要能够激发读者的阅读兴趣，并准确反映报告的整体内容。
3.  **大纲索引**：用 TOC 列出 10-20 个主要章节，确保每个章节标题都言之有物，能反映该部分的核心议题。
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

# 步骤二：生成单个章节内容的提示词模板
CHAPTER_PROMPT_TEMPLATE = """
{base_prompt}

## 全局上下文
- **完整字幕**: {full_transcript}
- **完整大纲**: 
{full_outline}

---
## **【核心指令】**
你的任务是为上述 **完整大纲** 中的**特定一章**撰写详细内容。

- **当前需要你撰写的章节是**：第 `{chapter_number}` 章 - `{current_chapter_title}`

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
- **只输出** 你当前负责的第 `{chapter_number}` 章 **'{current_chapter_title}'** 的完整内容。
- **格式至关重要**：输出必须以 `### {chapter_number}. {current_chapter_title}` (Markdown H3 标题) 开头。这是确保最终报告结构正确的关键。
- 不需要包含引言、总结、其他章节或任何无关的文字。
在生成 Markdown 内容时，严格遵守以下加粗样式规则：
1. 加粗语法（`**...**`）中只允许纯中文字符（无标点）或纯英文字符（字母、数字）。
2. 禁止在加粗内容中包含任何引号（中文 `“”`、英文 `""`）、括号（中文 `（）`、英文 `()`）或任何其他标点。
3. 如果原始内容包含引号或括号，将其移到加粗范围外，或重写句子以移除这些字符。
4. 确保加粗内容简洁，避免复杂结构，降低解析失败风险。
5. 示例：
   - 正确：`**控制平面**`、`**专家提示**`、`**LoadBalancingRouter**`
   - 错误：`**“控制平面”**`、`**控制平面（Control Plane）**`、`**“VPC路由”**`
6. 输出内容需兼容 CommonMark 规范，确保在 markdown-it 等渲染器中正确渲染为 `<strong>`。
---
**请开始撰写第 `{chapter_number}` 章 - `{current_chapter_title}` 的内容。**
"""

# 步骤三：生成引言、洞见与金句的提示词模板
CONCLUSION_PROMPT_TEMPLATE = """
{base_prompt}

## 全局上下文
- **完整字幕**: {full_transcript}
- **已生成的全部正文内容**: 
{all_generated_chapters}

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
2. 禁止在加粗内容中包含任何引号（中文 `“”`、英文 `""`）、括号（中文 `（）`、英文 `()`）或任何其他标点。
3. 如果原始内容包含引号或括号，将其移到加粗范围外，或重写句子以移除这些字符。
4. 确保加粗内容简洁，避免复杂结构，降低解析失败风险。
5. 示例：
   - 正确：`**控制平面**`、`**专家提示**`、`**LoadBalancingRouter**`
   - 错误：`**“控制平面”**`、`**控制平面（Control Plane）**`、`**“VPC路由”**`
6. 输出内容需兼容 CommonMark 规范，确保在 markdown-it 等渲染器中正确渲染为 `<strong>`。
---
**请开始生成洞见延伸和金句。**
"""


class PromptTemplateManager:
    """提示词模板管理器，支持参数化替换"""
    
    def __init__(self, template_path: str = "prompt/youtbe-deep-summary-adaptive.txt"):
        """
        初始化模板管理器
        
        Args:
            template_path: 自适应模板文件路径
        """
        self.template_path = Path(template_path)
        self.base_template = self._load_template()
    
    def _load_template(self) -> str:
        """加载基础模板"""
        try:
            if self.template_path.exists():
                with open(self.template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"成功加载自适应提示词模板: {self.template_path}")
                    return content
            else:
                logger.warning(f"自适应模板文件不存在: {self.template_path}，使用默认模板")
                # 回退到原始模板
                fallback_path = Path("prompt/youtbe-deep-summary.txt")
                if fallback_path.exists():
                    with open(fallback_path, 'r', encoding='utf-8') as f:
                        return f.read()
                return ""
        except Exception as e:
            logger.error(f"加载提示词模板失败: {e}")
            return ""
    
    def create_parameterized_prompt(self, length_params: Dict[str, Any]) -> str:
        """
        创建参数化的基础提示词
        
        Args:
            length_params: 长度相关参数字典
            
        Returns:
            str: 参数化后的基础提示词
        """
        if not self.base_template:
            logger.warning("基础模板为空，返回空字符串")
            return ""
        
        try:
            # 使用字符串格式化替换参数
            parameterized_prompt = self.base_template.format(**length_params)
            logger.debug("提示词参数化替换完成")
            return parameterized_prompt
        except KeyError as e:
            logger.error(f"提示词参数化失败，缺少参数: {e}")
            return self.base_template
        except Exception as e:
            logger.error(f"提示词参数化过程中发生错误: {e}")
            return self.base_template


def create_length_parameters(target_length: int, min_length: int, max_length: int,
                           chapter_count: int, avg_chapter_length: int,
                           detail_level: str, detail_description: str) -> Dict[str, Any]:
    """
    创建长度相关参数字典
    
    Args:
        target_length: 目标长度
        min_length: 最小长度
        max_length: 最大长度
        chapter_count: 章节数量
        avg_chapter_length: 平均章节长度
        detail_level: 详细程度级别
        detail_description: 详细程度描述
        
    Returns:
        Dict[str, Any]: 参数字典
    """
    # 根据详细程度确定各种指导语句
    content_density_instruction = _get_content_density_instruction(detail_level)
    chapter_length_instruction = _get_chapter_length_instruction(avg_chapter_length, detail_level)
    content_depth_instruction = _get_content_depth_instruction(detail_level)
    length_control_instruction = _get_length_control_instruction(target_length, detail_level)
    
    # 根据详细程度确定洞见和金句数量
    insight_count, quote_count, insight_length = _get_conclusion_params(detail_level)
    
    return {
        'TARGET_LENGTH': f"{target_length:,}",
        'MIN_LENGTH': f"{min_length:,}",
        'MAX_LENGTH': f"{max_length:,}",
        'CHAPTER_COUNT': str(chapter_count),
        'AVG_CHAPTER_LENGTH': f"{avg_chapter_length:,}",
        'DETAIL_LEVEL': detail_level,
        'DETAIL_DESCRIPTION': detail_description,
        'CONTENT_DENSITY_INSTRUCTION': content_density_instruction,
        'CHAPTER_LENGTH_INSTRUCTION': chapter_length_instruction,
        'CONTENT_DEPTH_INSTRUCTION': content_depth_instruction,
        'LENGTH_CONTROL_INSTRUCTION': length_control_instruction,
        'INSIGHT_COUNT': insight_count,
        'QUOTE_COUNT': quote_count,
        'INSIGHT_LENGTH': insight_length
    }


def _get_content_density_instruction(detail_level: str) -> str:
    """获取内容密度指导"""
    if detail_level == "简洁":
        return "重点突出核心观点，避免冗余描述，每个要点都要言简意赅"
    elif detail_level == "适度":
        return "在保持可读性的前提下，提供充分的论证和分析，平衡深度与广度"
    else:  # 深度
        return "全面展开论述，提供深度分析和多维度思考，包含完整的理论框架"


def _get_chapter_length_instruction(avg_chapter_length: int, detail_level: str) -> str:
    """获取章节长度指导"""
    min_chapter = int(avg_chapter_length * 0.8)
    max_chapter = int(avg_chapter_length * 1.2)
    
    base_instruction = f"每章节目标长度约 {avg_chapter_length:,} 字（范围：{min_chapter:,}-{max_chapter:,} 字）"
    
    if detail_level == "简洁":
        return f"{base_instruction}，重点保证内容质量，避免为了凑字数而添加无关内容"
    elif detail_level == "适度":
        return f"{base_instruction}，确保每个章节都有完整的论证链条和必要的案例支撑"
    else:  # 深度
        return f"{base_instruction}，每章节需要有丰富的内容层次，包含详细的分析和延伸思考"


def _get_content_depth_instruction(detail_level: str) -> str:
    """获取内容深度指导"""
    if detail_level == "简洁":
        return "保持内容精炼，直击要点，避免过度展开，但要确保逻辑完整"
    elif detail_level == "适度":
        return "在深度和可读性之间找到平衡，提供必要的背景和分析，但避免过于冗长"
    else:  # 深度
        return "追求内容的深度和广度，提供全面的分析框架，包含多层次的思考和洞察"


def _get_length_control_instruction(target_length: int, detail_level: str) -> str:
    """获取长度控制指导"""
    base_instruction = f"严格控制总体长度在 {target_length:,} 字左右"
    
    if detail_level == "简洁":
        return f"{base_instruction}，宁可内容精炼也不要为了凑字数而降低质量"
    elif detail_level == "适度":
        return f"{base_instruction}，在满足长度要求的同时确保内容的完整性和逻辑性"
    else:  # 深度
        return f"{base_instruction}，充分利用篇幅空间，提供深度分析和全面论述"


def _get_conclusion_params(detail_level: str) -> tuple[str, str, str]:
    """获取结论部分参数"""
    if detail_level == "简洁":
        return "5-7", "5-7", "150-200"
    elif detail_level == "适度":
        return "8-10", "8-10", "180-250"
    else:  # 深度
        return "10", "10", "250-300"


def create_adaptive_outline_prompt(base_prompt: str, transcript: str, 
                                 length_params: Dict[str, Any]) -> str:
    """
    创建自适应的大纲生成提示词
    
    Args:
        base_prompt: 参数化后的基础提示词
        transcript: 视频字幕
        length_params: 长度参数
        
    Returns:
        str: 自适应大纲提示词
    """
    return f"""
{base_prompt}

## 输入素材
- 完整英文字幕: 
{transcript}

---
## **【核心指令】**
你的**唯一任务**是根据上方提供的完整字幕，生成这份深度笔记的 **标题**、**引言** 和 **大纲索引 (TOC)**。

## 输出要求
1.  **标题**：直接输出标题正文，不要出现"标题"字眼。标题应高度概括视频核心内容。
2.  **引言**：概述视频的背景、主讲人、核心主题与价值。引言需要能够激发读者的阅读兴趣，并准确反映报告的整体内容。
3.  **大纲索引**：用 TOC 列出 {length_params['CHAPTER_COUNT']} 个主要章节，确保每个章节标题都言之有物，能反映该部分的核心议题。
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
... (直到所有 {length_params['CHAPTER_COUNT']} 个章节)

---
**请严格遵守上述指令，只输出标题、引言和大纲索引。**
"""


def create_adaptive_chapter_prompt(base_prompt: str, chapter_index: int, 
                                 chapter_title: str, outline: str, 
                                 transcript: str, length_params: Dict[str, Any]) -> str:
    """
    创建自适应的章节生成提示词
    
    Args:
        base_prompt: 参数化后的基础提示词
        chapter_index: 章节索引
        chapter_title: 章节标题
        outline: 完整大纲
        transcript: 视频字幕
        length_params: 长度参数
        
    Returns:
        str: 自适应章节提示词
    """
    avg_length = int(length_params['AVG_CHAPTER_LENGTH'].replace(',', ''))
    min_length = int(avg_length * 0.8)
    max_length = int(avg_length * 1.2)
    
    return f"""
{base_prompt}

## 当前章节长度要求
- **目标长度**：约 {avg_length:,} 字
- **允许范围**：{min_length:,} - {max_length:,} 字
- **质量要求**：{length_params['CONTENT_DENSITY_INSTRUCTION']}

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


def create_adaptive_conclusion_prompt(base_prompt: str, transcript: str, 
                                    all_chapters: str, length_params: Dict[str, Any]) -> str:
    """
    创建自适应的结论生成提示词
    
    Args:
        base_prompt: 参数化后的基础提示词
        transcript: 视频字幕
        all_chapters: 所有章节内容
        length_params: 长度参数
        
    Returns:
        str: 自适应结论提示词
    """
    return f"""
{base_prompt}

## 结论部分要求
- **洞见延伸数量**：{length_params['INSIGHT_COUNT']} 条
- **金句引用数量**：{length_params['QUOTE_COUNT']} 条
- **每条洞见长度**：{length_params['INSIGHT_LENGTH']} 字
- **深度要求**：{length_params['CONTENT_DEPTH_INSTRUCTION']}

## 全局上下文
- **完整字幕**: {transcript}
- **已生成的全部正文内容**: 
{all_chapters}

---
## **【核心指令】**
你已经完成了报告所有正文章节的撰写。现在，你的任务是基于 **完整字幕** 和 **已生成的全部正文内容**，为整份报告撰写收尾部分。

## 具体任务
请生成以下两个部分：

1.  **洞见延伸**：结合行业趋势或学术前沿，给出 {length_params['INSIGHT_COUNT']} 条具有可操作性的启示。
2.  **金句&原声引用**：从字幕中挑选 {length_params['QUOTE_COUNT']} 条有代表性的英文原句，并附上精准的中文翻译。

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