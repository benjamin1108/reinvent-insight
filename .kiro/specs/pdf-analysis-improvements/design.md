# Design Document

## Overview

本设计文档描述了如何修复PDF分析工作流中的两个关键问题：
1. 正确提取和使用英文标题而非PDF文件名
2. 确保洞见延伸内容正确拼接到最终报告中

设计方案将通过修改提示词、增强解析逻辑和改进报告组装流程来实现这些目标。

## Architecture

### 系统组件

```
┌─────────────────────────────────────────────────────────────┐
│                    DeepSummaryWorkflow                       │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Outline    │───>│   Chapters   │───>│  Conclusion  │ │
│  │  Generation  │    │  Generation  │    │  Generation  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                                        │          │
│         v                                        v          │
│  ┌──────────────┐                        ┌──────────────┐ │
│  │ Title        │                        │  Insights    │ │
│  │ Extraction   │                        │  Parsing     │ │
│  └──────────────┘                        └──────────────┘ │
│         │                                        │          │
│         └────────────────┬───────────────────────┘          │
│                          v                                  │
│                  ┌──────────────┐                          │
│                  │   Report     │                          │
│                  │  Assembly    │                          │
│                  └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

1. **Outline Generation Phase**
   - Input: PDF content
   - Process: AI generates outline with both Chinese and English titles
   - Output: outline.md containing structured title information

2. **Title Extraction Phase**
   - Input: outline.md content
   - Process: Parse and extract both title_cn and title_en
   - Output: Stored title information for later use

3. **Conclusion Generation Phase**
   - Input: All chapter contents + PDF content
   - Process: AI generates insights and quotes
   - Output: conclusion.md with structured sections

4. **Insights Parsing Phase**
   - Input: conclusion.md content
   - Process: Robust regex-based section extraction
   - Output: Separated insights and quotes content

5. **Report Assembly Phase**
   - Input: All components (title, intro, chapters, insights, quotes)
   - Process: Concatenate in correct order with proper formatting
   - Output: Final markdown report with correct metadata

## Components and Interfaces

### 1. Prompt Enhancement

#### OUTLINE_PROMPT_TEMPLATE 修改

**目的**: 要求AI同时提取/生成中文和英文标题

**修改内容**:
```python
OUTLINE_PROMPT_TEMPLATE = """
{base_prompt}

## 输入素材
- {content_type}: 
{full_content}

---
## 当前任务
你的**唯一任务**是根据上方提供的{content_description}，生成这份深度笔记的 **中文标题**、**英文标题**、**引言** 和 **大纲索引**。

## 标题提取/生成规则
1. **英文标题 (title_en)**：
   - 优先从PDF内容中提取原始的英文标题
   - 如果PDF中没有明确的英文标题，则基于内容生成一个简洁、专业的英文标题
   - 英文标题应该准确反映文档的核心主题
   - 格式：简洁的英文短语或句子，不超过15个单词

2. **中文标题 (title_cn)**：
   - 基于内容生成一个高度概括核心内容的中文标题
   - 应该具有吸引力和信息量

## 输出格式
```json
{
  "title_en": "[提取或生成的英文标题]",
  "title_cn": "[生成的中文标题]"
}
```

# [中文标题]

### 引言
[这里是引言内容]

### 主要目录
1. [第一章标题]
2. [第二章标题]
...

---
**请严格遵守上述指令，首先输出JSON格式的标题信息，然后输出标题、引言和大纲索引。**
"""
```

### 2. Title Extraction Logic

#### 新增函数: extract_titles_from_outline

**位置**: workflow.py

**功能**: 从outline内容中提取中英文标题

**实现**:
```python
def extract_titles_from_outline(outline_content: str) -> Tuple[Optional[str], Optional[str]]:
    """
    从outline内容中提取中英文标题
    
    Args:
        outline_content: outline.md的完整内容
        
    Returns:
        (title_en, title_cn) 元组，如果提取失败则返回None
    """
    # 尝试提取JSON格式的标题信息
    json_match = re.search(r'\{[\s\S]*?"title_en"[\s\S]*?"title_cn"[\s\S]*?\}', outline_content)
    if json_match:
        try:
            title_data = json.loads(json_match.group(0))
            title_en = title_data.get('title_en', '').strip()
            title_cn = title_data.get('title_cn', '').strip()
            if title_en and title_cn:
                return title_en, title_cn
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
    
    # 备用方案：从Markdown标题中提取
    title_match = re.search(r"^#\s*(.*)", outline_content, re.MULTILINE)
    title_cn = title_match.group(1).strip() if title_match else None
    
    # 如果没有英文标题，使用中文标题的拼音或简化版本
    title_en = None
    if title_cn:
        # 这里可以使用pypinyin库或简单的transliteration
        # 暂时返回None，让调用者处理
        pass
    
    return title_en, title_cn
