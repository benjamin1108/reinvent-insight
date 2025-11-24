# Implementation Plan

- [x] 1. 设置项目结构和核心接口
  - 创建 `src/reinvent_insight/html_to_markdown/` 目录结构
  - 定义数据模型类（ExtractedContent、ImageInfo、ConversionResult）
  - 定义异常类层次结构
  - 创建 `__init__.py` 导出主要接口
  - _Requirements: 8.1, 8.5_

- [x] 2. 实现HTML预处理器
  - 实现 HTMLPreprocessor 类的基本结构
  - 实现 script 标签移除功能
  - 实现 style 标签和属性移除功能
  - 实现 HTML 注释移除功能
  - 实现 SVG 和 Canvas 元素移除功能
  - 确保预处理后 HTML 结构保持完整
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]* 2.1 编写HTMLPreprocessor的属性测试
  - **Property 1: Script标签移除完整性**
  - **Validates: Requirements 2.1**

- [ ]* 2.2 编写HTMLPreprocessor的属性测试
  - **Property 2: Style移除完整性**
  - **Validates: Requirements 2.2**

- [ ]* 2.3 编写HTMLPreprocessor的属性测试
  - **Property 3: HTML注释移除**
  - **Validates: Requirements 2.3**

- [ ]* 2.4 编写HTMLPreprocessor的属性测试
  - **Property 4: SVG和Canvas移除**
  - **Validates: Requirements 2.4**

- [ ]* 2.5 编写HTMLPreprocessor的属性测试
  - **Property 5: HTML结构保持性**
  - **Validates: Requirements 2.5**

- [x] 3. 实现URL处理器
  - 实现 URLProcessor 类
  - 实现相对路径到绝对路径的转换
  - 实现 URL 有效性验证
  - 实现 data URI 检测和保留
  - 实现查询参数保留
  - 处理边界情况（空URL、无效URL）
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 3.1 编写URLProcessor的属性测试
  - **Property 14: 相对URL转换正确性**
  - **Validates: Requirements 9.1, 9.2**

- [ ]* 3.2 编写URLProcessor的属性测试
  - **Property 15: URL查询参数保留**
  - **Validates: Requirements 9.3**

- [ ]* 3.3 编写URLProcessor的属性测试
  - **Property 16: Data URI保留**
  - **Validates: Requirements 9.4**

- [x] 4. 创建LLM提示词模板
  - 在 `prompt/` 目录创建 `html_to_markdown.txt`
  - 编写清晰的任务描述
  - 定义 JSON 输出格式规范
  - 添加示例帮助模型理解
  - 指定内容过滤和保留规则
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4_

- [x] 5. 配置模型任务类型
  - 在 `config/model_config.yaml` 添加 `html_to_markdown` 任务配置
  - 配置使用 Gemini 3 Pro 模型
  - 设置合适的温度参数（0.5）
  - 设置足够的 max_output_tokens（16000）
  - 配置速率限制和重试参数
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. 实现LLM内容提取器
  - 实现 LLMContentExtractor 类
  - 实现提示词构建逻辑
  - 集成统一模型配置系统
  - 实现 LLM API 调用
  - 实现 JSON 响应解析
  - 处理 LLM 返回的内容并创建 ExtractedContent 对象
  - 实现错误处理和重试机制
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.4, 5.5_

- [ ]* 6.1 编写LLM内容提取的示例测试
  - 测试从新闻文章提取标题和正文
  - 测试从博客提取内容和作者信息
  - 测试过滤广告和导航元素
  - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 10.1, 10.2_

- [ ]* 6.2 编写图片提取的属性测试
  - **Property 6: 图片alt文本保留**
  - **Validates: Requirements 3.5**

- [ ]* 6.3 编写API重试机制的属性测试
  - **Property 7: API重试机制**
  - **Validates: Requirements 5.4**

- [x] 7. 实现Markdown生成器
  - 实现 MarkdownGenerator 类
  - 实现标题格式化
  - 实现图片列表格式化（使用标准 Markdown 语法）
  - 实现链接格式化
  - 实现 Markdown 语法验证
  - 实现文件保存功能
  - _Requirements: 6.1, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ]* 7.1 编写Markdown生成的属性测试
  - **Property 8: Markdown格式有效性**
  - **Validates: Requirements 6.1**

- [ ]* 7.2 编写图片语法的属性测试
  - **Property 9: 图片Markdown语法正确性**
  - **Validates: Requirements 6.5**

- [ ]* 7.3 编写标题层级的属性测试
  - **Property 10: 标题层级正确性**
  - **Validates: Requirements 7.1**

- [ ]* 7.4 编写链接格式的属性测试
  - **Property 11: 链接格式正确性**
  - **Validates: Requirements 7.3**

- [x] 8. 实现主转换器接口
  - 实现 HTMLToMarkdownConverter 类
  - 实现 `convert_from_string` 方法
  - 实现 `convert_from_file` 方法
  - 实现 `convert_from_url` 方法（使用 httpx 获取 HTML）
  - 协调各组件完成完整的转换流程
  - 实现进度日志输出
  - 返回 ConversionResult 对象
  - _Requirements: 1.1, 1.2, 1.4, 8.1, 8.2, 8.3_

- [ ]* 8.1 编写返回值的属性测试
  - **Property 12: 返回值完整性**
  - **Validates: Requirements 8.3**

- [ ]* 8.2 编写异常处理的属性测试
  - **Property 13: 异常类型正确性**
  - **Validates: Requirements 8.4**

- [ ]* 8.3 编写多语言处理的属性测试
  - **Property 17: 多语言字符处理**
  - **Validates: Requirements 10.4**

- [x] 9. 实现错误处理
  - 实现各种异常类的具体错误消息
  - 在各组件中添加适当的错误处理
  - 确保错误信息清晰且可操作
  - 实现宽松模式的 HTML 解析
  - _Requirements: 1.3, 4.5, 5.3, 5.5, 9.5_

- [ ]* 9.1 编写错误处理的单元测试
  - 测试无效 HTML 输入
  - 测试 LLM API 失败
  - 测试空内容处理
  - 测试文件 IO 错误
  - _Requirements: 1.3, 4.5, 5.5_

- [x] 10. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 11. 创建集成测试
  - 准备真实网页的 HTML 测试样本（新闻、博客、技术文档）
  - 测试完整的转换流程
  - 验证提取内容的质量
  - 测试各种边界情况
  - _Requirements: 10.1, 10.2, 10.3, 10.5_

- [ ]* 11.1 编写集成测试用例
  - 测试新闻文章转换
  - 测试博客文章转换
  - 测试技术文档转换
  - 测试包含代码块的页面
  - _Requirements: 10.1, 10.2, 10.3_

- [ ] 12. 添加CLI支持（可选）
  - 创建 `__main__.py` 支持命令行调用
  - 实现 `convert` 命令
  - 支持从文件或 URL 转换
  - 支持指定输出路径和 base URL
  - 添加详细的帮助信息
  - _Requirements: 8.1_

- [ ]* 12.1 编写CLI的单元测试
  - 测试命令行参数解析
  - 测试各种调用方式
  - _Requirements: 8.1_

- [x] 13. 编写使用文档和示例
  - 在模块 docstring 中添加使用示例
  - 创建 README 或使用指南
  - 添加代码注释和类型提示
  - 提供常见问题解答
  - _Requirements: 8.1_

- [x] 14. Final Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户
