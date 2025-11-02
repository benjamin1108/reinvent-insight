# Implementation Plan

- [x] 1. 增强 connectWebSocket 函数添加自动重连
  - 在 app.js 中添加重连相关状态变量（connectionState, reconnectAttempts等）
  - 实现 getReconnectDelay 函数计算指数退避延迟
  - 修改 ws.onclose 处理器添加自动重连逻辑
  - 修改 ws.onopen 处理器重置重连计数和显示恢复提示
  - 实现 manualReconnect 函数支持手动重连
  - 在 connectWebSocket 中保存 currentTaskId 供重连使用
  - 清理 reconnectTimer 避免内存泄漏
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. 创建 ConnectionStatus 组件
  - [x] 2.1 创建组件文件结构
    - 创建 web/components/common/ConnectionStatus 目录
    - 创建 ConnectionStatus.js 文件
    - 创建 ConnectionStatus.html 文件
    - 创建 ConnectionStatus.css 文件
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 2.2 实现组件逻辑
    - 定义 props（connectionState, reconnectAttempt, maxAttempts）
    - 实现 statusText 计算属性显示连接状态文本
    - 实现 showReconnectBtn 计算属性控制按钮显示
    - 定义 manual-reconnect 事件
    - _Requirements: 5.1, 5.2, 5.4_

  - [x] 2.3 实现组件样式
    - 实现基础容器样式
    - 实现 reconnecting 状态样式（黄色背景）
    - 实现 disconnected 状态样式（红色背景）
    - 实现手动重连按钮样式
    - _Requirements: 5.5_

- [x] 3. 集成 ConnectionStatus 到 CreateView
  - 在 CreateView.html 中添加 ConnectionStatus 组件
  - 传递 connectionState, reconnectAttempt 等 props
  - 监听 manual-reconnect 事件并调用 manualReconnect 函数
  - 在 app.js 的 return 中导出 connectionState 和 reconnectAttempt
  - 在 CreateView 的 props 中接收连接状态相关数据
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 4. 注册 ConnectionStatus 组件
  - 在 app.js 的组件注册列表中添加 ConnectionStatus
  - 确保组件在应用启动时正确加载
  - _Requirements: 5.1_

- [x] 5. 测试和验证
  - [x] 5.1 测试自动重连功能
    - 启动任务后断开网络
    - 验证自动重连触发
    - 验证指数退避延迟
    - 验证重连成功后状态恢复
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 3.2_

  - [x] 5.2 测试重连次数限制
    - 模拟连续5次重连失败
    - 验证停止自动重连
    - 验证显示手动重连按钮
    - 验证手动重连功能
    - _Requirements: 1.3, 5.4_

  - [x] 5.3 测试页面刷新恢复
    - 启动任务
    - 刷新页面
    - 验证任务状态恢复
    - 验证 WebSocket 重连
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 5.4 测试 UI 反馈
    - 验证连接状态文本显示正确
    - 验证重连倒计时显示
    - 验证手动重连按钮出现时机
    - 验证样式切换正确
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 5.5 测试边缘情况
    - 任务完成时断开连接（不应重连）
    - 用户主动停止任务（不应重连）
    - 快速多次断开重连
    - 长时间运行任务的稳定性
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