```

### 3. Insights Parsing Enhancement

#### 修改函数: _perform_assembly

**位置**: workflow.py

**问题**: 当前的洞见解析逻辑不够健壮

**当前实现**:
```python
conclusion_parts = re.split(r'\n###\s+', '\n' + conclusion_md)
for part in conclusion_parts:
    part = part.strip()
    if not part:
        continue
    full_part = "### " + part
    if part.lower().startswith('洞见延伸'):
        insights = full_part
    elif part.lower().startswith('金句&原声引用'):
        quotes = full_part
```

**改进实现**:
```python
def extract_insights_and_quotes(conclusion_md: str) -> Tuple[str, str]:
    """
    从conclusion内容中提取洞见和金句部分
    
    Args:
        conclusion_md: conclusion.md的完整内容
        
    Returns:
        (insights, quotes) 元组
    """
    insights = ""
    quotes = ""
    
    # 方法1: 使用更健壮的正则表达式
    # 匹配 "### 洞见延伸" 到下一个 "###" 或文件结尾
    insights_match = re.search(
        r'###\s*洞见延伸\s*\n(.*?)(?=\n###|\Z)', 
        conclusion_md, 
        re.DOTALL | re.IGNORECASE
    )
    if insights_match:
        insights = "### 洞见延伸\n" + insights_match.group(1).strip()
    else:
        logger.warning("未能从conclusion中提取洞见延伸部分")
    
    # 匹配 "### 金句&原声引用" 到文件结尾
    quotes_match = re.search(
        r'###\s*金句&原声引用\s*\n(.*?)(?=\n###|\Z)', 
        conclusion_md, 
        re.DOTALL | re.IGNORECASE
    )
    if quotes_match:
        quotes = "### 金句&原声引用\n" + quotes_match.group(1).strip()
    else:
        logger.warning("未能从conclusion中提取金句部分")
    
    # 方法2: 如果方法1失败，尝试按行解析
    if not insights or not quotes:
        logger.info("尝试使用备用解析方法")
        lines = conclusion_md.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            if line.strip().startswith('###'):
                # 保存上一个section
                if current_section and section_content:
                    content = '\n'.join(section_content)
                    if '洞见' in current_section:
                        insights = f"### {current_section}\n{content}"
                    elif '金句' in current_section:
                        quotes = f"### {current_section}\n{content}"
                
                # 开始新section
                current_section = line.strip().lstrip('#').strip()
                section_content = []
            elif current_section:
                section_content.append(line)
        
        # 处理最后一个section
        if current_section and section_content:
            content = '\n'.join(section_content)
            if '洞见' in current_section:
                insights = f"### {current_section}\n{content}"
            elif '金句' in current_section:
                quotes = f"### {current_section}\n{content}"
    
    return insights, quotes
