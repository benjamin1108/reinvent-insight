/**
 * Toast 功能的备用实现
 * 如果要严格遵循"只提取现有功能"的原则，可以使用这个文件替代 Toast 组件
 */

// 简单的 console.log 实现
const showToastFallback = (message, type = 'info', duration = 3000) => {
  const timestamp = new Date().toLocaleTimeString();
  const prefix = {
    'success': '✅',
    'error': '❌', 
    'danger': '❌', // 兼容原项目的 'danger' 类型
    'warning': '⚠️',
    'info': 'ℹ️'
  }[type] || 'ℹ️';
  
  console.log(`[${timestamp}] ${prefix} ${message}`);
  
  // 可选：在开发环境显示原生通知（如果浏览器支持）
  if (window.Notification && Notification.permission === 'granted') {
    new Notification(message, {
      icon: prefix,
      body: `类型: ${type}`,
      requireInteraction: false
    });
    
    // 自动关闭通知
    setTimeout(() => {
      // 通知会自动关闭
    }, duration);
  }
};

// 如果要使用这个备用方案，在 app.js 中替换 showToast 函数：
/*
const showToast = showToastFallback;
*/

// 导出以供使用
window.showToastFallback = showToastFallback; 