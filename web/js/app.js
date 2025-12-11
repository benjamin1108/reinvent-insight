const { createApp, ref, onMounted, computed, nextTick, watch, onUnmounted, reactive } = Vue;

// 全局库加载状态跟踪
window.librariesReady = window.librariesReady || {
  marked: typeof window.marked !== 'undefined',
  hljs: typeof window.hljs !== 'undefined',
  axios: typeof window.axios !== 'undefined',
  Vue: typeof window.Vue !== 'undefined'
};

// 确保 marked 准备就绪
const ensureMarkedReady = (callback) => {
  const checkMarked = () => {
    if (typeof window.marked !== 'undefined') {
      window.librariesReady.marked = true;
      return true;
    }
    return false;
  };

  if (checkMarked()) {
    callback(window.marked);
    return;
  }


  // 检查是否已经在加载中
  if (window.markedLoadingPromise) {
    window.markedLoadingPromise.then(() => {
      callback(window.marked);
    });
    return;
  }

  // 首先尝试等待已有的script标签加载完成
  const existingScript = document.querySelector('script[src*="marked"]');
  if (existingScript) {
    window.markedLoadingPromise = new Promise((resolve, reject) => {
      // 设置超时检查
      let checkCount = 0;
      const maxChecks = 50; // 最多检查5秒
      const checkInterval = setInterval(() => {
        checkCount++;
        if (checkMarked()) {
          clearInterval(checkInterval);
          resolve(window.marked);
        } else if (checkCount >= maxChecks) {
          clearInterval(checkInterval);
          console.error('❌ marked加载超时');
          reject(new Error('marked加载超时'));
        }
      }, 100);

      // 同时监听script的load事件（如果还没触发）
      if (existingScript.readyState === undefined || existingScript.readyState === 'loading') {
        existingScript.addEventListener('load', () => {
          if (checkMarked()) {
            clearInterval(checkInterval);
            resolve(window.marked);
          }
        });
        existingScript.addEventListener('error', () => {
          clearInterval(checkInterval);
          reject(new Error('marked脚本加载失败'));
        });
      }
    });
  } else {
    // 如果没有找到script标签，动态创建一个
    window.markedLoadingPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = '/js/vendor/marked.min.js';
      script.onload = () => {
        window.librariesReady.marked = true;
        resolve(window.marked);
      };
      script.onerror = () => {
        console.error('❌ marked.js加载失败');
        reject(new Error('marked.js加载失败'));
      };
      document.head.appendChild(script);
    });
  }

  window.markedLoadingPromise.then(() => {
    callback(window.marked);
  }).catch(error => {
    console.error('❌ marked加载错误:', error);
  });
};

// 配置 marked 和 highlight.js
const configureMarked = (markedInstance) => {
  if (!markedInstance || !markedInstance.setOptions) {
    console.warn('⚠️ marked实例无效，跳过配置');
    return;
  }

  try {
    markedInstance.setOptions({
      gfm: true,
      highlight: function (code, lang) {
        if (typeof hljs !== 'undefined') {
          if (lang && hljs.getLanguage(lang)) {
            try {
              return hljs.highlight(code, { language: lang }).value;
            } catch (__) { }
          }
          return hljs.highlightAuto(code).value;
        }
        return code; // 如果hljs未加载，返回原始代码
      },
      breaks: true,
      pedantic: false,
      sanitize: false,
      smartLists: true,
      smartypants: false
    });
  } catch (error) {
    console.error('❌ marked配置失败:', error);
  }
};

// 初始配置marked（如果已加载）
ensureMarkedReady(configureMarked);

// ===== 错误类型映射 =====
const ERROR_TYPE_CONFIG = {
  network_timeout: {
    icon: '⏱️',
    color: '#f59e0b', // 橙色
    title: '网络超时'
  },
  access_forbidden: {
    icon: '🚫',
    color: '#ef4444', // 红色
    title: '访问被拒绝'
  },
  no_subtitles: {
    icon: '📝',
    color: '#3b82f6', // 蓝色
    title: '字幕不可用'
  },
  tool_missing: {
    icon: '🔧',
    color: '#ef4444', // 红色
    title: '工具缺失'
  },
  invalid_url: {
    icon: '❌',
    color: '#ef4444', // 红色
    title: '无效的 URL'
  },
  video_not_found: {
    icon: '🔍',
    color: '#f59e0b', // 橙色
    title: '视频未找到'
  },
  rate_limited: {
    icon: '⏸️',
    color: '#eab308', // 黄色
    title: '请求过于频繁'
  },
  unknown: {
    icon: '⚠️',
    color: '#6b7280', // 灰色
    title: '未知错误'
  }
};

// 获取错误图标
const getErrorIcon = (errorType) => {
  return ERROR_TYPE_CONFIG[errorType]?.icon || ERROR_TYPE_CONFIG.unknown.icon;
};

// 获取错误颜色
const getErrorColor = (errorType) => {
  return ERROR_TYPE_CONFIG[errorType]?.color || ERROR_TYPE_CONFIG.unknown.color;
};

// 获取错误标题
const getErrorTitle = (errorType) => {
  return ERROR_TYPE_CONFIG[errorType]?.title || ERROR_TYPE_CONFIG.unknown.title;
};

// 将错误处理函数暴露到全局，供组件使用
window.getErrorIcon = getErrorIcon;
window.getErrorColor = getErrorColor;
window.getErrorTitle = getErrorTitle;

