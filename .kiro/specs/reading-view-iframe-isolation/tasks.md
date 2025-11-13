# Implementation Plan

- [x] 1. 准备工作和代码清理
  - 备份当前 ReadingView 组件的实现
  - 移除不再需要的 `visualHtmlContent` 状态和 `loadVisualHtml` 方法
  - _Requirements: 1.1, 5.5_

- [ ] 2. 实现 iframe 基础结构
  - [x] 2.1 修改 ReadingView.html 模板
    - 将 Quick Insight 模式的 `v-html` 容器替换为 iframe 容器
    - 添加 iframe 元素，绑定 `src`、`ref`、`style` 和 `@load` 事件
    - 保持 `reading-view__visual-header` 的位置和样式不变
    - _Requirements: 1.1, 1.3, 2.1_
  
  - [x] 2.2 添加 iframe 相关的响应式状态
    - 在 ReadingView.js 的 `setup` 函数中添加 `iframeHeight` ref（初始值 800）
    - 添加 `visualIframe` ref 用于引用 iframe 元素
    - 添加 `iframeMessageHandler` 变量用于存储消息处理器
    - _Requirements: 1.1, 3.1_
  
  - [x] 2.3 实现 iframe 加载处理方法
    - 创建 `handleIframeLoad` 方法，处理 iframe 加载完成事件
    - 添加基本的加载成功日志
    - 在 `return` 语句中导出 `handleIframeLoad` 方法
    - _Requirements: 1.4, 3.5_

- [ ] 3. 实现 postMessage 通信机制
  - [x] 3.1 创建消息监听器设置方法
    - 实现 `setupIframeMessageListener` 方法
    - 创建 `iframeMessageHandler` 函数，监听 `iframe-height` 类型的消息
    - 在接收到高度消息时更新 `iframeHeight` 状态（添加 20px 缓冲）
    - _Requirements: 3.1, 3.2_
  
  - [x] 3.2 创建消息监听器清理方法
    - 实现 `cleanupIframeMessageListener` 方法
    - 移除 window 上的 message 事件监听器
    - 清空 `iframeMessageHandler` 引用
    - _Requirements: 3.1_
  
  - [x] 3.3 在生命周期钩子中集成消息监听器
    - 在 `onMounted` 钩子中调用 `setupIframeMessageListener`
    - 在 `onUnmounted` 钩子中调用 `cleanupIframeMessageListener`
    - _Requirements: 3.1_

- [ ] 4. 添加 CSS 样式
  - [x] 4.1 添加 iframe 容器样式
    - 在 ReadingView.css 中添加 `.reading-view__visual-iframe-container` 样式
    - 设置 flex、width、background 和 overflow 属性
    - _Requirements: 1.3, 2.1_
  
  - [x] 4.2 添加 iframe 元素样式
    - 添加 `.reading-view__visual-iframe` 样式
    - 设置 width: 100%、min-height: 100vh、border: none
    - 确保 display: block 避免底部空隙
    - _Requirements: 1.3, 3.1_
  
  - [x] 4.3 添加移动端适配样式
    - 在 `@media (max-width: 768px)` 中添加 iframe 相关样式
    - 添加 `-webkit-overflow-scrolling: touch` 优化移动端滚动
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 5. 实现错误处理和安全验证
  - [x] 5.1 增强 iframe 加载错误处理
    - 在 `handleIframeLoad` 中添加 try-catch 错误捕获
    - 检查 iframe 是否成功加载（contentWindow 存在性）
    - 加载失败时更新 `visualStatus` 为 'failed'，`visualAvailable` 为 false
    - _Requirements: 3.5_
  
  - [x] 5.2 添加消息来源安全验证
    - 在 `iframeMessageHandler` 中验证 `event.origin`
    - 只接受来自允许源的消息（window.location.origin）
    - 验证消息格式和高度值的有效性（0 < height < 50000）
    - _Requirements: 1.2_
  
  - [x] 5.3 添加跨域问题的回退处理
    - 在无法访问 iframe 内容时，使用固定高度（800px）
    - 添加警告日志提示跨域限制
    - _Requirements: 3.5_

- [ ] 6. 清理和优化代码
  - [x] 6.1 移除不再需要的代码
    - 从响应式状态中移除 `visualHtmlContent`
    - 删除 `loadVisualHtml` 方法的完整实现
    - 从 `checkVisualStatus` 中移除 `await loadVisualHtml()` 调用
    - 从 `handleVersionChangeWithVisual` 中移除 `await loadVisualHtml()` 调用
    - _Requirements: 5.5_
  
  - [x] 6.2 添加性能优化
    - 在 `handleIframeMessage` 中实现防抖逻辑（100ms）
    - 在模式切换时清理 iframe 资源（设置 src 为 'about:blank'）
    - _Requirements: 1.5, 3.2_
  
  - [x] 6.3 更新 return 语句
    - 从 return 对象中移除 `visualHtmlContent`
    - 添加 `iframeHeight` 和 `visualIframe` 到 return 对象
    - 确保所有新方法都已导出
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 7. 后端脚本注入（如果需要）
  - [x] 7.1 在后端可视化 HTML 生成中添加高度通信脚本
    - 在 `</body>` 标签前注入 postMessage 脚本
    - 脚本应在 DOMContentLoaded、load 和 resize 事件时发送高度
    - 使用 MutationObserver 监听 DOM 变化并更新高度
    - _Requirements: 3.1, 3.2_
  
  - [ ]* 7.2 测试后端脚本注入
    - 验证脚本在可视化 HTML 中正确注入
    - 测试脚本能够正确计算和发送高度
    - _Requirements: 3.1_

- [ ] 8. 测试和验证
  - [x] 8.1 功能测试
    - 测试从 Deep Insight 切换到 Quick Insight 的流程
    - 测试 iframe 是否正确加载可视化内容
    - 测试 iframe 高度是否自动适配内容
    - 测试版本切换时 iframe 是否重新加载
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 3.1, 3.2_
  
  - [x] 8.2 样式隔离测试
    - 验证 iframe 内的样式不影响主应用
    - 验证主应用的样式不影响 iframe 内容
    - 测试模式切换器的位置和样式保持一致
    - _Requirements: 1.2, 2.1_
  
  - [ ]* 8.3 移动端测试
    - 在移动设备上测试 Quick Insight 模式
    - 测试触摸滚动体验
    - 测试屏幕方向改变时的布局
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 8.4 错误场景测试
    - 测试可视化内容不存在时的错误处理
    - 测试网络错误时的表现
    - 测试跨域限制的回退处理
    - _Requirements: 3.5_
  
  - [ ]* 8.5 性能测试
    - 测试 iframe 加载时间
    - 测试高度更新的性能影响
    - 测试大型可视化内容的渲染性能
    - _Requirements: 1.5, 4.5_

- [ ]* 9. 文档更新
  - [ ]* 9.1 更新组件 README
    - 在 ReadingView/README.md 中记录 iframe 实现方式
    - 说明 postMessage 通信机制
    - 添加故障排查指南
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [ ]* 9.2 更新代码注释
    - 为新增的方法添加详细的 JSDoc 注释
    - 为 iframe 相关的状态添加说明注释
    - _Requirements: 5.1, 5.2, 5.3_
