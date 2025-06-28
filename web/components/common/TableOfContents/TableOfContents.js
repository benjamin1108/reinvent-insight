/**
 * TableOfContents 组件
 * 文章目录，支持显示/隐藏、拖动调整宽度、点击跳转
 */
export default {
  props: {
    // 是否显示目录
    visible: {
      type: Boolean,
      default: true
    },
    // 目录HTML内容
    tocHtml: {
      type: String,
      default: ''
    },
    // 目录标题
    title: {
      type: String,
      default: '目录'
    },
    // 空目录提示文字
    emptyText: {
      type: String,
      default: '暂无目录'
    },
    // 目录宽度
    width: {
      type: Number,
      default: 320
    },
    // 最小宽度
    minWidth: {
      type: Number,
      default: 200
    },
    // 最大宽度
    maxWidth: {
      type: Number,
      default: 600
    },
    // 是否自动调整宽度
    autoAdjustWidth: {
      type: Boolean,
      default: true
    }
  },
  
  emits: ['update:visible', 'update:width', 'tocClick', 'widthChange'],
  
  setup(props, { emit, expose }) {
    const { ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue;
    
    // 引用
    const tocSidebar = ref(null);
    
    // 状态
    const actualWidth = ref(props.width);
    const isDragging = ref(false);
    const dragStartX = ref(0);
    const dragStartWidth = ref(0);
    const hasAutoAdjusted = ref(false);
    
    // 处理目录点击
    const handleClick = (event) => {
      const target = event.target;
      if (target.tagName === 'A') {
        event.preventDefault();
        
        const targetId = target.getAttribute('data-target');
        if (targetId) {
          emit('tocClick', {
            targetId,
            event
          });
        }
      }
    };
    
    // 开始拖动
    const startDrag = (e) => {
      isDragging.value = true;
      const event = e.type.includes('touch') ? e.touches[0] : e;
      
      dragStartX.value = event.clientX;
      dragStartWidth.value = actualWidth.value;
      
      // 使用CSS类控制拖拽状态
      document.documentElement.classList.add('is-dragging-toc');
      
      e.preventDefault();
    };
    
    // 处理拖动
    const handleDrag = (e) => {
      if (!isDragging.value) return;
      
      const event = e.type.includes('touch') ? e.touches[0] : e;
      const deltaX = event.clientX - dragStartX.value;
      let newWidth = dragStartWidth.value + deltaX;
      
      // 限制宽度范围
      newWidth = Math.max(props.minWidth, Math.min(newWidth, props.maxWidth));
      
      // 确保不超过窗口宽度的一半
      const maxAllowedWidth = Math.min(props.maxWidth, window.innerWidth * 0.5);
      newWidth = Math.min(newWidth, maxAllowedWidth);
      
      actualWidth.value = newWidth;
      emit('update:width', newWidth);
      emit('widthChange', newWidth);
      
      // 标记用户已手动调整过宽度
      hasAutoAdjusted.value = true;
    };
    
    // 结束拖动
    const endDrag = () => {
      if (!isDragging.value) return;
      
      isDragging.value = false;
      // 清除拖拽状态
      document.documentElement.classList.remove('is-dragging-toc');
    };
    
    // 自动调整宽度
    const adjustWidth = () => {
      if (!props.autoAdjustWidth || hasAutoAdjusted.value || !tocSidebar.value) return;
      
      const tocElement = tocSidebar.value.querySelector('.toc-content');
      if (!tocElement) return;
      
      const links = tocElement.querySelectorAll('a');
      if (links.length === 0) return;
      
      let maxWidth = 0;
      links.forEach(link => {
        const width = link.scrollWidth;
        if (width > maxWidth) {
          maxWidth = width;
        }
      });
      
      // 添加一些额外的边距
      const newWidth = Math.min(maxWidth + 60, Math.max(props.minWidth, window.innerWidth * 0.5));
      
      if (newWidth !== actualWidth.value) {
        actualWidth.value = newWidth;
        emit('update:width', newWidth);
        emit('widthChange', newWidth);
      }
    };
    
    // 监听props变化
    watch(() => props.width, (newWidth) => {
      if (!isDragging.value) {
        actualWidth.value = newWidth;
      }
    });
    
    watch(() => props.tocHtml, () => {
      // 当目录内容变化时，如果启用了自动调整且用户未手动调整过，则重新计算宽度
      if (props.autoAdjustWidth && !hasAutoAdjusted.value) {
        nextTick(() => {
          adjustWidth();
        });
      }
    });
    
    // 重置自动调整标记
    const resetAutoAdjust = () => {
      hasAutoAdjusted.value = false;
    };
    
    // 生命周期
    onMounted(() => {
      // 添加全局事件监听
      document.addEventListener('mousemove', handleDrag);
      document.addEventListener('mouseup', endDrag);
      document.addEventListener('touchmove', handleDrag, { passive: false });
      document.addEventListener('touchend', endDrag);
      
      // 初始自动调整宽度
      if (props.autoAdjustWidth && props.tocHtml) {
        nextTick(() => {
          adjustWidth();
        });
      }
    });
    
    onUnmounted(() => {
      // 移除全局事件监听
      document.removeEventListener('mousemove', handleDrag);
      document.removeEventListener('mouseup', endDrag);
      document.removeEventListener('touchmove', handleDrag);
      document.removeEventListener('touchend', endDrag);
    });
    
    // 暴露方法给父组件
    expose({
      adjustWidth,
      resetAutoAdjust
    });
    
    return {
      // 引用
      tocSidebar,
      
      // 状态
      actualWidth,
      isDragging,
      
      // 方法
      handleClick,
      startDrag
    };
  }
}; 