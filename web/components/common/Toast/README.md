# Toast 组件说明

## 组件性质
**⚠️ 注意：这是新增功能，不是从原项目提取的组件**

## 背景
- 原项目有 `showToast` 函数调用，但没有对应的 UI 实现
- 原项目可能使用 `console.log` 或计划实现但未完成
- 为了提供更好的用户体验，创建了这个 Toast 组件

## 如果要符合严格的重构原则
有以下选项：
1. **移除 Toast 组件**，将 `showToast` 调用改为 `console.log`
2. **使用原生 alert()**（但体验较差）
3. **保留但明确标记为新增功能**（当前选择）

## 组件功能
- 支持 success、error、warning、info 四种类型
- 自动关闭和手动关闭
- 响应式设计
- 使用事件总线进行全局通信

## 使用方式
```javascript
// 原项目的调用方式
showToast('消息内容', 'success');

// 组件系统映射
const toast = window.useToast();
toast.success('消息内容');
``` 