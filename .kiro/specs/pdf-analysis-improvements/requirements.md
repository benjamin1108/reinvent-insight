# Requirements Document

## Introduction

本需求文档旨在改进PDF文档分析工作流，解决当前存在的两个主要问题：
1. metadata中的title_en字段错误地使用了PDF文件名，而非从PDF内容中提取或生成的英文标题
2. 生成的洞见延伸内容未正确拼接到最终的summary文件中

## Glossary

- **PDF Workflow**: PDF文档分析工作流程，负责处理PDF文档并生成深度分析报告
- **Title Generation**: 标题生成过程，包括中文标题和英文标题的生成
- **Insights Section**: 洞见延伸部分，包含对文档的深度解读和关键洞察
- **Final Report**: 最终生成的Markdown格式分析报告
- **Task Directory**: 任务目录，存储中间生成文件的位置
- **Conclusion Content**: 收尾内容，包含洞见和金句部分

## Requirements

### Requirement 1: 正确提取和使用英文标题

**User Story:** 作为系统用户，我希望metadata中的title_en字段包含从PDF内容中提取或AI生成的真实英文标题，而不是PDF文件名，以便准确反映文档的实际标题

#### Acceptance Criteria

1. WHEN 生成大纲时，THE System SHALL 要求AI从PDF内容中提取原始英文标题
2. IF PDF内容中不存在英文标题，THEN THE System SHALL 要求AI基于内容生成一个合适的英文标题
3. WHEN 大纲生成完成后，THE System SHALL 从大纲内容中解析并保存AI提取或生成的英文标题
4. WHEN 组装最终报告时，THE System SHALL 使用提取的英文标题作为metadata中的title_en字段值
5. WHEN 英文标题提取失败时，THE System SHALL 记录警告并使用中文标题的拼音或简化版本作为后备方案

### Requirement 2: 洞见内容正确拼接到最终报告

**User Story:** 作为系统用户，我希望生成的洞见延伸内容能够正确拼接到最终的summary文件中，以便获得完整的分析结果

#### Acceptance Criteria

1. WHEN 生成收尾内容时，THE System SHALL 确保洞见延伸部分被正确生成并保存到conclusion.md文件
2. WHEN 组装最终报告时，THE System SHALL 从conclusion.md文件中正确解析洞见延伸部分
3. WHEN 解析洞见部分时，THE System SHALL 使用健壮的正则表达式匹配"### 洞见延伸"章节标题
4. WHEN 拼接最终报告时，THE System SHALL 将洞见内容放置在所有章节内容之后、金句之前的正确位置
5. WHEN 洞见部分解析失败时，THE System SHALL 记录详细的错误日志并尝试使用备用解析方法

### Requirement 3: 提升代码健壮性

**User Story:** 作为系统维护者，我希望代码能够处理各种边缘情况，以便系统更加稳定可靠

#### Acceptance Criteria

1. WHEN 解析大纲内容时，THE System SHALL 处理JSON格式和纯文本格式两种情况
2. WHEN 提取标题失败时，THE System SHALL 记录详细的错误信息并使用合理的默认值
3. WHEN 解析conclusion内容时，THE System SHALL 使用更健壮的正则表达式匹配章节标题
4. WHEN 文件读取失败时，THE System SHALL 提供清晰的错误消息并优雅地降级
5. WHEN 生成metadata时，THE System SHALL 确保所有必需字段都有有效值