// 创建Vue应用实例
const app = createApp({
  setup() {
    // ===== 状态管理 =====

    // 创建分析相关状态
    const url = ref('');
    const title = ref('');
    const logs = ref([]);
    const loading = ref(false);
    const progressPercent = ref(0);
    const createdFilename = ref('');
    const createdDocHash = ref('');

    // 错误状态
    const currentError = ref(null); // 存储结构化错误信息
    const showErrorDetails = ref(false); // 是否展开技术细节

    // SSE 重连相关状态
    const connectionState = ref('disconnected');
    const reconnectAttempts = ref(0);
    const reconnectTimer = ref(null);
    const currentTaskId = ref(null);
    const currentEventSource = ref(null);

    const MAX_RECONNECT_ATTEMPTS = 5;
    const BASE_RECONNECT_DELAY = 3000;
    const MAX_RECONNECT_DELAY = 30000;

    // 笔记库状态
    const summaries = ref([]);
    const libraryLoading = ref(false);
    const isShareView = ref(false);
    const readingVideoUrl = ref('');
    const pdfDownloading = ref(false);
    const markdownDownloading = ref(false);

    // 阅读视图状态
    const readingContent = ref('');
    const documentTitle = ref('');
    const documentTitleEn = ref('');
    const readingError = ref('');
    const readingFilename = ref('');
    const readingHash = ref('');
    const currentDocHash = ref(''); // 当前文档哈希（用于可视化解读）

    // 版本管理状态
    const documentVersions = ref([]);
    const currentVersion = ref(1); // 统一为数字类型
    const documentLoading = ref(false);

    // ========== 显示模式状态 ==========
    const displayMode = ref('deep'); // 'deep' | 'quick'
    const coreSummary = ref(null); // 核心要点数据（预留）
    const simplifiedText = ref(''); // 精简摘要内容（预留）
    const longImageGenerating = ref(false); // 长图生成状态
    const visualAvailable = ref(false);      // Visual Insight 是否可用
    const visualStatus = ref('pending');     // Visual 状态

    // 认证状态 - 必须在 getInitialView 之前声明
    const isAuthenticated = ref(false);
    const showLogin = ref(false);
    const loginSuccessCallback = ref(null); // 存储登录成功后的回调函数

    // 视图控制
    const getInitialView = () => {
      const path = window.location.pathname;
      const hashMatch = path.match(/^\/d\/([a-zA-Z0-9]+)$/);
      const docMatch = path.match(/\/documents\/(.+)/);

      if (hashMatch || docMatch) {
        return 'read';
      }
      
      // 支持回收站页面
      if (path === '/trash') {
        return 'trash';
      }

      // 默认显示最近文章页面（登录和未登录用户都可以访问）
      return 'recent';
    };

    const currentView = ref(getInitialView());

    // TOC 相关状态
    const showToc = ref(
      localStorage.getItem('showToc') === 'false'
        ? false
        : true // 默认显示
    );
    const tocWidth = ref(
      localStorage.getItem('tocWidth') !== null
        ? parseInt(localStorage.getItem('tocWidth'))
        : 350
    );

    // 视频播放器状态
    const showVideoPlayer = ref(false);
    const videoPlayerMinimized = ref(false);
    const videoPlayerPosition = ref({ x: null, y: null });
    const videoPlayerSize = ref({ width: 480, height: 320 });
    const currentVideoId = ref('');
    const currentVideoTitle = ref('');
    const isVideoResizing = ref(false);
    const isVideoDragging = ref(false);

    // 新增：主内容区域的引用
    const mainContent = ref(null);

    // 环境信息状态
    const environmentInfo = reactive({
      environment: 'production',
      is_development: false,
      loaded: false
    });

    // 筛选器状态
    const selectedLevel = ref('');
    const selectedYear = ref('');
    const showLevelDropdown = ref(false);
    const showYearDropdown = ref(false);

    // 回收站状态
    const trashItems = ref([]);
    const trashLoading = ref(false);

    // ===== 计算属性 =====

    // 显示首页区域的条件 - 仅在未登录且在 library 视图时显示
    const showHeroSection = computed(() => {
      return currentView.value === 'library' && !isAuthenticated.value && !isShareView.value;
    });

    // 最终确定的日志（用于进度显示）
    const finalizedLogs = computed(() => {
      return logs.value.slice(0, -1); // 排除最后一条实时日志
    });

    // 数据分类
    const categorizedSummaries = computed(() => {
      const reinvent = [];
      const other = [];

      summaries.value.forEach(summary => {
        // 优先使用后端的 is_reinvent 字段，其次才检查标题
        if (summary.is_reinvent) {
          reinvent.push(summary);
        } else {
          const titleEn = summary.title_en || '';
          if (titleEn.toLowerCase().includes('reinvent') || titleEn.toLowerCase().includes('re:invent')) {
            reinvent.push(summary);
          } else {
            other.push(summary);
          }
        }
      });

      return { reinvent, other };
    });

    // 可用年份列表
    const availableYears = computed(() => {
      const years = new Set();
      categorizedSummaries.value.reinvent.forEach(summary => {
        const titleMatch = summary.title_en && summary.title_en.match(/\b(20\d{2})\b/);
        if (titleMatch) {
          years.add(titleMatch[1]);
        } else if (summary.upload_date) {
          years.add(summary.upload_date.substring(0, 4));
        }
      });
      return Array.from(years).sort((a, b) => b - a);
    });

    // 筛选后的re:Invent摘要
    const filteredReinventSummaries = computed(() => {
      let filtered = categorizedSummaries.value.reinvent;

      // 级别筛选
      if (selectedLevel.value) {
        filtered = filtered.filter(summary => {
          if (!summary.level) return selectedLevel.value === 'Keynote';

          if (selectedLevel.value === 'Keynote') {
            return summary.level.toLowerCase().includes('keynote');
          }

          const levelMatch = summary.level.match(/\d+/);
          return levelMatch && levelMatch[0] === selectedLevel.value;
        });
      }

      // 年份筛选
      if (selectedYear.value) {
        filtered = filtered.filter(summary => {
          const titleMatch = summary.title_en && summary.title_en.match(/\b(20\d{2})\b/);
          const year = titleMatch ? titleMatch[1] : (summary.upload_date ? summary.upload_date.substring(0, 4) : '');
          return year === selectedYear.value;
        });
      }

      return filtered;
    });

    // TTS音频文本 - 使用ref而不是computed，以便更好地控制更新
    const articleTextForTTS = ref('');

    // 监听readingContent变化，手动更新articleTextForTTS
    watch([readingContent, currentView], ([content, view]) => {
      if (!content || view !== 'read') {
        articleTextForTTS.value = '';
        return;
      }

      // 提取文本的函数
      const extractText = () => {
        try {
          const parser = new DOMParser();
          const doc = parser.parseFromString(content, 'text/html');

          // 移除图片、脚本、样式和代码块
          doc.querySelectorAll('img, script, style, pre, code').forEach(el => el.remove());

          // 提取纯文本
          let text = doc.body.textContent || '';

          // 清理多余空白
          text = text.replace(/\s+/g, ' ').trim();

          // 限制长度（最多6000字符）
          const maxLength = 6000;
          if (text.length > maxLength) {
            text = text.substring(0, maxLength);
            // 在句子边界截断
            const lastPeriod = Math.max(
              text.lastIndexOf('。'),
              text.lastIndexOf('.'),
              text.lastIndexOf('！'),
              text.lastIndexOf('？')
            );
            if (lastPeriod > maxLength * 0.8) {
              text = text.substring(0, lastPeriod + 1);
            }
          }

          articleTextForTTS.value = text;

          // 强制触发Vue更新
          nextTick(() => {});
        } catch (error) {
          console.error('[TTS] 提取文本失败:', error);
          articleTextForTTS.value = '';
        }
      };

      extractText();
    });

    // ===== 核心业务方法 =====

    // 路由处理
    const handleRouting = () => {
      const path = window.location.pathname;
      const hashMatch = path.match(/^\/d\/([a-zA-Z0-9]+)$/);
      const docMatch = path.match(/\/documents\/(.+)/);

      if (hashMatch) {
        const docHash = hashMatch[1];
        loadSummaryByHash(docHash, false);
      } else if (docMatch) {
        const filename = decodeURIComponent(docMatch[1]);
        loadSummary(filename, false);
      } else if (path === '/trash') {
        // 回收站页面
        currentView.value = 'trash';
      } else {
        currentView.value = 'library';
        if (isAuthenticated.value && summaries.value.length === 0) {
          loadSummaries();
        }
      }
    };

    // 认证相关方法
    const login = async (formData) => {
      try {
        const res = await axios.post('/login', {
          username: formData.username,
          password: formData.password
        });
        const token = res.data.token;
        localStorage.setItem('authToken', token);
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        isAuthenticated.value = true;
        showLogin.value = false;

        // 如果有登录回调（如Ultra触发），则不切换视图，直接执行回调
        if (loginSuccessCallback.value) {
          const callback = loginSuccessCallback.value;
          loginSuccessCallback.value = null; // 清空回调
          await callback();
        } else {
          // 无回调时，正常跳转到主页
          currentView.value = 'recent';
          await nextTick();
          await loadSummaries();
        }
      } catch (error) {
        console.error('登录失败:', error);
        if (window.eventBus && window.eventBus.emit) {
          window.eventBus.emit('login-error', error.response?.data?.detail || '登录失败');
        }
        showToast(error.response?.data?.detail || '登录失败', 'danger');
      }
    };

    const logout = async () => {
      localStorage.removeItem('authToken');
      delete axios.defaults.headers.common['Authorization'];
      isAuthenticated.value = false;
      currentView.value = 'library';
      showLogin.value = true;
      showToast('会话已过期，请重新登录', 'warning');

      // 重新加载访客模式下的公开文章列表
      try {
        await loadSummaries();
      } catch (error) {
        console.error('❌ 退出登录后重新加载文章列表失败:', error);
        // 如果加载失败，至少保持数组为空而不是显示错误数据
        summaries.value = [];
      }
    };

    const checkAuth = () => {
      const token = localStorage.getItem('authToken');
      if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        isAuthenticated.value = true;
      } else {
        isAuthenticated.value = false;
      }
    };

    const requireAuth = (action) => {
      if (!isAuthenticated.value) {
        showLogin.value = true;
        showToast('请先登录', 'warning');
      } else {
        action();
      }
    };

    // Toast 消息显示
    const showToast = (message, type = 'success', duration = 3000) => {
      const toast = window.useToast();
      const typeMap = {
        'success': 'success',
        'danger': 'error',
        'warning': 'warning',
        'info': 'info'
      };
      const mappedType = typeMap[type] || 'info';
      toast.showToast({
        message,
        type: mappedType,
        duration
      });
    };

    // 默认页面标题
    const DEFAULT_PAGE_TITLE = 'reinvent Insight - 深度分析笔记';

    // 更新浏览器标题
    const updatePageTitle = (title) => {
      document.title = title || DEFAULT_PAGE_TITLE;
    };

    // 视图导航方法
    const goHome = () => {
      history.pushState(null, '', '/');
      currentView.value = 'recent';
      clearReadingState();
      closeVideoPlayer();
      updatePageTitle(); // 恢复默认标题
      loadSummaries();   // 刷新文章列表
    };

    const goBackToLibrary = () => {
      history.pushState(null, '', '/');
      currentView.value = 'library';
      clearReadingState();
      closeVideoPlayer();
      updatePageTitle(); // 恢复默认标题
      loadSummaries();   // 刷新文章列表
    };

    const clearReadingState = () => {
      readingContent.value = '';
      documentTitle.value = '';
      readingFilename.value = '';
      readingHash.value = '';
    };

    const handleViewChange = (view) => {
      const prevPath = window.location.pathname;
      currentView.value = view;
      // 更新 URL，避免停留在特殊页面路径
      if (prevPath !== '/') {
        history.pushState(null, '', '/');
      }
      // 切换到列表视图时加载数据（从特殊页面切换时强制刷新）
      if (view === 'library' || view === 'recent') {
        loadSummaries();
        updatePageTitle(); // 恢复默认标题
      }
    };

    const handleLoginShow = () => {
      showLogin.value = true;
    };

    const handleSummaryClick = (data) => {
      if (data && data.hash) {
        loadSummaryByHash(data.hash);
      } else {
        console.error('❌ 无效的摘要数据:', data);
      }
    };

    // TOC 相关方法
    const toggleToc = () => {

      showToc.value = !showToc.value;


      localStorage.setItem('showToc', showToc.value);
    };

    const handleTocResize = (width) => {
      tocWidth.value = width;
      localStorage.setItem('tocWidth', width.toString());
    };

    // YouTube URL 验证
    const isValidYoutubeUrl = (str) => {
      if (!str || typeof str !== 'string') return false;
      const url = str.trim();
      const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
      return youtubeRegex.test(url);
    };

    // 分析相关方法
    const clearActiveTask = () => {
      localStorage.removeItem('active_task_id');
      localStorage.removeItem('active_task_url');
    };

    // 计算重连延迟（指数退避）
    const getReconnectDelay = (attempt) => {
      const delay = Math.min(
        BASE_RECONNECT_DELAY * Math.pow(2, attempt),
        MAX_RECONNECT_DELAY
      );
      // 添加随机抖动（±20%）
      const jitter = delay * 0.2 * (Math.random() * 2 - 1);
      return Math.floor(delay + jitter);
    };

    // 手动重连
    const manualReconnect = () => {
      if (currentTaskId.value) {
        reconnectAttempts.value = 0;
        connectSSE(currentTaskId.value, true);
      }
    };

    const startSummarize = async (analysisData) => {
      requireAuth(async () => {
        if (loading.value || (!analysisData.url && !analysisData.file)) return;

        // 重置状态
        logs.value = [];
        title.value = '';
        createdFilename.value = '';
        createdDocHash.value = '';
        loading.value = true;

        try {
          let res;
          if (analysisData.file) {
            // 处理文档文件上传
            const formData = new FormData();
            formData.append('file', analysisData.file);

            // 获取文件类型
            const fileName = analysisData.file.name;
            const fileExt = fileName.split('.').pop().toUpperCase();
            const fileTypeMap = {
              'TXT': '文本文档',
              'MD': 'Markdown 文档',
              'PDF': 'PDF 文档',
              'DOCX': 'Word 文档'
            };
            const fileTypeName = fileTypeMap[fileExt] || '文档';

            // 添加上传进度日志
            logs.value.push(`正在上传${fileTypeName} (${(analysisData.file.size / 1024 / 1024).toFixed(2)} MB)...`);

            res = await axios.post('/analyze-document', formData, {
              headers: {
                'Content-Type': 'multipart/form-data'
              },
              onUploadProgress: (progressEvent) => {
                // 更新上传进度日志
                const uploadMB = (progressEvent.loaded / 1024 / 1024).toFixed(2);
                const totalMB = (progressEvent.total / 1024 / 1024).toFixed(2);
                const lastLog = logs.value[logs.value.length - 1];

                if (lastLog && lastLog.includes('正在上传')) {
                  logs.value[logs.value.length - 1] = `正在上传${fileTypeName}: ${uploadMB}MB / ${totalMB}MB (${Math.round((progressEvent.loaded * 100) / progressEvent.total)}%)`;
                }
              }
            });

            // 上传完成
            logs.value.push(`${fileTypeName}上传成功，服务器正在处理...`);
          } else {
            // 处理URL分析（保持原有逻辑）
            const requestUrl = analysisData.force ? '/summarize?force=true' : '/summarize';
            res = await axios.post(requestUrl, { url: analysisData.url });
            
            // 检查是否返回了重复视频信息
            if (res.data.exists) {
              // 视频已存在，停止分析
              loading.value = false;
              
              if (res.data.in_queue) {
                showToast('该视频已在队列中，请稍候', 'info');
              } else if (res.data.in_progress) {
                showToast('该视频正在分析中', 'info');
              } else {
                showToast('该视频已有解读', 'info');
              }
              return;
            }
          }

          const taskId = res.data.task_id;
          localStorage.setItem('active_task_id', taskId);
          if (analysisData.url) {
            localStorage.setItem('active_task_url', analysisData.url);
          }

          connectSSE(taskId);
        } catch (error) {
          console.error('任务创建失败:', error);
          loading.value = false;
          logs.value.push(`错误: ${error.response?.data?.detail || error.message}`);
          clearActiveTask();
        }
      });
    };

    const connectSSE = (taskId, isReconnect = false) => {
      // 清理之前的重连定时器
      if (reconnectTimer.value) {
        clearTimeout(reconnectTimer.value);
        reconnectTimer.value = null;
      }

      currentTaskId.value = taskId;
      connectionState.value = isReconnect ? 'reconnecting' : 'connecting';

      // 构建 SSE URL，包含认证 token
      // EventSource 不支持自定义 Header，所以通过查询参数传递 token
      const token = localStorage.getItem('authToken');
      const sseUrl = token
        ? `/api/tasks/${taskId}/stream?token=${encodeURIComponent(token)}`
        : `/api/tasks/${taskId}/stream`;


      // 创建 EventSource
      const eventSource = new EventSource(sseUrl);
      currentEventSource.value = eventSource;

      const displayedLogs = new Set(logs.value);

      // 连接打开
      eventSource.onopen = () => {
        connectionState.value = 'connected';
        reconnectAttempts.value = 0; // 重置重连计数
        loading.value = true;

        if (logs.value.length === 0) {
          logs.value.push('已连接到分析服务...');
        } else if (isReconnect) {
          logs.value.push('连接已恢复');
          showToast('连接已恢复', 'success', 2000);
        }
      };

      // 接收消息
      eventSource.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'result') {
            // 处理结果消息
            title.value = data.title;

            // 保存文件名和 hash（如果有的话）
            if (data.filename) {
              createdFilename.value = data.filename;
            }
            if (data.hash) {
              createdDocHash.value = data.hash;
            }

            loading.value = false;
            clearActiveTask();
            connectionState.value = 'disconnected';
            eventSource.close();
          } else if (data.type === 'log') {
            // 处理日志消息
            if (!displayedLogs.has(data.message)) {
              logs.value.push(data.message);
              displayedLogs.add(data.message);
            }
          } else if (data.type === 'progress') {
            // 处理进度消息（仅记录日志，不显示进度条）
          } else if (data.type === 'error') {
            // 处理结构化错误消息
            // 存储结构化错误信息
            currentError.value = {
              error_type: data.error_type || 'unknown',
              message: data.message || '未知错误',
              technical_details: data.technical_details,
              suggestions: data.suggestions || [],
              retry_after: data.retry_after
            };

            // 添加错误日志
            const errorTitle = getErrorTitle(data.error_type || 'unknown');
            logs.value.push(`${getErrorIcon(data.error_type || 'unknown')} ${errorTitle}: ${data.message}`);

            loading.value = false;
            clearActiveTask();
            connectionState.value = 'disconnected';
            eventSource.close();
          } else if (data.type === 'heartbeat') {
            // 心跳消息，保持连接活跃
          }
        } catch (error) {
          console.error('解析 SSE 消息失败:', error, event.data);
        }
      });

      // 连接错误
      eventSource.onerror = (error) => {
        console.error('SSE 连接错误:', error);
        eventSource.close();

        // 如果任务还在进行中，尝试重连
        if (loading.value && reconnectAttempts.value < MAX_RECONNECT_ATTEMPTS) {
          connectionState.value = 'reconnecting';
          reconnectAttempts.value++;

          const delay = getReconnectDelay(reconnectAttempts.value - 1);
          logs.value.push(`连接断开，${Math.ceil(delay / 1000)}秒后尝试重连 (${reconnectAttempts.value}/${MAX_RECONNECT_ATTEMPTS})`);

          reconnectTimer.value = setTimeout(() => {
            connectSSE(taskId, true);
          }, delay);
        } else if (loading.value && reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
          // 超过最大重连次数
          connectionState.value = 'disconnected';
          logs.value.push('连接失败，已达到最大重连次数');
          showToast('连接失败，请检查网络后手动重连', 'danger');
          loading.value = false;
        } else {
          // 任务已完成或用户主动断开
          connectionState.value = 'disconnected';
        }
      };
    };

    // 笔记库相关方法
    let isLoadingSummaries = false; // 防止重复调用
    
    // ===== 文档列表缓存管理 =====
    const SUMMARIES_CACHE_KEY = 'reinvent_summaries_cache';
    const SUMMARIES_VERSION_KEY = 'reinvent_summaries_version';
    const SUMMARIES_TIMESTAMP_KEY = 'reinvent_summaries_timestamp';
    const SUMMARIES_CACHE_TTL = 5 * 60 * 1000; // 5分钟
    
    // 获取缓存的文档列表
    const getCachedSummaries = () => {
      try {
        const cached = localStorage.getItem(SUMMARIES_CACHE_KEY);
        const timestamp = localStorage.getItem(SUMMARIES_TIMESTAMP_KEY);
        
        if (!cached || !timestamp) return null;
        
        // 检查缓存是否过期
        const cacheAge = Date.now() - parseInt(timestamp, 10);
        if (cacheAge > SUMMARIES_CACHE_TTL) return null;
        
        return JSON.parse(cached);
      } catch (error) {
        return null;
      }
    };
    
    // 保存文档列表到缓存
    const cacheSummaries = (data, version) => {
      try {
        localStorage.setItem(SUMMARIES_CACHE_KEY, JSON.stringify(data));
        localStorage.setItem(SUMMARIES_VERSION_KEY, String(version || 0));
        localStorage.setItem(SUMMARIES_TIMESTAMP_KEY, String(Date.now()));
      } catch (error) {
        // 存储失败（可能是空间不足），清理缓存
        clearSummariesCache();
      }
    };
    
    // 清除缓存
    const clearSummariesCache = () => {
      try {
        localStorage.removeItem(SUMMARIES_CACHE_KEY);
        localStorage.removeItem(SUMMARIES_VERSION_KEY);
        localStorage.removeItem(SUMMARIES_TIMESTAMP_KEY);
      } catch (error) {
        // 忽略
      }
    };
    
    // 获取缓存版本号
    const getCachedVersion = () => {
      try {
        const version = localStorage.getItem(SUMMARIES_VERSION_KEY);
        return version ? parseInt(version, 10) : 0;
      } catch (error) {
        return 0;
      }
    };
    
    // 检查服务器缓存版本（后台检查，不影响用户体验）
    const checkAndUpdateSummariesInBackground = async () => {
      try {
        const res = await axios.get('/api/public/cache-info');
        const serverVersion = res.data.cache_version || 0;
        const cachedVersion = getCachedVersion();
        
        if (serverVersion !== cachedVersion) {
          // 版本不一致，后台拉取新数据
          const newRes = await axios.get('/api/public/summaries');
          const newData = newRes.data.summaries || [];
          const newVersion = newRes.data.cache_version || 0;
          
          cacheSummaries(newData, newVersion);
          summaries.value = newData;
        }
      } catch (error) {
        // 后台检查失败，忽略
      }
    };
    
    const loadSummaries = async (forceRefresh = false) => {
      if (isLoadingSummaries) {
        return;
      }
      
      isLoadingSummaries = true;
      
      // 优先使用缓存（如果不是强制刷新）
      if (!forceRefresh) {
        const cached = getCachedSummaries();
        if (cached && Array.isArray(cached) && cached.length > 0) {
          summaries.value = cached;
          libraryLoading.value = false;
          isLoadingSummaries = false;
          
          // 后台检查是否有更新
          checkAndUpdateSummariesInBackground();
          return;
        }
      }
      
      // 缓存无效或强制刷新，从服务器获取
      libraryLoading.value = true;
      try {
        const res = await axios.get('/api/public/summaries');
        const dataArray = res.data.summaries || [];
        const version = res.data.cache_version || 0;
        
        summaries.value = dataArray;
        cacheSummaries(dataArray, version);
      } catch (error) {
        console.error('加载笔记库失败:', error);
        showToast('加载笔记库失败', 'danger');
      } finally {
        libraryLoading.value = false;
        isLoadingSummaries = false;
      }
    };

    // 删除文章
    const deleteSummary = async (data) => {
      if (!data || !data.hash) {
        console.error('❌ 无效的删除数据:', data);
        showToast('删除失败：无效的文章数据', 'danger');
        return;
      }

      try {
        const res = await axios.delete(`/api/summaries/${data.hash}`);
        
        if (res.data.success) {
          // 从本地列表中移除
          summaries.value = summaries.value.filter(s => s.hash !== data.hash);
          // 清除缓存（下次加载时会从服务器重新获取）
          clearSummariesCache();
          
          const title = data.titleCn || data.titleEn || '文章';
          showToast(`已删除「${title.substring(0, 20)}${title.length > 20 ? '...' : ''}」`, 'success');
        } else {
          throw new Error(res.data.message || '删除失败');
        }
      } catch (error) {
        console.error('❌ 删除文章失败:', error);
        const errorMsg = error.response?.data?.detail || error.message || '删除失败';
        showToast(`删除失败：${errorMsg}`, 'danger');
      }
    };

    // ===== 回收站管理方法 =====
    
    // 加载回收站列表
    const loadTrashItems = async () => {
      if (!isAuthenticated.value) {
        showToast('请先登录', 'warning');
        return;
      }
      
      trashLoading.value = true;
      try {
        const res = await axios.get('/api/admin/trash');
        trashItems.value = res.data.items || [];
      } catch (error) {
        console.error('✖ 加载回收站失败:', error);
        showToast('加载回收站失败', 'danger');
      } finally {
        trashLoading.value = false;
      }
    };

    // 恢复文章
    const restoreFromTrash = async (docHash, title) => {
      try {
        const res = await axios.post(`/api/admin/trash/${docHash}/restore`);
        
        if (res.data.success) {
          // 从回收站列表中移除
          trashItems.value = trashItems.value.filter(item => item.doc_hash !== docHash);
          // 清除缓存并刷新主列表
          clearSummariesCache();
          loadSummaries(true);
          
          const displayTitle = title ? (title.length > 20 ? title.substring(0, 20) + '...' : title) : '文章';
          showToast(`已恢复「${displayTitle}」`, 'success');
        }
      } catch (error) {
        console.error('✖ 恢复文章失败:', error);
        const errorMsg = error.response?.data?.detail || error.message || '恢复失败';
        showToast(`恢复失败：${errorMsg}`, 'danger');
      }
    };

    // 永久删除文章
    const permanentlyDelete = async (docHash, title) => {
      try {
        const res = await axios.delete(`/api/admin/trash/${docHash}`);
        
        if (res.data.success) {
          trashItems.value = trashItems.value.filter(item => item.doc_hash !== docHash);
          
          const displayTitle = title ? (title.length > 20 ? title.substring(0, 20) + '...' : title) : '文章';
          showToast(`已永久删除「${displayTitle}」`, 'success');
        }
      } catch (error) {
        console.error('✖ 永久删除失败:', error);
        const errorMsg = error.response?.data?.detail || error.message || '删除失败';
        showToast(`删除失败：${errorMsg}`, 'danger');
      }
    };

    // 清空回收站
    const emptyTrash = async () => {
      if (trashItems.value.length === 0) {
        showToast('回收站已为空', 'info');
        return;
      }
      
      try {
        const res = await axios.delete('/api/admin/trash');
        
        if (res.data.success) {
          trashItems.value = [];
          showToast('已清空回收站', 'success');
        }
      } catch (error) {
        console.error('✖ 清空回收站失败:', error);
        const errorMsg = error.response?.data?.detail || error.message || '清空失败';
        showToast(`清空回收站失败：${errorMsg}`, 'danger');
      }
    };

    const loadSummary = async (filename, pushState = true) => {
      documentLoading.value = true;
      readingError.value = '';

      try {
        const res = await axios.get(`/api/public/summaries/${encodeURIComponent(filename)}`);
        const data = res.data;

        viewSummary(
          data.title_cn || data.title,
          data.title_cn,
          data.title_en,
          data.content,
          filename,
          data.video_url || '',
          data.hash,
          data.versions || []
        );

        if (pushState) {
          history.pushState(null, '', `/documents/${encodeURIComponent(filename)}`);
        }
      } catch (error) {
        console.error('加载文档失败:', error);
        readingError.value = '加载文档失败';
      } finally {
        documentLoading.value = false;
      }
    };

    const loadSummaryByHash = async (docHash, pushState = true) => {
      documentLoading.value = true;
      readingError.value = '';

      try {
        // 使用正确的API端点
        const res = await axios.get(`/api/public/doc/${docHash}`);

        // 检查是否返回了HTML而不是JSON
        if (typeof res.data === 'string' && res.data.includes('<!DOCTYPE html>')) {
          throw new Error('API返回了HTML页面而不是JSON数据，可能是路由配置问题');
        }

        const data = res.data;

        // 检查是否需要重定向到新的统一hash
        if (data.redirect && data.new_hash) {
          showToast(data.message || '文档链接已更新', 'info');

          // 递归调用新的hash，但不推送历史状态（避免重复）
          await loadSummaryByHash(data.new_hash, false);

          // 更新URL到新的hash
          if (pushState) {
            history.replaceState(null, '', `/d/${data.new_hash}`);
          }
          return;
        }

        viewSummary(
          data.title_cn || data.title,
          data.title_cn,
          data.title_en,
          data.content,
          data.filename,
          data.video_url || '',
          data.redirect ? data.new_hash : docHash,  // 使用重定向后的新hash
          data.versions || []
        );

        if (pushState) {
          history.pushState(null, '', `/d/${docHash}`);
        }
      } catch (error) {
        console.error('加载文档失败:', error);
        readingError.value = '加载文档失败';
      } finally {
        documentLoading.value = false;
      }
    };

    const viewSummary = (dataOrTitle, title_cn, title_en, content, filename, videoUrl = '', docHash, versions = []) => {
      // 处理来自 CreateView 的对象参数
      if (typeof dataOrTitle === 'object' && dataOrTitle !== null) {
        const data = dataOrTitle;

        // 如果有 hash，直接使用 hash 导航
        if (data.hash) {
          loadSummaryByHash(data.hash);
          return;
        }

        // 如果只有标题，显示提示信息
        if (data.title) {
          showToast('文档正在后台处理，请稍等片刻后在笔记库中查看', 'info');
          currentView.value = 'library';
          return;
        }

        return; // 提前返回，不执行后续代码
      }

      // 处理传统的多参数调用（来自 LibraryView）
      const title = dataOrTitle;

      // 先设置文档数据
      documentTitle.value = title_cn || title;
      documentTitleEn.value = title_en || '';
      readingFilename.value = filename;
      readingVideoUrl.value = videoUrl;
      readingHash.value = docHash;
      currentDocHash.value = docHash; // 设置当前文档哈希用于可视化解读
      documentVersions.value = versions;

      // 更新浏览器标题
      const pageTitle = title_en || title_cn || title;
      updatePageTitle(pageTitle ? `${pageTitle} - reinvent Insight` : null);

      // 切换视图
      currentView.value = 'read';

      // 使用 nextTick 确保在DOM更新后执行滚动，彻底解决视图切换时的滚动位置残留问题
      nextTick(() => {
        if (mainContent.value) {
          mainContent.value.scrollTo(0, 0);
        } else {
          window.scrollTo(0, 0); // Fallback
        }
      });

      // 恢复用户之前选择的版本，如果没有则使用第一个版本
      let savedVersion = null;
      if (docHash) {
        try {
          const savedVersionStr = localStorage.getItem(`document_version_${docHash}`);
          if (savedVersionStr) {
            const parsedVersion = Number(savedVersionStr);
            // 验证是有效数字且不是NaN
            if (!isNaN(parsedVersion) && isFinite(parsedVersion) && parsedVersion >= 0) {
              savedVersion = parsedVersion;
            }
          }
        } catch (error) {
          console.warn('localStorage版本数据损坏，已清理:', error);
          // 清理损坏的数据
          localStorage.removeItem(`document_version_${docHash}`);
        }
      }

      // 统一版本号为数字类型，确保版本列表中所有版本都是数字
      const normalizedVersions = versions.map(v => ({
        ...v,
        version: Number(v.version)
      }));
      documentVersions.value = normalizedVersions;

      // 确定要显示的版本：优先localStorage保存的版本，其次是最新版本（版本号最大）
      const defaultVersion = normalizedVersions.length > 0 ?
        Math.max(...normalizedVersions.map(v => v.version)) : 1; // 使用最新版本作为默认

      let targetVersion = defaultVersion;
      if (savedVersion !== null && normalizedVersions.some(v => v.version === savedVersion)) {
        targetVersion = savedVersion;
      }

      // 设置版本选择器状态
      currentVersion.value = targetVersion;

      // 根据目标版本决定是否需要加载不同的内容
      const needVersionSwitch = targetVersion !== defaultVersion;

      const updateContent = (contentToRender = content) => {
        if (!contentToRender) {
          console.warn('⚠️ 没有内容可渲染');
          return;
        }


        // 确保marked已加载
        if (typeof marked === 'undefined' || typeof window.marked === 'undefined') {
          console.error('❌ marked未定义，无法渲染');
          return;
        }

        try {
          // 确保marked配置正确
          configureMarked(marked);

          const renderedHtml = marked.parse(contentToRender);
          readingContent.value = renderedHtml;
        } catch (error) {
          console.error('❌ 内容渲染失败:', error);
        }
      };

      if (needVersionSwitch) {
        // 需要切换版本：先显示加载状态，然后加载目标版本内容
        documentLoading.value = true;
        nextTick(async () => {
          try {
            await switchVersion(targetVersion);
          } catch (error) {
            console.error('切换到保存的版本失败，使用默认内容:', error);
            // 切换失败，使用当前内容并重置版本选择器
            currentVersion.value = defaultVersion;
            ensureMarkedReady(() => updateContent());
          } finally {
            documentLoading.value = false;
          }
        });
      } else {
        // 不需要切换版本：直接显示当前内容

        // 使用双重nextTick确保视图完全切换后再渲染内容
        nextTick(() => {
          nextTick(() => {
            ensureMarkedReady(() => {
              updateContent(content);
            });
          });
        });
      }
    };

    // 版本切换
    const switchVersion = async (version) => {
      const versionNumber = Number(version); // 确保是数字

      // 检查目标版本是否有效
      const isValidVersion = documentVersions.value.some(v => v.version === versionNumber);
      if (!isValidVersion) {
        console.error('目标版本无效:', versionNumber, '可用版本:', documentVersions.value.map(v => v.version));
        showToast('无效的版本号', 'danger');
        throw new Error(`无效的版本号: ${versionNumber}`);
      }

      // 保存当前版本，用于错误回退
      const previousVersion = currentVersion.value;

      // 先更新版本选择器状态
      currentVersion.value = versionNumber;

      if (readingHash.value) {
        try {
          // 发送API请求获取指定版本的内容
          const res = await axios.get(`/api/public/doc/${readingHash.value}/${versionNumber}`);
          const data = res.data;


          // 使用ensureMarkedReady确保marked已加载
          await new Promise((resolve, reject) => {
            ensureMarkedReady(() => {
              try {
                // 确保marked配置正确
                configureMarked(marked);

                // 更新阅读视图的内容和标题
                const renderedHtml = marked.parse(data.content);
                readingContent.value = renderedHtml;
                documentTitle.value = data.title_cn || data.title;
                documentTitleEn.value = data.title_en || '';

                resolve();
              } catch (error) {
                reject(error);
              }
            });
          });

          // 将用户选择的版本保存到 localStorage（成功后才保存）
          localStorage.setItem(`document_version_${readingHash.value}`, versionNumber);

        } catch (error) {
          console.error('❌ 切换版本失败:', error);

          // 回退版本选择器状态
          currentVersion.value = previousVersion;

          // 清理可能损坏的localStorage数据
          if (readingHash.value) {
            localStorage.removeItem(`document_version_${readingHash.value}`);
          }

          // 显示错误提示
          showToast(`切换到版本 ${versionNumber} 失败`, 'danger');

          // 重新抛出错误，让调用方处理
          throw error;
        }
      } else {
        console.warn('没有文档hash，无法切换版本');
        currentVersion.value = previousVersion;
        throw new Error('没有文档hash，无法切换版本');
      }
    };

    // ========== 显示模式相关方法 ==========

    // 处理显示模式切换
    const handleDisplayModeChange = (mode) => {
      try {
        displayMode.value = mode;

        // TODO: 后续在此处触发后端数据加载
        // 根据模式加载对应的数据
        // if (mode === 'core-summary' && !coreSummary.value && readingHash.value) {
        //   loadCoreSummary(readingHash.value);
        // } else if (mode === 'simplified-text' && !simplifiedText.value && readingHash.value) {
        //   loadSimplifiedText(readingHash.value);
        // }

      } catch (error) {
        console.error('❌ 显示模式切换失败:', error);
        showToast('模式切换失败，请重试', 'danger');
      }
    };

    // 处理 Visual 状态变化
    const handleVisualStatusChange = (data) => {
      visualAvailable.value = data.available;
      visualStatus.value = data.status;
    };

    // TODO: 预留后端数据加载方法
    // const loadCoreSummary = async (docHash) => {
    //   try {
    //     const res = await axios.get(`/api/public/doc/${docHash}/summary`);
    //     coreSummary.value = res.data;
    //   } catch (error) {
    //     console.error('加载核心要点失败:', error);
    //     showToast('加载核心要点失败', 'danger');
    //   }
    // };

    // const loadSimplifiedText = async (docHash) => {
    //   try {
    //     const res = await axios.get(`/api/public/doc/${docHash}/simplified`);
    //     simplifiedText.value = res.data.content;
    //   } catch (error) {
    //     console.error('加载精简摘要失败:', error);
    //     showToast('加载精简摘要失败', 'danger');
    //   }
    // };

    // 视频播放器相关方法
    const extractYoutubeVideoId = (url) => {
      if (!url) {
        return null;
      }

      const regexes = [
        /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/,
        /^https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})$/,
        /^https?:\/\/(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})$/,
        /^https?:\/\/(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})$/
      ];

      for (const regex of regexes) {
        const match = url.match(regex);
        if (match && match[1]) {
          return match[1];
        }
      }

      return null;
    };

    const openVideoPlayer = () => {
      if (!readingVideoUrl.value) return;

      const videoId = extractYoutubeVideoId(readingVideoUrl.value);
      if (videoId) {
        currentVideoId.value = videoId;
        currentVideoTitle.value = documentTitle.value || '视频播放';
        showVideoPlayer.value = true;
      }
    };

    const closeVideoPlayer = () => {
      showVideoPlayer.value = false;
      currentVideoId.value = '';
      currentVideoTitle.value = '';
    };

    const toggleVideoPlayerMinimize = () => {
      videoPlayerMinimized.value = !videoPlayerMinimized.value;
    };

    const handleVideoPositionChange = (position) => {
      videoPlayerPosition.value = position;
    };

    const handleVideoSizeChange = (size) => {
      videoPlayerSize.value = size;
    };

    // PDF 下载
    const downloadPDF = async () => {
      if (!readingFilename.value) return;

      pdfDownloading.value = true;
      try {
        const encodedFilename = encodeURIComponent(readingFilename.value);
        const response = await axios.get(`/api/public/summaries/${encodedFilename}/pdf`, {
          responseType: 'blob'
        });

        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${documentTitle.value || readingFilename.value}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        showToast('PDF下载成功', 'success');
      } catch (error) {
        console.error('PDF下载失败:', error);
        showToast('PDF下载失败', 'danger');
      } finally {
        pdfDownloading.value = false;
      }
    };

    // Markdown 下载
    const downloadMarkdown = async () => {
      if (!readingFilename.value) {
        return;
      }

      markdownDownloading.value = true;
      try {
        const encodedFilename = encodeURIComponent(readingFilename.value);
        const response = await axios.get(`/api/public/summaries/${encodedFilename}/markdown`, {
          responseType: 'blob'
        });

        const blob = new Blob([response.data], { type: 'text/markdown; charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;

        // 从响应头获取文件名，如果没有则使用默认名称
        const contentDisposition = response.headers['content-disposition'];
        let filename = `${documentTitle.value || readingFilename.value}.md`;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename\*=UTF-8''(.+)/);
          if (filenameMatch) {
            filename = decodeURIComponent(filenameMatch[1]);
          }
        }

        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        showToast('Markdown下载成功', 'success');
      } catch (error) {
        console.error('Markdown下载失败:', error);
        showToast('Markdown下载失败', 'danger');
      } finally {
        markdownDownloading.value = false;
      }
    };

    // 下载 Visual Insight 长图
    const downloadLongImage = async () => {
      if (!readingHash.value) {
        showToast('文章信息不完整', 'danger');
        return;
      }

      longImageGenerating.value = true;
      try {
        // 调用生成长图 API
        const generateUrl = `/api/article/${readingHash.value}/visual/to-image`;
        const params = new URLSearchParams();
        if (currentVersion.value) {
          params.append('version', currentVersion.value);
        }
        
        const generateResponse = await axios.post(
          params.toString() ? `${generateUrl}?${params}` : generateUrl
        );

        if (generateResponse.data.status !== 'success') {
          throw new Error(generateResponse.data.message || '生成失败');
        }

        // 下载生成的长图
        const imageUrl = generateResponse.data.image_url;
        const downloadResponse = await axios.get(imageUrl, {
          responseType: 'blob'
        });

        const blob = new Blob([downloadResponse.data], { type: 'image/png' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${documentTitle.value || 'visual-insight'}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        showToast('长图下载成功', 'success');
      } catch (error) {
        console.error('长图下载失败:', error);
        const errorMsg = error.response?.data?.detail || error.message || '长图生成失败';
        showToast(errorMsg, 'danger');
      } finally {
        longImageGenerating.value = false;
      }
    };

    // 文章点击处理
    const handleArticleClick = (event) => {
      // 处理文章内的链接点击等
    };

    // 处理笔记库排序变化
    const handleLibrarySortChange = (sortOrder) => {
      localStorage.setItem('librarySortOrder', sortOrder);
    };

    // 测试Toast
    const testToast = () => {
      showToast('这是一个测试消息', 'success');
    };

    // 清理版本相关localStorage数据
    const clearVersionStorage = () => {
      try {
        const keys = Object.keys(localStorage);
        const versionKeys = keys.filter(key => key.startsWith('document_version_'));
        versionKeys.forEach(key => localStorage.removeItem(key));
        showToast(`已清理 ${versionKeys.length} 个版本记录`, 'success');
      } catch (error) {
        console.error('清理版本数据失败:', error);
        showToast('清理版本数据失败', 'danger');
      }
    };

    // 筛选器相关方法
    const toggleLevelDropdown = () => {
      showLevelDropdown.value = !showLevelDropdown.value;
      showYearDropdown.value = false;
    };

    const toggleYearDropdown = () => {
      showYearDropdown.value = !showYearDropdown.value;
      showLevelDropdown.value = false;
    };

    const selectLevel = (level) => {
      selectedLevel.value = level;
      showLevelDropdown.value = false;
    };

    const selectYear = (year) => {
      selectedYear.value = year;
      showYearDropdown.value = false;
    };

    // 格式化方法
    const formatWordCount = (count) => {
      if (!count) return '0';
      if (count >= 10000) {
        return `${(count / 10000).toFixed(1)}万`;
      }
      return count.toString();
    };

    // 点击外部关闭下拉菜单
    const handleClickOutside = (event) => {
      const dropdowns = document.querySelectorAll('.custom-dropdown');
      let clickedInsideDropdown = false;

      dropdowns.forEach(dropdown => {
        if (dropdown.contains(event.target)) {
          clickedInsideDropdown = true;
        }
      });

      if (!clickedInsideDropdown) {
        showLevelDropdown.value = false;
        showYearDropdown.value = false;
      }
    };

    // 任务恢复
    const restoreTask = async () => {
      const taskId = localStorage.getItem('active_task_id');
      const taskUrl = localStorage.getItem('active_task_url');

      if (taskId && taskUrl) {
        try {
          // 先检查任务是否存在
          const token = localStorage.getItem('authToken');
          const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
          
          const response = await axios.get(`/api/tasks/${taskId}/status`, { headers });
          
          if (response.data && response.data.status) {
            // 只有进行中的任务才恢复SSE连接
            if (['queued', 'processing', 'running'].includes(response.data.status)) {
              url.value = taskUrl;
              loading.value = true;
              connectSSE(taskId);
            } else {
              clearActiveTask();
            }
          }
        } catch (error) {
          // 404或其他错误表示任务不存在，清理localStorage
          clearActiveTask();
        }
      }
    };

    // Axios 拦截器
    axios.interceptors.response.use(
      response => response,
      error => {
        if (error.response && error.response.status === 401) {
          if (error.config.url !== '/login') {
            logout();
          }
        }
        return Promise.reject(error);
      }
    );

    // ===== 生命周期钩子 =====

    onMounted(async () => {
      // 检查认证状态
      checkAuth();

      // 处理路由
      handleRouting();

      // 监听浏览器前进后退
      window.addEventListener('popstate', handleRouting);

      // 恢复任务
      await restoreTask();

      // 加载笔记库（已登录用户或访客都需要）
      // 注意：handleRouting 可能已经触发了加载，避免重复调用
      if ((currentView.value === 'library' || currentView.value === 'recent') && summaries.value.length === 0) {
        await loadSummaries();
      }

      // 加载环境信息
      try {
        const res = await axios.get('/api/env');
        Object.assign(environmentInfo, res.data, { loaded: true });
      } catch (error) {
        console.error('获取环境信息失败:', error);
        environmentInfo.loaded = true;
      }

      // 添加点击外部关闭下拉菜单的监听器
      document.addEventListener('click', handleClickOutside);
      
      // 监听 require-login 事件（用于Ultra DeepInsight等功能）
      if (window.eventBus) {
        window.eventBus.on('require-login', ({ reason, callback }) => {
          // 保存回调函数
          if (callback && typeof callback === 'function') {
            loginSuccessCallback.value = callback;
          }
          
          // 显示登录弹窗
          showLogin.value = true;
          
          // 显示提示
          if (reason) {
            showToast(reason, 'warning');
          }
        });
        
        // 监听 session-expired 事件
        window.eventBus.on('session-expired', () => {
          logout();
        });
        
        // 监听 reload-document 事件（用于Ultra完成后刷新）
        window.eventBus.on('reload-document', async ({ hash, reason }) => {
          if (hash && currentView.value === 'read') {
            // Ultra完成后，清除保存的版本号，强制使用最新版本
            if (reason === 'ultra_completed') {
              localStorage.removeItem(`document_version_${hash}`);
            }
            
            // 重新加载文档
            await loadSummaryByHash(hash);
            
            // 通知 ReadingView 刷新状态（因为 hash 没变，watch 不会触发）
            window.eventBus.emit('refresh-reading-status');
          }
        });
      }
    });

    watch(currentView, (newView, oldView) => {
      if (newView === 'library' && oldView === 'read') {
        loadSummaries();
      }
    });

    onUnmounted(() => {
      window.removeEventListener('popstate', handleRouting);
      document.removeEventListener('click', handleClickOutside);
    });

    // ===== 返回响应式数据和方法 =====

    return {
      // 状态
      url,
      title,
      logs,
      loading,
      progressPercent,
      createdFilename,
      createdDocHash,
      currentError,
      showErrorDetails,
      connectionState,
      reconnectAttempts,
      summaries,
      libraryLoading,
      isShareView,
      readingVideoUrl,
      pdfDownloading,
      markdownDownloading,
      longImageGenerating,
      visualAvailable,
      visualStatus,
      readingContent,
      documentTitle,
      documentTitleEn,
      readingError,
      readingFilename,
      readingHash,
      currentDocHash,
      documentVersions,
      currentVersion,
      documentLoading,
      displayMode,
      coreSummary,
      simplifiedText,
      articleTextForTTS,
      currentView,
      isAuthenticated,
      showLogin,
      showToc,
      tocWidth,
      showVideoPlayer,
      videoPlayerMinimized,
      videoPlayerPosition,
      videoPlayerSize,
      currentVideoId,
      currentVideoTitle,
      isVideoResizing,
      isVideoDragging,
      environmentInfo,
      mainContent,

      // 筛选器状态
      selectedLevel,
      selectedYear,
      showLevelDropdown,
      showYearDropdown,

      // 回收站状态
      trashItems,
      trashLoading,

      // 计算属性
      showHeroSection,
      finalizedLogs,
      categorizedSummaries,
      availableYears,
      filteredReinventSummaries,

      // 方法
      login,
      logout,
      goHome,
      goBackToLibrary,
      handleViewChange,
      handleLoginShow,
      handleSummaryClick,
      deleteSummary,
      loadTrashItems,
      restoreFromTrash,
      permanentlyDelete,
      emptyTrash,
      toggleToc,
      handleTocResize,
      startSummarize,
      loadSummaryByHash,
      viewSummary,
      switchVersion,
      handleDisplayModeChange,
      handleVisualStatusChange,
      openVideoPlayer,
      closeVideoPlayer,
      toggleVideoPlayerMinimize,
      handleVideoPositionChange,
      handleVideoSizeChange,
      downloadPDF,
      downloadMarkdown,
      downloadLongImage,
      handleArticleClick,
      handleLibrarySortChange,
      testToast,
      showToast,
      clearVersionStorage,
      toggleLevelDropdown,
      toggleYearDropdown,
      selectLevel,
      selectYear,
      formatWordCount,
      isValidYoutubeUrl,
      manualReconnect
    };
  }
});

