# DashScope (阿里云通义千问) 集成测试

## 概述

本目录包含 DashScope 模型客户端的测试脚本，用于验证与阿里云通义千问的集成。

## 前置要求

### 1. 安装 DashScope SDK

```bash
pip install dashscope
```

### 2. 获取 API Key

1. 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 创建 API Key
3. 设置环境变量：

```bash
export DASHSCOPE_API_KEY=your-api-key-here
```

## 测试脚本

### 快速测试 (推荐)

最简单的测试方式，验证基本功能：

```bash
python tests/quick_test_dashscope.py
```

**测试内容：**
- 模块导入
- 客户端初始化
- 基础文本生成
- 配置系统集成

**预期输出：**
```
============================================================
DashScope 快速测试
============================================================
✓ API Key: sk-xxxxx...xxxx
✓ 模块导入成功
✓ DashScope 客户端初始化成功
测试文本生成...
✓ 生成成功!
  提示词: 请用一句话介绍阿里云。
  响应: 阿里云是阿里巴巴集团旗下的云计算服务平台...
✓ 配置系统集成成功
============================================================
✓ 所有快速测试通过！
============================================================
```

### 完整测试

更全面的测试，包含多种场景：

```bash
# 基础测试
python tests/test_dashscope_client.py

# 包含多模态测试（需要提供测试文件）
python tests/test_dashscope_client.py --test-file path/to/test.pdf

# 指定 API Key（不使用环境变量）
python tests/test_dashscope_client.py --api-key your-api-key
```

**测试内容：**
1. 基础文本生成
2. JSON 格式输出
3. 多模态文件处理（可选）
4. 错误处理
5. 速率限制

**预期输出：**
```
============================================================
DashScope 客户端测试
============================================================
✓ API Key: sk-xxxxx...xxxx
✓ DashScope 客户端初始化成功

============================================================
1. 基础功能测试
============================================================
[TEST] 测试基础文本生成...
✓ 基础文本生成成功
  提示词: 请用一句话介绍人工智能。
  响应: 人工智能是计算机科学的一个分支...

============================================================
2. JSON输出测试
============================================================
[TEST] 测试JSON格式输出...
✓ JSON格式输出成功
✓ JSON解析成功: {'sentiment': 'positive', ...}

...

============================================================
测试总结
============================================================
总测试数: 5
通过: 5
失败: 0

✓ 所有测试通过！
```

## 配置使用

### 在配置文件中使用 DashScope

编辑 `config/model_config.yaml`，取消注释 DashScope 配置：

```yaml
tasks:
  # 使用 DashScope 进行视频摘要
  video_summary:
    provider: dashscope
    model_name: qwen-max
    api_key_env: DASHSCOPE_API_KEY
    
    generation:
      temperature: 0.7
      top_p: 0.9
      max_output_tokens: 8000
    
    rate_limit:
      interval: 0.5
      max_retries: 3
```

### 在代码中使用

```python
from reinvent_insight.model_config import get_model_client

# 获取 DashScope 客户端
client = get_model_client("video_summary")

# 文本生成
result = await client.generate_content("你的提示词")

# 多模态生成
file_info = await client.upload_file("path/to/file.pdf")
result = await client.generate_content_with_file("分析这个文档", file_info)
```

## 支持的模型

### 文本模型
- `qwen-turbo`: 最快，适合简单任务
- `qwen-plus`: 平衡性能和质量
- `qwen-max`: 最强大，适合复杂任务
- `qwen-max-longcontext`: 支持超长上下文

### 多模态模型
- `qwen-vl-plus`: 支持图片和文档分析
- `qwen-vl-max`: 最强多模态能力

## 常见问题

### 1. ImportError: No module named 'dashscope'

**解决方案：**
```bash
pip install dashscope
```

### 2. Invalid API-key

**解决方案：**
- 检查 API Key 是否正确
- 确认环境变量已设置：`echo $DASHSCOPE_API_KEY`
- 验证 API Key 在控制台中是否有效

### 3. 速率限制错误

**解决方案：**
- 增加 `rate_limit.interval` 配置
- 减少并发请求数量
- 升级 API 配额

### 4. 多模态测试失败

**原因：**
- 文件格式不支持
- 文件过大
- 使用了非多模态模型

**解决方案：**
- 使用 `qwen-vl-plus` 或 `qwen-vl-max` 模型
- 确保文件格式为 PDF、图片等支持的格式
- 检查文件大小限制

## 性能对比

| 模型 | 速度 | 质量 | 成本 | 适用场景 |
|------|------|------|------|----------|
| qwen-turbo | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 简单任务、快速响应 |
| qwen-plus | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 通用任务 |
| qwen-max | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 复杂任务、高质量要求 |
| qwen-vl-plus | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 多模态分析 |
| qwen-vl-max | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 复杂多模态任务 |

## 参考资料

- [DashScope 官方文档](https://help.aliyun.com/zh/dashscope/)
- [DashScope Python SDK](https://github.com/dashscope/dashscope-sdk-python)
- [通义千问 API 文档](https://help.aliyun.com/zh/dashscope/developer-reference/api-details)
- [模型定价](https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-thousand-questions-metering-and-billing)

## 技术支持

如遇到问题，请：
1. 查看测试脚本的详细错误信息
2. 检查 DashScope 控制台的 API 调用日志
3. 参考官方文档
4. 提交 Issue 到项目仓库
