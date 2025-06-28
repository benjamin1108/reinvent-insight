/**
 * VideoPlayer 组件
 * 浮动视频播放器，支持拖动、调整大小、最小化
 */
export default {
  props: {
    // 是否显示播放器
    visible: {
      type: Boolean,
      required: true
    },
    // 视频ID（YouTube）
    videoId: {
      type: String,
      required: true
    },
    // 视频标题
    title: {
      type: String,
      default: '视频播放器'
    },
    // 初始位置
    initialPosition: {
      type: Object,
      default: () => ({ x: null, y: null })
    },
    // 初始大小
    initialSize: {
      type: Object,
      default: () => ({ width: 480, height: 320 })
    },
    // 是否默认最小化
    defaultMinimized: {
      type: Boolean,
      default: false
    }
  },
  
  emits: ['update:visible', 'close', 'positionChange', 'sizeChange', 'minimizeChange'],
  
  setup(props, { emit }) {
    const { ref, computed, reactive, watch, onMounted, onUnmounted, nextTick } = Vue;
    
    // 状态
    const minimized = ref(props.defaultMinimized);
    const position = reactive({
      x: props.initialPosition.x,
      y: props.initialPosition.y
    });
    const size = reactive({
      width: props.initialSize.width,
      height: props.initialSize.height
    });
    
    // 拖动相关
    const isDragging = ref(false);
    const dragStartPos = reactive({ x: 0, y: 0 });
    const playerStartPos = reactive({ x: 0, y: 0 });
    
    // 调整大小相关
    const isResizing = ref(false);
    const resizeStartPos = reactive({ x: 0, y: 0 });
    const playerStartSize = reactive({ width: 0, height: 0 });
    
    // 计算属性
    const iframeSrc = computed(() => {
      if (!props.videoId) return '';
      return `https://www.youtube.com/embed/${props.videoId}?enablejsapi=1&modestbranding=1&rel=0`;
    });
    
    // 方法
    const close = () => {
      emit('close');
      emit('update:visible', false);
    };
    
    const toggleMinimize = () => {
      minimized.value = !minimized.value;
      emit('minimizeChange', minimized.value);
    };
    
    // 拖动功能
    const startDrag = (e) => {
      if (e.target.closest('.video-control-btn')) return;
      
      isDragging.value = true;
      const event = e.type.includes('touch') ? e.touches[0] : e;
      
      dragStartPos.x = event.clientX;
      dragStartPos.y = event.clientY;
      
      // 如果当前使用的是默认位置（右下角），需要计算实际位置
      if (position.x === null || position.y === null) {
        const playerEl = e.target.closest('.floating-video-player');
        if (playerEl) {
          const rect = playerEl.getBoundingClientRect();
          position.x = rect.left;
          position.y = rect.top;
        }
      }
      
      playerStartPos.x = position.x || 0;
      playerStartPos.y = position.y || 0;
      
      e.preventDefault();
    };
    
    const handleDrag = (e) => {
      if (!isDragging.value) return;
      
      const event = e.type.includes('touch') ? e.touches[0] : e;
      const deltaX = event.clientX - dragStartPos.x;
      const deltaY = event.clientY - dragStartPos.y;
      
      let newX = playerStartPos.x + deltaX;
      let newY = playerStartPos.y + deltaY;
      
      // 限制在视口内
      const maxX = window.innerWidth - (minimized.value ? 300 : size.width);
      const maxY = window.innerHeight - 41; // 标题栏高度
      
      newX = Math.max(0, Math.min(newX, maxX));
      newY = Math.max(0, Math.min(newY, maxY));
      
      position.x = newX;
      position.y = newY;
      
      emit('positionChange', { x: newX, y: newY });
    };
    
    const endDrag = () => {
      isDragging.value = false;
    };
    
    // 调整大小功能
    const startResize = (e) => {
      if (minimized.value) return;
      
      isResizing.value = true;
      const event = e.type.includes('touch') ? e.touches[0] : e;
      
      resizeStartPos.x = event.clientX;
      resizeStartPos.y = event.clientY;
      playerStartSize.width = size.width;
      playerStartSize.height = size.height;
      
      e.preventDefault();
    };
    
    const handleResize = (e) => {
      if (!isResizing.value) return;
      
      const event = e.type.includes('touch') ? e.touches[0] : e;
      const deltaX = event.clientX - resizeStartPos.x;
      const deltaY = event.clientY - resizeStartPos.y;
      
      let newWidth = playerStartSize.width + deltaX;
      let newHeight = playerStartSize.height + deltaY;
      
      // 限制最小/最大尺寸
      newWidth = Math.max(320, Math.min(newWidth, window.innerWidth - (position.x || 0)));
      newHeight = Math.max(240, Math.min(newHeight, window.innerHeight - (position.y || 0)));
      
      // 保持16:9比例（可选）
      // newHeight = newWidth / (16/9);
      
      size.width = newWidth;
      size.height = newHeight;
      
      emit('sizeChange', { width: newWidth, height: newHeight });
    };
    
    const endResize = () => {
      isResizing.value = false;
    };
    
    // 自动调整位置（防止超出视口）
    const adjustPosition = () => {
      if (position.x === null || position.y === null) return;
      
      const maxX = window.innerWidth - (minimized.value ? 300 : size.width);
      const maxY = window.innerHeight - 41;
      
      let adjusted = false;
      
      if (position.x > maxX) {
        position.x = maxX;
        adjusted = true;
      }
      
      if (position.y > maxY) {
        position.y = maxY;
        adjusted = true;
      }
      
      if (adjusted) {
        emit('positionChange', { x: position.x, y: position.y });
      }
    };
    
    // 监听props变化
    watch(() => props.videoId, (newId) => {
      // 视频ID变化时可以做一些处理
    });
    
    watch(() => props.visible, (newVal) => {
      if (newVal) {
        // 显示时调整初始位置
        nextTick(() => {
          adjustPosition();
        });
      }
    });
    
    // 生命周期
    onMounted(() => {
      // 添加全局事件监听
      document.addEventListener('mousemove', handleDrag);
      document.addEventListener('mouseup', endDrag);
      document.addEventListener('touchmove', handleDrag, { passive: false });
      document.addEventListener('touchend', endDrag);
      
      document.addEventListener('mousemove', handleResize);
      document.addEventListener('mouseup', endResize);
      document.addEventListener('touchmove', handleResize, { passive: false });
      document.addEventListener('touchend', endResize);
      
      // 窗口大小变化时调整位置
      window.addEventListener('resize', adjustPosition);
    });
    
    onUnmounted(() => {
      // 移除全局事件监听
      document.removeEventListener('mousemove', handleDrag);
      document.removeEventListener('mouseup', endDrag);
      document.removeEventListener('touchmove', handleDrag);
      document.removeEventListener('touchend', endDrag);
      
      document.removeEventListener('mousemove', handleResize);
      document.removeEventListener('mouseup', endResize);
      document.removeEventListener('touchmove', handleResize);
      document.removeEventListener('touchend', endResize);
      
      window.removeEventListener('resize', adjustPosition);
    });
    
    return {
      // 状态
      minimized,
      position,
      size,
      isDragging,
      isResizing,
      
      // 计算属性
      iframeSrc,
      
      // 方法
      close,
      toggleMinimize,
      startDrag,
      startResize
    };
  }
}; 