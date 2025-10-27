# PDF上传和标题生成功能测试文档

## 修改内容总结

### 1. 前端上传进度显示

**文件**: `web/js/app.js`

**修改内容**:
- 在`startSummarize`方法中添加了`onUploadProgress`回调
- 上传进度占总进度的0-20%
- 实时显示上传的MB数和百分比
- 上传完成后显示"PDF文件上传成功，服务器正在处理..."

**效果**:
```
正在上传PDF文件: 2.5MB / 10.0MB (25%)
正在上传PDF文件: 5.0MB / 10.0MB (50%)
正在上传PDF文件: 7.5MB / 10.0MB (75%)
正在上传PDF文件: 10.0MB / 10.0MB (100%)
PDF文件上传成功，服务器正在处理...
```

### 2. AI生成英文标题

**文件**: `src/reinvent_insight/pdf_processor.py`

**修改内容**:
- 在`_build_outline_prompt`方法中添加了`title_en`字段的生成指令
- 提示AI优先使用PDF中的原始英文标题
- 如果没有原始标题，则根据内容归纳一个简洁的英文标题（5-15个单词）
- 在`generate_outline`方法的返回值中添加了`title_en`字段

**提示词示例**:
```
"title_en": "基于PDF内容生成一个简洁的英文标题，优先使用PDF文档中的原始英文标题，如果没有则根据内容归纳一个（5-15个单词）"
```

### 3. Workflow集成英文标题

**文件**: `src/reinvent_insight/workflow.py`

**修改内容**:
- 在`DeepSummaryWorkflow`类中添加了`generated_title_en`属性
- 在`run`方法中，解析大纲时提取AI生成的英文标题
- 在组装最终报告前，如果是PDF且有AI生成的英文标题，则更新metadata使用该标题
- 这样最终的文件名会使用AI生成的英文标题

**逻辑流程**:
1. Workflow生成大纲时，AI会返回包含`title_en`的JSON
2. 从大纲内容中提取`title_en`
3. 在组装报告时，创建新的metadata对象，使用AI生成的英文标题
4. 文件名基于metadata.title生成，因此会使用英文标题

### 4. PDF Worker简化

**文件**: `src/reinvent_insight/pdf_worker.py`

**修改内容**:
- 移除了提前生成大纲的逻辑
- 使用临时标识符和标题
- 让workflow在内部完成标题生成和文件命名

## 测试场景

### 场景1: 上传带原始英文标题的PDF
- **输入**: AWS白皮书 "Amazon S3 Best Practices.pdf"
- **期望**: 
  - 前端显示上传进度
  - AI提取原始标题 "Amazon S3 Best Practices"
  - 文件名: `Amazon_S3_Best_Practices.md`

### 场景2: 上传中文PDF
- **输入**: 中文技术文档 "深度学习实践指南.pdf"
- **期望**:
  - 前端显示上传进度
  - AI根据内容生成英文标题，如 "Deep Learning Practice Guide"
  - 文件名: `Deep_Learning_Practice_Guide.md`

### 场景3: 上传大文件
- **输入**: 50MB的PDF文件
- **期望**:
  - 前端实时显示上传进度（MB和百分比）
  - 上传完成后显示"服务器正在处理"
  - 不会出现"上传失败"或"无响应"的情况

## 验证方法

1. **前端验证**:
   - 打开浏览器开发者工具的Network标签
   - 上传PDF文件
   - 观察上传进度是否正确显示
   - 检查日志区域是否显示上传进度信息

2. **后端验证**:
   - 查看服务器日志，确认AI生成的英文标题
   - 检查生成的文件名是否使用英文标题
   - 验证metadata中的title_en字段

3. **文件验证**:
   - 检查生成的Markdown文件的YAML front matter
   - 确认包含`title_en`和`title_cn`两个字段
   - 文件名应该基于`title_en`

## 注意事项

1. **字符编码**: 确保所有文本使用UTF-8编码
2. **文件名清理**: 英文标题会通过`sanitize_filename`函数清理，移除特殊字符
3. **错误处理**: 如果AI未能生成有效的英文标题，会使用备用标题
4. **向后兼容**: 对于YouTube视频，原有逻辑保持不变

## 相关文件

- `web/js/app.js` - 前端上传逻辑
- `src/reinvent_insight/pdf_processor.py` - PDF处理器
- `src/reinvent_insight/pdf_worker.py` - PDF工作流
- `src/reinvent_insight/workflow.py` - 统一工作流
- `src/reinvent_insight/prompts.py` - 提示词模板
