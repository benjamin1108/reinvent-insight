# YouTube URL Robustness 测试文档

## 概述

本文档描述了 YouTube URL 健壮性功能的测试覆盖情况。

## 测试文件

### 1. test_url_normalization.py

测试 YouTube URL 标准化功能，确保系统能够正确处理各种 URL 格式。

**测试覆盖：**
- ✅ 标准格式 URL (`youtube.com/watch?v=VIDEO_ID`)
- ✅ 带时间戳的 URL (`&t=2209s`)
- ✅ 带播放列表的 URL (`&list=PLAYLIST_ID`)
- ✅ 短链接格式 (`youtu.be/VIDEO_ID`)
- ✅ 带分享参数的短链接 (`?si=SHARE_ID`)
- ✅ 嵌入式格式 (`youtube.com/embed/VIDEO_ID`)
- ✅ 移动端格式 (`m.youtube.com`)
- ✅ 不带协议的 URL
- ✅ 带多个参数的 URL
- ✅ 无效 URL 处理（空、None、无视频 ID、错误域名）
- ✅ 视频 ID 格式验证
- ✅ 大小写不敏感的域名处理

**测试数量：** 15 个测试用例

### 2. test_error_classification.py

测试下载错误分类功能，确保系统能够准确识别和分类各种错误类型。

**测试覆盖：**
- ✅ 403 Forbidden 错误
- ✅ 网络超时错误
- ✅ 429 限流错误
- ✅ 视频不存在错误
- ✅ 无字幕错误
- ✅ 工具缺失错误
- ✅ 未知错误
- ✅ 错误对象序列化（to_dict）
- ✅ 连接重置错误
- ✅ 私密视频错误
- ✅ 技术细节截断
- ✅ 大小写不敏感的错误匹配

**测试数量：** 12 个测试用例

### 3. test_retry_strategy.py

测试智能重试策略，确保系统能够根据错误类型采用合适的重试策略。

**测试覆盖：**
- ✅ 默认配置
- ✅ 自定义配置
- ✅ 网络超时应该重试
- ✅ 无字幕不应该重试
- ✅ 视频不存在不应该重试
- ✅ 工具缺失不应该重试
- ✅ 无效 URL 不应该重试
- ✅ 指数退避延迟计算
- ✅ 403 错误的递增延迟
- ✅ 限流错误的固定延迟
- ✅ 自定义重试延迟
- ✅ 最大延迟限制
- ✅ 不可重试错误集合

**测试数量：** 13 个测试用例

## 运行测试

### 运行所有测试

```bash
source .venv/bin/activate
python -m pytest tests/test_url_normalization.py tests/test_error_classification.py tests/test_retry_strategy.py -v
```

### 运行单个测试文件

```bash
# URL 标准化测试
python -m pytest tests/test_url_normalization.py -v

# 错误分类测试
python -m pytest tests/test_error_classification.py -v

# 重试策略测试
python -m pytest tests/test_retry_strategy.py -v
```

### 运行特定测试

```bash
python -m pytest tests/test_url_normalization.py::TestURLNormalization::test_standard_format -v
```

## 测试结果

**总计：** 40 个测试用例
**通过：** 40 个 ✅
**失败：** 0 个
**覆盖率：** 100%

## 测试策略

### URL 标准化测试
- 使用真实的 YouTube URL 格式进行测试
- 验证标准化后的 URL 格式正确
- 验证元数据提取的准确性
- 测试边界情况和错误处理

### 错误分类测试
- 模拟真实的 yt-dlp 错误输出
- 验证错误类型识别的准确性
- 检查建议操作的合理性
- 测试技术细节的提取和格式化

### 重试策略测试
- 测试不同错误类型的重试决策
- 验证延迟时间计算的正确性
- 测试重试次数限制
- 验证不可重试错误的处理

## 未来改进

1. 添加集成测试，使用真实的 YouTube URL 进行端到端测试
2. 添加性能测试，验证大量 URL 处理的性能
3. 添加并发测试，验证多线程环境下的行为
4. 添加 mock 测试，模拟 yt-dlp 的各种响应
