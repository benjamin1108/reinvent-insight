# Design Document

## Overview

本设计文档描述了将前端与后端通信方式从 WebSocket 重构为 SSE（Server-Sent Events）的技术方案。SSE 是一种基于 HTTP 的单向推送技术，相比 WebSocket 更简单、更可靠，特别适合服务器到客户端的单向数据流场景。

### 为什么选择 SSE

1. **更简单的协议**: SSE 基于标准 HTTP，不需要协议升级，更容易通过代理和防火墙
2. **自动重连**: 浏览器原生支持自动重连，减少客户端代码复杂度
3. **更好的兼容性**: 在各种网络环境下更稳定，特别是移动网络
4. **单向通信足够**: 当前系统只需要服务器推送数据到客户端，不需要双向通信
5. **更低的资源消耗**: SSE 连接更轻量，服务器资源占用更少

### 当前 WebSocket 实现的问题

1. 频繁断线和重连失败
2. 复杂的心跳机制维护
3. 手动实现的重连逻辑容易出错
4. 在某些网络环境下连接不稳定

## Architecture

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (Vue.js)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  CreateView Component                                   │ │
│  │  - 提交任务                                             │ │
│  │  - 建立 SSE 连接                                        │ │
│  │  - 处理消息                                             │ │
│  │  - 显示进度和日志                                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓ SSE                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  SSE Endpoint: /api/tasks/{task_id}/stream             │ │
│  │  - 接受 SSE 连接                                        │ │
│  │  - 流式推送消息                                         │ │
│  │  - 处理断开连接                                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Task Manager (重构)                                    │ │
│  │  - 管理任务状态                                         │ │
│  │  - 管理 SSE 连接队列                                    │ │
│  │  - 推送消息到队列                                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Worker (异步任务)                                      │ │
│  │  - 执行分析任务                                         │ │
│  │  - 发送进度更新                                         │ │
│  │  - 发送日志消息                                         │ │
│  │  - 发送结果                                             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 消息流程

```
1. 用户提交任务
   Frontend → POST /summarize or /analyze-document → Backend
   Backend 返回 task_id

2. 建立 SSE 连接
   Frontend → GET /api/tasks/{task_id}/stream → Backend
   Backend 接受连接并开始推送消息

3. 任务执行过程
   Worker → TaskManager.send_message() → SSE Queue → Frontend
   Worker → TaskManager.update_progress() → SSE Queue → Frontend

4. 任务完成
   Worker → TaskManager.send_result() → SSE Queue → Frontend
   Backend 关闭 SSE 连接

5. 连接断开重连
   Frontend 检测到断开 → 等待延迟 → 重新建立 SSE 连接
   Backend 发送历史消息 → 继续推送新消息
```

## Components and Interfaces

### Backend Components

#### 1. SSE Endpoint

**文件**: `src/reinvent_insight/api.py`

**新增端点**:
```python
@app.get("/api/tasks/{task_id}/stream")
async def stream_task_updates(task_id: str, request: Request):
    """
    SSE 端点，流式推送任务更新
    
    Args:
        task_id: 任务ID
        request: FastAPI Request 对象，用于检测客户端断开
        
    Returns:
        StreamingResponse with text/event-stream content type
    """
```

**消息格式**:
```
event: message
data: {"type": "log", "message": "正在下载字幕..."}

event: message
data: {"type": "progress", "progress": 50, "message": "分析中..."}

event: message
data: {"type": "result", "title": "...", "summary": "...", "filename": "...", "hash": "..."}

event: message
data: {"type": "error", "message": "错误信息"}
```

#### 2. Task Manager (重构)

**文件**: `src/reinvent_insight/task_manager.py`

**主要变更**:

```python
from asyncio import Queue
from typing import Dict, Optional
from dataclasses import dataclass, field

@dataclass
class TaskState:
    task_id: str
    status: str
    logs: List[str] = field(default_factory=list)
    progress: int = 0
    result_title: Optional[str] = None
    result_summary: Optional[str] = None
    result_path: Optional[str] = None
    task: Optional[asyncio.Task] = None
    # 新增：消息队列，用于 SSE 推送
    message_queue: Optional[Queue] = None

class TaskManager:
    """管理 SSE 连接和后台任务状态"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskState] = {}
    
    async def register_sse_connection(self, task_id: str) -> Queue:
        """
        注册 SSE 连接，返回消息队列
        
        Args:
            task_id: 任务ID
            
        Returns:
            Queue: 消息队列，用于接收任务更新
        """
    
    async def unregister_sse_connection(self, task_id: str):
        """
        注销 SSE 连接
        
        Args:
            task_id: 任务ID
        """
    
    async def send_message(self, message: str, task_id: str):
        """
        发送日志消息到队列
        
        Args:
            message: 日志消息
            task_id: 任务ID
        """
    
    async def update_progress(self, task_id: str, progress: int, message: Optional[str] = None):
        """
        更新任务进度并发送到队列
        
        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            message: 可选的进度消息
        """
    
    async def send_result(self, title: str, summary: str, task_id: str, 
                         filename: str = None, doc_hash: str = None):
        """
        发送任务结果到队列
        
        Args:
            title: 文档标题
            summary: 文档摘要内容
            task_id: 任务ID
            filename: 文件名（可选）
            doc_hash: 文档哈希（可选）
        """
    
    async def set_task_error(self, task_id: str, message: str):
        """
        设置任务错误状态并发送到队列
        
        Args:
            task_id: 任务ID
            message: 错误消息
        """
```

