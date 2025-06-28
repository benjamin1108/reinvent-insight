/**
 * ToastContainer组件
 * 管理多个Toast的显示
 */
export default {
  components: {
    // 注册Toast组件（如果使用局部注册）
    // Toast组件应该通过ComponentLoader全局注册
  },
  setup() {
    const { ref, onMounted, onUnmounted } = Vue;
    
    const toasts = ref([]);
    let toastId = 0;
    
    const addToast = (options) => {
      const id = toastId++;
      const toast = {
        id,
        ...options
      };
      
      toasts.value.push(toast);
      
      // 返回移除函数
      return () => removeToast(id);
    };
    
    const removeToast = (id) => {
      const index = toasts.value.findIndex(t => t.id === id);
      if (index > -1) {
        toasts.value.splice(index, 1);
      }
    };
    
    // 监听事件总线的toast事件
    const handleShowToast = (options) => {
      if (typeof options === 'string') {
        options = { message: options };
      }
      addToast(options);
    };
    
    onMounted(() => {
      // 等待eventBus可用
      const checkEventBus = () => {
        if (window.eventBus) {
          window.eventBus.on('show-toast', handleShowToast);
        } else {
          // 如果eventBus还未加载，稍后再试
          setTimeout(checkEventBus, 10);
        }
      };
      checkEventBus();
    });
    
    onUnmounted(() => {
      if (window.eventBus) {
        window.eventBus.off('show-toast', handleShowToast);
      }
    });
    
    return {
      toasts,
      removeToast,
      addToast  // 导出addToast方便调试
    };
  }
}; 