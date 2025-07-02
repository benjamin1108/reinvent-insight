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
    
    // 文档标题（中文）
    documentTitle: {
      type: String,
      default: ''
    },

    // 文档标题（英文）
    documentTitleEn: {
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
      type: Number,
      default: 1,
      validator: (value) => {
        return typeof value === 'number' && !isNaN(value) && isFinite(value);
      }
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
    const isTocVisible = computed(() => props.initialShowToc);
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
      
      headings.forEach((heading, index) => {
        const level = parseInt(heading.tagName.charAt(1));
        let id = heading.id;
        
        const originalText = heading.textContent.trim();
        
        // 如果没有ID，生成一个
        if (!id) {
          id = originalText
            .toLowerCase()
            .replace(/[^\w\u4e00-\u9fff\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/^-+|-+$/g, '');
          
          // 如果生成的ID为空或以数字开头，添加前缀
          if (!id || /^\d/.test(id)) {
            id = `section-${id || index}`;
          }
          
          // 确保ID以字母开头（CSS选择器要求）
          if (/^\d/.test(id)) {
            id = `section-${id}`;
          }
        }
        
        const section = {
          id,
          text: originalText,
          level,
          children: []
        };
        
        // 处理层级关系
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
      if (!sections || sections.length === 0) {
        return '';
      }
      
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
      
      let html = '<ul class="toc-list">';
      sections.forEach(section => {
        html += renderSection(section);
      });
      html += '</ul>';
      
      return html;
    };
    
    // 直接使用后端清理过的内容
    const cleanContent = computed(() => {
      // 后端已经清理了元数据，直接返回
      return props.content || '';
    });

    // 计算属性
    const hasMultipleVersions = computed(() => {
      return props.versions && props.versions.length > 1;
    });

    const tocHtml = computed(() => {
      if (!cleanContent.value) {
        return '';
      }
      
      parsedSections.value = parseContent(cleanContent.value);
      const html = generateTocHtml(parsedSections.value);
      
      return html;
    });
    
    // TOC相关方法
    const toggleToc = () => {
      emit('toc-toggle');
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
      // 使用nextTick确保DOM已更新
      nextTick(() => {
        // 尝试找到真正的滚动容器
        const possibleContainers = [
          document.querySelector('.reading-view__content'),
          document.querySelector('.reading-view'),
          document.documentElement,
          document.body,
          window
        ].filter(Boolean);
        
        // 优先使用内容容器查找元素
        const container = document.querySelector('.reading-view__content');
        
        if (!container) {
          return;
        }
        
        // 列出所有可用的标题ID用于调试
        const allHeadings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
        
        // 在文章正文中查找目标元素
        let element;
        try {
          if (typeof CSS !== 'undefined' && CSS.escape) {
            element = container.querySelector(`#${CSS.escape(sectionId)}`);
          } else {
            element = container.querySelector(`[id="${sectionId}"]`);
          }
        } catch (e) {
          element = document.getElementById(sectionId);
        }
        
        // 如果直接查找失败，进行智能匹配
        if (!element) {
          // 尝试多种ID格式匹配
          const idVariations = [
            sectionId,  // 原始ID
            `section-${sectionId}`,  // 添加section-前缀
            sectionId.replace(/^section-/, ''),  // 移除section-前缀
            sectionId.replace(/^\d+[-.]?\s*/, ''),  // 移除数字前缀
            `section-${sectionId.replace(/^\d+[-.]?\s*/, '')}`,  // section- + 无数字前缀
          ];
          
          // 逐个尝试ID变化形式
          for (const idVariation of idVariations) {
            try {
              if (typeof CSS !== 'undefined' && CSS.escape) {
                element = container.querySelector(`#${CSS.escape(idVariation)}`);
              } else {
                element = container.querySelector(`[id="${idVariation}"]`);
              }
              
              if (element) {
                break;
              }
            } catch (e) {
              // 忽略CSS.escape错误，继续尝试
            }
          }
          
          // 如果ID变化还是找不到，尝试文本内容匹配
          if (!element) {
            // 从原始sectionId提取核心关键词
            const keywords = sectionId
              .replace(/^(section-)?(\d+[-.]?\s*)?/, '')  // 移除前缀和数字
              .split(/[-_\s]+/)  // 按分隔符拆分
              .filter(word => word.length > 1);  // 过滤短词
            
            // 在标题中查找包含关键词的元素
            for (const heading of allHeadings) {
              const headingText = heading.textContent.trim().toLowerCase();
              const headingId = heading.id.toLowerCase();
              const targetLower = sectionId.toLowerCase();
              
              // 多种匹配策略
              const matchStrategies = [
                // 1. 精确ID匹配
                headingId === targetLower,
                // 2. ID包含匹配
                headingId.includes(targetLower) || targetLower.includes(headingId),
                // 3. 关键词匹配（所有关键词都要匹配）
                keywords.length > 0 && keywords.every(keyword => 
                  headingText.includes(keyword.toLowerCase()) || headingId.includes(keyword.toLowerCase())
                ),
                // 4. 部分关键词匹配（至少2个关键词匹配）
                keywords.length > 1 && keywords.filter(keyword => 
                  headingText.includes(keyword.toLowerCase()) || headingId.includes(keyword.toLowerCase())
                ).length >= Math.min(2, keywords.length),
                // 5. 数字序号匹配
                /^\d+/.test(sectionId) && headingText.includes(sectionId.match(/^\d+/)[0])
              ];
              
              for (let i = 0; i < matchStrategies.length; i++) {
                if (matchStrategies[i]) {
                  element = heading;
                  break;
                }
              }
              
              if (element) break;
            }
          }
        }
        
        if (!element) {
          return;
        }
        
        // 检测哪个容器是真正的滚动容器
        let scrollContainer = null;
        
        for (const testContainer of possibleContainers) {
          if (testContainer === window) {
            // window总是可以滚动
            scrollContainer = window;
            break;
          } else {
            const style = window.getComputedStyle(testContainer);
            const hasScroll = style.overflow === 'auto' || 
                            style.overflow === 'scroll' || 
                            style.overflowY === 'auto' || 
                            style.overflowY === 'scroll' ||
                            testContainer.scrollHeight > testContainer.clientHeight;
            
            if (hasScroll) {
              scrollContainer = testContainer;
              break;
            }
          }
        }
        
        if (!scrollContainer) {
          scrollContainer = window; // 回退到window
        }
        
        // 执行滚动
        if (scrollContainer === window) {
          // 使用window滚动
          const elementRect = element.getBoundingClientRect();
          const targetTop = window.pageYOffset + elementRect.top - (props.scrollOffset || 80);
          
          window.scrollTo({
            top: Math.max(0, targetTop),
            behavior: 'smooth'
          });
        } else {
          // 使用容器滚动
          const containerRect = scrollContainer.getBoundingClientRect();
          const elementRect = element.getBoundingClientRect();
          const currentScrollTop = scrollContainer.scrollTop;
          const elementOffsetTop = elementRect.top - containerRect.top + currentScrollTop;
          const targetScrollTop = Math.max(0, elementOffsetTop - (props.scrollOffset || 80));
          
          scrollContainer.scrollTo({
            top: targetScrollTop,
            behavior: 'smooth'
          });
        }
        
        // 更新激活状态
        activeSection.value = sectionId;
        
        // 更新URL hash
        if (window.history.replaceState) {
          window.history.replaceState(null, null, `#${sectionId}`);
        }
        
        // 额外的备用方案：直接使用scrollIntoView
        setTimeout(() => {
          element.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start',
            inline: 'nearest'
          });
        }, 100);
      });
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
      // 处理文档内的锚点链接
      const target = event.target;
      if (target.tagName === 'A' && target.getAttribute('href')) {
        const href = target.getAttribute('href');
        
        // 如果是锚点链接（以#开头）
        if (href.startsWith('#')) {
          event.preventDefault();
          let sectionId = href.substring(1);
          
          // URL解码处理（文档内的链接可能被编码）
          try {
            sectionId = decodeURIComponent(sectionId);
          } catch (e) {
            // 使用原始ID
          }
          
          if (sectionId) {
            scrollToSection(sectionId);
            return;
          }
        }
      }
      
      emit('article-click', event);
    };
    
    // 版本相关方法
    const handleVersionChange = (version) => {
      emit('version-change', version);
    };
    
    // 响应式处理
    const handleResize = () => {
      // 在移动设备上自动隐藏TOC
      if (window.innerWidth <= 768 && isTocVisible.value) {
        emit('toc-toggle');
      }
    };
    
    // 滚动监听：高亮当前章节
    const handleScroll = () => {
      if (!cleanContent.value) return;
      
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
      if (event.key === 'Escape' && window.innerWidth <= 768 && isTocVisible.value) {
        emit('toc-toggle');
      }
    };
    
    // 监听内容变化
    watch(() => cleanContent.value, () => {
      if (cleanContent.value) {
        // 使用nextTick确保DOM更新后再解析
        nextTick(() => {
          parsedSections.value = parseContent(cleanContent.value);
          // 确保实际DOM中的标题也有ID
          ensureHeadingIds();
        });
      }
    });
    
    // 确保实际DOM中的标题有ID
    const ensureHeadingIds = () => {
      const container = document.querySelector('.reading-view__content');
      if (!container) {
        return;
      }
      
      const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
      
      headings.forEach((heading, index) => {
        if (!heading.id) {
          const text = heading.textContent.trim();
          let id = text
            .toLowerCase()
            .replace(/[^\w\u4e00-\u9fff\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/^-+|-+$/g, '');
          
          // 如果生成的ID为空或以数字开头，添加前缀
          if (!id || /^\d/.test(id)) {
            id = `section-${id || index}`;
          }
          
          // 确保ID以字母开头（CSS选择器要求）
          if (/^\d/.test(id)) {
            id = `section-${id}`;
          }
          
          // 确保ID唯一
          let finalId = id;
          let counter = 1;
          while (document.getElementById(finalId)) {
            finalId = `${id}-${counter}`;
            counter++;
          }
          
          heading.id = finalId;
        }
      });
      
      // 调用标记函数隐藏正文目录数字
      markInBodyToc();
    };
    
    // helper to mark in-body directory ordered list (正文章节目录)，用于隐藏数字
    const markInBodyToc = () => {
      const bodyEl = document.querySelector('.reading-view__body');
      if (!bodyEl) return;
      const headings = bodyEl.querySelectorAll('h1, h2, h3, h4, h5, h6');
      headings.forEach(h => {
        const text = h.textContent.trim();
        if (/目录/.test(text)) {
          let el = h.nextElementSibling;
          while (el && el.nodeType !== 1) {
            el = el.nextSibling;
          }
          if (el && el.tagName === 'OL') {
            el.setAttribute('data-inbody-toc', 'true');
          }
        }
      });
    };
    
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
      if (cleanContent.value) {
        nextTick(() => {
          parsedSections.value = parseContent(cleanContent.value);
          ensureHeadingIds();
        });
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
      emit('toc-toggle');
      tocWidth.value = props.initialTocWidth;
    };
    
    return {
      // 引用
      tocSidebar,
      
      // 响应式状态
      isTocVisible,
      tocWidth,
      isDragging,
      activeSection,
      
      // 计算属性
      hasMultipleVersions,
      tocHtml,
      cleanContent,
      
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