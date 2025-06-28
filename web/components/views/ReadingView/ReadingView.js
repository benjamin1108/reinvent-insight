/**
 * ReadingView组件
 * 文章阅读界面，集成TableOfContents和VersionSelector组件
 */
export default {
  dependencies: [
    ['table-of-contents', '/components/common/TableOfContents', 'TableOfContents'],
    ['version-selector', '/components/shared/VersionSelector', 'VersionSelector']
  ],
  
  props: {
    // 文章内容（HTML）
    content: {
      type: String,
      default: ''
    },
    
    // TOC HTML内容
    tocHtml: {
      type: String,
      default: ''
    },
    
    // 加载状态
    loading: {
      type: Boolean,
      default: false
    },
    
    // 错误信息
    error: {
      type: String,
      default: ''
    },
    
    // 加载文本
    loadingText: {
      type: String,
      default: '加载文章中...'
    },
    
    // 版本信息
    versions: {
      type: Array,
      default: () => []
    },
    
    // 当前版本
    currentVersion: {
      type: String,
      default: '1'
    },
    
    // 初始TOC显示状态
    initialShowToc: {
      type: Boolean,
      default: true
    },
    
    // 初始TOC宽度
    initialTocWidth: {
      type: Number,
      default: 280
    }
  },
  
  emits: [
    'toc-click',
    'article-click',
    'version-change',
    'toc-toggle',
    'toc-resize'
  ],
  
  setup(props, { emit }) {
    const { ref, computed, onMounted, onUnmounted } = Vue;
    
    // 状态管理
    const showToc = ref(props.initialShowToc);
    const tocWidth = ref(props.initialTocWidth);
    const isDragging = ref(false);
    const dragStartX = ref(0);
    const dragStartWidth = ref(0);
    
    // 计算属性
    const hasMultipleVersions = computed(() => {
      return props.versions && props.versions.length > 1;
    });
    
    // TOC相关方法
    const toggleToc = () => {
      showToc.value = !showToc.value;
      emit('toc-toggle', showToc.value);
    };
    
    const handleTocClick = (event) => {
      emit('toc-click', event);
    };
    
    // 拖拽相关方法
    const initDrag = (event) => {
      if (event.button !== 0) return; // 只处理鼠标左键
      
      event.preventDefault();
      isDragging.value = true;
      dragStartX.value = event.clientX;
      dragStartWidth.value = tocWidth.value;
      
      document.addEventListener('mousemove', handleDrag);
      document.addEventListener('mouseup', stopDrag);
      // 使用CSS类来控制拖拽状态，避免直接修改body
      document.documentElement.classList.add('is-dragging-toc');
    };
    
    const handleDrag = (event) => {
      if (!isDragging.value) return;
      
      const deltaX = event.clientX - dragStartX.value;
      let newWidth = dragStartWidth.value + deltaX;
      
      // 限制TOC宽度范围
      const minWidth = 200;
      const maxWidth = Math.min(600, window.innerWidth * 0.5);
      
      newWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
      tocWidth.value = newWidth;
      
      emit('toc-resize', newWidth);
    };
    
    const stopDrag = () => {
      isDragging.value = false;
      document.removeEventListener('mousemove', handleDrag);
      document.removeEventListener('mouseup', stopDrag);
      // 清除拖拽状态
      document.documentElement.classList.remove('is-dragging-toc');
    };
    
    // 文章相关方法
    const handleArticleClick = (event) => {
      emit('article-click', event);
    };
    
    // 版本相关方法
    const handleVersionChange = (version) => {
      emit('version-change', version);
    };
    
    // 响应式处理
    const handleResize = () => {
      // 在移动设备上自动隐藏TOC
      if (window.innerWidth <= 768) {
        showToc.value = false;
      } else if (window.innerWidth > 768 && !showToc.value) {
        showToc.value = props.initialShowToc;
      }
      
      // 调整TOC宽度以适应屏幕
      const maxWidth = Math.min(600, window.innerWidth * 0.5);
      if (tocWidth.value > maxWidth) {
        tocWidth.value = maxWidth;
      }
    };
    
    // 键盘快捷键
    const handleKeydown = (event) => {
      // Ctrl + T 或 Cmd + T 切换TOC
      if ((event.ctrlKey || event.metaKey) && event.key === 't') {
        event.preventDefault();
        toggleToc();
      }
      
      // ESC 键隐藏TOC（仅在移动设备上）
      if (event.key === 'Escape' && window.innerWidth <= 768) {
        showToc.value = false;
      }
    };
    
    // 生命周期
    onMounted(() => {
      window.addEventListener('resize', handleResize);
      document.addEventListener('keydown', handleKeydown);
      
      // 初始响应式检查
      handleResize();
    });
    
    onUnmounted(() => {
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('keydown', handleKeydown);
      
      // 清理拖拽事件
      if (isDragging.value) {
        stopDrag();
      }
    });
    
    // 公开方法
    const scrollToElement = (selector) => {
      const element = document.querySelector(selector);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };
    
    const resetLayout = () => {
      showToc.value = props.initialShowToc;
      tocWidth.value = props.initialTocWidth;
    };
    
    return {
      // 响应式状态
      showToc,
      tocWidth,
      isDragging,
      
      // 计算属性
      hasMultipleVersions,
      
      // 方法
      toggleToc,
      handleTocClick,
      initDrag,
      handleArticleClick,
      handleVersionChange,
      scrollToElement,
      resetLayout
    };
  }
}; 