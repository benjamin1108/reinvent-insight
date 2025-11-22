# Implementation Plan

## Overview

本实现计划将文本转语音播放器功能分解为可执行的任务。每个任务都是独立的、可测试的代码单元，按照依赖关系组织，确保增量开发和持续集成。

## Task List

- [x] 1. 配置统一模型框架支持 TTS
  - 在 `config/model_config.yaml` 添加 `text_to_speech` 任务配置
  - 配置 DashScope provider 和 qwen3-tts-flash 模型
  - 设置 TTS 特定参数（音色、采样率、缓存设置）
  - _Requirements: 11.1, 11.2, 11.4_

- [x] 2. 扩展 DashScope 客户端支持 TTS API
- [x] 2.1 实现 TTS 流式生成方法
  - 在 `DashScopeClient` 类添加 `generate_tts_stream()` 方法
  - 实现 SSE 连接到 Qwen3-TTS API
  - 处理 Base64 编码的 PCM 音频块
  - 实现错误处理和重试逻辑
  - _Requirements: 1.1, 3.1, 9.3_

- [x] 2.2 实现 TTS 完整生成方法
  - 在 `DashScopeClient` 类添加 `generate_tts()` 方法
  - 实现非流式音频生成
  - 返回完整的音频数据
  - _Requirements: 1.1_

- [ ]* 2.3 编写 DashScope TTS 客户端单元测试
  - 测试流式生成方法
  - 测试完整生成方法
  - 测试错误处理
  - 使用 mock 模拟 API 响应
  - _Requirements: 1.1, 3.1, 9.3_

- [x] 3. 实现文本预处理服务
- [x] 3.1 创建 TTSService 类
  - 创建 `src/reinvent_insight/services/tts_service.py`
  - 实现 `preprocess_text()` 方法
  - 去除 HTML 标签、Markdown 格式、代码块
  - 规范化空白字符
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 3.2 实现文本分块逻辑
  - 实现 `chunk_text()` 方法
  - 按句子边界分割长文本
  - 确保每块不超过 600 字符
  - _Requirements: 7.5_

- [x] 3.3 实现哈希计算
  - 实现 `calculate_hash()` 方法
  - 基于文本、音色、语言计算 SHA256 哈希
  - 用于缓存键生成
  - _Requirements: 4.1_

- [ ]* 3.4 编写文本预处理属性测试
  - **Property 20: Markdown stripping completeness**
  - **Validates: Requirements 7.1**
  - 使用 Hypothesis 生成随机 Markdown 文本
  - 验证预处理后无 Markdown 语法字符
  - _Requirements: 7.1_

- [ ]* 3.5 编写 HTML 标签移除属性测试
  - **Property 21: HTML tag removal**
  - **Validates: Requirements 7.2**
  - 使用 Hypothesis 生成随机 HTML 文本
  - 验证预处理后无 HTML 标签
  - _Requirements: 7.2_


- [ ]* 3.6 编写文本分块属性测试
  - **Property 24: Text chunking for long content**
  - **Validates: Requirements 7.5**
  - 使用 Hypothesis 生成超长文本
  - 验证所有块 ≤ 600 字符
  - 验证拼接后等于原文本
  - _Requirements: 7.5_

- [x] 4. 实现音频缓存系统
- [x] 4.1 创建 AudioCache 类
  - 创建 `src/reinvent_insight/services/audio_cache.py`
  - 实现 `__init__()` 初始化缓存目录
  - 实现 `get()` 方法查找缓存
  - 实现 `put()` 方法存储音频
  - 实现 `invalidate()` 方法删除缓存
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 4.2 实现 LRU 缓存淘汰
  - 实现 `evict_lru()` 方法
  - 按 last_accessed 时间排序
  - 删除最旧文件直到空间足够
  - 实现 `get_cache_size()` 方法
  - _Requirements: 4.5_

- [x] 4.3 实现缓存元数据管理
  - 创建 AudioMetadata 数据类
  - 实现元数据持久化（JSON 文件）
  - 跟踪访问时间和访问次数
  - _Requirements: 4.1, 4.5_

- [ ]* 4.4 编写缓存查找属性测试
  - **Property 11: Cache-first lookup**
  - **Validates: Requirements 4.2, 4.3, 9.1**
  - 生成随机音频数据
  - 验证缓存总是在 API 调用前检查
  - _Requirements: 4.2, 4.3, 9.1_

