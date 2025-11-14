# 需求文档

## 简介

本功能旨在增强 YouTube 字幕下载系统的健壮性，使其能够兼容各种 YouTube URL 格式，并在前端透明地展示下载失败的详细原因，帮助用户理解问题并采取相应措施。

## 术语表

- **System**: YouTube 字幕下载系统
- **URL Normalization**: URL 标准化，将各种格式的 YouTube 链接转换为统一格式的过程
- **Error Context**: 错误上下文，包含错误类型、原因、建议操作等详细信息
- **Frontend**: 前端界面，用户与系统交互的 Web 界面
- **Backend**: 后端服务，处理字幕下载和错误处理的服务端
- **yt-dlp**: 用于下载 YouTube 视频和字幕的命令行工具
- **WebSocket**: 用于实时通信的协议，在本系统中用于推送任务状态更新

## 需求

### 需求 1: URL 格式兼容性

**用户故事:** 作为用户，我希望系统能够识别和处理各种 YouTube URL 格式，这样我就可以直接粘贴任何形式的 YouTube 链接而无需手动修改。

#### 验收标准

1. WHEN 用户提交包含时间戳参数的 YouTube URL（如 `&t=2209s`），THEN THE System SHALL 正确提取视频 ID 并移除时间戳参数
2. WHEN 用户提交包含播放列表参数的 YouTube URL（如 `&list=...`），THEN THE System SHALL 正确提取视频 ID 并移除播放列表参数
3. WHEN 用户提交包含分享参数的 YouTube URL（如 `?si=...`），THEN THE System SHALL 正确提取视频 ID 并移除分享参数
4. WHEN 用户提交嵌入式 YouTube URL（如 `youtube.com/embed/VIDEO_ID`），THEN THE System SHALL 正确提取视频 ID 并转换为标准格式
5. WHEN 用户提交移动端 YouTube URL（如 `m.youtube.com`），THEN THE System SHALL 正确识别并转换为标准格式

### 需求 2: 错误信息透明化

**用户故事:** 作为用户，当字幕下载失败时，我希望看到清晰的错误原因和建议操作，这样我就能理解问题所在并知道如何解决。

#### 验收标准

1. WHEN 字幕下载因网络超时失败，THEN THE System SHALL 向前端发送包含"网络超时"错误类型和重试建议的错误消息
2. WHEN 字幕下载因 403 错误失败，THEN THE System SHALL 向前端发送包含"访问被拒绝"错误类型和 Cookie 更新建议的错误消息
3. WHEN 字幕下载因视频无字幕失败，THEN THE System SHALL 向前端发送包含"字幕不可用"错误类型的明确消息
4. WHEN 字幕下载因 yt-dlp 工具未安装失败，THEN THE System SHALL 向前端发送包含"工具缺失"错误类型和安装指引的错误消息
5. WHEN 字幕下载因视频 ID 无效失败，THEN THE System SHALL 向前端发送包含"无效 URL"错误类型和格式示例的错误消息

### 需求 3: 前端错误展示

**用户故事:** 作为用户，我希望在前端界面上看到格式化的错误信息，这样我就能快速理解问题并采取行动。

#### 验收标准

1. WHEN 前端接收到错误消息，THEN THE Frontend SHALL 在任务卡片中显示错误类型标题
2. WHEN 前端接收到错误消息，THEN THE Frontend SHALL 在任务卡片中显示详细错误原因
3. WHEN 前端接收到包含建议操作的错误消息，THEN THE Frontend SHALL 在任务卡片中显示可操作的建议列表
4. WHEN 前端接收到错误消息，THEN THE Frontend SHALL 使用不同的视觉样式（如红色警告框）区分错误状态和正常状态
5. WHERE 错误消息包含技术细节，THE Frontend SHALL 提供展开/折叠功能以显示或隐藏技术细节

### 需求 4: 下载重试机制增强

**用户故事:** 作为系统，当遇到临时性错误时，我希望能够智能地重试下载，这样就能提高下载成功率并减少用户干预。

#### 验收标准

1. WHEN 字幕下载遇到网络超时错误，THEN THE System SHALL 使用指数退避策略重试最多 3 次
2. WHEN 字幕下载遇到 403 错误，THEN THE System SHALL 在重试前等待递增的时间间隔（5秒、10秒、15秒）
3. WHEN 字幕下载遇到 429 限流错误，THEN THE System SHALL 等待 30 秒后重试
4. WHEN 字幕下载遇到不可恢复的错误（如视频不存在），THEN THE System SHALL 立即停止重试并返回错误
5. WHEN 所有重试尝试都失败，THEN THE System SHALL 记录完整的错误历史并返回最后一次错误的详细信息

### 需求 5: 日志和监控

**用户故事:** 作为开发者，我希望系统能够记录详细的下载日志，这样我就能分析失败原因并优化系统。

#### 验收标准

1. WHEN 系统开始处理 URL，THEN THE System SHALL 记录原始 URL 和标准化后的 URL
2. WHEN 系统执行 yt-dlp 命令，THEN THE System SHALL 记录完整的命令参数和执行时间
3. WHEN 下载失败，THEN THE System SHALL 记录 yt-dlp 的标准输出和错误输出
4. WHEN 下载重试，THEN THE System SHALL 记录重试次数、等待时间和重试原因
5. WHEN 下载成功或最终失败，THEN THE System SHALL 记录总耗时和最终状态
