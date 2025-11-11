# Requirements Document

## Introduction

本文档定义了将前端与后端通信方式从 WebSocket 重构为 SSE（Server-Sent Events）的需求。当前系统使用 WebSocket 进行实时通信，但经常出现连接不稳定的问题，包括频繁断线、重连失败等。SSE 是一种更简单、更可靠的服务器推送技术，特别适合单向数据流（服务器到客户端）的场景。

## Glossary

- **SSE (Server-Sent Events)**: 一种基于 HTTP 的服务器推送技术，允许服务器向客户端推送实时更新
- **WebSocket**: 一种全双工通信协议，支持客户端和服务器之间的双向实时通信
- **Frontend**: 基于 Vue.js 的前端应用，位于 web/ 目录
- **Backend**: 基于 FastAPI 的后端服务，位于 src/reinvent_insight/ 目录
- **Task Manager**: 后端任务管理器，负责管理异步任务的生命周期
- **Connection State**: 连接状态，包括 connected、disconnected、reconnecting 等
- **Progress Update**: 进度更新消息，包含任务执行进度信息
- **Log Message**: 日志消息，包含任务执行过程中的日志信息
- **Result Message**: 结果消息，包含任务完成后的结果数据

## Requirements

### Requirement 1

**User Story:** 作为系统用户，我希望在创建分析任务时能够稳定地接收服务器推送的进度更新，以便实时了解任务执行状态

#### Acceptance Criteria

1. WHEN 用户提交分析任务（YouTube URL 或文档文件），THE Frontend SHALL 建立 SSE 连接以接收任务更新
2. WHEN Backend 处理任务时，THE Backend SHALL 通过 SSE 连接向 Frontend 推送进度更新消息
3. WHEN Backend 处理任务时，THE Backend SHALL 通过 SSE 连接向 Frontend 推送日志消息
4. WHEN 任务完成时，THE Backend SHALL 通过 SSE 连接向 Frontend 推送结果消息
5. WHEN 任务失败时，THE Backend SHALL 通过 SSE 连接向 Frontend 推送错误消息

### Requirement 2

**User Story:** 作为系统用户，我希望 SSE 连接能够自动处理网络中断和重连，以便在网络波动时不会丢失任务状态

#### Acceptance Criteria

1. WHEN SSE 连接意外断开时，THE Frontend SHALL 自动尝试重新建立连接
2. WHEN Frontend 重新连接时，THE Frontend SHALL 使用相同的 task_id 恢复任务状态
3. WHEN 重连次数超过最大限制时，THE Frontend SHALL 显示错误提示并停止重连
4. WHEN 重连成功时，THE Frontend SHALL 显示连接恢复提示
5. THE Frontend SHALL 使用指数退避算法计算重连延迟时间

### Requirement 3

**User Story:** 作为系统开发者，我希望移除所有 WebSocket 相关代码，以便简化代码库并减少维护成本

#### Acceptance Criteria

1. THE Backend SHALL 移除 WebSocket 端点 `/ws/{task_id}`
2. THE Backend SHALL 移除 WebSocket 连接管理相关代码
3. THE Frontend SHALL 移除 WebSocket 连接创建和管理代码
4. THE Frontend SHALL 移除 WebSocket 心跳机制相关代码
5. THE Frontend SHALL 移除 WebSocket 重连逻辑相关代码

### Requirement 4

**User Story:** 作为系统用户，我希望能够看到清晰的连接状态指示，以便了解当前与服务器的连接情况

#### Acceptance Criteria

1. THE Frontend SHALL 显示当前连接状态（已连接、断开连接、重连中）
2. WHEN 连接状态变化时，THE Frontend SHALL 更新连接状态显示
3. WHEN 连接断开时，THE Frontend SHALL 显示重连倒计时
4. WHEN 连接失败时，THE Frontend SHALL 提供手动重连按钮
5. THE Frontend SHALL 在连接状态组件中显示重连尝试次数

### Requirement 5

**User Story:** 作为系统开发者，我希望 SSE 实现能够支持任务恢复，以便用户刷新页面后能够继续查看正在进行的任务

#### Acceptance Criteria

1. WHEN 用户刷新页面时，THE Frontend SHALL 从 localStorage 读取活动任务信息
2. WHEN 存在活动任务时，THE Frontend SHALL 自动重新建立 SSE 连接
3. THE Backend SHALL 支持通过 task_id 恢复任务状态
4. WHEN 任务已完成时，THE Backend SHALL 立即返回完成状态
5. WHEN 任务仍在进行时，THE Backend SHALL 继续推送更新消息

### Requirement 6

**User Story:** 作为系统用户，我希望 SSE 连接能够正确处理各种消息类型，以便准确显示任务执行信息

#### Acceptance Criteria

1. THE Backend SHALL 发送 `progress` 类型消息以更新任务进度百分比
2. THE Backend SHALL 发送 `log` 类型消息以推送任务执行日志
3. THE Backend SHALL 发送 `result` 类型消息以推送任务完成结果
4. THE Backend SHALL 发送 `error` 类型消息以推送错误信息
5. THE Frontend SHALL 根据消息类型正确处理和显示消息内容

### Requirement 7

**User Story:** 作为系统开发者，我希望 SSE 实现能够正确处理并发任务，以便多个用户可以同时使用系统

#### Acceptance Criteria

1. THE Backend SHALL 为每个任务创建独立的 SSE 连接
2. THE Backend SHALL 使用 task_id 隔离不同任务的消息流
3. THE Backend SHALL 在任务完成后正确关闭 SSE 连接
4. THE Backend SHALL 在客户端断开连接后清理相关资源
5. THE Task Manager SHALL 支持多个并发 SSE 连接

### Requirement 8

**User Story:** 作为系统用户，我希望在任务执行过程中能够看到实时的进度条和日志输出，以便了解任务的详细执行情况

#### Acceptance Criteria

1. THE Frontend SHALL 根据 progress 消息更新进度条显示
2. THE Frontend SHALL 将 log 消息追加到日志列表中
3. THE Frontend SHALL 避免显示重复的日志消息
4. THE Frontend SHALL 在任务完成时显示 100% 进度
5. THE Frontend SHALL 在任务失败时保持最后的进度状态
