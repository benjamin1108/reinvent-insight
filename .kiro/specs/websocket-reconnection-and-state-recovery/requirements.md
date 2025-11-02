# Requirements Document

## Introduction

本需求文档旨在解决前端在解析内容时，因网络中断或页面刷新导致WebSocket连接断开，用户无法继续查看解析状态的问题。通过实现WebSocket自动重连机制和任务状态持久化，确保用户能够在连接恢复后继续查看正在进行的解析任务状态。

## Glossary

- **WebSocket Connection**: 前端与后端之间建立的WebSocket连接，用于实时推送解析进度和状态信息
- **Task State**: 任务状态，包括任务ID、当前进度、状态消息、完成百分比等信息
- **Reconnection**: 重连机制，当WebSocket连接断开时自动尝试重新建立连接
- **State Recovery**: 状态恢复，重连成功后从服务器获取当前正在进行的任务状态
- **Progress Message**: 进度消息，通过WebSocket推送的实时状态更新信息
- **Task Persistence**: 任务持久化，在服务器端保存任务的当前状态，以便客户端重连后恢复
- **Active Task**: 活跃任务，当前正在执行中的解析任务
- **Client Session**: 客户端会话，用于标识和关联特定客户端的任务

## Requirements

### Requirement 1: WebSocket自动重连机制

**User Story:** 作为用户，当网络短暂中断或页面意外刷新时，我希望系统能够自动重新建立WebSocket连接，以便继续接收解析状态更新

#### Acceptance Criteria

1. WHEN WebSocket连接断开时，THE System SHALL 在3秒后自动尝试重新连接
2. WHEN 重连失败时，THE System SHALL 使用指数退避策略进行重试，最大间隔不超过30秒
3. WHEN 连续重连失败超过5次时，THE System SHALL 向用户显示连接失败提示，并提供手动重连按钮
4. WHEN 重连成功时，THE System SHALL 向用户显示连接已恢复的提示
5. WHEN 用户主动关闭页面或导航离开时，THE System SHALL 停止重连尝试

### Requirement 2: 任务状态持久化

**User Story:** 作为系统开发者，我希望服务器能够持久化任务的当前状态，以便客户端重连后能够恢复显示

#### Acceptance Criteria

1. WHEN 任务开始执行时，THE System SHALL 在服务器端创建任务状态记录，包含任务ID、开始时间、当前阶段等信息
2. WHEN 任务进度更新时，THE System SHALL 实时更新服务器端的任务状态记录
3. WHEN 任务完成或失败时，THE System SHALL 更新任务状态为最终状态，并保留至少1小时
4. WHEN 任务状态更新时，THE System SHALL 包含时间戳信息，以便追踪状态变化历史
5. THE System SHALL 定期清理超过24小时的已完成任务状态记录

### Requirement 3: 状态恢复机制

**User Story:** 作为用户，当WebSocket重连成功后，我希望能够立即看到当前正在进行的解析任务状态，而不是从头开始

#### Acceptance Criteria

1. WHEN WebSocket重连成功时，THE System SHALL 向服务器请求当前客户端关联的活跃任务列表
2. WHEN 服务器返回活跃任务时，THE System SHALL 恢复任务的UI显示状态，包括进度条、状态消息等
3. WHEN 任务已完成时，THE System SHALL 显示完成状态和结果链接
4. WHEN 任务失败时，THE System SHALL 显示错误信息和重试选项
5. WHEN 没有活跃任务时，THE System SHALL 显示空闲状态

### Requirement 4: 客户端会话管理

**User Story:** 作为系统开发者，我希望能够识别和关联特定客户端的任务，以便在重连时恢复正确的任务状态

#### Acceptance Criteria

1. WHEN 客户端首次连接时，THE System SHALL 生成唯一的会话ID并存储在浏览器本地存储中
2. WHEN 客户端发起任务时，THE System SHALL 将会话ID与任务ID关联
3. WHEN 客户端重连时，THE System SHALL 发送会话ID到服务器
4. WHEN 服务器接收到会话ID时，THE System SHALL 查询该会话关联的所有活跃任务
5. WHEN 会话ID不存在或无效时，THE System SHALL 生成新的会话ID

### Requirement 5: 用户体验优化

**User Story:** 作为用户，我希望在连接状态变化时能够得到清晰的视觉反馈，以便了解当前系统状态

#### Acceptance Criteria

1. WHEN WebSocket连接断开时，THE System SHALL 在UI上显示"连接已断开，正在重连..."的提示
2. WHEN 正在重连时，THE System SHALL 显示重连倒计时或动画效果
3. WHEN 重连成功时，THE System SHALL 显示"连接已恢复"的成功提示，并在3秒后自动消失
4. WHEN 连接彻底失败时，THE System SHALL 显示明确的错误信息和手动重连按钮
5. WHEN 任务状态恢复时，THE System SHALL 平滑过渡到当前进度，避免UI闪烁

### Requirement 6: 错误处理和降级策略

**User Story:** 作为系统维护者，我希望系统能够优雅地处理各种异常情况，确保用户体验不会因为边缘情况而严重受损

#### Acceptance Criteria

1. WHEN 状态恢复API调用失败时，THE System SHALL 记录错误日志并向用户显示友好的错误提示
2. WHEN 服务器返回的任务状态数据格式错误时，THE System SHALL 使用默认值并记录警告
3. WHEN 本地存储不可用时，THE System SHALL 使用内存中的临时会话ID
4. WHEN 任务状态数据不一致时，THE System SHALL 以服务器端数据为准
5. WHEN 网络持续不稳定时，THE System SHALL 建议用户检查网络连接

