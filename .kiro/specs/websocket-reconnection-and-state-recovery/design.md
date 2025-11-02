# Design Document

## Overview

基于现有代码的最小化增强方案，添加WebSocket自动重连功能。

**现有实现**:
- ✅ localStorage保存active_task_id和active_task_url
- ✅ 页面刷新时restoreTask()恢复任务
- ✅ 后端TaskManager保存任务状态并支持重连时发送历史记录

**问题**:
- ❌ WebSocket断开后不会自动重连
- ❌ 没有连接状态UI反馈

**解决方案**:
1. 在connectWebSocket函数的ws.onclose中添加自动重连逻辑
2. 添加ConnectionStatus组件显示连接状态
3. 添加手动重连按钮

## Architecture

```
前端 app.js
├── connectWebSocket() - 增强：添加重连逻辑
├── connectionState - 新增：连接状态
├── reconnectAttempts - 新增：重连次数
└── manualReconnect() - 新增：手动重连

前端 UI
└── ConnectionStatus组件 - 新增：显示连接状态

后端（无需修改）
└── TaskManager.send_history() - 已有：发送历史记录
```

## Components and Interfaces

### 1. 增强 connectWebSocket 函数

**文件**: `web/js/app.js`

**新增状态变量**:
```javascript
const connectionState = ref('disconnected');
const reconnectAttempts = ref(0);
const reconnectTimer = ref(null);
const currentTaskId = ref(null);

const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY = 3000;
const MAX_RECONNECT_DELAY = 30000;
```

**核心修改 - ws.onclose**:
```javascript
ws.onclose = (event) => {
  // 如果任务还在进行中，尝试重连
  if (loading.value && reconnectAttempts.value < MAX_RECONNECT_ATTEMPTS) {
    connectionState.value = 'reconnecting';
    reconnectAttempts.value++;
    
    const delay = getReconnectDelay(reconnectAttempts.value - 1);
    logs.value.push(`连接断开，${Math.ceil(delay / 1000)}秒后重连 (${reconnectAttempts.value}/${MAX_RECONNECT_ATTEMPTS})`);
    
    reconnectTimer.value = setTimeout(() => {
      connectWebSocket(taskId, true);
    }, delay);
  } else if (reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
    connectionState.value = 'disconnected';
    logs.value.push('连接失败，已达到最大重连次数');
    showToast('连接失败，请手动重连', 'danger');
  }
};
```

**新增函数**:
```javascript
// 指数退避计算
const getReconnectDelay = (attempt) => {
  return Math.min(
    BASE_RECONNECT_DELAY * Math.pow(2, attempt),
    MAX_RECONNECT_DELAY
  );
};

// 手动重连
const manualReconnect = () => {
  if (currentTaskId.value) {
    reconnectAttempts.value = 0;
    connectWebSocket(currentTaskId.value, true);
  }
};
```

### 2. ConnectionStatus 组件

**文件**: `web/components/common/ConnectionStatus/ConnectionStatus.js`

**组件代码**:
```javascript
export default {
  props: {
    connectionState: String,
    reconnectAttempt: Number,
    maxAttempts: Number
  },
  emits: ['manual-reconnect'],
  setup(props, { emit }) {
    const { computed } = Vue;
    
    const statusText = computed(() => {
      switch (props.connectionState) {
        case 'connected': return '已连接';
        case 'reconnecting': return `正在重连 (${props.reconnectAttempt}/${props.maxAttempts})`;
        case 'disconnected': return '连接已断开';
        default: return '';
      }
    });
    
    const showReconnectBtn = computed(() => {
      return props.connectionState === 'disconnected' && 
             props.reconnectAttempt >= props.maxAttempts;
    });
    
    return { statusText, showReconnectBtn };
  }
};
```

**HTML模板**:
```html
<div v-if="connectionState !== 'connected'" class="connection-status" :class="`connection-status--${connectionState}`">
  <span class="connection-status__text">{{ statusText }}</span>
  <button v-if="showReconnectBtn" @click="$emit('manual-reconnect')" class="connection-status__btn">
    手动重连
  </button>
</div>
```

**CSS样式**:
```css
.connection-status {
  padding: 8px 16px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.connection-status--reconnecting {
  background-color: #fff3cd;
  color: #856404;
}

.connection-status--disconnected {
  background-color: #f8d7da;
  color: #721c24;
}

.connection-status__btn {
  padding: 4px 12px;
  border: 1px solid currentColor;
  border-radius: 4px;
  background: transparent;
  color: inherit;
  cursor: pointer;
}
```

### 3. 集成到 CreateView

**文件**: `web/components/views/CreateView/CreateView.html`

在进度显示区域添加：
```html
<connection-status
  v-if="loading"
  :connection-state="connectionState"
  :reconnect-attempt="reconnectAttempt"
  :max-attempts="5"
  @manual-reconnect="$emit('manual-reconnect')"
/>
```

## Data Models

### ConnectionState
```typescript
type ConnectionState = 'connected' | 'connecting' | 'disconnected' | 'reconnecting';
```

### ReconnectInfo
```typescript
interface ReconnectInfo {
  attempts: number;
  maxAttempts: number;
  delay: number;
}
```

## Error Handling

1. **连接失败** - 自动重连，最多5次
2. **重连超限** - 显示手动重连按钮
3. **任务完成** - 停止重连，正常断开

## Testing Strategy

### 单元测试
1. 测试指数退避计算
2. 测试重连次数限制
3. 测试ConnectionStatus组件渲染

### 集成测试
1. 模拟网络断开 → 验证自动重连
2. 模拟多次失败 → 验证手动重连按钮
3. 页面刷新 → 验证任务恢复

## Implementation Notes

**关键点**:
1. 只在任务进行中（loading=true）时重连
2. 使用指数退避避免服务器压力
3. 保存currentTaskId供重连使用
4. 清理reconnectTimer避免内存泄漏

**不需要修改**:
- 后端代码（已支持重连）
- localStorage逻辑（已有）
- restoreTask函数（已有）
