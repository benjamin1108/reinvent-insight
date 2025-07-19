# 自适应内容长度功能使用指南

## 概述

自适应内容长度功能已成功集成到系统中，能够根据视频特征自动调整生成文章的长度和章节数量。

## 功能特性

### 🎯 智能长度计算
- **短视频**（<20分钟）：生成 12k-18k 字文章，8-12 个章节
- **中等视频**（20-60分钟）：生成 20k-30k 字文章，12-16 个章节  
- **长视频**（60-120分钟）：生成 30k-45k 字文章，16-20 个章节
- **超长视频**（>120分钟）：生成 40k-60k 字文章，20-25 个章节

### 📊 视频特征分析
- 自动分析视频时长和信息密度
- 根据语速调整内容详细程度
- 评估内容复杂度并相应调整

### 🔄 实时长度监控
- 章节级别的长度跟踪
- 动态调整建议
- 进度预测和偏差检测

## 使用方法

### 1. 命令行使用（默认启用）

```bash
# 处理单个视频（自动启用自适应功能）
python -m reinvent_insight.main --url "https://www.youtube.com/watch?v=VIDEO_ID"

# 批量处理
python -m reinvent_insight.main --file video_urls.txt
```

### 2. Web API 使用

```bash
# 启动 Web 服务
python -m reinvent_insight.main web --host 0.0.0.0 --port 8001
```

API 请求示例：
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "length_config": {
    "enable_adaptive": true,
    "target_length": null,
    "detail_level": "适度"
  }
}
```

### 3. 配置调整

编辑 `config/length_config.yaml` 文件来调整参数：

```yaml
# 基础长度比例
base_ratios:
  short: 0.7      # 短视频：70%
  medium: 0.8     # 中等视频：80%
  long: 0.9       # 长视频：90%
  extra_long: 1.0 # 超长视频：100%

# 信息密度调整系数
density_multipliers:
  low: 1.2    # 低密度：增加20%
  medium: 1.0 # 中密度：保持不变
  high: 0.8   # 高密度：减少20%

# 章节数量范围
chapter_ranges:
  short: [8, 12]      # 短视频：8-12章节
  medium: [12, 16]    # 中等视频：12-16章节
  long: [16, 20]      # 长视频：16-20章节
  extra_long: [20, 25] # 超长视频：20-25章节
```

## 日志和监控

### 查看自适应分析日志
系统会自动记录以下信息：
- 视频特征分析结果
- 长度目标计算过程
- 章节生成进度监控
- 长度偏差和调整建议

### 监控文件位置
- 长度监控数据：`logs/length_monitoring/`
- 性能指标：`logs/length_metrics/`
- 调整记录：`logs/length_adjustments/`

## 故障排除

### 常见问题

**Q: 生成的文章长度不符合预期？**
A: 检查配置文件中的参数设置，特别是 `base_ratios` 和 `density_multipliers`。

**Q: 章节数量不合适？**
A: 调整 `chapter_ranges` 配置中对应视频类型的范围。

**Q: 如何禁用自适应功能？**
A: 在 API 请求中设置 `"enable_adaptive": false`，或修改代码中的默认配置。

### 调试模式
启用详细日志：
```bash
export LOG_LEVEL=DEBUG
python -m reinvent_insight.main --url "VIDEO_URL"
```

## 性能优化建议

1. **配置调优**：根据实际使用情况调整配置参数
2. **监控指标**：定期检查 `logs/length_metrics/health.json` 中的系统健康指标
3. **错误处理**：系统具有完善的降级机制，即使分析失败也能正常工作

## 技术细节

### 核心组件
- `VideoAnalyzer`：视频特征分析
- `LengthCalculator`：长度目标计算
- `LengthMonitor`：实时长度监控
- `DynamicPromptGenerator`：动态提示词生成

### 集成点
- `AdaptiveDeepSummaryWorkflow`：自适应工作流
- `main.py`：命令行入口（默认启用）
- `api.py`：Web API 接口
- `worker.py`：后台任务处理

## 更新日志

### v1.0.0 (2024-07-19)
- ✅ 完成核心自适应组件开发
- ✅ 集成到现有工作流系统
- ✅ 添加完善的错误处理和监控
- ✅ 支持配置文件热重载
- ✅ 提供详细的使用文档

---

如有问题或建议，请查看项目文档或提交 Issue。