# Implementation Plan

- [x] 1. 修改提示词模板以支持标题提取
  - 修改prompts.py中的OUTLINE_PROMPT_TEMPLATE
  - 添加JSON格式的标题输出要求
  - 明确英文标题的提取/生成规则
  - _Requirements: 1.1, 1.2_

- [x] 2. 实现标题提取逻辑
- [x] 2.1 创建extract_titles_from_outline函数
  - 在workflow.py中添加新函数
  - 实现JSON格式解析逻辑
  - 实现Markdown格式备用解析
  - 添加错误处理和日志记录
  - _Requirements: 1.1, 1.3, 3.1, 3.2_

- [x] 2.2 修改_generate_outline方法
  - 在大纲生成后调用extract_titles_from_outline
  - 保存提取的title_en到实例变量
  - 添加提取失败的处理逻辑
  - _Requirements: 1.1, 1.5, 3.4_

- [ ] 3. 实现洞见解析增强
- [ ] 3.1 创建extract_insights_and_quotes函数
  - 在workflow.py中添加新函数
  - 实现基于正则表达式的主解析方法
  - 实现逐行解析的备用方法
  - 添加详细的日志记录
  - _Requirements: 2.2, 2.3, 3.3_

- [ ]* 3.2 添加解析测试用例
  - 创建测试文件test_workflow.py
  - 测试正常情况的洞见解析
  - 测试各种边缘情况
  - 测试错误恢复机制
  - _Requirements: 2.5, 3.4_

- [ ] 4. 修改报告组装逻辑
- [ ] 4.1 修改_perform_assembly函数签名
  - 将conclusion_md参数改为insights和quotes两个参数
  - 更新函数文档字符串
  - 移除内部的洞见解析逻辑
  - _Requirements: 2.4_

- [ ] 4.2 修改_assemble_final_report方法
  - 调用extract_insights_and_quotes提取洞见和金句
  - 使用self.generated_title_en作为metadata的title
  - 传递提取的insights和quotes给_perform_assembly
  - 添加错误处理逻辑
  - _Requirements: 1.4, 2.1, 2.4, 3.4_

- [ ] 4.3 更新metadata生成逻辑
  - 确保title_en使用提取的英文标题
  - 确保title_cn使用AI生成的中文标题
  - 添加字段验证
  - _Requirements: 1.4, 3.5_

- [ ] 5. 添加日志和错误处理
- [ ] 5.1 增强日志记录
  - 在标题提取处添加详细日志
  - 在洞见解析处添加详细日志
  - 记录所有后备方案的使用
  - _Requirements: 3.2, 3.4_

- [ ] 5.2 完善错误处理
  - 确保所有异常都被捕获
  - 提供清晰的错误消息
  - 实现优雅降级
  - _Requirements: 3.4, 3.5_

- [ ] 6. 测试和验证
- [ ] 6.1 手动测试完整流程
  - 使用真实PDF文档测试
  - 验证title_en正确性
  - 验证洞见出现在最终报告中
  - 检查metadata格式
  - _Requirements: 1.1, 1.4, 2.1, 2.4_

- [ ]* 6.2 创建集成测试
  - 测试完整的PDF分析流程
  - 测试各种错误场景
  - 验证向后兼容性
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 7. 文档更新
- [ ] 7.1 更新代码注释
  - 为新函数添加详细的docstring
  - 更新修改函数的文档
  - 添加使用示例
  - _Requirements: All_

- [ ]* 7.2 更新用户文档
  - 说明新的标题提取机制
  - 说明洞见部分的改进
  - 提供故障排除指南
  - _Requirements: All_