- [ ]* 4.5 编写 LRU 淘汰属性测试
  - **Property 13: LRU cache eviction**
  - **Validates: Requirements 4.5**
  - 填充缓存超过限制
  - 验证最旧文件被删除
  - _Requirements: 4.5_

- [x] 5. 实现 WAV 文件组装
- [x] 5.1 创建音频工具模块
  - 创建 `src/reinvent_insight/utils/audio_utils.py`
  - 实现 `assemble_wav()` 函数
  - 拼接 PCM 块并添加 WAV 头
  - 支持 24kHz 采样率、单声道、16-bit
  - _Requirements: 3.1, 4.1_

- [x] 5.2 实现 Base64 解码
  - 实现 `decode_base64_pcm()` 函数
  - 解码 API 返回的 Base64 音频数据
  - 转换为字节数组
  - _Requirements: 3.1_

- [ ]* 5.3 编写 WAV 组装单元测试
  - 测试 WAV 头格式正确性
  - 测试 PCM 数据完整性
  - 测试文件可被音频播放器读取
  - _Requirements: 3.1, 4.1_

- [x] 6. 实现 TTS API 端点
- [x] 6.1 创建 TTS 路由
  - 创建 `src/reinvent_insight/api/tts.py`
  - 定义 POST `/api/tts/generate` 端点
  - 定义 GET `/api/tts/stream` 端点（SSE）
  - 定义 GET `/api/tts/cache/{hash}` 端点
  - _Requirements: 1.1, 3.1, 4.3_

- [x] 6.2 实现非流式生成端点
  - 实现 `/api/tts/generate` 处理逻辑
  - 检查缓存，返回 URL 或生成新音频
  - 返回 JSON 响应（audio_url, duration, cached）
  - _Requirements: 1.1, 4.2, 4.3_

- [x] 6.3 实现流式生成端点
  - 实现 `/api/tts/stream` SSE 处理逻辑
  - 检查缓存，如有则发送 cached 事件
  - 否则流式生成，发送 chunk 事件
  - 完成后发送 complete 事件并缓存
  - _Requirements: 3.1, 3.2, 3.3, 4.1_

- [x] 6.4 实现缓存文件服务端点
  - 实现 `/api/tts/cache/{hash}` 处理逻辑
  - 验证哈希值有效性
  - 返回 WAV 文件（Content-Type: audio/wav）
  - 更新缓存访问时间
  - _Requirements: 4.3_


- [ ]* 6.5 编写 API 端点单元测试
  - 测试 `/api/tts/generate` 端点
  - 测试 `/api/tts/stream` SSE 连接
  - 测试 `/api/tts/cache/{hash}` 文件服务
  - 测试错误响应（无效输入、API 错误）
  - _Requirements: 1.1, 3.1, 4.3, 8.1_

- [x] 7. 创建前端 AudioPlayer 类
- [x] 7.1 创建 AudioPlayer 模块
  - 创建 `web/utils/AudioPlayer.js`
  - 初始化 Web Audio API（AudioContext）
  - 创建音频节点（source, gain, destination）
  - _Requirements: 1.2, 2.1, 2.2_

- [x] 7.2 实现播放控制方法
  - 实现 `play()` 方法
  - 实现 `pause()` 方法
  - 实现 `stop()` 方法
  - 实现 `seek(time)` 方法
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 7.3 实现音量和速度控制
  - 实现 `setVolume(volume)` 方法
  - 实现 `setPlaybackRate(rate)` 方法
  - 使用 GainNode 控制音量
  - 使用 playbackRate 控制速度
  - _Requirements: 10.2, 10.3_

- [x] 7.4 实现进度跟踪
  - 实现 `getCurrentTime()` 方法
  - 实现 `getDuration()` 方法
  - 使用 requestAnimationFrame 更新进度
  - 触发 timeupdate 事件
  - _Requirements: 5.3_

- [ ]* 7.5 编写播放控制属性测试
  - **Property 3: Pause and resume position preservation**
  - **Validates: Requirements 2.2**
  - 使用 fast-check 生成随机暂停位置
  - 验证恢复后位置一致（误差 < 100ms）
  - _Requirements: 2.2_

- [ ]* 7.6 编写 seek 功能属性测试
  - **Property 4: Seek position accuracy**
  - **Validates: Requirements 2.3**
  - 使用 fast-check 生成随机 seek 位置
  - 验证实际位置与目标位置误差 < 100ms
  - _Requirements: 2.3_

- [ ]* 7.7 编写播放速度属性测试
  - **Property 29: Playback speed application**
  - **Validates: Requirements 10.2, 10.3**
  - 使用 fast-check 生成随机速度（0.5x-2x）
  - 验证速度立即应用且位置保持
  - _Requirements: 10.2, 10.3_

