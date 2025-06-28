/**
 * ReadingView组件
 * 文章阅读界面，集成目录解析、版本选择等功能
 */
export default {
  dependencies: [
    ['version-selector', '/components/shared/VersionSelector', 'VersionSelector']
  ],
  
  props: {
    // 文章内容（HTML）
    content: {
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
    },
    
    // TOC 设置
    tocTitle: {
      type: String,
      default: '目录'
    },
    
    tocEmptyText: {
      type: String,
      default: '暂无目录'
    },
    
    tocMinWidth: {
      type: Number,
      default: 200
    },
    
    tocMaxWidth: {
      type: Number,
      default: 600
    },
    
    scrollOffset: {
      type: Number,
      default: 80
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
    const { ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue;
    
    // 引用
    const tocSidebar = ref(null);
    
    // 状态管理
    const showToc = ref(props.initialShowToc);
    const tocWidth = ref(props.initialTocWidth);
    const isDragging = ref(false);
    const dragStartX = ref(0);
    const dragStartWidth = ref(0);
    const parsedSections = ref([]);
    const activeSection = ref('');
    let scrollTimer = null;
    
    // 解析内容HTML生成目录结构
    const parseContent = (html) => {
      if (!html) return [];
      
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const headings = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
      
      const sections = [];
      const stack = [];
      
      headings.forEach(heading => {
        const level = parseInt(heading.tagName.charAt(1));
        const id = heading.id || heading.textContent.trim().toLowerCase().replace(/\s+/g, '-');
        const text = heading.textContent.trim();
        
        // 确保标题有ID
        if (!heading.id) {
          heading.id = id;
        }
        
        const section = {
          id,
          text,
          level,
          children: []
        };
        
        // 构建层级结构
        while (stack.length > 0 && stack[stack.length - 1].level >= level) {
          stack.pop();
        }
        
        if (stack.length === 0) {
          sections.push(section);
        } else {
          stack[stack.length - 1].children.push(section);
        }
        
        stack.push(section);
      });
      
      return sections;
    };
    
    // 生成目录HTML
    const generateTocHtml = (sections) => {
      if (!sections || sections.length === 0) return '';
      
      const renderSection = (section) => {
        const hasChildren = section.children && section.children.length > 0;
        let html = `<li>`;
        html += `<a href="#${section.id}" data-target="${section.id}" class="${activeSection.value === section.id ? 'active' : ''}">${section.text}</a>`;
        
        if (hasChildren) {
          html += '<ul>';
          section.children.forEach(child => {
            html += renderSection(child);
          });
          html += '</ul>';
        }
        
        html += '</li>';
        return html;
      };
      
      let html = '<ul>';
      sections.forEach(section => {
        html += renderSection(section);
      });
      html += '</ul>';
      
      return html;
    };
    
    // 计算属性
    const hasMultipleVersions = computed(() => {
      return props.versions && props.versions.length > 1;
    });
    
    const tocHtml = computed(() => {
      if (!props.content) return '';
      parsedSections.value = parseContent(props.content);
      return generateTocHtml(parsedSections.value);
    });
    
    // TOC相关方法
    const toggleToc = () => {
      showToc.value = !showToc.value;
      emit('toc-toggle', showToc.value);
    };
    
    const handleTocClick = (event) => {
      const target = event.target;
      if (target.tagName === 'A') {
        event.preventDefault();
        
        const targetId = target.getAttribute('data-target');
        if (targetId) {
          scrollToSection(targetId);
          emit('toc-click', { targetId, event });
        }
      }
    };
    
    // 滚动到指定章节
    const scrollToSection = (sectionId) => {
      const element = document.getElementById(sectionId);
      if (!element) return;
      
      const container = document.querySelector('.reading-view__content');
      if (!container) return;
      
      const elementTop = element.getBoundingClientRect().top;
      const scrollTop = container.scrollTop;
      const targetScrollTop = scrollTop + elementTop - props.scrollOffset;
      
      container.scrollTo({
        top: targetScrollTop,
        behavior: 'smooth'
      });
      
      activeSection.value = sectionId;
    };
    
    // 拖动相关方法
    const startDrag = (e) => {
      isDragging.value = true;
      const event = e.type.includes('touch') ? e.touches[0] : e;
      
      dragStartX.value = event.clientX;
      dragStartWidth.value = tocWidth.value;
      
      document.documentElement.classList.add('reading-view--dragging');
      e.preventDefault();
    };
    
    const handleDrag = (e) => {
      if (!isDragging.value) return;
      
      const event = e.type.includes('touch') ? e.touches[0] : e;
      const deltaX = event.clientX - dragStartX.value;
      let newWidth = dragStartWidth.value + deltaX;
      
      // 限制宽度范围
      newWidth = Math.max(props.tocMinWidth, Math.min(newWidth, props.tocMaxWidth));
      
      // 确保不超过窗口宽度的一半
      const maxAllowedWidth = Math.min(props.tocMaxWidth, window.innerWidth * 0.5);
      newWidth = Math.min(newWidth, maxAllowedWidth);
      
      tocWidth.value = newWidth;
      emit('toc-resize', newWidth);
    };
    
    const endDrag = () => {
      if (!isDragging.value) return;
      
      isDragging.value = false;
      document.documentElement.classList.remove('reading-view--dragging');
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
      } else if (window.innerWidth > 768 && !showToc.value && props.initialShowToc) {
        showToc.value = true;
      }
    };
    
    // 滚动监听：高亮当前章节
    const handleScroll = () => {
      if (!props.content) return;
      
      const container = document.querySelector('.reading-view__content');
      if (!container) return;
      
      const scrollTop = container.scrollTop;
      
      // 获取所有标题元素
      const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
      let currentSection = '';
      
      headings.forEach(heading => {
        if (heading.id) {
          const rect = heading.getBoundingClientRect();
          const top = rect.top + scrollTop - props.scrollOffset;
          
          if (scrollTop >= top - 10) {
            currentSection = heading.id;
          }
        }
      });
      
      if (currentSection && currentSection !== activeSection.value) {
        activeSection.value = currentSection;
      }
    };
    
    // 防抖处理
    const debouncedHandleScroll = () => {
      if (scrollTimer) clearTimeout(scrollTimer);
      scrollTimer = setTimeout(handleScroll, 100);
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
        emit('toc-toggle', false);
      }
    };
    
    // 监听内容变化
    watch(() => props.content, () => {
      if (props.content) {
        parsedSections.value = parseContent(props.content);
      }
    });
    
    // 监听活动章节变化，触发目录更新
    watch(activeSection, () => {
      // 触发 Vue 重新计算 tocHtml
    });
    
    // 生命周期
    onMounted(() => {
      window.addEventListener('resize', handleResize);
      document.addEventListener('keydown', handleKeydown);
      
      // 添加拖动事件监听
      document.addEventListener('mousemove', handleDrag);
      document.addEventListener('mouseup', endDrag);
      document.addEventListener('touchmove', handleDrag, { passive: false });
      document.addEventListener('touchend', endDrag);
      
      // 添加滚动监听
      const container = document.querySelector('.reading-view__content');
      if (container) {
        container.addEventListener('scroll', debouncedHandleScroll);
      }
      
      // 初始响应式检查
      handleResize();
      
      // 初始化时解析内容
      if (props.content) {
        parsedSections.value = parseContent(props.content);
      }
    });
    
    onUnmounted(() => {
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('keydown', handleKeydown);
      
      // 移除拖动事件监听
      document.removeEventListener('mousemove', handleDrag);
      document.removeEventListener('mouseup', endDrag);
      document.removeEventListener('touchmove', handleDrag);
      document.removeEventListener('touchend', endDrag);
      
      // 移除滚动监听
      const container = document.querySelector('.reading-view__content');
      if (container) {
        container.removeEventListener('scroll', debouncedHandleScroll);
      }
      
      // 清理定时器
      if (scrollTimer) {
        clearTimeout(scrollTimer);
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
      // 引用
      tocSidebar,
      
      // 响应式状态
      showToc,
      tocWidth,
      isDragging,
      activeSection,
      
      // 计算属性
      hasMultipleVersions,
      tocHtml,
      
      // 方法
      toggleToc,
      handleTocClick,
      handleArticleClick,
      handleVersionChange,
      scrollToElement,
      resetLayout,
      startDrag,
      scrollToSection,
      
      // props
      tocTitle: props.tocTitle,
      tocEmptyText: props.tocEmptyText
    };
  }
}; 