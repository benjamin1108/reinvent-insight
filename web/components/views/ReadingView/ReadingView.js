/**
 * ReadingView组件
 * 文章阅读界面，集成目录解析、版本选择等功能
 */
export default {
  dependencies: [
    ['version-selector', '/components/shared/VersionSelector', 'VersionSelector'],
    ['mode-selector', '/components/shared/ModeSelector', 'ModeSelector'],
    ['mode-toggle', '/components/shared/ModeToggle', 'ModeToggle']
  ],
  
  components: {
    'core-summary-view': {
      template: `
        <div class="core-summary-view">
          <div v-if="!hasData" class="core-summary-view__placeholder">
            <div class="core-summary-view__placeholder-card">
              <div class="core-summary-view__placeholder-icon">📌</div>
              <h2 class="core-summary-view__placeholder-title">核心要点</h2>
              <div class="core-summary-view__placeholder-content">
                <div class="core-summary-view__placeholder-badge">🚀 功能即将推出</div>
                <p class="core-summary-view__placeholder-text">
                  我们正在开发核心要点提取功能，将为您智能提炼文章的关键信息和核心观点。
                </p>
                <p class="core-summary-view__placeholder-text">
                  敬请期待！
                </p>
              </div>
            </div>
          </div>
          <div v-else class="core-summary-view__content">
            <!-- TODO: 后端数据接入后实现 -->
          </div>
        </div>
      `,
      props: {
        summaryData: {
          type: Object,
          default: null
        }
      },
      setup(props) {
        const { computed } = Vue;
        const hasData = computed(() => {
          return props.summaryData && props.summaryData.keyPoints && props.summaryData.keyPoints.length > 0;
        });
        return { hasData };
      }
    },
    'simplified-text-view': {
      template: `
        <div class="simplified-text-view">
          <div v-if="!hasContent" class="simplified-text-view__placeholder">
            <div class="simplified-text-view__placeholder-header">
              <div class="simplified-text-view__placeholder-icon">📝</div>
              <h2 class="simplified-text-view__placeholder-title">精简摘要</h2>
            </div>
            <div class="simplified-text-view__placeholder-content">
              <p class="simplified-text-view__placeholder-badge">功能即将推出</p>
              <p class="simplified-text-view__placeholder-text">
                我们正在开发精简摘要功能，将为您提供简洁易读的文章概要，帮助您快速了解文章的主要内容和核心观点。
              </p>
              <p class="simplified-text-view__placeholder-text">
                敬请期待！
              </p>
            </div>
          </div>
          <div v-else class="simplified-text-view__content">
            <div class="simplified-text-view__text" v-html="simplifiedContent"></div>
          </div>
        </div>
      `,
      props: {
        simplifiedContent: {
          type: String,
          default: ''
        }
      },
      setup(props) {
        const { computed } = Vue;
        const hasContent = computed(() => {
          return props.simplifiedContent && props.simplifiedContent.trim().length > 0;
        });
        return { hasContent };
      }
    }
  },
  
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
    },
    
    // ========== 显示模式相关 Props ==========
    
    // 初始显示模式
    initialDisplayMode: {
      type: String,
      default: 'full-analysis',
      validator: (value) => ['quick', 'deep'].includes(value)
    },
    
    // 核心要点数据（预留后端数据接口）
    coreSummary: {
      type: Object,
      default: null
      // 预期数据格式：
      // {
      //   keyPoints: [
      //     {
      //       title: string,        // 要点标题
      //       content: string,      // 要点内容
      //       importance: 'high' | 'medium' | 'low'  // 重要程度
      //     }
      //   ],
      //   mainTheme: string,        // 主题
      //   tags: string[],           // 标签
      //   generatedAt: string       // ISO 8601 时间戳
      // }
    },
    
    // 精简摘要内容（预留后端数据接口）
    simplifiedText: {
      type: String,
      default: ''
      // 预期数据格式：纯文本或简单 Markdown
      // 示例：
      // "本文介绍了...\n\n主要观点包括：\n1. ...\n2. ...\n\n结论：..."
    },
    
    // 当前文档的哈希值（用于获取可视化解读）
    currentHash: {
      type: String,
      default: ''
    }
  },
  
  emits: [
    'toc-click',
    'article-click',
    'version-change',
    'toc-toggle',
    'toc-resize',
    'display-mode-change'
  ],
  
  setup(props, { emit }) {
    const { ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue;
    
    // 引用
    const tocSidebar = ref(null);
    const visualIframe = ref(null);
    
    // 状态管理
    // 移动端强制隐藏 TOC，不管 props 如何设置
    const isMobile = window.innerWidth <= 768;
    const isTocVisible = ref(isMobile ? false : props.initialShowToc);
    const tocWidth = ref(props.initialTocWidth);
    const isDragging = ref(false);
    const dragStartX = ref(0);
    const dragStartWidth = ref(0);
    const parsedSections = ref([]);
    const activeSection = ref('');
    let scrollTimer = null;
    let heightUpdateTimer = null; // 🔧 修复：添加缺失的 heightUpdateTimer 定义
    
    // ========== 显示模式状态管理 ==========
    const displayMode = ref(props.initialDisplayMode);
    
    // ========== 可视化解读状态管理 ==========
    const visualAvailable = ref(false);
    const visualStatus = ref('pending');  // 'pending' | 'processing' | 'completed' | 'failed'
    const visualHtmlUrl = ref(null);
    const currentVersion = ref(props.currentVersion || 0);  // 从 props 初始化
    
    // ========== Ultra DeepInsight 状态管理 ==========
    const ultraAvailable = ref(false);      // Ultra版本是否可用
    const ultraStatus = ref('checking');    // 'checking' | 'not_exists' | 'generating' | 'completed' | 'failed'
    const isGeneratingUltra = ref(false);   // 是否正在生成Ultra
    const ultraVersion = ref(null);         // Ultra版本号
    const ultraWordCount = ref(0);          // Ultra版本字数
    const ultraTaskInfo = ref(null);        // Ultra任务信息（进度、阶段等）
    let ultraPollingTimer = null;           // Ultra状态轮询定时器
    let visualPollingTimer = null;           // 可视化状态轮询定时器
    let unsubscribeRefreshStatus = null;    // 取消订阅刷新状态事件
    
    // 根据显示模式决定是否显示目录
    // 只有"Deep Insight"模式才显示目录（不是 Quick Insight）
    // 移动端（包括 iPad）强制隐藏 TOC
    const shouldShowToc = computed(() => {
      // 检测是否为移动设备（包括平板）
      const isMobile = window.innerWidth <= 768;
      const result = !isMobile && displayMode.value !== 'quick' && isTocVisible.value;
      console.log('🔍 [DEBUG] shouldShowToc 计算:', {
        isMobile,
        windowWidth: window.innerWidth,
        displayMode: displayMode.value,
        isTocVisible: isTocVisible.value,
        result
      });
      return result;
    });
    
    // 解析内容HTML生成目录结构（只显示3级标题：h1, h2, h3）
    const parseContent = (html) => {
      if (!html) return [];
      
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      // 只选择 h1, h2, h3 标题
      const headings = doc.querySelectorAll('h1, h2, h3');
      
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
    
    // 生成目录HTML（不带编号，因为标题本身已有编号）
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
    
    // 检查是否已登录
    const isAuthenticated = computed(() => {
      return !!localStorage.getItem('authToken');
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
      console.log('🔄 [DEBUG] toggleToc 被调用');
      console.log('🔍 [DEBUG] 当前 isTocVisible:', isTocVisible.value);
      console.log('🔍 [DEBUG] 当前 displayMode:', displayMode.value);
      
      isTocVisible.value = !isTocVisible.value;
      
      console.log('✅ [DEBUG] 切换后 isTocVisible:', isTocVisible.value);
      console.log('✅ [DEBUG] shouldShowToc:', shouldShowToc.value);
      
      emit('toc-toggle', isTocVisible.value);
    };
    
    const handleTocClick = (event) => {
      console.log('📌 [DEBUG] handleTocClick 被触发');
      console.log('📌 [DEBUG] event.target:', event.target);
      
      const target = event.target;
      
      if (target.tagName === 'A') {
        event.preventDefault();
        event.stopPropagation(); // 🔧 阻止冒泡
        
        const targetId = target.getAttribute('data-target');
        console.log('📌 [DEBUG] targetId:', targetId);
        
        if (targetId) {
          scrollToSection(targetId);
          emit('toc-click', { targetId, event });
        }
      }
    };
    
    // 滚动到指定章节
    const scrollToSection = (sectionId) => {
      console.log('🎯 [DEBUG] scrollToSection 被调用，目标 ID:', sectionId);
      
      // 使用nextTick确保DOM已更新
      nextTick(() => {
        // 优先在文章正文中查找元素（.reading-view__body 包含实际的文章内容）
        const bodyContainer = document.querySelector('.reading-view__body');
        
        if (!bodyContainer) {
          console.warn('⚠️ [DEBUG] 找不到 .reading-view__body');
          return;
        }
        
        // 列出所有可用的标题ID用于调试
        const allHeadings = bodyContainer.querySelectorAll('h1, h2, h3, h4, h5, h6');
        
        // 在文章正文中查找目标元素
        let element;
        try {
          if (typeof CSS !== 'undefined' && CSS.escape) {
            element = bodyContainer.querySelector(`#${CSS.escape(sectionId)}`);
          } else {
            element = bodyContainer.querySelector(`[id="${sectionId}"]`);
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
                element = bodyContainer.querySelector(`#${CSS.escape(idVariation)}`);
              } else {
                element = bodyContainer.querySelector(`[id="${idVariation}"]`);
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
          console.warn('⚠️ [DEBUG] 找不到目标元素:', sectionId);
          return;
        }
        
        console.log('✅ [DEBUG] 找到目标元素:', element);
        
        // 找到真正的滚动容器
        // 尝试顺序：.reading-view__content -> .reading-view -> window
        const possibleContainers = [
          document.querySelector('.reading-view__content'),
          document.querySelector('.reading-view'),
          window
        ].filter(Boolean);
        
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
        
        // 执行滚动 - 使用统一的 scrollIntoView 方法
        // 计算目标位置，考虑 scrollOffset
        const scrollOffset = props.scrollOffset || 80;
        
        // 获取元素相对于滚动容器的位置
        const elementRect = element.getBoundingClientRect();
        const containerRect = scrollContainer === window 
          ? { top: 0 } 
          : scrollContainer.getBoundingClientRect();
        
        // 计算目标滚动位置
        const elementTop = elementRect.top - containerRect.top;
        const currentScroll = scrollContainer === window 
          ? window.pageYOffset 
          : scrollContainer.scrollTop;
        
        const targetScroll = currentScroll + elementTop - scrollOffset;
        
        // 执行滚动
        if (scrollContainer === window) {
          window.scrollTo({
            top: Math.max(0, targetScroll),
            behavior: 'smooth'
          });
        } else {
          scrollContainer.scrollTo({
            top: Math.max(0, targetScroll),
            behavior: 'smooth'
          });
        }
        
        // 更新激活状态
        activeSection.value = sectionId;
        
        // 更新URL hash
        if (window.history.replaceState) {
          window.history.replaceState(null, null, `#${sectionId}`);
        }
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
      // 📝 注意：文档内的 TOC 链接已由 rebindInDocumentTocLinks() 处理
      // 这里只处理其他点击事件
      emit('article-click', event);
    };
    
    // 版本相关方法
    const handleVersionChange = (version) => {
      emit('version-change', version);
    };
    
    // ========== 显示模式相关方法 ==========
    
    // 处理显示模式切换
    const handleDisplayModeChange = async (mode) => {
      try {
        if (mode === displayMode.value) return;
        
        // 切换到 quick 模式时，确保 URL 已设置并强制刷新
        if (mode === 'quick' && visualAvailable.value) {
          const newUrl = `/api/article/${props.currentHash}/visual?version=${currentVersion.value}&t=${Date.now()}`;
          visualHtmlUrl.value = newUrl;
          console.log('🔄 [DEBUG] 切换到 quick 模式，刷新 URL:', newUrl);
        }
        
        displayMode.value = mode;
        
        // 使用 nextTick 确保视图更新
        await nextTick();
        
        emit('display-mode-change', mode);
      } catch (error) {
        console.error('模式切换失败:', error);
      }
    };
    
    // ========== 可视化解读相关方法 ==========
    
    // 检查可视化状态
    const checkVisualStatus = async () => {
      console.log('🔍 [Visual] checkVisualStatus 开始');
      console.log('🔍 [Visual] currentHash:', props.currentHash);
      console.log('🔍 [Visual] currentVersion:', currentVersion.value);
      
      if (!props.currentHash) {
        console.log('⚠️ [Visual] 没有 currentHash，跳过检查');
        return 'not_exists';
      }
      
      try {
        const url = `/api/article/${props.currentHash}/visual/status?version=${currentVersion.value}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('🔍 [Visual] API 响应:', data);
        
        const status = data.status || 'not_exists';
        visualStatus.value = status;
        visualAvailable.value = status === 'completed';
        
        if (visualAvailable.value) {
          visualHtmlUrl.value = `/api/article/${props.currentHash}/visual?version=${currentVersion.value}`;
          console.log('✅ [Visual] 可视化可用，URL:', visualHtmlUrl.value);
          stopVisualPolling();
        } else if (status === 'processing') {
          console.log('🔄 [Visual] 可视化正在生成中，启动轮询');
          startVisualPolling();
        } else {
          console.log('⚠️ [Visual] 可视化不可用，状态:', status);
        }
        
        return status;
      } catch (error) {
        console.error('❌ [Visual] 检查可视化状态失败:', error);
        return 'error';
      }
    };
    
    // 启动可视化状态轮询
    const startVisualPolling = () => {
      if (visualPollingTimer) {
        return; // 避免重复轮询
      }
      
      console.log('🔄 [Visual] 启动状态轮询（每5秒）');
      
      visualPollingTimer = setInterval(async () => {
        const status = await checkVisualStatus();
        
        if (status === 'completed') {
          console.log('✅ [Visual] 检测到可视化完成，停止轮询');
          stopVisualPolling();
          
          // 显示提示
          if (window.eventBus) {
            window.eventBus.emit('show-toast', {
              message: '可视化解读已完成，可切换查看',
              type: 'success'
            });
          }
        } else if (status === 'failed' || status === 'error') {
          console.log('❌ [Visual] 检测到可视化失败，停止轮询');
          stopVisualPolling();
        }
      }, 5000); // 每5秒检查一次
    };
    
    // 停止可视化状态轮询
    const stopVisualPolling = () => {
      if (visualPollingTimer) {
        console.log('🛑 [Visual] 停止状态轮询');
        clearInterval(visualPollingTimer);
        visualPollingTimer = null;
      }
    };
    
    // ========== Ultra DeepInsight 相关方法 ==========
    
    // 检查Ultra DeepInsight状态
    const checkUltraStatus = async () => {
      console.log('🔍 [Ultra] checkUltraStatus 开始');
      console.log('🔍 [Ultra] currentHash:', props.currentHash);
      
      if (!props.currentHash) {
        console.log('⚠️ [Ultra] 没有 currentHash，跳过检查');
        return 'not_exists';
      }
      
      try {
        const url = `/api/article/${props.currentHash}/ultra-deep/status`;
        console.log('🔍 [Ultra] 请求 URL:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('🔍 [Ultra] API 响应:', data);
        
        const status = data.status || 'not_exists';
        ultraStatus.value = status;
        ultraAvailable.value = data.exists && status === 'completed';
        
        // 保存任务信息（用于进度显示）
        if (status === 'generating' && data.task_info) {
          ultraTaskInfo.value = data.task_info;
          console.log('🔄 [Ultra] 任务进行中，进度信息:', ultraTaskInfo.value);
          
          // 启动轮询
          startUltraPolling();
        } else {
          ultraTaskInfo.value = null;
        }
        
        if (ultraAvailable.value) {
          ultraVersion.value = data.version;
          ultraWordCount.value = data.word_count || 0;
          console.log('✅ [Ultra] Ultra版本可用，版本:', ultraVersion.value, '字数:', ultraWordCount.value);
          
          // 停止轮询
          stopUltraPolling();
        } else if (status === 'failed') {
          console.log('❌ [Ultra] Ultra生成失败');
          stopUltraPolling();
        } else {
          console.log('🔴 [Ultra] Ultra版本不可用，状态:', ultraStatus.value);
        }
        
        return status;
      } catch (error) {
        console.error('❌ [Ultra] 检查Ultra状态失败:', error);
        ultraStatus.value = 'not_exists';
        ultraAvailable.value = false;
        ultraTaskInfo.value = null;
        return 'not_exists';
      }
    };
    
    // 启动Ultra状态轮询
    const startUltraPolling = () => {
      if (ultraPollingTimer) {
        console.log('🔄 [Ultra] 轮询已在运行中');
        return; // 避免重复轮询
      }
      
      console.log('🔄 [Ultra] 启动状态轮询（每10秒）');
      
      ultraPollingTimer = setInterval(async () => {
        console.log('🔄 [Ultra] 执行轮询检查...');
        const status = await checkUltraStatus();
        
        if (status === 'completed') {
          console.log('✅ [Ultra] 检测到生成完成，停止轮询');
          stopUltraPolling();
          
          // 触发自动切换到Ultra版本（问题3）
          await handleUltraCompleted();
        } else if (status === 'failed') {
          console.log('❌ [Ultra] 检测到生成失败，停止轮询');
          stopUltraPolling();
        }
      }, 10000); // 每10秒检查一次
    };
    
    // 停止Ultra状态轮询
    const stopUltraPolling = () => {
      if (ultraPollingTimer) {
        console.log('🛑 [Ultra] 停止状态轮询');
        clearInterval(ultraPollingTimer);
        ultraPollingTimer = null;
      }
    };
    
    // 处理Ultra生成完成（自动切换）
    const handleUltraCompleted = async () => {
      console.log('✅ [Ultra] Ultra生成完成，准备自动切换');
      
      try {
        // 显示完成提示
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: 'Ultra DeepInsight 已生成完成！正在自动加载...',
            type: 'success'
          });
        }
        
        // 自动刷新页面以加载新的Ultra版本
        // 通过触发事件让父组件重新加载文档
        if (props.currentHash && window.eventBus) {
          console.log('🔄 [Ultra] 触发重新加载文档');
          window.eventBus.emit('reload-document', {
            hash: props.currentHash,
            reason: 'ultra_completed'
          });
        }
        
        isGeneratingUltra.value = false;
      } catch (error) {
        console.error('❌ [Ultra] 自动切换失败:', error);
      }
    };
    
    // 触发Ultra DeepInsight生成
    const triggerUltraGeneration = async () => {
      console.log('🚀 [Ultra] 触发Ultra生成');
      
      if (!props.currentHash) {
        console.error('❌ [Ultra] 没有 currentHash');
        return;
      }
      
      // 检查认证状态
      const token = localStorage.getItem('authToken');
      if (!token) {
        console.log('🔑 [Ultra] 未登录，触发登录请求');
        
        // 触发登录请求事件
        if (window.eventBus) {
          window.eventBus.emit('require-login', {
            reason: 'Ultra DeepInsight功能需要登录',
            callback: () => {
              // 登录成功后自动重试
              console.log('✅ [Ultra] 登录成功，重试Ultra生成');
              triggerUltraGeneration();
            }
          });
        }
        return;
      }
      
      // 先检查当前状态，防止重复生成
      const currentStatus = await checkUltraStatus();
      
      if (currentStatus === 'generating') {
        console.warn('⚠️ [Ultra] Ultra生成任务已在进行中');
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: 'Ultra DeepInsight 正在生成中，请稍候...',
            type: 'info'
          });
        }
        return;
      }
      
      if (currentStatus === 'completed') {
        console.warn('⚠️ [Ultra] Ultra版本已存在');
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: 'Ultra DeepInsight 版本已存在',
            type: 'info'
          });
        }
        return;
      }
      
      if (isGeneratingUltra.value) {
        console.warn('⚠️ [Ultra] 已在生成中');
        return;
      }
      
      try {
        isGeneratingUltra.value = true;
        ultraStatus.value = 'generating';
        
        const url = `/api/article/${props.currentHash}/ultra-deep`;
        console.log('🔍 [Ultra] POST 请求 URL:', url);
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        const data = await response.json();
        console.log('🔍 [Ultra] 响应:', data);
        
        // 处理01错误（会话过期）
        if (response.status === 401) {
          console.log('⚠️ [Ultra] 会话已过期');
          localStorage.removeItem('authToken');
          if (window.eventBus) {
            window.eventBus.emit('session-expired');
          }
          isGeneratingUltra.value = false;
          return;
        }
        
        if (!response.ok) {
          throw new Error(data.detail || data.message || 'Ultra生成失败');
        }
        
        if (data.success) {
          console.log('✅ [Ultra] 生成任务已启动，task_id:', data.task_id);
          
          // 显示提示
          if (window.eventBus) {
            window.eventBus.emit('show-toast', {
              message: 'Ultra DeepInsight 生成中，预计15-20分钟',
              type: 'info'
            });
          }
          
          // 启动轮询
          startUltraPolling();
        }
      } catch (error) {
        console.error('❌ [Ultra] 生成失败:', error);
        ultraStatus.value = 'failed';
        isGeneratingUltra.value = false;
        
        // 显示错误提示
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: error.message || 'Ultra DeepInsight 生成失败',
            type: 'danger'
          });
        }
      }
    };
    

    
    // 处理版本切换（同步可视化版本）
    const handleVersionChangeWithVisual = async (version) => {
      currentVersion.value = version;
      
      // 重新检查当前版本的可视化状态
      await checkVisualStatus();
      
      // 触发原有的版本切换事件
      emit('version-change', version);
    };
    
    // ========== iframe 相关方法 ==========
    
    // 处理 iframe 加载完成事件
    const handleIframeLoad = () => {
      const iframe = visualIframe.value;
      
      try {
        if (!iframe || !iframe.contentWindow) {
          throw new Error('无法访问 iframe');
        }
        
        // 尝试访问 iframe 内容（可能因跨域失败）
        try {
          const doc = iframe.contentDocument || iframe.contentWindow.document;
          
          // 检查是否为错误页面
          if (doc && (doc.title.includes('Error') || doc.title.includes('404'))) {
            throw new Error('可视化内容不存在');
          }
          
          // 临时方案：如果 iframe 内容没有高度通信脚本，手动注入
          if (doc && doc.body) {
            // 检查是否已有脚本
            const hasScript = doc.body.innerHTML.includes('iframe-height');
            
            if (!hasScript) {
              console.log('🔧 [DEBUG] 检测到旧的可视化 HTML，手动注入通信脚本');
              
              const script = doc.createElement('script');
              script.textContent = `
(function() {
  function sendHeight() {
    // 🔧 最优化的高度计算：使用多种方法取最合理值
    
    // 方法1: body 的 scrollHeight
    const bodyScrollHeight = document.body.scrollHeight;
    
    // 方法2: documentElement 的 scrollHeight
    const docScrollHeight = document.documentElement.scrollHeight;
    
    // 方法3: body 的 offsetHeight
    const bodyOffsetHeight = document.body.offsetHeight;
    
    // 方法4: 查找最后一个可见元素的底部位置
    let lastVisibleBottom = 0;
    const allElements = Array.from(document.body.children);
    
    // 只检查 body 的直接子元素，避免过度计算
    allElements.forEach(el => {
      const style = window.getComputedStyle(el);
      
      // 跳过隐藏和定位元素
      if (style.display === 'none' || 
          style.visibility === 'hidden' || 
          style.position === 'absolute' || 
          style.position === 'fixed') {
        return;
      }
      
      const rect = el.getBoundingClientRect();
      const bottom = rect.bottom + window.pageYOffset;
      
      if (bottom > lastVisibleBottom) {
        lastVisibleBottom = bottom;
      }
    });
    
    // 取所有方法中的中位数（更稳定的估计）
    const heights = [
      bodyScrollHeight,
      docScrollHeight,
      bodyOffsetHeight,
      lastVisibleBottom
    ].filter(h => h > 0).sort((a, b) => a - b);
    
    // 使用中位数或平均值
    let finalHeight;
    if (heights.length >= 2) {
      // 取中间两个值的平均值
      const mid = Math.floor(heights.length / 2);
      finalHeight = heights.length % 2 === 0 
        ? (heights[mid - 1] + heights[mid]) / 2 
        : heights[mid];
    } else {
      finalHeight = heights[0] || bodyScrollHeight;
    }
    
    // 添加适度缓冲（50px）
    finalHeight = Math.ceil(finalHeight) + 50;
    
    console.log('📏 [iframe] 高度计算详情:', {
      bodyScrollHeight,
      docScrollHeight,
      bodyOffsetHeight,
      lastVisibleBottom,
      allHeights: heights,
      finalHeight
    });
    
    window.parent.postMessage({
      type: 'iframe-height',
      height: finalHeight
    }, '*');
  }
  
  // 防抖函数
  let debounceTimer;
  function debouncedSendHeight() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(sendHeight, 300);
  }
  
  // 初始发送（延迟执行，确保渲染完成）
  if (document.readyState === 'complete') {
    setTimeout(sendHeight, 500);
  } else {
    window.addEventListener('load', () => setTimeout(sendHeight, 500));
  }
  
  // 监听窗口大小变化
  window.addEventListener('resize', debouncedSendHeight);
  
  // 使用 MutationObserver 监听 DOM 变化（防抖）
  const observer = new MutationObserver(debouncedSendHeight);
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: true
  });
  
  // 监听图片加载完成
  const images = document.querySelectorAll('img');
  let loadedImages = 0;
  images.forEach(img => {
    if (img.complete) {
      loadedImages++;
    } else {
      img.addEventListener('load', () => {
        loadedImages++;
        if (loadedImages === images.length) {
          setTimeout(sendHeight, 200);
        }
      });
    }
  });
})();
              `;
              doc.body.appendChild(script);
              console.log('✅ [DEBUG] 通信脚本注入成功');
            }
          }
        } catch (crossOriginError) {
          // 跨域限制，iframe将使用CSS定义的高度
          console.warn('⚠️ 跨域限制，无法访问 iframe 内容');
        }
        
        console.log('✅ iframe 加载成功');
      } catch (error) {
        console.error('❌ iframe 加载错误:', error);
        
        // 更新状态为失败
        visualStatus.value = 'failed';
        visualAvailable.value = false;
        
        // 可选：自动切换回 Deep Insight 模式
        // displayMode.value = 'deep';
      }
    };
    
    // iframe 消息监听器（简化版 - 不再处理高度）
    const setupIframeMessageListener = () => {
      // 预留给未来可能的iframe通信需求
      console.log('✅ iframe 已准备就绪');
    };
    
    // 清理 iframe 消息监听器
    const cleanupIframeMessageListener = () => {
      // 预留清理逻辑
    };
    
    // 全屏相关方法已移除
    
    // 响应式处理
    const handleResize = () => {
      // 在移动设备上自动隐藏TOC
      if (window.innerWidth <= 768 && isTocVisible.value) {
        isTocVisible.value = false;
        emit('toc-toggle', false);
      }
      // 强制触发 shouldShowToc 重新计算
      // 通过修改一个依赖项来触发
      nextTick(() => {
        console.log('📱 [DEBUG] 窗口大小变化，当前宽度:', window.innerWidth);
      });
    };
    
    // 处理页面可见性变化（应用切换时触发）
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('👁️ [DEBUG] 页面重新可见，检查布局');
        // 页面重新可见时，强制检查并修复布局
        nextTick(() => {
          const isMobile = window.innerWidth <= 768;
          if (isMobile && isTocVisible.value) {
            console.log('📱 [DEBUG] 应用切换后检测到移动端，强制隐藏 TOC');
            isTocVisible.value = false;
            emit('toc-toggle', false);
          }
          // 强制重新计算布局
          handleResize();
        });
      }
    };
    
    // 处理页面获得焦点（从其他应用切换回来）
    const handlePageFocus = () => {
      console.log('🔄 [DEBUG] 页面获得焦点');
      // 延迟执行，确保浏览器完成布局更新
      setTimeout(() => {
        const isMobile = window.innerWidth <= 768;
        if (isMobile && isTocVisible.value) {
          console.log('📱 [DEBUG] 焦点恢复后检测到移动端，强制隐藏 TOC');
          isTocVisible.value = false;
          emit('toc-toggle', false);
        }
        handleResize();
      }, 100); // 100ms 延迟，等待浏览器完成渲染
    };
    
    // 滚动监听：高亮当前章节
    const handleScroll = () => {
      if (!cleanContent.value) return;
      
      // 在文章正文中查找标题
      const bodyContainer = document.querySelector('.reading-view__body');
      if (!bodyContainer) return;
      
      // 获取滚动容器
      const scrollContainer = document.querySelector('.reading-view__content');
      if (!scrollContainer) return;
      
      const scrollTop = scrollContainer.scrollTop;
      
      // 获取所有标题元素
      const headings = bodyContainer.querySelectorAll('h1, h2, h3, h4, h5, h6');
      let currentSection = '';
      
      headings.forEach(heading => {
        if (heading.id) {
          const rect = heading.getBoundingClientRect();
          const containerRect = scrollContainer.getBoundingClientRect();
          const relativeTop = rect.top - containerRect.top;
          
          if (relativeTop <= props.scrollOffset + 10) {
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
          // 🔧 修复：初始加载时也需要绑定文档内 TOC 链接
          rebindInDocumentTocLinks();
        });
      }
    });
    
    // 确保实际DOM中的标题有ID
    const ensureHeadingIds = () => {
      // 在文章正文中查找标题
      const bodyContainer = document.querySelector('.reading-view__body');
      if (!bodyContainer) {
        return;
      }
      
      const headings = bodyContainer.querySelectorAll('h1, h2, h3, h4, h5, h6');
      
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
    
    // 🔧 修复：重新绑定文档内 TOC 链接的点击事件
    const rebindInDocumentTocLinks = () => {
      const bodyContainer = document.querySelector('.reading-view__body');
      if (!bodyContainer) {
        console.warn('⚠️ [DEBUG] 找不到 .reading-view__body，无法绑定文档内 TOC 链接');
        return;
      }
      
      // 查找所有文档内的锚点链接
      const tocLinks = bodyContainer.querySelectorAll('a[href^="#"]');
      console.log(`🔗 [DEBUG] 找到 ${tocLinks.length} 个文档内 TOC 链接`);
      
      tocLinks.forEach(link => {
        // 移除旧的事件监听器（如果有）
        const oldHandler = link._tocClickHandler;
        if (oldHandler) {
          link.removeEventListener('click', oldHandler);
        }
        
        // 创建新的事件处理器
        const newHandler = (event) => {
          // 🔑 关键修复：阻止默认行为和事件冒泡
          event.preventDefault();
          event.stopPropagation(); // 阻止冒泡，避免触发父元素的点击事件
          
          const href = link.getAttribute('href');
          if (href && href.startsWith('#')) {
            let sectionId = href.substring(1);
            
            // URL解码处理
            try {
              sectionId = decodeURIComponent(sectionId);
            } catch (e) {
              // 使用原始ID
            }
            
            console.log('🔗 [DEBUG] 文档内 TOC 链接点击，目标 ID:', sectionId);
            scrollToSection(sectionId);
          }
        };
        
        // 🔑 关键：使用 capture 阶段捕获事件，确保最先执行
        link.addEventListener('click', newHandler, true);
        // 保存引用以便后续移除
        link._tocClickHandler = newHandler;
      });
      
      console.log('✅ [DEBUG] 文档内 TOC 链接绑定完成');
    };
    
    // 监听活动章节变化，触发目录更新
    watch(activeSection, () => {
      // 触发 Vue 重新计算 tocHtml
    });
    
    // 🔍 调试：监控关键状态变化
    
    // 监听 props.initialShowToc 的变化，同步到本地状态
    watch(() => props.initialShowToc, (newVal, oldVal) => {
      console.log('🔄 [DEBUG] props.initialShowToc 变化:', oldVal, '->', newVal);
      console.log('🔍 [DEBUG] 当前本地 isTocVisible:', isTocVisible.value);
      
      // 移动端强制隐藏 TOC，不管 props 如何变化
      const isMobile = window.innerWidth <= 768;
      if (isMobile) {
        console.log('📱 [DEBUG] 移动端检测到，强制隐藏 TOC');
        if (isTocVisible.value !== false) {
          isTocVisible.value = false;
        }
        return;
      }
      
      // 同步 prop 到本地状态（仅桌面端）
      if (newVal !== isTocVisible.value) {
        console.log('✅ [DEBUG] 同步 prop 到本地状态');
        isTocVisible.value = newVal;
      }
    });
    
    watch(isTocVisible, (newVal, oldVal) => {
      console.log('🔄 [DEBUG] isTocVisible 变化:', oldVal, '->', newVal);
      console.log('🔍 [DEBUG] 当前 displayMode:', displayMode.value);
      console.log('🔍 [DEBUG] 计算后 shouldShowToc:', shouldShowToc.value);
    });
    
    watch(visualAvailable, (newVal, oldVal) => {
      console.log('🔄 [DEBUG] visualAvailable 变化:', oldVal, '->', newVal);
    });
    
    watch(visualStatus, (newVal, oldVal) => {
      console.log('🔄 [DEBUG] visualStatus 变化:', oldVal, '->', newVal);
    });
    
    watch(displayMode, (newVal, oldVal) => {
      console.log('🔄 [DEBUG] displayMode 变化:', oldVal, '->', newVal);
      console.log('🔍 [DEBUG] 当前 isTocVisible:', isTocVisible.value);
      console.log('🔍 [DEBUG] 当前 shouldShowToc:', shouldShowToc.value);
      
      // 从 Quick Insight 切换出去时，清理 iframe 资源
      if (oldVal === 'quick' && newVal !== 'quick') {
        const iframe = visualIframe.value;
        if (iframe) {
          // 设置 src 为 about:blank 释放内存
          iframe.src = 'about:blank';
          console.log('🧹 [DEBUG] 清理 iframe 资源');
        }
        
        // 清理高度更新定时器
        if (heightUpdateTimer) {
          clearTimeout(heightUpdateTimer);
          heightUpdateTimer = null;
        }
      }
      
      // 切换到 Deep Insight 模式时，重新初始化 DOM
      if (newVal === 'deep' && oldVal !== 'deep') {
        console.log('✅ [DEBUG] 切换到 Deep Insight 模式，重新初始化');
        // DOM 会被重新渲染，需要等待 DOM 更新后重新初始化标题 ID
        // 使用双重 nextTick 确保 v-html 内容完全渲染
        nextTick(() => {
          nextTick(() => {
            console.log('🔧 [DEBUG] 重新解析内容和初始化标题 ID');
            if (cleanContent.value) {
              parsedSections.value = parseContent(cleanContent.value);
              ensureHeadingIds();
              console.log('✅ [DEBUG] 标题 ID 初始化完成');
              
              // 🔧 修复：重新绑定文档内 TOC 链接的点击事件
              rebindInDocumentTocLinks();
              
              // 验证 DOM 元素是否存在
              const bodyContainer = document.querySelector('.reading-view__body');
              const scrollContainer = document.querySelector('.reading-view__content');
              console.log('🔍 [DEBUG] bodyContainer 存在:', !!bodyContainer);
              console.log('🔍 [DEBUG] scrollContainer 存在:', !!scrollContainer);
              
              if (bodyContainer) {
                const headings = bodyContainer.querySelectorAll('h1, h2, h3, h4, h5, h6');
                console.log('🔍 [DEBUG] 找到标题数量:', headings.length);
                console.log('🔍 [DEBUG] 前3个标题 ID:', 
                  Array.from(headings).slice(0, 3).map(h => h.id));
              }
            }
          });
        });
      }
    });
    
    watch(() => props.currentHash, (newVal, oldVal) => {
      console.log('🔄 [DEBUG] currentHash 变化:', oldVal, '->', newVal);
      if (newVal) {
        console.log('🔍 [DEBUG] currentHash 变化，重新检查状态');
        checkVisualStatus();
        checkUltraStatus();  // 同时检查Ultra状态
      }
    });
    
    // 同步 props.currentVersion 到内部变量
    watch(() => props.currentVersion, (newVal, oldVal) => {
      console.log('🔄 [DEBUG] props.currentVersion 变化:', oldVal, '->', newVal);
      if (newVal !== undefined && newVal !== null) {
        currentVersion.value = newVal;
        // 版本变化后重新检查可视化状态
        checkVisualStatus();
      }
    });
    
    // 生命周期
    onMounted(() => {
      console.log('🚀 [DEBUG] ReadingView onMounted');
      console.log('🔍 [DEBUG] 初始 props:', {
        currentHash: props.currentHash,
        initialDisplayMode: props.initialDisplayMode,
        currentVersion: props.currentVersion
      });
      console.log('🔍 [DEBUG] 初始状态:', {
        displayMode: displayMode.value,
        visualAvailable: visualAvailable.value,
        visualStatus: visualStatus.value
      });
      
      window.addEventListener('resize', handleResize);
      document.addEventListener('keydown', handleKeydown);
      
      // 添加页面可见性和焦点监听（处理应用切换）
      document.addEventListener('visibilitychange', handleVisibilityChange);
      window.addEventListener('focus', handlePageFocus);
      window.addEventListener('pageshow', handlePageFocus); // iOS Safari 特殊处理
      
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
      
      // 全屏监听已移除
      
      // 设置 iframe 消息监听器
      setupIframeMessageListener();
      
      // 初始响应式检查
      handleResize();
      
      // 🔧 Chrome iPad 特殊修复：强制刷新布局
      // 解决 Chrome 在 iPad 上缓存 CSS 变量导致的半屏问题
      const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
      const isMobile = window.innerWidth <= 768;
      
      if (isMobile) {
        console.log('📱 [CHROME FIX] 检测到移动端，强制刷新布局');
        console.log('🔍 [CHROME FIX] 浏览器:', isChrome ? 'Chrome' : 'Other');
        
        nextTick(() => {
          // 强制触发重排，清除可能的缓存
          const layout = document.querySelector('.reading-view__layout');
          const content = document.querySelector('.reading-view__content');
          
          if (layout && content) {
            // 方法1: 读取 offsetHeight 强制浏览器重新计算布局
            const _ = layout.offsetHeight;
            const __ = content.offsetHeight;
            
            // 方法2: 如果是 Chrome，使用更激进的修复
            if (isChrome) {
              console.log('🔧 [CHROME FIX] 应用 Chrome 特殊修复');
              
              // 临时移除并重新添加样式，强制 Chrome 重新渲染
              const originalLeft = content.style.left;
              content.style.left = '0px';
              
              // 使用 requestAnimationFrame 确保渲染完成
              requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                  content.style.left = originalLeft || '';
                  console.log('✅ [CHROME FIX] Chrome 特殊修复完成');
                });
              });
            }
            
            console.log('📱 [CHROME FIX] 布局已强制刷新');
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
      
      // 检查可视化状态
      console.log('🔍 [DEBUG] 准备检查可视化状态...');
      checkVisualStatus();
      
      // 检查Ultra DeepInsight状态
      console.log('🔍 [Ultra] 准备检查Ultra状态...');
      checkUltraStatus();
      
      // 监听刷新状态事件（用于Ultra完成后刷新）
      if (window.eventBus) {
        unsubscribeRefreshStatus = window.eventBus.on('refresh-reading-status', () => {
          console.log('🔄 [刷新] 收到刷新状态事件');
          checkVisualStatus();
          checkUltraStatus();
        });
      }
      
      // 添加打印前处理 - 修复分页问题
      const beforePrintHandler = () => {
        console.log('🖨️ [打印] 准备打印，强制移除flex布局...');
        const elements = document.querySelectorAll('.reading-view, .reading-view *, .reading-view__article, .reading-view__article-wrapper');
        elements.forEach(el => {
          // 跳过需要隐藏的元素
          if (el.matches('.reading-view__toc, .reading-view__version-selector, .reading-view__mode-toggle-wrapper, .reading-view__mode-toggle, .reading-view__ultra-button-wrapper, .reading-view__ultra-generating')) {
            return;
          }
          el.style.setProperty('position', 'static', 'important');
          el.style.setProperty('height', 'auto', 'important');
          el.style.setProperty('min-height', '0', 'important');
          el.style.setProperty('max-height', 'none', 'important');
          el.style.setProperty('overflow', 'visible', 'important');
          el.style.setProperty('flex', 'none', 'important');
        });
      };
      
      const afterPrintHandler = () => {
        console.log('🖨️ [打印] 打印完成，恢复样式');
        // 移除内联样式，恢复CSS控制
        const elements = document.querySelectorAll('.reading-view, .reading-view *, .reading-view__article, .reading-view__article-wrapper');
        elements.forEach(el => {
          el.style.removeProperty('position');
          el.style.removeProperty('height');
          el.style.removeProperty('min-height');
          el.style.removeProperty('max-height');
          el.style.removeProperty('overflow');
          el.style.removeProperty('flex');
        });
      };
      
      window.addEventListener('beforeprint', beforePrintHandler);
      window.addEventListener('afterprint', afterPrintHandler);
    });
    
    onUnmounted(() => {
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('keydown', handleKeydown);
      
      // 移除打印监听
      if (typeof beforePrintHandler !== 'undefined') {
        window.removeEventListener('beforeprint', beforePrintHandler);
        window.removeEventListener('afterprint', afterPrintHandler);
      }
      
      // 移除页面可见性和焦点监听
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handlePageFocus);
      window.removeEventListener('pageshow', handlePageFocus);
      
      // 移除拖动事件监听
      document.removeEventListener('mousemove', handleDrag);
      document.removeEventListener('mouseup', endDrag);
      document.removeEventListener('touchmove', handleDrag);
      document.removeEventListener('touchend', endDrag);
      
      // 全屏监听已移除
      
      // 清理 iframe 消息监听器
      cleanupIframeMessageListener();
      
      // 移除滚动监听
      const container = document.querySelector('.reading-view__content');
      if (container) {
        container.removeEventListener('scroll', debouncedHandleScroll);
      }
      
      // 清理定时器
      if (scrollTimer) {
        clearTimeout(scrollTimer);
      }
      
      // 清理Ultra轮询定时器
      stopUltraPolling();
      
      // 清理可视化轮询定时器
      stopVisualPolling();
      
      // 清理刷新状态事件监听
      if (unsubscribeRefreshStatus) {
        unsubscribeRefreshStatus();
      }
    });
    

    // 下载 Markdown 原文
    const downloadMarkdown = () => {
      try {
        // 获取清理后的内容（已去除元数据）
        const content = cleanContent.value;
        
        if (!content) {
          console.warn('没有可下载的内容');
          return;
        }
        
        // 添加标题到内容开头
        let fullContent = '';
        if (props.documentTitleEn) {
          fullContent += `# ${props.documentTitleEn}\n\n`;
        }
        if (props.documentTitle) {
          fullContent += `${props.documentTitle}\n\n`;
        }
        fullContent += content;
        
        // 创建 Blob
        const blob = new Blob([fullContent], { type: 'text/markdown;charset=utf-8' });
        
        // 生成文件名（使用英文标题或中文标题）
        const title = props.documentTitleEn || props.documentTitle || 'document';
        // 清理文件名中的非法字符
        const safeTitle = title
          .replace(/[<>:"/\\|?*]/g, '-')
          .replace(/\s+/g, '_')
          .substring(0, 100); // 限制文件名长度
        const filename = `${safeTitle}.md`;
        
        // 创建下载链接
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        
        // 触发下载
        document.body.appendChild(link);
        link.click();
        
        // 清理
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        console.log('✅ Markdown 文件下载成功:', filename);
      } catch (error) {
        console.error('❌ 下载 Markdown 文件失败:', error);
      }
    };
    
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
      visualIframe,
      
      // 响应式状态
      isTocVisible,
      tocWidth,
      isDragging,
      activeSection,
      displayMode,
      visualAvailable,
      visualStatus,
      visualHtmlUrl,
      currentVersion,
      
      // Ultra DeepInsight 状态
      ultraAvailable,
      ultraStatus,
      isGeneratingUltra,
      ultraVersion,
      ultraWordCount,
      ultraTaskInfo,
      
      // 计算属性
      hasMultipleVersions,
      isAuthenticated,
      tocHtml,
      cleanContent,
      shouldShowToc,
      
      // 方法
      toggleToc,
      handleTocClick,
      handleArticleClick,
      handleVersionChange: handleVersionChangeWithVisual,
      handleDisplayModeChange,
      checkVisualStatus,
      checkUltraStatus,
      triggerUltraGeneration,
      handleIframeLoad,
      scrollToElement,
      resetLayout,
      startDrag,
      scrollToSection,
      downloadMarkdown,
      
      // props
      tocTitle: props.tocTitle,
      tocEmptyText: props.tocEmptyText
    };
  }
}; 