```

### 4. Report Assembly Enhancement

#### 修改函数: _assemble_final_report

**位置**: workflow.py

**修改内容**:
1. 使用提取的title_en而非PDF文件名
2. 调用新的insights解析函数
3. 确保正确的组装顺序

**实现**:
```python
async def _assemble_final_report(
    self, 
    title: str, 
    introduction: str, 
    toc_md: str, 
    conclusion_md: str, 
    chapter_count: int, 
    metadata: VideoMetadata
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """步骤4：在本地组装所有部分以生成最终的Markdown文件"""
    await self._log("步骤 4/4: 正在整理最终报告...")
    try:
        # 读取所有章节
        chapter_contents = []
        for i in range(chapter_count):
            chapter_path = os.path.join(self.task_dir, f"chapter_{i + 1}.md")
            with open(chapter_path, 'r', encoding='utf-8') as f:
                chapter_contents.append(f.read().strip())
        
        # 提取洞见和金句
        insights, quotes = extract_insights_and_quotes(conclusion_md)
        
        # 使用提取的英文标题
        title_en = self.generated_title_en if self.generated_title_en else metadata.title
        
        # 创建更新后的metadata
        updated_metadata = VideoMetadata(
            title=title_en,  # 使用提取的英文标题
            upload_date=metadata.upload_date,
            video_url=metadata.video_url,
            is_reinvent=metadata.is_reinvent,
            course_code=metadata.course_code,
            level=metadata.level
        )
        
        # 调用核心拼接逻辑
        final_report = _perform_assembly(
            title, 
            introduction, 
            toc_md, 
            insights,  # 传入提取的洞见
            quotes,    # 传入提取的金句
            chapter_contents, 
            updated_metadata
        )
        
        # ... 后续保存逻辑
```

#### 修改函数: _perform_assembly

**修改签名**:
```python
def _perform_assembly(
    title: str, 
    introduction: str, 
    toc_md: str, 
    insights: str,  # 改为直接接收洞见内容
    quotes: str,    # 改为直接接收金句内容
    chapter_contents: List[str], 
    metadata: Optional[VideoMetadata] = None, 
    version: int = 0
) -> str:
```

**修改实现**:
```python
def _perform_assembly(...):
    """可复用的核心拼接逻辑"""
    # 1. 生成 YAML Front Matter
    metadata_yaml = ""
    if metadata:
        try:
            import yaml
            metadata_dict = {
                "title_en": metadata.title,  # 现在是提取的英文标题
                "title_cn": title,  # AI生成的中文标题
                "upload_date": metadata.upload_date,
                "video_url": metadata.video_url,
                "is_reinvent": metadata.is_reinvent,
                "course_code": metadata.course_code,
                "level": metadata.level,
                "created_at": datetime.now().isoformat()
            }
            if version > 0:
                metadata_dict['version'] = version
            yaml_content = yaml.dump(metadata_dict, allow_unicode=True, sort_keys=False).rstrip()
            metadata_yaml = f"---\n{yaml_content}\n---\n\n"
        except Exception as e:
            logger.error(f"生成 YAML front matter 时出错: {e}")
    
    # 2. 按正确的顺序拼接（洞见和金句已经是提取好的）
    final_report_parts = [
        metadata_yaml,
        f"# {title}",
        f"### 引言\n{introduction}" if introduction else "",
        toc_md,
        "\n\n---\n\n".join(chapter_contents),
        insights,  # 直接使用传入的洞见
        quotes     # 直接使用传入的金句
    ]
    
    return "\n\n".join(part for part in final_report_parts if part and part.strip())
```

## Data Models

### Title Information

```python
@dataclass
class TitleInfo:
    """标题信息"""
    title_en: str  # 英文标题（从PDF提取或AI生成）
    title_cn: str  # 中文标题（AI生成）
```

### Conclusion Sections

```python
@dataclass
class ConclusionSections:
    """收尾部分的各个章节"""
    insights: str  # 洞见延伸内容
    quotes: str    # 金句和原声引用内容
```

## Error Handling

### Title Extraction Errors

1. **JSON解析失败**
   - 记录警告日志
   - 尝试从Markdown标题提取
   - 如果仍失败，使用PDF文件名作为后备

2. **英文标题缺失**
   - 记录警告日志
   - 使用中文标题的transliteration
   - 或使用PDF文件名

### Insights Parsing Errors

1. **正则匹配失败**
   - 记录警告日志
   - 尝试备用的逐行解析方法
   - 如果仍失败，返回空字符串但不中断流程

2. **Section内容为空**
   - 记录警告日志
   - 在最终报告中跳过该section
   - 继续处理其他部分

## Testing Strategy

### Unit Tests

1. **test_extract_titles_from_outline**
   - 测试JSON格式提取
   - 测试Markdown格式提取
   - 测试错误处理

2. **test_extract_insights_and_quotes**
   - 测试正常情况
   - 测试缺少洞见部分
   - 测试缺少金句部分
   - 测试格式变体

3. **test_perform_assembly**
   - 测试完整组装
   - 测试缺少某些部分的情况
   - 测试metadata生成

### Integration Tests

1. **test_full_workflow_with_pdf**
   - 使用真实PDF测试完整流程
   - 验证title_en正确性
   - 验证洞见出现在最终报告中

2. **test_error_recovery**
   - 测试各种错误情况下的恢复能力
   - 验证日志记录

## Implementation Notes

### 关键修改点

1. **prompts.py**
   - 修改OUTLINE_PROMPT_TEMPLATE，要求输出JSON格式的标题信息

2. **workflow.py**
   - 添加extract_titles_from_outline函数
   - 添加extract_insights_and_quotes函数
   - 修改_generate_outline方法，提取并保存title_en
   - 修改_assemble_final_report方法，使用提取的title_en
   - 修改_perform_assembly函数签名和实现

3. **日志增强**
   - 在关键步骤添加详细日志
   - 记录提取的标题信息
   - 记录洞见解析结果

### 向后兼容性

- 保持现有的VideoMetadata结构不变
- 如果title_en提取失败，回退到原有逻辑
- 如果洞见解析失败，不中断流程，只记录警告

### 性能考虑

- 正则表达式优化，避免过度回溯
- 文件读取使用缓冲
- 避免重复解析相同内容
