/**
 * ConnectionStatus组件
 * 显示WebSocket连接状态和重连信息
 */
export default {
  props: {
    connectionState: {
      type: String,
      required: true,
      validator: (value) => ['connected', 'connecting', 'disconnected', 'reconnecting'].includes(value)
    },
    reconnectAttempt: {
      type: Number,
      default: 0
    },
    maxAttempts: {
      type: Number,
      default: 5
    }
  },
  
  emits: ['manual-reconnect'],
  
  setup(props, { emit }) {
    const { computed } = Vue;
    
    const statusText = computed(() => {
      switch (props.connectionState) {
        case 'connected':
          return '已连接';
        case 'connecting':
          return '正在连接...';
        case 'reconnecting':
          return `正在重连 (${props.reconnectAttempt}/${props.maxAttempts})`;
        case 'disconnected':
          return '连接已断开';
        default:
          return '';
      }
    });
    
    // 只在重连中或真正断开（有重连尝试）时显示
    const shouldShow = computed(() => {
      return props.connectionState === 'reconnecting' || 
             (props.connectionState === 'disconnected' && props.reconnectAttempt > 0);
    });
    
    const showReconnectBtn = computed(() => {
      return props.connectionState === 'disconnected' && 
             props.reconnectAttempt >= props.maxAttempts;
    });
    
    const handleManualReconnect = () => {
      emit('manual-reconnect');
    };
    
    return {
      statusText,
      shouldShow,
      showReconnectBtn,
      handleManualReconnect
    };
  }
};