// 注册组件
const componentLoader = window.ComponentLoader;

// 注册主要组件（依赖组件将自动加载）
// 配置格式：{ name, path, fileName, critical, priority, version }
const components = [
  // 关键组件 - 首屏必需（只保留最核心的2个）
  {
    name: 'app-header',
    path: '/components/common/AppHeader',
    fileName: 'AppHeader',
    critical: true,
    priority: 1,
    version: '1.0.0'
  },
  {
    name: 'toast-container',
    path: '/components/common/ToastContainer',
    fileName: 'ToastContainer',
    critical: true,
    priority: 1,
    version: '1.0.0'
  },

  // 次要组件 - 根据路由按需加载
  {
    name: 'hero-section',
    path: '/components/views/HeroSection',
    fileName: 'HeroSection',
    critical: false,
    priority: 4,
    version: '1.0.0'
  },
  {
    name: 'library-view',
    path: '/components/views/LibraryView',
    fileName: 'LibraryView',
    critical: false,
    priority: 4,
    version: '1.0.0'
  },
  {
    name: 'recent-view',
    path: '/components/views/RecentView',
    fileName: 'RecentView',
    critical: false,
    priority: 4,
    version: '1.0.0'
  },
  {
    name: 'reading-view',
    path: '/components/views/ReadingView',
    fileName: 'ReadingView',
    critical: false,
    priority: 4,
    version: '1.0.0'
  },
  {
    name: 'create-view',
    path: '/components/views/CreateView',
    fileName: 'CreateView',
    critical: false,
    priority: 6,
    version: '1.0.0'
  },
  {
    name: 'video-player',
    path: '/components/common/VideoPlayer',
    fileName: 'VideoPlayer',
    critical: false,
    priority: 7,
    version: '1.0.0'
  },
  {
    name: 'login-modal',
    path: '/components/common/LoginModal',
    fileName: 'LoginModal',
    critical: true,
    priority: 1,
    version: '1.0.0'
  },
  {
    name: 'connection-status',
    path: '/components/common/ConnectionStatus',
    fileName: 'ConnectionStatus',
    critical: false,
    priority: 8,
    version: '1.0.0'
  },
  {
    name: 'trash-view',
    path: '/components/views/TrashView',
    fileName: 'TrashView',
    critical: false,
    priority: 9,
    version: '1.0.0'
  }
];

