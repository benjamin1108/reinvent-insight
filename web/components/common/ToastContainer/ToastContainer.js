/**
 * ToastContainer组件
 * 管理多个Toast的显示
 */
export default {
  props: {
    // 事件总线实例，支持依赖注入
    eventBus: {
      type: Object,
      default: null
    }
  },
  setup(props) {
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
      const bus = props.eventBus || window.eventBus;
      if (bus) {
        bus.on('show-toast', handleShowToast);
      } else {
        console.warn('ToastContainer: 没有找到eventBus实例');
      }
    });
    
    onUnmounted(() => {
      const bus = props.eventBus || window.eventBus;
      if (bus) {
        bus.off('show-toast', handleShowToast);
      }
    });
    
    return {
      toasts,
      removeToast,
      addToast  // 导出addToast方便调试
    };
  }
}; 