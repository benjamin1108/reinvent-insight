# Implementation Plan

- [x] 1. 创建模型配置系统核心模块
  - 创建 `src/reinvent_insight/model_config.py` 文件，实现配置管理和模型客户端
  - 实现 ModelConfig 数据类
  - 实现 RateLimiter 速率限制器
  - 实现 BaseModelClient 抽象基类
  - _Requirements: 1.1, 2.1, 2.2, 5.1, 5.2, 5.3_

- [x] 2. 实现 Gemini 模型客户端
  - 在 `model_config.py` 中实现 GeminiClient 类
  - 实现 generate_content 方法（文本生成）
  - 实现 generate_content_with_file 方法（多模态生成）
  - 集成速率限制和重试机制
  - _Requirements: 2.2, 2.3, 5.1, 5.2, 5.3_

- [x] 3. 实现配置管理器和工厂类
  - 在 `model_config.py` 中实现 ModelConfigManager 类
  - 实现配置文件加载逻辑（YAML + 环境变量）
  - 实现 ModelClientFactory 工厂类
  - 实现 get_model_client 便捷函数
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3_

- [x] 4. 创建默认配置文件
  - 创建 `config/model_config.yaml` 配置文件
  - 定义 default 默认配置
  - 定义 video_summary 任务配置
  - 定义 pdf_processing 任务配置
  - 定义 visual_generation 任务配置
  - 定义 document_analysis 任务配置
  - 添加详细的配置注释说明
  - _Requirements: 1.1, 1.2, 1.3, 6.1, 6.2, 6.3, 6.4_

- [x] 5. 重构 visual_worker.py 使用新配置系统
  - 修改 VisualInterpretationWorker.__init__ 方法
  - 移除 get_summarizer 调用，改用 get_model_client("visual_generation")
  - 更新 _generate_html 方法使用新的客户端接口
  - 验证功能正常
  - _Requirements: 3.1, 3.3, 3.4_

- [x] 6. 重构 pdf_processor.py 使用新配置系统
  - 修改 PDFProcessor.__init__ 方法
  - 移除硬编码的 model_name 和 genai.configure
  - 使用 get_model_client("pdf_processing") 获取客户端
  - 更新 generate_outline 方法使用新客户端
  - 更新 generate_section_content 方法使用新客户端
  - 移除 upload_pdf 和 delete_file 方法（移到 GeminiClient）
  - _Requirements: 3.2, 3.4_

- [x] 7. 重构 workflow.py 使用新配置系统
  - 查找所有模型调用位置
  - 替换为使用 get_model_client 获取客户端
  - 更新所有 generate_content 调用
  - 验证工作流正常运行
  - _Requirements: 3.1, 3.4_

- [x] 8. 重构 document_worker.py 使用新配置系统
  - 检查是否有直接的模型调用
  - 如有，替换为使用 get_model_client("document_analysis")
  - 验证文档分析功能正常
  - _Requirements: 3.1, 3.4_

- [x] 9. 删除旧的 summarizer.py 实现
  - 备份 summarizer.py 文件（以防需要参考）
  - 删除 GeminiSummarizer、XaiSummarizer、AlibabaSummarizer 类
  - 删除 get_summarizer 工厂函数
  - 删除 MODEL_MAP 映射
  - 保留文件但清空内容，添加迁移说明注释
  - _Requirements: 3.4_

- [x] 10. 更新 config.py 清理旧配置
  - 移除 PREFERRED_MODEL 配置（已由 model_config.yaml 替代）
  - 保留 API Key 配置（仍需要用于环境变量）
  - 添加 MODEL_CONFIG_PATH 配置项
  - 更新配置文档注释
  - _Requirements: 1.1, 4.1, 4.2_

- [x] 11. 添加错误处理和日志
  - 在 model_config.py 中定义自定义异常类
  - 添加配置验证逻辑
  - 添加详细的日志记录
  - 处理 API Key 缺失的情况
  - 处理配置文件不存在的情况
  - _Requirements: 5.4_

- [x] 12. 验证和测试
  - 测试视频摘要功能
  - 测试 PDF 处理功能
  - 测试可视化生成功能
  - 测试文档分析功能
  - 验证配置文件加载
  - 验证环境变量覆盖
  - 检查日志输出
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_
