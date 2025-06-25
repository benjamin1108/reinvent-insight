# Metadata 更新说明

## 背景
原有的文档metadata结构中，`title`字段存储的是YouTube视频的原始英文标题，但前端却将其作为中文标题使用。这导致了显示上的混乱。

## 更新内容

### 1. YAML Front Matter 结构变更
**旧格式：**
```yaml
---
title: AWS re:Invent 2024 - Build scalable, secure, global connectivity with AWS (NET311)
upload_date: '20241208'
video_url: https://www.youtube.com/watch?v=oMTwQysHtl4
is_reinvent: true
course_code: NET311
level: 300 - Advanced
---
```

**新格式：**
```yaml
---
title_en: AWS re:Invent 2024 - Build scalable, secure, global connectivity with AWS (NET311)
title_cn: 化繁为简：AWS Cloud WAN 如何重塑全球网络连接与安全范式
upload_date: '20241208'
video_url: https://www.youtube.com/watch?v=oMTwQysHtl4
is_reinvent: true
course_code: NET311
level: 300 - Advanced
---
```

### 2. API 更新
- 所有API端点现在同时返回 `title_cn` 和 `title_en` 字段
- 为了向后兼容，保留了 `title` 字段（值与 `title_cn` 相同）
- API能够处理新旧两种格式的文档

### 3. 文档生成更新
- 新生成的文档将使用新的metadata格式
- `title_en` 存储原始英文视频标题
- `title_cn` 存储AI生成的中文标题

## 使用方法

### 1. 更新现有文档
运行以下命令来批量更新所有现有文档的metadata：

```bash
# 方法一：使用shell脚本
./run_update.sh

# 方法二：直接运行Python脚本
python update_metadata.py
```

脚本会：
- 遍历 `downloads/summaries` 目录下的所有 `.md` 文件
- 将原有的 `title` 字段改为 `title_en`
- 从文档的H1标题中提取中文标题，添加为 `title_cn`
- 跳过已经更新过的文档

### 2. 测试API
运行测试脚本验证API是否正常工作：

```bash
python test_api.py
```

## 注意事项

1. **备份建议**：在运行更新脚本之前，建议先备份 `downloads/summaries` 目录
2. **API重启**：更新完成后，需要重启API服务以确保使用最新代码
3. **前端兼容**：前端代码可能需要相应更新以充分利用新的中英文标题字段

## 技术细节

### 中文标题来源优先级
1. 首先尝试从metadata中的 `title_cn` 字段获取
2. 如果没有，则查找文档中的第一个H1标题（`# 开头的行`）
3. 如果还是没有，使用英文标题作为备用
4. 最后的备选是使用文件名（去除.md扩展名）

### 兼容性处理
- API会自动检测文档格式（新格式有`title_cn`和`title_en`，旧格式只有`title`）
- 对于旧格式文档，`title`字段会被当作`title_en`处理
- 所有API响应都包含向后兼容的`title`字段 