# Implementation Plan

- [x] 1. 创建 Prompt 配置基础设施
  - 创建 `prompt/` 目录结构（base/, templates/, fragments/）
  - 创建 `config.yaml` 主配置文件，定义所有 prompt 的元数据
  - 迁移现有 prompt 内容到对应的文件中
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. 实现 PromptManager 核心类
  - [x] 2.1 实现 PromptConfig 数据类
    - 定义 prompt 配置的数据结构
    - 实现配置验证逻辑
    - _Requirements: 1.1, 3.1_

  - [x] 2.2 实现 PromptManager 基础功能
    - 实现 `__init__` 方法，支持配置路径和热重载选项
    - 实现 `load_prompts` 方法，从 YAML 加载配置
    - 实现 `get_prompt` 方法，获取 prompt 内容
    - 实现文件读取和缓存机制
    - _Requirements: 1.1, 1.2, 5.1, 5.4_

  - [x] 2.3 实现 prompt 片段组合功能
    - 实现 `{{include:key}}` 语法解析
    - 实现递归包含和循环检测
    - 实现片段缓存优化
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 2.4 实现模板参数替换功能
    - 实现 `format_prompt` 方法
    - 实现 `{param}` 占位符替换
    - 实现必需参数和可选参数验证
    - 实现条件包含 `{{if:param}}...{{endif}}` 语法
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 2.5 实现热重载功能
    - 实现 `reload_prompts` 方法
    - 实现文件监控机制（开发模式）
    - 实现重载失败时的降级策略
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 2.6 实现验证和诊断功能
    - 实现 `validate_prompts` 方法
    - 实现 `list_prompts` 方法
    - 实现详细的错误信息生成
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. 实现异常处理体系
  - 定义 `PromptError` 基类和子类异常
  - 实现异常的详细错误信息
  - 在 PromptManager 中集成异常处理
  - _Requirements: 3.2_

- [x] 4. 创建向后兼容层
  - [x] 4.1 更新 prompts.py 模块
    - 创建全局 PromptManager 实例
    - 实现 `__getattr__` 方法提供旧常量访问
    - 添加弃用警告日志
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 4.2 验证向后兼容性
    - 确保现有代码无需修改即可运行
    - 验证所有旧常量都能正确访问
    - _Requirements: 6.1, 6.2_

- [x] 5. 迁移现有代码使用新 API
  - [x] 5.1 更新 workflow.py
    - 替换 `load_base_prompt()` 为 `PromptManager.get_prompt()`
    - 更新所有 prompt 模板的格式化调用
    - 移除硬编码的 `BASE_PROMPT_PATH`
    - _Requirements: 1.4_

  - [x] 5.2 更新其他使用 prompt 的模块
    - 检查并更新所有导入 `prompts` 模块的代码
    - 使用新的 PromptManager API
    - _Requirements: 1.4_

- [x] 6. 添加配置和文档
  - [x] 6.1 创建 prompt 配置文档
    - 编写 `prompt/README.md` 说明配置格式
    - 提供 prompt 编写指南和最佳实践
    - 添加示例配置
    - _Requirements: 1.2_

  - [x] 6.2 更新项目文档
    - 更新主 README 说明新的 prompt 管理方式
    - 添加迁移指南
    - _Requirements: 6.1_

- [x] 7. 编写测试
  - [x] 7.1 编写 PromptManager 单元测试
    - 测试 prompt 加载和缓存
    - 测试参数替换功能
    - 测试片段包含和组合
    - 测试错误处理
    - _Requirements: 1.1, 2.1, 2.2, 4.1, 4.2_

  - [x] 7.2 编写配置解析测试
    - 测试 YAML 配置解析
    - 测试配置验证
    - 测试版本信息提取
    - _Requirements: 3.1, 3.2_

  - [x] 7.3 编写向后兼容性测试
    - 测试旧接口是否正常工作
    - 测试弃用警告是否正确触发
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 7.4 编写集成测试
    - 测试在实际工作流中使用新的 PromptManager
    - 测试 PDF 和视频两种模式
    - 测试完整的生成流程
    - _Requirements: 1.1, 2.1, 4.1_

  - [x] 7.5 编写热重载测试
    - 测试修改 prompt 文件后是否自动重载
    - 测试重载失败时的降级行为
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 8. 性能优化和清理
  - 分析 prompt 加载和格式化性能
  - 优化缓存策略
  - 清理临时代码和注释
  - _Requirements: 5.4_

- [x] 9. 最终验证和部署
  - 运行完整的测试套件
  - 在开发环境验证所有功能
  - 更新部署文档
  - _Requirements: 3.1, 3.4_
