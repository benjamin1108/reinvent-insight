# 实现计划

- [x] 1. 增强 URL 标准化功能
  - 扩展 `normalize_youtube_url` 函数以支持所有常见的 YouTube URL 格式
  - 实现多个正则表达式模式按优先级匹配（嵌入式、短链接、标准格式）
  - 提取并返回 URL 元数据（video_id、timestamp、playlist_id 等）
  - 添加 URL 验证逻辑，对无效 URL 抛出 ValueError
  - _需求: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. 实现结构化错误处理
  - [x] 2.1 创建错误类型定义
    - 在 `downloader.py` 中定义 `DownloadErrorType` 枚举类
    - 创建 `DownloadError` 数据类，包含 error_type、message、technical_details、suggestions、retry_after 字段
    - 实现 `to_dict()` 方法用于 JSON 序列化
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.2 实现错误分类逻辑
    - 创建 `classify_download_error` 函数
    - 实现基于 stderr 内容的错误类型识别（403、timeout、no subtitles 等）
    - 为每种错误类型生成相应的建议操作列表
    - 提取并格式化技术细节信息
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. 实现智能重试机制
  - [x] 3.1 创建重试策略类
    - 定义 `RetryConfig` 数据类，包含 max_attempts、base_delay、max_delay 等配置
    - 实现 `RetryStrategy` 类
    - 实现 `should_retry` 方法判断是否应该重试
    - 实现 `get_delay` 方法计算重试延迟时间
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.2 集成重试逻辑到下载器
    - 修改 `SubtitleDownloader` 类，添加 `retry_strategy` 和 `error_history` 属性
    - 重构 `_download_subtitles_with_retry` 方法使用新的重试策略
    - 实现针对不同错误类型的重试逻辑（指数退避、递增延迟、固定延迟）
    - 记录每次重试的错误历史
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4. 更新 Worker 层错误传播
  - 修改 `worker.py` 中的 `summary_task_worker_async` 函数
  - 捕获 `DownloadError` 对象并通过 TaskManager 传播
  - 使用 `manager.set_task_error` 发送结构化错误信息
  - 确保错误信息包含所有必要字段（error_type、message、suggestions 等）
  - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. 增强 TaskManager 错误处理
  - 修改 `task_manager.py` 中的 `set_task_error` 方法
  - 支持接收结构化的错误对象（字典或 DownloadError 实例）
  - 序列化错误信息为 JSON 格式
  - 通过 WebSocket/SSE 发送完整的错误上下文
  - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6. 实现前端错误展示组件
  - [x] 6.1 创建错误类型映射
    - 在 `app.js` 中定义错误类型到图标、颜色、标题的映射
    - 实现 `getErrorIcon` 和 `getErrorColor` 辅助函数
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 6.2 增强错误消息处理
    - 修改 WebSocket 消息处理逻辑，识别结构化的错误消息
    - 解析 error_type、message、technical_details、suggestions 字段
    - 存储错误信息到响应式状态
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 6.3 更新 UI 展示错误信息
    - 修改任务卡片模板，添加错误类型标题和图标
    - 显示详细错误原因和建议操作列表
    - 实现技术细节的展开/折叠功能
    - 使用不同的视觉样式区分错误状态（红色警告框）
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 7. 增强日志记录
  - 在 `downloader.py` 中添加结构化日志
  - 记录原始 URL 和标准化后的 URL
  - 记录完整的 yt-dlp 命令参数和执行时间
  - 记录重试次数、等待时间和重试原因
  - 记录最终状态（成功/失败）和总耗时
  - _需求: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. 编写测试
  - [x] 8.1 URL 标准化测试
    - 测试所有支持的 URL 格式（标准、时间戳、播放列表、短链接、嵌入式、移动端）
    - 测试无效 URL 的处理
    - 测试边界情况（特殊字符、超长 URL）
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 8.2 错误分类测试
    - 模拟各种 yt-dlp 错误输出（403、timeout、no subtitles 等）
    - 验证错误类型分类的准确性
    - 测试建议操作的生成
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 8.3 重试策略测试
    - 测试不同错误类型的重试行为
    - 验证延迟时间计算（指数退避、递增延迟）
    - 测试最大重试次数限制
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 9. 集成和验证
  - 使用真实的 YouTube URL 进行端到端测试
  - 验证带时间戳的 URL 能正确下载
  - 验证无字幕视频的错误提示
  - 验证网络超时的处理和重试
  - 验证前端能正确展示所有类型的错误信息
  - _需求: 1.1, 2.1, 3.1, 4.1, 5.1_
