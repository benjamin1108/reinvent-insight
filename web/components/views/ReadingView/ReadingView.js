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
    
    // ========== 显示模式状态管理 ==========
    const displayMode = ref(props.initialDisplayMode);
    
    // ========== 可视化解读状态管理 ==========
    const visualAvailable = ref(false);
    const visualStatus = ref('pending');  // 'pending' | 'processing' | 'completed' | 'failed'
    const visualHtmlUrl = ref(null);
    const currentVersion = ref(0);
    const iframeHeight = ref(800);  // iframe 动态高度，初始值 800px
    let iframeMessageHandler = null;  // 消息处理器引用
    let heightUpdateTimer = null;  // 高度更新防抖定时器
    
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
        // 优先在文章正文中查找元素（.reading-view__body 包含实际的文章内容）
        const bodyContainer = document.querySelector('.reading-view__body');
        
        if (!bodyContainer) {
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
          return;
        }
        
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
    
    // ========== 显示模式相关方法 ==========
    
    // 处理显示模式切换
    const handleDisplayModeChange = async (mode) => {
      try {
        if (mode === displayMode.value) return;
        
        displayMode.value = mode;
        
        // 不再自动全屏，用户可以手动使用浏览器的全屏功能
        
        emit('display-mode-change', mode);
      } catch (error) {
        console.error('模式切换失败:', error);
      }
    };
    
    // ========== 可视化解读相关方法 ==========
    
    // 检查可视化状态
    const checkVisualStatus = async () => {
      console.log('🔍 [DEBUG] checkVisualStatus 开始');
      console.log('🔍 [DEBUG] currentHash:', props.currentHash);
      console.log('🔍 [DEBUG] currentVersion:', currentVersion.value);
      
      if (!props.currentHash) {
        console.log('⚠️ [DEBUG] 没有 currentHash，跳过检查');
        return;
      }
      
      try {
        const url = `/api/article/${props.currentHash}/visual/status?version=${currentVersion.value}`;
        console.log('🔍 [DEBUG] 请求 URL:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('🔍 [DEBUG] API 响应:', data);
        
        visualStatus.value = data.status;
        visualAvailable.value = data.status === 'completed';
        
        console.log('🔍 [DEBUG] visualStatus:', visualStatus.value);
        console.log('🔍 [DEBUG] visualAvailable:', visualAvailable.value);
        
        if (visualAvailable.value) {
          visualHtmlUrl.value = `/api/article/${props.currentHash}/visual?version=${currentVersion.value}`;
          console.log('✅ [DEBUG] 可视化可用，URL:', visualHtmlUrl.value);
        } else {
          console.log('⚠️ [DEBUG] 可视化不可用，状态:', data.status);
        }
      } catch (error) {
        console.error('❌ [DEBUG] 检查可视化状态失败:', error);
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
    const height = Math.max(
      document.body.scrollHeight,
      document.body.offsetHeight,
      document.documentElement.clientHeight,
      document.documentElement.scrollHeight,
      document.documentElement.offsetHeight
    );
    
    window.parent.postMessage({
      type: 'iframe-height',
      height: height
    }, '*');
  }
  
  // 初始发送
  sendHeight();
  
  // 监听内容变化
  window.addEventListener('load', sendHeight);
  window.addEventListener('resize', sendHeight);
  
  // 使用 MutationObserver 监听 DOM 变化
  const observer = new MutationObserver(sendHeight);
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: true
  });
})();
              `;
              doc.body.appendChild(script);
              console.log('✅ [DEBUG] 通信脚本注入成功');
            }
          }
        } catch (crossOriginError) {
          // 跨域限制，使用固定高度
          console.warn('⚠️ 跨域限制，无法访问 iframe 内容，使用固定高度');
          iframeHeight.value = 800;
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
    
    // 设置 iframe 消息监听器
    const setupIframeMessageListener = () => {
      iframeMessageHandler = (event) => {
        // 安全验证：验证消息来源
        // 在生产环境中，应该严格验证 event.origin
        const allowedOrigins = [
          window.location.origin,
          // 可以添加其他允许的源
        ];
        
        // 注意：在开发环境中，如果使用不同端口，可能需要调整
        // 暂时允许所有同源消息，生产环境应该严格验证
        if (event.origin !== window.location.origin) {
          console.warn('⚠️ 拒绝来自未知源的消息:', event.origin);
          // 在开发环境中，可以注释掉下面的 return 以允许跨域消息
          // return;
        }
        
        // 验证消息格式
        if (!event.data || typeof event.data !== 'object') {
          return;
        }
        
        // 处理高度消息
        if (event.data.type === 'iframe-height') {
          const height = parseInt(event.data.height, 10);
          
          // 验证高度值有效性
          if (isNaN(height) || height <= 0 || height > 50000) {
            console.warn('⚠️ 无效的高度值:', event.data.height);
            return;
          }
          
          // 防抖：避免频繁更新高度
          if (heightUpdateTimer) {
            clearTimeout(heightUpdateTimer);
          }
          
          heightUpdateTimer = setTimeout(() => {
            // 更新 iframe 高度（添加 20px 缓冲）
            iframeHeight.value = height;
            //console.log('📏 [DEBUG] 更新 iframe 高度:', iframeHeight.value);
          }, 100);  // 100ms 防抖
        }
      };
      
      window.addEventListener('message', iframeMessageHandler);
      console.log('✅ iframe 消息监听器已设置');
    };
    
    // 清理 iframe 消息监听器
    const cleanupIframeMessageListener = () => {
      if (iframeMessageHandler) {
        window.removeEventListener('message', iframeMessageHandler);
        iframeMessageHandler = null;
        console.log('✅ iframe 消息监听器已清理');
      }
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
        console.log('🔍 [DEBUG] currentHash 变化，重新检查可视化状态');
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
    });
    
    onUnmounted(() => {
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('keydown', handleKeydown);
      
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
      iframeHeight,
      
      // 计算属性
      hasMultipleVersions,
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
      handleIframeLoad,
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