- [x] 8. 创建前端 StreamBuffer 类
- [x] 8.1 创建 StreamBuffer 模块
  - 创建 `web/utils/StreamBuffer.js`
  - 初始化缓冲区数组
  - 设置采样率和声道数
  - _Requirements: 3.1, 3.2_

- [x] 8.2 实现音频块追加
  - 实现 `appendChunk(base64Data)` 方法
  - Base64 解码为 ArrayBuffer
  - 转换为 Float32Array
  - 追加到缓冲区数组
  - _Requirements: 3.1_

- [x] 8.3 实现 AudioBuffer 创建
  - 实现 `getAudioBuffer()` 方法
  - 创建 AudioBuffer 对象
  - 填充 PCM 数据
  - 返回可播放的 AudioBuffer
  - _Requirements: 3.2, 3.3_

- [x] 8.4 实现缓冲区管理
  - 实现 `clear()` 方法
  - 实现 `getDuration()` 方法
  - 实现 `getBufferedAmount()` 方法
  - _Requirements: 3.2_

- [ ]* 8.5 编写流缓冲属性测试
  - **Property 6: Stream buffer append order**
  - **Validates: Requirements 3.1**
  - 使用 fast-check 生成随机音频块序列
  - 验证块按接收顺序追加
  - _Requirements: 3.1_

- [x] 9. 创建 AudioControlBar 组件
- [x] 9.1 创建 Vue 组件文件
  - 创建 `web/components/shared/AudioControlBar/AudioControlBar.js`
  - 创建 `web/components/shared/AudioControlBar/AudioControlBar.html`
  - 创建 `web/components/shared/AudioControlBar/AudioControlBar.css`
  - 定义组件 props 和 data
  - _Requirements: 5.1, 5.2_


- [x] 9.2 实现播放控制按钮
  - 实现播放/暂停/停止按钮
  - 绑定点击事件到 AudioPlayer 方法
  - 实现按钮状态切换（播放中/暂停/停止）
  - 添加加载状态指示器
  - _Requirements: 1.4, 1.5, 2.1, 2.2, 2.4_

- [x] 9.3 实现进度条滑块
  - 实现可拖动的进度条
  - 显示当前时间和总时长
  - 绑定拖动事件到 seek 方法
  - 实时更新进度显示
  - _Requirements: 2.3, 5.3_

- [x] 9.4 实现音色选择器
  - 创建音色下拉菜单
  - 列出 17 种 Qwen3-TTS 音色
  - 绑定选择事件
  - 保存用户偏好到 localStorage
  - _Requirements: 6.1, 6.2, 6.4_

- [x] 9.5 实现播放速度控制
  - 创建速度选择器（0.5x-2x）
  - 绑定选择事件到 setPlaybackRate
  - 显示当前速度指示器
  - 保存用户偏好到 localStorage
  - _Requirements: 10.1, 10.2, 10.5_

- [x] 9.6 实现音量控制
  - 创建音量滑块
  - 绑定滑动事件到 setVolume
  - 添加静音按钮
  - _Requirements: 2.1_

- [x] 9.7 实现错误提示
  - 创建错误消息显示区域
  - 实现友好的错误消息
  - 添加重试按钮
  - _Requirements: 8.1, 8.2_

- [x] 9.8 实现响应式布局
  - 添加移动端适配样式
  - 调整控件布局（≤768px）
  - 确保所有控件可用
  - _Requirements: 5.5_

- [ ]* 9.9 编写 UI 响应性单元测试
  - 测试按钮点击响应
  - 测试进度条拖动
  - 测试音色选择
  - 测试速度选择
  - 测试响应式布局
  - _Requirements: 5.2, 5.5_

- [x] 10. 集成 AudioControlBar 到 ReadingView
- [x] 10.1 更新 ReadingView 组件
  - 在 `ReadingView.js` 添加 AudioControlBar 依赖
  - 添加 TTS 相关状态管理
  - 传递 articleHash 和 articleText props
  - _Requirements: 5.1_

- [x] 10.2 实现控件定位
  - 将 AudioControlBar 定位在页面底部
  - 使用 sticky 定位保持可见
  - 确保不遮挡文章内容
  - _Requirements: 5.1_

- [x] 10.3 实现 SSE 连接管理
  - 创建 EventSource 连接到 `/api/tts/stream`
  - 处理 chunk、complete、cached、error 事件
  - 实现连接错误重试
  - 清理连接资源
  - _Requirements: 3.1, 3.4, 8.3_

