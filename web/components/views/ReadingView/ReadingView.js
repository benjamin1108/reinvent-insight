/**
 * ReadingView组件
 * 文章阅读界面，集成目录解析、版本选择等功能
 */
export default {
  dependencies: [
    ['version-selector', '/components/shared/VersionSelector', 'VersionSelector'],
    ['tech-button', '/components/shared/TechButton', 'TechButton']
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
    
    // 文档Hash ID（用于Quick-Insight API）
    documentHash: {
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
    'toc-resize',
    'insight-mode-change',
    'quick-insight-load'
  ],
  
  setup(props, { emit }) {
    const { ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue;
    
    // 引用
    const tocSidebar = ref(null);
    
    // 状态管理
    const userTocPreference = ref(props.initialShowToc); // 用户的TOC偏好设置
    const tocWidth = ref(props.initialTocWidth);
    const isDragging = ref(false);
    const dragStartX = ref(0);
    const dragStartWidth = ref(0);
    const parsedSections = ref([]);
    const activeSection = ref('');
    let scrollTimer = null;
    
    // 智能TOC显示逻辑：Quick-Insight模式下强制隐藏，Deep-Insight模式下根据用户偏好
    const isTocVisible = computed(() => {
      // Quick-Insight模式下强制隐藏TOC，因为AI生成的HTML有自己的导航布局
      if (currentInsightMode.value === 'quick') {
        return false;
      }
      // Deep-Insight模式下根据用户偏好显示
      return userTocPreference.value;
    });
    
    // Quick-Insight 相关状态
    const currentInsightMode = ref('deep'); // 'deep' | 'quick'
    const hasQuickInsight = ref(false);
    const quickInsightContent = ref('');
    const quickIframeSrcdoc = ref(''); // iframe srcdoc 内容
    const quickInsightLoading = ref(false);
    const quickInsightError = ref('');
    const insightMetadata = ref(null);
    
    // Quick-Insight API 调用方法
    const checkQuickInsightAvailability = async () => {
      if (!props.documentHash) {
        hasQuickInsight.value = false;
        return Promise.resolve(null);
      }
      
      try {
        const response = await axios.get(`/api/articles/${props.documentHash}/insight`);
        const data = response.data;
        
        hasQuickInsight.value = data.has_insight;
        if (data.has_insight) {
          insightMetadata.value = data.metadata;
          // 首次使用引导
          showQuickInsightTip();
        }
        
        return data;
      } catch (error) {
        console.error('检查Quick-Insight失败:', error);
        hasQuickInsight.value = false;
        return null;
      }
    };
    
        const cleanQuickInsightHtml = (htmlContent) => {
      if (!htmlContent) return '';
      
      let cleanedContent = htmlContent;
      
      // 简单清理：移除markdown代码块标记和基本的问题结构
      cleanedContent = cleanedContent.replace(/^```html\s*$/gm, '');
      cleanedContent = cleanedContent.replace(/^```\s*$/gm, '');
      
      // 移除可能形成悬浮黑条的header结构
      cleanedContent = cleanedContent.replace(/<header[^>]*class="[^"]*site-header[^"]*"[^>]*>[\s\S]*?<\/header>/gi, '');
      cleanedContent = cleanedContent.replace(/<header[^>]*>[\s\S]*?Reinvent Insight[\s\S]*?<\/header>/gi, '');
      
      // 移除title中的Reinvent Insight
      cleanedContent = cleanedContent.replace(/<title>([^<]*?)\s*\|\s*Reinvent Insight<\/title>/gi, '<title>$1</title>');
      cleanedContent = cleanedContent.replace(/<title>Reinvent Insight\s*\|\s*([^<]*?)<\/title>/gi, '<title>$1</title>');
      
      // 提取可在Vue中渲染的内容
      if (cleanedContent.includes('<!DOCTYPE html>')) {
        // 提取head中的style标签
        const headMatch = cleanedContent.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
        const bodyMatch = cleanedContent.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
        
        let styles = '';
        let bodyContent = '';
        
        if (headMatch) {
          // 提取所有style标签和link标签
          const styleMatches = headMatch[1].match(/<style[^>]*>[\s\S]*?<\/style>/gi) || [];
          const linkMatches = headMatch[1].match(/<link[^>]*>/gi) || [];
          styles = [...styleMatches, ...linkMatches].join('\n');
        }
        
        if (bodyMatch) {
          bodyContent = bodyMatch[1];
        }
        
        // 组合成可在Vue中渲染的HTML片段
        cleanedContent = `${styles}\n${bodyContent}`;
      }
      
      cleanedContent = cleanedContent.trim();
      
      return cleanedContent;
    };
    
    const loadQuickInsightContent = async (forceReload = false) => {
      if (!props.documentHash || (quickInsightContent.value && !forceReload)) {
        return; // 已经加载过了
      }
      
      quickInsightLoading.value = true;
      quickInsightError.value = '';
      
      try {
        const response = await axios.get(`/api/articles/${props.documentHash}/insight/content`);
        const cleanedContent = cleanQuickInsightHtml(response.data);
        
        // 验证清理后的内容是否为空
        if (!cleanedContent || cleanedContent.trim().length === 0) {
          throw new Error('Quick-Insight内容为空');
        }
        
        // 验证清理后的内容是否是有效的HTML
        if (!cleanedContent.includes('<') || !cleanedContent.includes('>')) {
          throw new Error('Quick-Insight内容不是有效的HTML');
        }
        
        quickInsightContent.value = cleanedContent;
        quickIframeSrcdoc.value = cleanedContent; // 设置 iframe srcdoc
        emit('quick-insight-load', { content: cleanedContent });
        
        console.log('Quick-Insight内容加载成功，长度:', cleanedContent.length);
        console.log('清理后内容预览:', cleanedContent.substring(0, 500));
        
        // 检查清理效果
        const hasDoctype = cleanedContent.includes('<!DOCTYPE html>');
        const hasStyle = cleanedContent.includes('<style>');
        const hasHeader = cleanedContent.includes('<header');
        const hasReinvent = cleanedContent.includes('Reinvent Insight');
        
        console.log('清理效果检查:');
        console.log('- 包含DOCTYPE:', hasDoctype);
        console.log('- 包含样式:', hasStyle);
        console.log('- 包含header:', hasHeader);
        console.log('- 包含Reinvent Insight:', hasReinvent);
        
        if (!hasDoctype && !hasStyle) {
          console.error('❌ 清理过度：缺少HTML结构和样式');
        } else if (hasDoctype && hasStyle && !hasHeader) {
          console.log('✅ 清理成功：保留样式，移除header');
        }
      } catch (error) {
        console.error('加载Quick-Insight内容失败:', error);
        quickInsightError.value = '加载Quick-Insight内容失败';
        quickIframeSrcdoc.value = '';
        
        // 如果是当前模式，自动切换回Deep-Insight模式
        if (currentInsightMode.value === 'quick') {
          currentInsightMode.value = 'deep';
          if (window.eventBus) {
            window.eventBus.emit('show-toast', {
              type: 'warning',
              message: 'Quick-Insight加载失败，已切换到Deep-Insight模式'
            });
          }
        } else {
          // 显示错误提示
          if (window.eventBus) {
            window.eventBus.emit('show-toast', {
              type: 'error',
              message: '加载Quick-Insight内容失败，请稍后重试'
            });
          }
        }
      } finally {
        quickInsightLoading.value = false;
      }
    };
    
    const switchInsightMode = async (mode) => {
      if (mode === currentInsightMode.value) return;
      
      if (mode === 'quick' && !hasQuickInsight.value) {
        // 显示提示：Quick-Insight不可用
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            type: 'warning',
            message: '该文章暂无Quick-Insight版本'
          });
        }
        return;
      }
      
      // 如果切换到Quick-Insight模式，强制重新加载内容（使用最新的清理逻辑）
      if (mode === 'quick') {
        await loadQuickInsightContent(true); // 强制重新加载
        if (quickInsightError.value) {
          return; // 加载失败，不切换模式
        }
      }
      
      currentInsightMode.value = mode;
      emit('insight-mode-change', { mode, hasQuickInsight: hasQuickInsight.value });
      
      // 保存用户偏好（文档特定 + 全局）
      localStorage.setItem('preferred-insight-mode', mode);
      if (props.documentHash) {
        localStorage.setItem(`insight-mode-${props.documentHash}`, mode);
      }
      
      // 切换模式后重新解析内容和重置状态
      await nextTick();
      
      // 重新解析内容（Deep-Insight模式需要重新解析TOC）
      if (cleanContent.value) {
        parsedSections.value = parseContent(cleanContent.value);
        ensureHeadingIds();
      }
      
      // 平滑滚动到顶部
      const container = document.querySelector('.reading-view__content');
      if (container) {
        container.scrollTo({ top: 0, behavior: 'smooth' });
      }
      
      // 如果切换回Deep-Insight模式，确保TOC状态正确
      if (mode === 'deep') {
        // 重新初始化TOC状态
        const savedTocPreference = localStorage.getItem('showToc');
        if (savedTocPreference !== null) {
          userTocPreference.value = savedTocPreference === 'true';
        }
      }
    };
    
    const showQuickInsightTip = () => {
      if (hasQuickInsight.value && !localStorage.getItem('quick-insight-tip-shown')) {
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            type: 'info',
            message: '🎉 发现新功能！点击 Quick-Insight 体验AI视觉化阅读',
            duration: 5000
          });
        }
        localStorage.setItem('quick-insight-tip-shown', 'true');
      }
    };
    
    const loadUserPreference = () => {
      // 优先使用当前文档的特定偏好
      if (props.documentHash) {
        const docPreference = localStorage.getItem(`insight-mode-${props.documentHash}`);
        if (docPreference && (docPreference === 'deep' || docPreference === 'quick')) {
          return docPreference;
        }
      }
      
      // 回退到全局偏好
      const globalPreference = localStorage.getItem('preferred-insight-mode');
      if (globalPreference && (globalPreference === 'deep' || globalPreference === 'quick')) {
        return globalPreference;
      }
      
      return 'deep'; // 默认模式
    };
    
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
    
    // 根据当前模式返回对应的内容
    const cleanContent = computed(() => {
      if (currentInsightMode.value === 'quick' && quickInsightContent.value) {
        return quickInsightContent.value;
      }
      // Deep-Insight模式：使用后端清理过的markdown内容
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
      // Quick-Insight模式下不允许切换TOC，显示提示
      if (currentInsightMode.value === 'quick') {
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            type: 'info',
            message: 'Quick-Insight模式下TOC已智能隐藏',
            duration: 2000
          });
        }
        return;
      }
      
      // Deep-Insight模式下切换用户偏好并保存
      userTocPreference.value = !userTocPreference.value;
      localStorage.setItem('showToc', userTocPreference.value.toString());
      emit('toc-toggle');
      
      // 确保在Deep-Insight模式下TOC状态正确更新
      nextTick(() => {
        if (cleanContent.value) {
          parsedSections.value = parseContent(cleanContent.value);
          ensureHeadingIds();
        }
      });
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
    
    // 监听文档Hash变化，重新检查Quick-Insight可用性和用户偏好
    watch(() => props.documentHash, (newHash) => {
      if (newHash) {
        // 重置状态
        hasQuickInsight.value = false;
        quickInsightContent.value = '';
        quickInsightError.value = '';
        
        // 加载新文档的用户偏好
        const preferredMode = loadUserPreference();
        currentInsightMode.value = preferredMode;
        
        // 检查新文档的Quick-Insight可用性
        checkQuickInsightAvailability().then(() => {
          if (preferredMode === 'quick' && hasQuickInsight.value) {
            loadQuickInsightContent(true); // 强制重新加载
          } else if (preferredMode === 'quick' && !hasQuickInsight.value) {
            currentInsightMode.value = 'deep';
          }
        });
      }
    });
    
    // 监听洞察模式变化，重新解析内容
    watch(currentInsightMode, () => {
      nextTick(() => {
        if (cleanContent.value) {
          parsedSections.value = parseContent(cleanContent.value);
          ensureHeadingIds();
        }
      });
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
      
      // 初始化用户TOC偏好（从localStorage加载）
      const savedTocPreference = localStorage.getItem('showToc');
      if (savedTocPreference !== null) {
        userTocPreference.value = savedTocPreference === 'true';
      }
      
      // Quick-Insight 初始化
      if (props.documentHash) {
        // 先加载用户偏好，再检查可用性
        const preferredMode = loadUserPreference();
        currentInsightMode.value = preferredMode; // 立即设置模式，避免闪切
        
        // 异步检查Quick-Insight可用性
        checkQuickInsightAvailability().then(() => {
          // API检查完成后，根据可用性调整模式
          if (preferredMode === 'quick' && hasQuickInsight.value) {
            // 如果偏好是quick且可用，预加载内容
            loadQuickInsightContent(true); // 强制重新加载
          } else if (preferredMode === 'quick' && !hasQuickInsight.value) {
            // 如果偏好是quick但不可用，回退到deep模式
            currentInsightMode.value = 'deep';
          }
        });
      }
      
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
    
    const adjustIframeHeight = (event) => {
      const iframe = event.target;
      try {
        // 尝试访问iframe内容获取实际高度
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        if (doc && doc.body) {
          const contentHeight = Math.max(
            doc.body.scrollHeight,
            doc.body.offsetHeight,
            doc.documentElement.clientHeight,
            doc.documentElement.scrollHeight,
            doc.documentElement.offsetHeight
          );
          
          // 设置iframe高度，确保有足够的空间
          iframe.style.height = Math.max(contentHeight + 50, 800) + 'px';
          console.log('✅ iframe高度已调整为:', iframe.style.height);
        }
      } catch (e) {
        // 沙盒限制下无法访问，使用默认高度策略
        console.log('⚠️ 无法访问iframe内容，使用默认高度策略');
        
        // 根据视口高度设置一个合理的默认高度
        const viewportHeight = window.innerHeight;
        const defaultHeight = Math.max(viewportHeight * 0.9, 800);
        iframe.style.height = defaultHeight + 'px';
        
        // 确保iframe可以正常滚动
        iframe.style.overflow = 'auto';
        iframe.scrolling = 'yes';
      }
    };
    
    return {
      // 引用
      tocSidebar,
      
      // 响应式状态
      isTocVisible,
      userTocPreference,
      tocWidth,
      isDragging,
      activeSection,
      
      // Quick-Insight 状态
      currentInsightMode,
      hasQuickInsight,
      quickInsightContent,
      quickIframeSrcdoc,
      quickInsightLoading,
      quickInsightError,
      insightMetadata,
      
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
      
      // Quick-Insight 方法
      switchInsightMode,
      checkQuickInsightAvailability,
      loadQuickInsightContent,
      cleanQuickInsightHtml,
      adjustIframeHeight,
      
      // props
      tocTitle: props.tocTitle,
      tocEmptyText: props.tocEmptyText
    };
  }
}; 