/**
 * Toast组件
 * 用于显示全局通知消息
 */
export default {
  props: {
    message: {
      type: String,
      required: true
    },
    type: {
      type: String,
      default: 'success',
      validator: (value) => ['success', 'warning', 'error', 'info'].includes(value)
    },
    duration: {
      type: Number,
      default: 3000
    },
    closable: {
      type: Boolean,
      default: true
    }
  },
  
  setup(props, { emit }) {
    const { ref, onMounted, onUnmounted } = Vue;
    
    const visible = ref(true);
    let timer = null;
    
    const close = () => {
      visible.value = false;
      emit('close');
    };
    
    onMounted(() => {
      if (props.duration > 0) {
        timer = setTimeout(close, props.duration);
      }
    });
    
    onUnmounted(() => {
      if (timer) {
        clearTimeout(timer);
      }
    });
    
    return {
      visible,
      close
    };
  }
}; 