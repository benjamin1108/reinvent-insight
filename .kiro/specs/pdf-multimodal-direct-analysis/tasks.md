# Implementation Plan

- [x] 1. 创建PDF内容数据模型
  - 在 `workflow.py` 中创建 `PDFContent` 数据类
  - 实现 `file_id` 和 `is_local` 属性
  - 添加内容类型检测辅助函数 `is_pdf_content()`
  - _Requirements: 1.1, 2.3_

- [x] 2. 修改工作流支持PDF内容
  - [x] 2.1 修改 `DeepSummaryWorkflow.__init__()` 接受通用content参数
    - 将 `transcript` 参数改为 `content`，类型为 `Union[str, PDFContent]`
    - 添加 `self.is_pdf` 属性判断内容类型
    - 保持向后兼容，支持字符串类型的transcript
    - 更新 `self.transcript` 为 `self.content` 并在需要时保持兼容性
    - _Requirements: 1.1, 4.4_

  - [x] 2.2 修改 `_generate_outline()` 方法支持PDF
    - 检测内容类型（PDF或文本）
    - 如果是PDF，调用 `summarizer.generate_content_with_pdf()`
    - 如果是文本，保持原有逻辑调用 `summarizer.generate_content()`
    - _Requirements: 1.1, 1.2_

  - [x] 2.3 修改 `_generate_single_chapter()` 方法支持PDF
    - 根据内容类型选择不同的生成方式
    - PDF内容传递文件引用给API
    - 文本内容保持原有逻辑
    - _Requirements: 1.1, 1.2_

  - [x] 2.4 修改 `_generate_conclusion()` 方法支持PDF
    - 根据内容类型调整处理逻辑
    - 确保PDF分析的结论质量
    - _Requirements: 1.1, 5.4_

  - [x] 2.5 更新 `run_deep_summary_workflow()` 入口函数
    - 将 `transcript` 参数改为 `content`，类型为 `Union[str, PDFContent]`
    - 保持向后兼容性
    - _Requirements: 1.1, 4.4_

- [x] 3. 更新提示词模板
  - [x] 3.1 修改 `prompts.py` 中的提示词模板
    - 将OUTLINE_PROMPT_TEMPLATE中的"完整英文字幕"改为通用的"内容"表述
    - 将CHAPTER_PROMPT_TEMPLATE中的"完整字幕"改为通用的"内容"表述
    - 将CONCLUSION_PROMPT_TEMPLATE中的"完整字幕"改为通用的"内容"表述
    - 添加 `{content_type}` 占位符用于区分PDF和视频
    - 保持提示词的核心结构和质量要求
    - _Requirements: 2.1, 2.2, 5.2_

  - [x] 3.2 添加PDF多模态分析指导常量
    - 创建 `PDF_MULTIMODAL_GUIDE` 常量包含视觉元素分析指南
    - 明确架构图、流程图、数据图表的分析要点
    - 强调文本与视觉信息的关联分析
    - 在PDF模式下将此指导添加到提示词中
    - _Requirements: 1.3, 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. 实现Summarizer的PDF支持
  - [x] 4.1 在 `summarizer.py` 中的 `GeminiSummarizer` 类添加 `generate_content_with_pdf()` 方法
    - 接受prompt和pdf_file_info参数
    - 处理本地文件（使用file_data）和远程文件（使用genai.get_file）两种情况
    - 调用Gemini API进行多模态分析
    - 使用与generate_content相同的速率限制逻辑
    - _Requirements: 1.1, 1.2_

- [x] 5. 重构PDF Worker移除文本提取
  - [x] 5.1 修改 `pdf_analysis_worker_async()` 函数
    - 完全移除 `extract_pdf_content()` 调用和函数定义
    - 创建 `PDFContent` 对象封装PDF文件信息
    - 直接将 `PDFContent` 传递给 `run_deep_summary_workflow()`
    - 移除保存提取内容到文件的逻辑（pdf_extracted_content.md）
    - _Requirements: 1.1, 4.1, 4.2, 4.3_

  - [x] 5.2 更新PDF处理的日志和进度消息
    - 修改进度提示文字，反映新的处理流程
    - 移除"正在提取PDF文本内容"相关的消息
    - 添加"正在使用多模态分析PDF"相关的消息
    - _Requirements: 5.1_

- [x] 6. 实现错误处理机制
  - [x] 6.1 添加多模态分析异常处理
    - 在 `pdf_analysis_worker_async()` 中捕获分析失败
    - 记录详细错误日志
    - 直接返回错误信息给用户，不进行降级
    - _Requirements: 4.4_

  - [x] 6.2 实现重试机制
    - PDF上传失败时重试3次
    - API调用失败时使用指数退避
    - 记录重试次数和原因
    - _Requirements: 4.4_

  - [x] 6.3 添加文件清理逻辑
    - 确保临时PDF文件被删除
    - 清理Gemini上的过期文件
    - 处理异常情况下的资源泄漏
    - _Requirements: 4.4_

- [ ]* 7. 编写测试用例
  - [ ]* 7.1 单元测试
    - 测试 `PDFContent` 类的创建和属性访问
    - 测试 `is_pdf_content()` 函数
    - 测试提示词生成逻辑
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 7.2 集成测试
    - 使用真实PDF文件测试完整流程
    - 验证包含图表的PDF分析质量
    - 对比新旧流程的输出差异
    - _Requirements: 1.3, 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 7.3 性能测试
    - 测量API调用次数，验证减少50%
    - 对比端到端处理时间
    - 评估内存使用情况
    - _Requirements: 4.3_

  - [ ]* 7.4 降级测试
    - 模拟多模态分析失败场景
    - 验证fallback机制正常工作
    - 确保系统稳定性
    - _Requirements: 4.4_

- [ ]* 8. 更新开发文档
  - [ ]* 8.1 更新开发文档
    - 记录架构变更
    - 更新流程图
    - 添加troubleshooting指南
    - _Requirements: 2.4_
