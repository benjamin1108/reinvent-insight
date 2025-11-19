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
    console.log('✅ marked已就绪，直接执行回调');
    callback(window.marked);
    return;
  }
  
  console.log('⏳ marked未加载，等待加载...');
  
  // 检查是否已经在加载中
  if (window.markedLoadingPromise) {
    window.markedLoadingPromise.then(() => {
      console.log('✅ marked加载完成（复用Promise）');
      callback(window.marked);
    });
    return;
  }
  
  // 首先尝试等待已有的script标签加载完成
  const existingScript = document.querySelector('script[src*="marked"]');
  if (existingScript) {
    console.log('⏳ 检测到marked脚本标签，等待加载完成...');
    window.markedLoadingPromise = new Promise((resolve, reject) => {
      // 设置超时检查
      let checkCount = 0;
      const maxChecks = 50; // 最多检查5秒
      const checkInterval = setInterval(() => {
        checkCount++;
        if (checkMarked()) {
          clearInterval(checkInterval);
          console.log('✅ marked加载完成（轮询检测）');
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
    console.log('⏳ 动态加载marked.js...');
    window.markedLoadingPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = '/js/vendor/marked.min.js';
      script.onload = () => {
        console.log('✅ marked.js脚本加载完成');
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
    console.log('✅ marked配置完成');
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

    // 认证状态 - 必须在 getInitialView 之前声明
    const isAuthenticated = ref(false);
    const showLogin = ref(false);

    // 视图控制
    const getInitialView = () => {
      const path = window.location.pathname;
      const hashMatch = path.match(/^\/d\/([a-zA-Z0-9]+)$/);
      const docMatch = path.match(/\/documents\/(.+)/);
      
      if (hashMatch || docMatch) {
        return 'read';
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
        const titleEn = summary.title_en || '';
        if (titleEn.toLowerCase().includes('reinvent') || titleEn.toLowerCase().includes('re:invent')) {
          reinvent.push(summary);
        } else {
          other.push(summary);
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
        
        currentView.value = 'recent';
        await nextTick();
        console.log('🔐 登录成功，正在重新加载笔记库...');
        await loadSummaries();
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
        console.log('🔄 退出登录后重新加载公开文章列表成功');
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
    
    // 视图导航方法
    const goHome = () => {
      history.pushState(null, '', '/');
      currentView.value = 'recent';
      clearReadingState();
      closeVideoPlayer();
    };

    const goBackToLibrary = () => {
      history.pushState(null, '', '/');
      currentView.value = 'library';
      clearReadingState();
      closeVideoPlayer();
    };

    const clearReadingState = () => {
      readingContent.value = '';
      documentTitle.value = '';
      readingFilename.value = '';
      readingHash.value = '';
    };

    const handleViewChange = (view) => {
      currentView.value = view;
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
      console.log('🔘 [APP] toggleToc 被调用');
      console.log('🔍 [APP] 当前 showToc:', showToc.value);
      
      showToc.value = !showToc.value;
      
      console.log('✅ [APP] 切换后 showToc:', showToc.value);
      console.log('💾 [APP] 保存到 localStorage');
      
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
        progressPercent.value = 0;

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
                // 计算上传进度（0-20%用于上传）
                const uploadPercent = Math.round((progressEvent.loaded * 20) / progressEvent.total);
                progressPercent.value = uploadPercent;
                
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
            progressPercent.value = 20;
          } else {
            // 处理URL分析（保持原有逻辑）
            res = await axios.post('/summarize', { url: analysisData.url });
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
      
      console.log(`🔌 建立 SSE 连接: ${sseUrl.replace(/token=[^&]+/, 'token=***')}`);
      
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
            progressPercent.value = 100;
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
            // 处理进度消息
            progressPercent.value = data.progress || 0;
            console.log(`📊 进度更新: ${progressPercent.value}%`);
          } else if (data.type === 'error') {
            // 处理结构化错误消息
            console.log('📛 收到错误消息:', data);
            
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
            console.log('💓 SSE 心跳正常');
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
    const loadSummaries = async () => {
      libraryLoading.value = true;
      try {
        // 根据认证状态使用不同的API端点
        const endpoint = isAuthenticated.value ? '/summaries' : '/api/public/summaries';
        console.log(`📚 正在加载笔记库，认证状态: ${isAuthenticated.value}, 端点: ${endpoint}`);
        
        let res;
        try {
          res = await axios.get(endpoint);
        } catch (error) {
          // 如果认证端点返回401，自动切换到公开端点
          if (error.response?.status === 401 && isAuthenticated.value) {
            console.log('🔄 认证失效，切换到公开端点');
            isAuthenticated.value = false;
            res = await axios.get('/api/public/summaries');
          } else {
            throw error;
          }
        }
        
        console.log('📚 API响应:', res.data);
        
        // 统一处理API响应格式
        let dataArray;
        if (isAuthenticated.value) {
          // 已认证用户：直接使用res.data，如果是数组则直接用，否则尝试res.data.summaries
          dataArray = Array.isArray(res.data) ? res.data : (res.data.summaries || []);
        } else {
          // 访客用户：使用res.data.summaries
          dataArray = res.data.summaries || [];
        }
        
        summaries.value = dataArray;
        console.log(`📚 设置summaries数组，长度: ${summaries.value.length}`);
      } catch (error) {
        console.error('加载笔记库失败:', error);
        showToast('加载笔记库失败', 'danger');
      } finally {
        libraryLoading.value = false;
      }
    };
    
    const loadSummary = async (filename, pushState = true) => {
      documentLoading.value = true;
      readingError.value = '';
      
      try {
        const res = await axios.get(`/summary/${encodeURIComponent(filename)}`);
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
        
        console.log('📄 加载文档数据:', {
          title: data.title_cn || data.title,
          contentLength: data.content?.length || 0,
          hasContent: !!data.content
        });
        
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
        
        console.log('🔄 开始渲染内容，长度:', contentToRender.length);
        
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
          console.log('✅ 内容渲染完成，HTML长度:', renderedHtml.length);
          
          // 强制触发Vue的响应式更新
          nextTick(() => {
            console.log('✅ DOM已更新');
          });
        } catch (error) {
          console.error('❌ 内容渲染失败:', error);
        }
      };
      
      if (needVersionSwitch) {
        // 需要切换版本：先显示加载状态，然后加载目标版本内容
        console.log('🔄 需要切换到版本:', targetVersion);
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
        console.log('✅ 使用默认版本，直接渲染内容，content长度:', content?.length || 0);
        
        // 使用双重nextTick确保视图完全切换后再渲染内容
        nextTick(() => {
          nextTick(() => {
            ensureMarkedReady(() => {
              console.log('✅ marked.js已就绪，开始渲染内容');
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
          
          console.log('📄 版本切换：获取到内容，长度:', data.content?.length || 0);
          
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
                
                console.log('✅ 版本内容渲染完成，HTML长度:', renderedHtml.length);
                resolve();
              } catch (error) {
                reject(error);
              }
            });
          });
          
          // 将用户选择的版本保存到 localStorage（成功后才保存）
          localStorage.setItem(`document_version_${readingHash.value}`, versionNumber);
          
          console.log(`✅ 版本切换成功: ${previousVersion} → ${versionNumber}`);
          
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
        console.log('🔄 切换显示模式:', displayMode.value, '→', mode);
        displayMode.value = mode;
        
        // TODO: 后续在此处触发后端数据加载
        // 根据模式加载对应的数据
        // if (mode === 'core-summary' && !coreSummary.value && readingHash.value) {
        //   loadCoreSummary(readingHash.value);
        // } else if (mode === 'simplified-text' && !simplifiedText.value && readingHash.value) {
        //   loadSimplifiedText(readingHash.value);
        // }
        
        console.log('✅ 显示模式切换成功:', mode);
      } catch (error) {
        console.error('❌ 显示模式切换失败:', error);
        showToast('模式切换失败，请重试', 'danger');
      }
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
      if (!readingFilename.value) return;
      
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

    // 文章点击处理
    const handleArticleClick = (event) => {
      // 处理文章内的链接点击等
    };
    
    // 处理笔记库排序变化
    const handleLibrarySortChange = (sortOrder) => {
      console.log('笔记库排序方式已更改:', sortOrder);
      // 可以在这里添加额外的逻辑，如保存用户偏好到localStorage
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
        url.value = taskUrl;
        connectSSE(taskId);
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
      if (currentView.value === 'library' || currentView.value === 'recent') {
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
    });

    watch(currentView, (newView, oldView) => {
      if (newView === 'library' && oldView === 'read') {
        loadSummaries();
      }
    });
    
    // 🔍 调试：监控 showToc 变化
    watch(showToc, (newVal, oldVal) => {
      console.log('🔄 [APP WATCH] showToc 变化:', oldVal, '->', newVal);
      console.log('🔍 [APP WATCH] currentView:', currentView.value);
      console.log('🔍 [APP WATCH] displayMode:', displayMode.value);
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
      connectionState,
      reconnectAttempts,
      summaries,
      libraryLoading,
      isShareView,
      readingVideoUrl,
      pdfDownloading,
      markdownDownloading,
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
      toggleToc,
      handleTocResize,
      startSummarize,
      loadSummaryByHash,
      viewSummary,
      switchVersion,
      handleDisplayModeChange,
      openVideoPlayer,
      closeVideoPlayer,
      toggleVideoPlayerMinimize,
      handleVideoPositionChange,
      handleVideoSizeChange,
      downloadPDF,
      downloadMarkdown,
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
  // 关键组件 - 首屏必需
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
  {
    name: 'hero-section',
    path: '/components/views/HeroSection',
    fileName: 'HeroSection',
    critical: true,
    priority: 2,
    version: '1.0.0'
  },
  {
    name: 'library-view',
    path: '/components/views/LibraryView',
    fileName: 'LibraryView',
    critical: true,
    priority: 2,
    version: '1.0.0'
  },
  {
    name: 'recent-view',
    path: '/components/views/RecentView',
    fileName: 'RecentView',
    critical: true,
    priority: 2,
    version: '1.0.0'
  },
  
  // 非关键组件 - 可延迟加载
  {
    name: 'reading-view',
    path: '/components/views/ReadingView',
    fileName: 'ReadingView',
    critical: true,  // 改为关键组件，因为直接访问文章链接时需要立即显示
    priority: 3,
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
    critical: false,
    priority: 4,
    version: '1.0.0'
  },
  {
    name: 'connection-status',
    path: '/components/common/ConnectionStatus',
    fileName: 'ConnectionStatus',
    critical: false,
    priority: 8,
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
    console.log('✅ 关键组件加载完成，挂载应用...');
    updateLoadingProgress('正在启动应用...');
    
    setTimeout(() => {
      app.mount('#app');
      
      setTimeout(() => {
        showApp();
        console.log('✅ 应用已启动，后台继续加载非关键组件...');
      }, 50);
    }, 50);
  }
}).then((results) => {
  console.log('✅ 所有组件加载完成');
  
  // 输出性能报告
  if (window.PerformanceMonitor) {
    const report = window.PerformanceMonitor.getReport();
    console.log(`📊 性能统计: 总耗时 ${report.totalLoadTime.toFixed(2)}ms, 缓存命中率 ${(report.cacheHitRate * 100).toFixed(1)}%`);
  }
  
  // 输出缓存统计
  if (window.CacheManager) {
    const stats = window.CacheManager.getStats();
    console.log(`💾 缓存统计: 命中率 ${(stats.hitRate * 100).toFixed(1)}%, 条目数 ${stats.entryCount}`);
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