**移除的方法**:
- `async def connect(self, websocket: WebSocket, task_id: str)` - WebSocket 连接管理
- `def disconnect(self, task_id: str)` - WebSocket 断开管理
- `async def send_history(self, task_id: str)` - 历史消息发送（SSE 会自动处理）

### Frontend Components

#### 1. SSE Connection Manager

**文件**: `web/js/app.js`

**新增功能**:

```javascript
// SSE 连接管理
const connectSSE = (taskId, isReconnect = false) => {
  // 清理之前的重连定时器
  if (reconnectTimer.value) {
    clearTimeout(reconnectTimer.value);
    reconnectTimer.value = null;
  }

  currentTaskId.value = taskId;
  connectionState.value = isReconnect ? 'reconnecting' : 'connecting';

  // 创建 EventSource
  const eventSource = new EventSource(`/api/tasks/${taskId}/stream`);
  currentEventSource.value = eventSource;

  const displayedLogs = new Set(logs.value);

  // 连接打开
  eventSource.onopen = () => {
    connectionState.value = 'connected';
    reconnectAttempts.value = 0;
    loading.value = true;
    
    if (logs.value.length === 0) {
      logs.value.push('已连接到分析服务...');
    } else if (isReconnect) {
      logs.value.push('连接已恢复');
      showToast('连接已恢复', 'success', 2000);
    }
  };

  // 接收消息
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'result') {
      // 处理结果消息
      title.value = data.title;
      if (data.filename) createdFilename.value = data.filename;
      if (data.hash) createdDocHash.value = data.hash;
      
      loading.value = false;
      progressPercent.value = 100;
      clearActiveTask();
      connectionState.value = 'disconnected';
      eventSource.close();
    } else if (data.type === 'log') {
      // 处理日志消息
      if (!displayedLogs.has(data.message)) {
        logs.value.push(data.message);
        displayedLogs.add(data.message);
      }
    } else if (data.type === 'progress') {
      // 处理进度消息
      progressPercent.value = data.progress || 0;
      console.log(`📊 进度更新: ${progressPercent.value}%`);
    } else if (data.type === 'error') {
      // 处理错误消息
      logs.value.push(`错误: ${data.message}`);
      loading.value = false;
      clearActiveTask();
      connectionState.value = 'disconnected';
      eventSource.close();
    }
  };

  // 连接错误
  eventSource.onerror = (error) => {
    console.error('SSE 连接错误:', error);
    eventSource.close();
    
    // 如果任务还在进行中，尝试重连
    if (loading.value && reconnectAttempts.value < MAX_RECONNECT_ATTEMPTS) {
      connectionState.value = 'reconnecting';
      reconnectAttempts.value++;
      
      const delay = getReconnectDelay(reconnectAttempts.value - 1);
      logs.value.push(`连接断开，${Math.ceil(delay / 1000)}秒后尝试重连 (${reconnectAttempts.value}/${MAX_RECONNECT_ATTEMPTS})`);
      
      reconnectTimer.value = setTimeout(() => {
        connectSSE(taskId, true);
      }, delay);
    } else if (loading.value && reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
      // 超过最大重连次数
      connectionState.value = 'disconnected';
      logs.value.push('连接失败，已达到最大重连次数');
      showToast('连接失败，请检查网络后手动重连', 'danger');
      loading.value = false;
    } else {
      // 任务已完成或用户主动断开
      connectionState.value = 'disconnected';
    }
  };
};
```

**移除的功能**:
- `connectWebSocket()` - WebSocket 连接创建
- WebSocket 心跳机制相关代码
- WebSocket 特定的错误处理

#### 2. Connection State Component

**文件**: `web/components/common/ConnectionStatus/ConnectionStatus.js`

保持现有的连接状态显示组件，但更新状态管理逻辑以适配 SSE。

## Data Models

### Message Types

所有消息都使用 JSON 格式，通过 SSE 的 `data` 字段传输。

#### Log Message
```json
{
  "type": "log",
  "message": "正在下载字幕..."
}
```

