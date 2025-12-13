# -*- coding: utf-8 -*-
"""
字幕翻译提示词模板

用于将英文字幕翻译为中文，支持：
- 机器生成字幕的纠错
- 基于文章上下文的全局理解
- 分段翻译
"""

# 字幕翻译主提示词（带文章上下文）
SUBTITLE_TRANSLATION_PROMPT_WITH_CONTEXT = """你是一个专业的视频字幕翻译专家。请将以下{source_language}字幕翻译为{target_language}。

## 文章背景（上下文）
{article_content}

## 核心原则（必须严格遵守）
**"声画同步"优于"句子完整"**。观众必须在听到声音的同时看到对应的文字，绝对**禁止**显示尚未播放的内容。

## 翻译与时间轴规则
1. **严格的一一对应（禁止随意合并）**：
   - 原则上，**请保持原始的时间轴切分**，逐行翻译。
   - **例外**：只有当一行字幕**少于 1 秒**且**字数极少**（如 "and", "the"）时，才允许将其合并到下一行。
   - **严禁**将超过 3 行的字幕合并为一行。

2. **处理语序差异（抗抢跑机制）**：
   - 英文常将修饰语放在句尾（如从句），而中文习惯放在句首。
   - **关键操作**：如果英文原句很长且跨越多行，**不要**为了中文语法的完美而把后几行的意思提前移到第一行。
   - **处理方法**：请将长句拆分为多个短句，或者使用“倒装”、“补充说明”的中文句式，确保文字出现的时间与声音对应。
   - *错误示例*：(00:01) I suggest (00:04) the plan we made -> (00:01) 我建议我们制定的计划 (错！"计划"在00:04才说)
   - *正确示例*：(00:01) 我建议 (00:04) 采用我们制定的计划

3. **时间轴完整性**：
   - 每一行输出的字幕，必须严格沿用输入字幕的【开始时间】和【结束时间】（或者合并后的首尾时间）。
   - 禁止凭空创造时间戳。

4. **表达要求**：
   - 语言简洁、口语化。
   - 字幕服务于听觉，不需要像书面文章那样结构严密，**允许**句子在中间断开。

## 输出格式
每行一条字幕，格式为：
开始时间 --> 结束时间
翻译内容

## 待翻译字幕
{subtitle_text}

请严格基于上述“声画同步”原则开始翻译："""

# 字幕翻译提示词（无文章上下文时的回退）
SUBTITLE_TRANSLATION_PROMPT_FALLBACK = """你是一个专业的视频字幕翻译专家。请将以下{source_language}字幕翻译为{target_language}。

## 核心原则（必须严格遵守）
**"声画同步"优于"句子完整"**。观众必须在听到声音的同时看到对应的文字，绝对**禁止**显示尚未播放的内容。

## 翻译与时间轴规则
1. **严格的一一对应（禁止随意合并）**：
   - 原则上，**请保持原始的时间轴切分**，逐行翻译。
   - **例外**：只有当一行字幕**少于 1 秒**且**字数极少**（如 "and", "the"）时，才允许将其合并到下一行。
   - **严禁**将超过 3 行的字幕合并为一行。

2. **处理语序差异（抗抢跑机制）**：
   - 英文常将修饰语放在句尾（如从句），而中文习惯放在句首。
   - **关键操作**：如果英文原句很长且跨越多行，**不要**为了中文语法的完美而把后几行的意思提前移到第一行。
   - **处理方法**：请将长句拆分为多个短句，或者使用“倒装”、“补充说明”的中文句式，确保文字出现的时间与声音对应。
   - *错误示例*：(00:01) I suggest (00:04) the plan we made -> (00:01) 我建议我们制定的计划 (错！"计划"在00:04才说)
   - *正确示例*：(00:01) 我建议 (00:04) 采用我们制定的计划

3. **时间轴完整性**：
   - 每一行输出的字幕，必须严格沿用输入字幕的【开始时间】和【结束时间】（或者合并后的首尾时间）。
   - 禁止凭空创造时间戳。

4. **表达要求**：
   - 语言简洁、口语化。
   - 字幕服务于听觉，不需要像书面文章那样结构严密，**允许**句子在中间断开。

## 输出格式
每行一条字幕，格式为：
开始时间 --> 结束时间
翻译内容

## 待翻译字幕
{subtitle_text}

请严格基于上述“声画同步”原则开始翻译："""

# 分片修正提示词模板
CHUNK_CORRECTION_PROMPT = """你之前翻译的字幕存在以下问题，请修正。

## 问题诊断报告
{diagnosis_report}

## 修正规则（必须严格遵守）
1. **只修改有问题的部分**，保留翻译正确的内容
2. **时间戳必须精确复制原始字幕**，禁止创造、修改、四舍五入任何时间戳
3. **每条输出字幕的起始时间必须在原始输入中存在**
4. **覆盖完整时间范围**，不能有时间空洞
5. 如果原始字幕间隔 > 3秒，必须保持分离，不能合并
6. **单条字幕时长不得超过10秒**，超过必须拆分

## 原始字幕（权威来源，时间戳以此为准）
{original_subtitle}

## 你之前的翻译（参考，修正有问题的部分）
{previous_translation}

请输出修正后的完整翻译，格式要求：
开始时间 --> 结束时间
翻译内容

（空行分隔每条字幕）
"""


def build_correction_prompt(
    diagnosis_report: str,
    original_subtitle: str,
    previous_translation: str
) -> str:
    """
    构建分片修正提示词
    
    Args:
        diagnosis_report: 问题诊断报告
        original_subtitle: 原始字幕文本
        previous_translation: 之前的翻译结果
        
    Returns:
        格式化后的修正提示词
    """
    return CHUNK_CORRECTION_PROMPT.format(
        diagnosis_report=diagnosis_report,
        original_subtitle=original_subtitle,
        previous_translation=previous_translation
    )


def build_translation_prompt(
    subtitle_text: str,
    source_language: str = "英文",
    target_language: str = "中文",
    article_content: str = None
) -> str:
    """
    构建字幕翻译提示词
    
    Args:
        subtitle_text: 待翻译的字幕文本（已格式化为 [序号] 内容 格式）
        source_language: 源语言
        target_language: 目标语言
        article_content: 可选，解读文章全文（提供全局上下文）
        
    Returns:
        格式化后的提示词
    """
    if article_content:
        return SUBTITLE_TRANSLATION_PROMPT_WITH_CONTEXT.format(
            source_language=source_language,
            target_language=target_language,
            article_content=article_content,
            subtitle_text=subtitle_text
        )
    else:
        return SUBTITLE_TRANSLATION_PROMPT_FALLBACK.format(
            source_language=source_language,
            target_language=target_language,
            subtitle_text=subtitle_text
        )
