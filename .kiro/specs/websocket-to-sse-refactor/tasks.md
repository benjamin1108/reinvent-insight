# Implementation Plan

- [x] 1. 重构 TaskManager 以支持 SSE 消息队列
  - 在 TaskState 数据类中添加 message_queue 字段（asyncio.Queue 类型）
  - 实现 register_sse_connection() 方法，创建并返回消息队列
  - 实现 unregister_sse_connection() 方法，清理队列资源
  - 重构 send_message() 方法，将消息推送到队列而不是 WebSocket
  - 重构 update_progress() 方法，将进度更新推送到队列
  - 重构 send_result() 方法，将结果推送到队列
  - 重构 set_task_error() 方法，将错误推送到队列
  - 移除 connect() 方法（WebSocket 连接管理）
  - 移除 disconnect() 方法（WebSocket 断开管理）
  - 移除 send_history() 方法（SSE 不需要历史消息）
  - _Requirements: 1.2, 1.3, 5.3, 7.2, 7.4_

- [x] 2. 实现 SSE 端点
  - [x] 2.1 创建 SSE 流式响应生成器
    - 实现 async generator 函数 generate_sse_stream()
    - 从 TaskManager 获取消息队列
    - 循环读取队列消息并格式化为 SSE 格式
    - 处理队列为空时的等待逻辑（使用 asyncio.wait_for 设置超时）
    - 处理客户端断开连接的情况（检测 Request.is_disconnected）
    - 在连接关闭时清理队列资源
    - _Requirements: 1.1, 1.2, 5.4, 7.1, 7.3_
  
  - [x] 2.2 添加 SSE API 路由
    - 在 api.py 中添加 GET /api/tasks/{task_id}/stream 端点
    - 验证 task_id 是否存在，不存在返回 404
    - 调用 TaskManager.register_sse_connection() 获取消息队列
    - 返回 StreamingResponse，content_type 设置为 text/event-stream
    - 设置必要的 HTTP 头（Cache-Control, X-Accel-Buffering 等）
    - 添加认证验证（Bearer Token）
    - _Requirements: 1.1, 5.3, 7.1_

- [x] 3. 实现前端 SSE 连接管理
  - [x] 3.1 创建 SSE 连接函数
    - 在 app.js 中实现 connectSSE(taskId, isReconnect) 函数
    - 使用 EventSource API 创建 SSE 连接
    - 保存 EventSource 实例到 currentEventSource ref
    - 设置连接状态为 connecting 或 reconnecting
    - 清理之前的重连定时器
    - _Requirements: 1.1, 2.1, 4.2_
  
  - [x] 3.2 实现 SSE 事件处理
    - 实现 onopen 事件处理器，更新连接状态为 connected
    - 实现 onmessage 事件处理器，解析 JSON 消息
    - 根据消息类型（log, progress, result, error）分别处理
    - 实现 onerror 事件处理器，触发重连逻辑
    - 在任务完成或错误时关闭 EventSource 连接
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [x] 3.3 实现自动重连机制
    - 实现 getReconnectDelay(attempt) 函数，使用指数退避算法
    - 在 onerror 中检查是否需要重连（任务进行中且未超过最大次数）
    - 更新重连尝试次数和连接状态
    - 显示重连倒计时消息
    - 设置定时器延迟后重新调用 connectSSE
    - 超过最大重连次数时显示错误提示
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.3_
  
  - [x] 3.4 实现手动重连功能
    - 实现 manualReconnect() 函数
    - 重置重连尝试次数
    - 调用 connectSSE 重新建立连接
    - 在连接状态组件中绑定手动重连按钮
    - _Requirements: 2.4, 4.4_

- [x] 4. 更新任务提交流程
  - 修改 startSummarize() 函数，在获取 task_id 后调用 connectSSE
  - 移除 connectWebSocket 调用
  - 保持其他逻辑不变（文件上传、进度显示等）
  - _Requirements: 1.1, 5.1_

- [x] 5. 实现任务恢复功能
  - 修改 restoreTask() 函数，使用 connectSSE 替代 connectWebSocket
  - 从 localStorage 读取 active_task_id
  - 验证任务是否仍在进行中
  - 自动建立 SSE 连接恢复任务状态
  - _Requirements: 5.1, 5.2, 5.5_

- [x] 6. 更新连接状态显示
  - 确保 ConnectionStatus 组件正确显示 SSE 连接状态
  - 显示重连倒计时和尝试次数
  - 在连接失败时显示手动重连按钮
  - 测试各种连接状态的 UI 显示
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 7. 移除 WebSocket 相关代码
  - [x] 7.1 移除后端 WebSocket 代码
    - 删除 api.py 中的 /ws/{task_id} 端点
    - 从 TaskManager 移除 websocket 字段
    - 移除 WebSocket 相关的导入语句
    - _Requirements: 3.1, 3.2_
  
  - [x] 7.2 移除前端 WebSocket 代码
    - 删除 connectWebSocket() 函数
    - 删除 WebSocket 心跳机制代码
    - 删除 currentWs ref
    - 移除 WebSocket 相关的状态管理
    - _Requirements: 3.3, 3.4, 3.5_

- [x] 8. 添加错误处理和资源清理
  - 在 SSE 生成器中添加 try-finally 块确保资源清理
  - 在前端添加 EventSource 清理逻辑（组件卸载时）
  - 处理任务不存在的情况（返回 404）
  - 处理认证失败的情况（返回 401）
  - 添加消息队列大小限制（防止内存溢出）
  - _Requirements: 7.3, 7.4_

- [x] 9. 修复 SSE 认证问题（EventSource 不支持自定义 Header）
  - [x] 9.1 更新后端 SSE 端点以支持查询参数认证
    - 修改 stream_task_updates() 函数，添加 token 查询参数
    - 更新认证逻辑，优先使用查询参数中的 token，其次使用 Header
    - 保持向后兼容性（同时支持 Header 和查询参数）
    - _Requirements: 1.1_
  
  - [x] 9.2 更新前端 SSE 连接以传递认证 token
    - 修改 connectSSE() 函数，在 URL 中添加 token 查询参数
    - 从 localStorage 读取 authToken
    - 构建包含 token 的 SSE URL: `/api/tasks/${taskId}/stream?token=${token}`
    - _Requirements: 1.1_

- [ ] 10. 测试和验证
  - [ ]* 10.1 后端单元测试
    - 测试 TaskManager 的消息队列管理
    - 测试 SSE 消息格式化
    - 测试错误处理逻辑
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ]* 10.2 前端单元测试
    - 测试 SSE 连接管理逻辑
    - 测试消息处理函数
    - 测试重连算法
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ]* 10.3 集成测试
    - 测试完整的任务提交和执行流程
    - 测试连接断开和重连场景
    - 测试页面刷新后的任务恢复
    - 测试多个并发任务
    - _Requirements: 5.1, 5.2, 5.5, 7.1, 7.2_
  
  - [ ]* 10.4 手动测试
    - 测试网络断开场景（关闭 WiFi）
    - 测试服务器重启场景
    - 测试长时间运行的任务
    - 测试多标签页同时使用
    - _Requirements: 2.1, 2.2, 2.3, 4.1, 4.2, 4.3_

- [ ] 11. 更新文档
  - [ ]* 11.1 更新 API 文档
    - 记录新的 SSE 端点
    - 记录消息格式
    - 记录错误码
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ]* 11.2 更新开发文档
    - 更新架构图
    - 更新部署说明
    - 添加故障排查指南
    - _Requirements: 所有需求_
