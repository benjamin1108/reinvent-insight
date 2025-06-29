/**
 * useToast Composable
 * 提供便捷的Toast调用方法
 */
export function useToast() {
  const showToast = (options) => {
    if (typeof options === 'string') {
      options = { message: options };
    }
    // 确保 eventBus 已经加载
    if (!window.eventBus) {
      console.warn('EventBus 尚未加载，延迟显示 Toast');
      // 延迟重试，等待 eventBus 加载
      setTimeout(() => {
        if (window.eventBus) {
          window.eventBus.emit('show-toast', options);
        } else {
          console.error('EventBus 加载失败，无法显示 Toast');
        }
      }, 100);
      return;
    }
    window.eventBus.emit('show-toast', options);
  };
  
  const success = (message, options = {}) => {
    showToast({
      message,
      type: 'success',
      ...options
    });
  };
  
  const error = (message, options = {}) => {
    showToast({
      message,
      type: 'error',
      ...options
    });
  };
  
  const warning = (message, options = {}) => {
    showToast({
      message,
      type: 'warning',
      ...options
    });
  };
  
  const info = (message, options = {}) => {
    showToast({
      message,
      type: 'info',
      ...options
    });
  };
  
  return {
    showToast,
    success,
    error,
    warning,
    info
  };
}

// 导出到全局
window.useToast = useToast; 