#### Progress Message
```json
{
  "type": "progress",
  "progress": 50,
  "message": "分析中..."
}
```

#### Result Message
```json
{
  "type": "result",
  "title": "文档标题",
  "summary": "文档内容",
  "filename": "document.md",
  "hash": "abc123"
}
```

#### Error Message
```json
{
  "type": "error",
  "message": "错误描述"
}
```

### Task State

```python
@dataclass
class TaskState:
    task_id: str                          # 任务唯一标识
    status: str                           # pending, running, completed, error
    logs: List[str]                       # 日志消息列表
    progress: int                         # 进度百分比 (0-100)
    result_title: Optional[str]           # 结果标题
    result_summary: Optional[str]         # 结果摘要
    result_path: Optional[str]            # 结果文件路径
    task: Optional[asyncio.Task]          # 异步任务对象
    message_queue: Optional[Queue]        # SSE 消息队列
```

## Error Handling

### Backend Error Handling

1. **任务不存在**: 返回 404 错误
2. **任务执行失败**: 通过 SSE 发送 error 类型消息
3. **连接断开**: 清理队列资源，等待客户端重连
4. **队列满**: 丢弃旧消息或拒绝新消息（根据策略）

### Frontend Error Handling

1. **连接失败**: 自动重连（指数退避）
2. **超过最大重连次数**: 显示错误提示，提供手动重连按钮
3. **消息解析失败**: 记录错误日志，继续处理后续消息
4. **任务错误**: 显示错误消息，停止进度更新

### Reconnection Strategy

使用指数退避算法计算重连延迟：

```javascript
const getReconnectDelay = (attempt) => {
  const BASE_DELAY = 3000;      // 基础延迟 3 秒
  const MAX_DELAY = 30000;      // 最大延迟 30 秒
  const delay = Math.min(
    BASE_DELAY * Math.pow(2, attempt),
    MAX_DELAY
  );
  // 添加随机抖动（±20%）
  const jitter = delay * 0.2 * (Math.random() * 2 - 1);
  return Math.floor(delay + jitter);
};
```

重连次数限制：最多 5 次

## Testing Strategy

### Backend Testing

1. **单元测试**:
   - TaskManager 的消息队列管理
   - SSE 端点的消息格式化
   - 错误处理逻辑

2. **集成测试**:
   - 完整的任务执行流程
   - SSE 连接建立和消息推送
   - 断开重连场景

3. **负载测试**:
   - 多个并发 SSE 连接
   - 长时间运行的任务
   - 频繁断开重连

### Frontend Testing

1. **单元测试**:
   - SSE 连接管理逻辑
   - 消息处理函数
   - 重连算法

2. **集成测试**:
   - 完整的用户交互流程
   - 连接状态显示
   - 错误提示

3. **手动测试**:
   - 网络断开场景
   - 页面刷新恢复
   - 多标签页同时使用

## Migration Strategy

### Phase 1: 实现 SSE 基础设施
1. 重构 TaskManager，添加消息队列支持
2. 实现 SSE 端点
3. 保留 WebSocket 端点（向后兼容）

### Phase 2: 前端迁移
1. 实现 SSE 连接管理
2. 更新消息处理逻辑
3. 添加功能开关，支持 SSE/WebSocket 切换

### Phase 3: 测试和验证
1. 在开发环境测试 SSE 实现
2. 在生产环境灰度发布
3. 监控错误率和性能指标

### Phase 4: 清理
1. 移除 WebSocket 相关代码
2. 移除功能开关
3. 更新文档

## Performance Considerations

1. **消息队列大小**: 限制队列大小为 100 条消息，防止内存溢出
2. **连接超时**: SSE 连接空闲 60 秒后自动关闭
3. **消息批处理**: 对于高频消息（如进度更新），考虑批处理发送
4. **资源清理**: 任务完成或连接断开后及时清理队列和任务状态

## Security Considerations

1. **认证**: SSE 端点需要验证 Bearer Token
2. **任务隔离**: 确保用户只能访问自己的任务
3. **资源限制**: 限制每个用户的并发任务数
4. **输入验证**: 验证 task_id 格式，防止注入攻击

## Monitoring and Logging

1. **连接指标**:
   - 活跃 SSE 连接数
   - 平均连接时长
   - 重连次数

2. **性能指标**:
   - 消息推送延迟
   - 队列大小
   - 任务完成时间

3. **错误指标**:
   - 连接失败率
   - 任务失败率
   - 重连失败率

## Rollback Plan

如果 SSE 实现出现严重问题，可以快速回滚到 WebSocket：

1. 恢复 WebSocket 端点代码
2. 前端切换回 WebSocket 连接
3. 回滚数据库迁移（如有）
4. 监控系统恢复正常

回滚时间预计：< 30 分钟
