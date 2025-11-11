# Implementation Plan

- [x] 1. 创建DocumentProcessor核心组件
  - 创建`src/reinvent_insight/document_processor.py`文件
  - 实现DocumentProcessor类的基本结构
  - 实现格式识别逻辑（_get_document_type方法）
  - 实现文本文档处理策略（_process_text_document方法）
  - 实现多模态文档处理策略（_process_multimodal_document方法）
  - 实现统一的process_document入口方法
  - _Requirements: 1.1, 2.1, 3.1, 4.2, 4.3, 6.1, 6.2_

- [x] 2. 扩展DocumentContent数据模型
  - 在`src/reinvent_insight/workflow.py`中扩展现有的PDFContent
  - 添加content_type字段（'text'或'multimodal'）
  - 添加text_content字段（可选，仅text类型使用）
  - 实现is_text和is_multimodal属性方法
  - 创建PDFContent别名以保持向后兼容
  - _Requirements: 4.4, 5.1, 5.2, 6.3_

- [x] 3. 修改Workflow以支持多种内容类型
  - 在DeepSummaryWorkflow.__init__中添加content_type判断逻辑
  - 修改_generate_outline方法，根据content_type选择处理方式
  - 修改_generate_single_chapter方法，根据content_type选择处理方式
  - 修改_generate_conclusion方法，根据content_type选择处理方式
  - 确保向后兼容字符串类型的transcript参数
  - _Requirements: 4.5, 5.3, 6.4, 6.5_

- [x] 4. 扩展utils工具函数
  - 在`src/reinvent_insight/utils.py`中添加generate_document_identifier函数
  - 实现is_text_document判断函数
  - 实现is_multimodal_document判断函数
  - 扩展现有的generate_doc_hash以支持文档标识符
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 5. 添加API端点
  - 在`src/reinvent_insight/api.py`中添加analyze_document端点
  - 实现文件上传和验证逻辑
  - 实现文件格式检查（基于扩展名和MIME类型）
  - 实现文件大小验证
  - 集成DocumentProcessor调用
  - 创建并启动document_analysis_worker
  - 实现临时文件清理逻辑
  - _Requirements: 4.1, 7.1, 7.2, 7.4_

- [x] 6. 创建document_worker模块
  - 创建`src/reinvent_insight/document_worker.py`文件
  - 实现document_analysis_worker_async函数
  - 处理DocumentContent对象并调用workflow
  - 实现错误处理和资源清理
  - 复用现有的任务管理器通信机制
  - _Requirements: 6.1, 6.2, 7.3, 7.4_

- [x] 7. 添加配置项
  - 在`src/reinvent_insight/config.py`中添加MAX_TEXT_FILE_SIZE配置
  - 添加MAX_BINARY_FILE_SIZE配置
  - 添加SUPPORTED_TEXT_FORMATS配置
  - 添加SUPPORTED_BINARY_FORMATS配置
  - _Requirements: 7.2_

- [x] 8. 更新前端UI
  - 修改文件上传组件以支持多种格式
  - 更新文件类型提示信息
  - 添加格式图标显示
  - _Requirements: 4.1_

- [ ] 9. 编写测试用例
  - 创建`tests/test_document_processor.py`测试文件
  - 编写格式识别测试
  - 编写文本文档处理测试
  - 编写多模态文档处理测试
  - 编写错误处理测试
  - 创建`tests/test_document_content.py`测试文件
  - 编写数据模型测试
  - 编写向后兼容性测试
  - 准备测试数据文件（test_sample.txt, test_sample.md, test_sample.docx）
  - _Requirements: 所有需求的验证_

- [x] 10. 集成测试和验证
  - 测试TXT文件端到端流程
  - 测试MD文件端到端流程
  - 测试DOCX文件端到端流程
  - 验证PDF文件处理不受影响
  - 测试错误场景（不支持格式、损坏文件、超大文件）
  - 验证生成报告的格式和质量
  - _Requirements: 所有需求的集成验证_

- [x] 11. 文档更新
  - 更新README.md添加支持格式说明
  - 更新API文档说明新端点
  - 添加使用示例
  - 更新配置说明
  - _Requirements: 用户文档需求_