// 更新加载进度
const updateLoadingProgress = (message, percent = null) => {
  const progressEl = document.getElementById('loading-progress');
  if (progressEl) {
    if (percent !== null) {
      progressEl.textContent = `${message} (${percent}%)`;
    } else {
      progressEl.textContent = message;
    }
  }
};

// 隐藏加载指示器并显示应用
const showApp = () => {
  const loadingEl = document.getElementById('loading-indicator');
  const appEl = document.getElementById('app');

  if (loadingEl && appEl) {
    // 淡出加载指示器
    loadingEl.classList.add('fade-out');

    // 显示应用
    appEl.classList.remove('app-hidden');
    appEl.classList.add('app-visible');

    // 延迟移除加载指示器
    setTimeout(() => {
      loadingEl.style.display = 'none';
    }, 300);
  }
};

// 批量注册组件（使用关键组件优先加载策略）
updateLoadingProgress('正在初始化...');

// 预加载关键组件资源（使用浏览器原生预加载）
// 动态优化关键组件：根据当前路由标记首屏组件为关键组件
const currentPath = window.location.pathname;
let extraCriticalComponents = [];

if (currentPath.match(/^\/d\/|^\/documents\//)) {
  // 阅读页
  extraCriticalComponents = ['reading-view', 'video-player'];
} else if (currentPath === '/trash') {
  // 回收站页面
  extraCriticalComponents = ['trash-view'];
} else {
  // 首页/列表页 (同时加载 library 和 recent 以确保切换流畅)
  extraCriticalComponents = ['library-view', 'hero-section', 'recent-view'];
}

components.forEach(c => {
  if (extraCriticalComponents.includes(c.name)) {
    c.critical = true;
    // 提升优先级
    c.priority = 2;
  }
});

if (window.ResourceHints) {
  const criticalComponents = components.filter(c => c.critical === true);
  window.ResourceHints.preloadComponents(criticalComponents);
}

// 使用LoadingStrategy进行关键组件优先加载
window.LoadingStrategy.loadCriticalFirst(app, components, {
  useCache: true,
  timeout: 10000,
  onProgress: (loaded, total, name, phase) => {
    const percent = Math.round((loaded / total) * 100);
    const phaseText = phase === 'critical' ? '关键组件' : '组件';
    updateLoadingProgress(`正在加载${phaseText}: ${name}`, percent);
  },
  onCriticalComplete: (results) => {
    // 关键组件加载完成，立即挂载应用
    updateLoadingProgress('正在启动应用...');

    setTimeout(() => {
      app.mount('#app');

      setTimeout(() => {
        showApp();
      }, 50);
    }, 50);
  }
}).then((results) => {

  // 输出性能报告
  if (window.PerformanceMonitor) {
    const report = window.PerformanceMonitor.getReport();
  }

  // 输出缓存统计
  if (window.CacheManager) {
    const stats = window.CacheManager.getStats();
  }

  // 检查失败的组件
  const failed = results.filter(r => !r.success);
  if (failed.length > 0) {
    console.warn(`⚠️ ${failed.length} 个组件加载失败:`, failed.map(r => r.name));
  }
}).catch(error => {
  console.error('❌ 组件加载失败:', error);
  updateLoadingProgress('组件加载失败，正在降级处理...');

  // 降级处理：仍然挂载应用，但可能缺少某些组件
  setTimeout(() => {
    try {
      app.mount('#app');
      setTimeout(() => {
        showApp();
        console.warn('⚠️ 应用已启动（降级模式）');
      }, 100);
    } catch (mountError) {
      console.error('❌ 应用挂载失败:', mountError);
      updateLoadingProgress('应用启动失败，请刷新页面');
    }
  }, 500);
}); 