- [x] 10.4 实现用户偏好持久化
  - 使用 localStorage 保存音色偏好
  - 使用 localStorage 保存速度偏好
  - 组件加载时恢复偏好
  - _Requirements: 6.4, 10.4_

- [ ]* 10.5 编写偏好持久化属性测试
  - **Property 17: Voice selection persistence**
  - **Validates: Requirements 6.2, 6.4**
  - 使用 fast-check 生成随机音色
  - 验证偏好跨会话保持
  - _Requirements: 6.2, 6.4_

- [ ]* 10.6 编写速度偏好属性测试
  - **Property 30: Speed preference persistence**
  - **Validates: Requirements 10.4**
  - 使用 fast-check 生成随机速度
  - 验证偏好跨会话保持
  - _Requirements: 10.4_

- [ ] 11. 实现端到端集成
- [ ] 11.1 实现完整播放流程
  - 用户点击播放 → 检查缓存 → 生成/加载音频 → 播放
  - 处理所有状态转换
  - 确保错误恢复
  - _Requirements: 1.1, 1.2, 4.2, 4.3_

- [ ] 11.2 实现音色切换流程
  - 播放中切换音色 → 停止播放 → 重新生成 → 播放
  - 清除旧缓存
  - _Requirements: 6.3, 4.4_


- [ ] 11.3 实现缓存复用流程
  - 第一次播放生成音频
  - 第二次播放使用缓存
  - 验证无重复 API 调用
  - _Requirements: 4.2, 4.3, 9.2_

- [ ]* 11.4 编写端到端集成测试
  - 测试完整播放流程
  - 测试缓存命中流程
  - 测试流式播放流程
  - 测试错误恢复流程
  - 测试音色切换流程
  - _Requirements: 1.1, 3.1, 4.2, 4.3, 6.3_

- [ ] 12. Checkpoint - 确保所有测试通过
  - 运行所有单元测试
  - 运行所有属性测试
  - 运行所有集成测试
  - 修复任何失败的测试
  - 确保代码覆盖率达标（后端 80%，前端 75%）

- [ ] 13. 性能优化和错误处理增强
- [ ] 13.1 实现 API 速率限制
  - 使用现有的 RateLimiter 类
  - 配置 0.5 秒调用间隔
  - _Requirements: 9.3_

- [ ] 13.2 实现指数退避重试
  - 在 TTSService 中实现重试逻辑
  - 使用 2^attempt 秒延迟
  - 最多重试 3 次
  - _Requirements: 9.3_

- [ ]* 13.3 编写重试逻辑属性测试
  - **Property 28: Exponential backoff retry**
  - **Validates: Requirements 9.3**
  - 模拟 API 错误
  - 验证重试延迟符合指数模式
  - _Requirements: 9.3_

- [ ] 13.4 实现网络错误恢复
  - 检测网络连接丢失
  - 尝试重新连接
  - 通知用户连接状态
  - _Requirements: 8.3_

- [ ] 13.5 优化前端性能
  - 使用 requestAnimationFrame 更新进度
  - 防抖滑块拖动事件
  - 节流音量/速度变化
  - _Requirements: 5.2, 5.3_

- [ ] 14. 文档和部署准备
- [ ] 14.1 更新 API 文档
  - 记录 TTS API 端点
  - 添加请求/响应示例
  - 记录错误代码
  - _Requirements: All_

- [ ] 14.2 创建用户指南
  - 编写使用说明
  - 添加截图
  - 记录快捷键
  - _Requirements: All_

- [ ] 14.3 配置环境变量
  - 设置 DASHSCOPE_API_KEY
  - 配置缓存目录权限
  - 验证配置加载
  - _Requirements: 11.1, 11.3_

- [ ] 14.4 创建部署检查清单
  - 验证所有依赖已安装
  - 测试 API 端点
  - 验证缓存读写
  - 测试移动端响应式
  - _Requirements: All_

- [ ] 15. Final Checkpoint - 最终验证
  - 确保所有测试通过
  - 验证所有需求已实现
  - 进行用户验收测试
  - 修复任何发现的问题
  - 准备发布

## Notes

- 标记为 `*` 的任务是可选的测试任务，可以根据时间和资源决定是否实现
- 每个任务完成后应该提交代码并运行相关测试
- Checkpoint 任务用于确保代码质量和功能完整性
- 所有属性测试应运行至少 100 次迭代
- 集成测试应覆盖所有主要用户流程
