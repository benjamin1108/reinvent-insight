const { createApp, ref, onMounted, computed, nextTick, watch, onUnmounted, reactive } = Vue;

// 配置 marked 和 highlight.js
marked.setOptions({
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value;
      } catch (__) { }
    }
    return hljs.highlightAuto(code).value;
  },
  breaks: true,
  gfm: true
});

createApp({
  setup() {
    // --- 状态管理 ---
    const url = ref('');
    const summary = ref('');
    const title = ref('');
    const rendered = ref('');
    const logs = ref([]);
    const loading = ref(false);
    const progressPercent = ref(0);

    // 笔记库状态
    const summaries = ref([]);
    const libraryLoading = ref(false);
    const isShareView = ref(false);
    const readingVideoUrl = ref('');
    const pdfDownloading = ref(false); // 新增：PDF下载状态
    
    // 筛选器状态
    const selectedLevel = ref('');
    const selectedYear = ref('');
    const showLevelDropdown = ref(false);
    const showYearDropdown = ref(false);
    
    // 视频播放器状态
    const showVideoPlayer = ref(false);
    const videoPlayerMinimized = ref(false);
    const videoPlayerPosition = ref({ x: null, y: null });
    const videoPlayerSize = ref({ width: 480, height: 320 });
    const currentVideoId = ref('');
    const currentVideoTitle = ref('');
    
    // 阅读视图状态
    const readingContent = ref('');
    const documentTitle = ref('');
    const readingError = ref('');
    const readingFilename = ref(''); // 新增：当前阅读的文件名
    const readingHash = ref(''); // 新增：当前阅读文档的hash
    
    // 版本管理状态
    const documentVersions = ref([]); // 当前文档的所有版本
    const currentVersion = ref(0); // 当前选中的版本
    const showVersionDropdown = ref(false); // 版本下拉菜单显示状态
    const hasMultipleVersions = computed(() => documentVersions.value.length > 1); // 是否有多个版本

    // 视图控制
    const currentView = ref('library'); // 默认视图 'create', 'library', 'read'
    
    // 认证状态
    const isAuthenticated = ref(false);
    const showLogin = ref(false);
    const loginUsername = ref('');
    const loginPassword = ref('');
    
    // Toast 状态
    const toast = reactive({ show: false, message: '', type: '' });

    // 添加一个标志来防止重复加载
    let loadingPromise = null;

    // TOC 相关状态
    const showToc = ref(true);
    const tocHtml = ref('');
    const tocWidth = ref(416); // 26rem = 416px
    const isVideoResizing = ref(false); // 添加响应式状态
    const isVideoDragging = ref(false); // 添加拖动响应式状态

    // --- 路由处理 ---
    const handleRouting = () => {
      const path = window.location.pathname;
      
      // 检查是否是短链接格式 /d/hash
      const hashMatch = path.match(/^\/d\/([a-zA-Z0-9]+)$/);
      const docMatch = path.match(/\/documents\/(.+)/);

      if (hashMatch) {
        const docHash = hashMatch[1];
        loadSummaryByHash(docHash, false); // false: 不要推入历史记录
      } else if (docMatch) {
        const filename = decodeURIComponent(docMatch[1]);
        loadSummary(filename, false); // false: 不要推入历史记录，因为我们已经在这个URL上
      } else {
        // 如果不是文档URL，则显示笔记库
        currentView.value = 'library';
        if (isAuthenticated.value && summaries.value.length === 0) {
            loadSummaries();
        }
      }
    };
    
    // 监听浏览器前进后退
    window.addEventListener('popstate', handleRouting);


    // --- 认证 ---
    const login = async () => {
      try {
        const res = await axios.post('/login', {
          username: loginUsername.value,
          password: loginPassword.value
        });
        const token = res.data.token;
        localStorage.setItem('authToken', token);
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        isAuthenticated.value = true;
        showLogin.value = false;
        showToast('登录成功', 'success');
        // 登录后切换到笔记库视图并加载数据
        currentView.value = 'library';
        // 使用 nextTick 确保视图更新后再加载数据
        await nextTick();
        await loadSummaries();
      } catch (error) {
        console.error('登录失败:', error);
        showToast(error.response?.data?.detail || '登录失败', 'danger');
      }
    };

    const logout = () => {
      localStorage.removeItem('authToken');
      delete axios.defaults.headers.common['Authorization'];
      isAuthenticated.value = false;
      currentView.value = 'library'; // 退出后返回笔记库(公共展示页)
      summaries.value = []; // 清空笔记库数据
      showLogin.value = true; // 显示登录框
      showToast('会话已过期，请重新登录', 'warning');
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

    // 权限检查辅助函数
    const requireAuth = (action) => {
        if (!isAuthenticated.value) {
            showLogin.value = true;
            showToast('请先登录', 'warning');
        } else {
            action();
        }
    };

    // --- Axios Interceptor for 401 Handling ---
    axios.interceptors.response.use(
      response => response,
      error => {
        if (error.response && error.response.status === 401) {
          // 检查这是否是登录请求本身失败，避免无限循环
          if (error.config.url !== '/login') {
            logout();
          }
        }
        return Promise.reject(error);
      }
    );

    // --- UI & 交互 ---
    const showToast = (message, type = 'success', duration = 3000) => {
      toast.show = true;
      toast.message = message;
      toast.type = type;
      setTimeout(() => {
        toast.show = false;
      }, duration);
    };
    
    const goHome = () => {
      history.pushState(null, '', '/');
      currentView.value = 'library';
      // 清理阅读视图状态
      readingContent.value = '';
      documentTitle.value = '';
      readingFilename.value = '';
      tocHtml.value = '';
    };

    const goBackToLibrary = () => {
      history.pushState(null, '', '/');
      currentView.value = 'library';
      // 清理阅读视图状态
      readingContent.value = '';
      documentTitle.value = '';
      readingFilename.value = '';
      tocHtml.value = '';
    };

    const toggleToc = () => {
      showToc.value = !showToc.value;
    };

    // 下拉菜单方法
    const toggleLevelDropdown = () => {
      showLevelDropdown.value = !showLevelDropdown.value;
      showYearDropdown.value = false; // 关闭其他下拉菜单
    };

    const toggleYearDropdown = () => {
      showYearDropdown.value = !showYearDropdown.value;
      showLevelDropdown.value = false; // 关闭其他下拉菜单
    };

    const selectLevel = (level) => {
      selectedLevel.value = level;
      showLevelDropdown.value = false;
    };

    const selectYear = (year) => {
      selectedYear.value = year;
      showYearDropdown.value = false;
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
      
      // 处理版本下拉菜单
      const versionSelector = document.querySelector('.version-selector');
      if (versionSelector && !versionSelector.contains(event.target)) {
        showVersionDropdown.value = false;
      }
    };

    // 处理目录点击
    const handleTocClick = (event) => {
      const target = event.target;
      if (target.tagName.toLowerCase() === 'a' && target.dataset.target) {
        event.preventDefault();
        const id = target.dataset.target;
        const el = document.getElementById(id);
        if (el) {
          const articleContainer = document.querySelector('.mobile-reading .flex-1.overflow-y-auto');
          if (articleContainer) {
            const containerRect = articleContainer.getBoundingClientRect();
            const elementRect = el.getBoundingClientRect();
            const relativeTop = elementRect.top - containerRect.top;
            
            const newScrollTop = articleContainer.scrollTop + relativeTop - 20; // 预留20px顶部空间

            articleContainer.scrollTo({
              top: newScrollTop,
              behavior: 'smooth'
            });
          } else {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }
      }
    };

    // 拖拽侧栏分隔条
    let isDragging = false;

    const initDrag = (e) => {
      isDragging = true;
      document.addEventListener('mousemove', doDrag);
      document.addEventListener('mouseup', stopDrag);
      e.preventDefault();
    };

    const doDrag = (e) => {
      if (!isDragging) return;
      const newWidth = Math.max(300, Math.min(800, e.clientX));
      tocWidth.value = newWidth;
    };

    const stopDrag = () => {
      isDragging = false;
      document.removeEventListener('mousemove', doDrag);
      document.removeEventListener('mouseup', stopDrag);
    };
    
    // ---------- 动态调整TOC宽度 ----------
    const adjustTocWidth = () => {
      const tocElement = document.querySelector('.toc-sidebar .toc'); // Target specifically within the sidebar
      if (!tocElement) return;

      const links = tocElement.querySelectorAll('a');
      if (!links || links.length === 0) return;

      let maxWidth = 0;
      links.forEach(link => {
        if (link.scrollWidth > maxWidth) {
          maxWidth = link.scrollWidth;
        }
      });

      if (maxWidth > 0) {
        const newTocWidth = Math.min(maxWidth + 60, Math.max(300, window.innerWidth * 0.5)); 
        tocWidth.value = newTocWidth;
      }
    };

    // ---------- 渲染 Markdown 并生成目录 ----------
    const slugify = (str) => {
      return str.toLowerCase()
        .replace(/[^\w\u4e00-\u9fa5\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
    };
    
    const renderMarkdownWithToc = (markdown) => {
      const rawHtml = marked.parse(markdown);
      const parser = new DOMParser();
      const doc = parser.parseFromString(rawHtml, 'text/html');
      
      // 首先，确保所有标题都有ID，以便能够链接到它们
      const allHeadings = [...doc.body.querySelectorAll('h1,h2,h3,h4,h5,h6')];
      allHeadings.forEach(h => {
        const text = h.textContent.replace(/\s*\(#.+\)$/g, '').trim();
        h.id = slugify(text);
      });
      
      // 现在，仅使用 H3 元素构建目录
      const h3Elements = doc.querySelectorAll('h3');
      if (h3Elements.length > 0) {
          // 构建目录列表，不添加额外的标题
          let tocHtmlContent = '<ul>';
          h3Elements.forEach((h3) => {
              const text = h3.textContent.replace(/\s*\(#.+\)$/g, '').trim();
              const id = h3.id; // 使用已分配的ID
              tocHtmlContent += `<li><a data-target="${id}">${text}</a></li>`;
          });
          tocHtmlContent += '</ul>';
          return { html: doc.body.innerHTML, tocHtml: tocHtmlContent };
      }
      
      // 如果没有找到H3，则返回不带TOC的内容
      return { html: doc.body.innerHTML, tocHtml: '' };
    };


    // --- 主要功能方法 ---

    const isValidYoutubeUrl = (str) => {
      if (!str || typeof str !== 'string') return false;
      const url = str.trim();
      const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
      return youtubeRegex.test(url);
    };

    const clearActiveTask = () => {
        localStorage.removeItem('active_task_id');
        localStorage.removeItem('active_task_url');
    };

    const startSummarize = async () => {
      requireAuth(async () => {
        if (loading.value || !url.value) return;

        logs.value = [];
        summary.value = '';
        title.value = '';
        rendered.value = '';
        loading.value = true;
        progressPercent.value = 0;

        try {
          const res = await axios.post('/summarize', { url: url.value });
          const taskId = res.data.task_id;
          
          // --- 新增：保存任务状态到localStorage ---
          localStorage.setItem('active_task_id', taskId);
          localStorage.setItem('active_task_url', url.value);
          
          connectWebSocket(taskId);
        } catch (error) {
          console.error('任务创建失败:', error);
          loading.value = false;
          logs.value.push(`错误: ${error.response?.data?.detail || error.message}`);
          clearActiveTask(); // 创建失败时清理
        }
      });
    };
    
    const connectWebSocket = (taskId) => {
        const wsUrl = `ws://${window.location.host}/ws/${taskId}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            loading.value = true;
            logs.value.push('已连接到分析服务...');
        };

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          
          if (data.type === 'result') {
            title.value = data.title;
            summary.value = data.summary;
            rendered.value = marked.parse(data.summary);
            
            // --- 关键修改: 收到结果后立即解除加载状态 ---
            loading.value = false;
            progressPercent.value = 100;
            
            ws.close();
            clearActiveTask();
          } else if (data.type === 'progress') {
            // 处理带进度的消息
            logs.value.push(data.message);
            progressPercent.value = data.progress;
          } else if (data.type === 'error') {
            // 处理错误消息
            logs.value.push('错误: ' + data.message);
            loading.value = false;
            progressPercent.value = 0;
            ws.close();
            clearActiveTask();
          } else {
            // 处理普通日志消息 (type === 'log')
            logs.value.push(data.message);
            progressPercent.value = Math.min(99, (logs.value.length / 10) * 100);
          }
        };
        ws.onerror = (event) => {
          console.error("WebSocket error:", event);
          logs.value.push("错误: WebSocket 连接中断。");
          loading.value = false;
          // 错误发生时也清理，避免卡住
          clearActiveTask();
        };
        ws.onclose = () => {
          loading.value = false;
          progressPercent.value = 100;
          console.log("WebSocket connection closed or task finished.");
          // 正常关闭（任务完成）时，localStorage已在onmessage中清理
        };
    };

    const loadSummaries = async () => {
      // 如果已经有正在进行的加载，返回现有的 Promise
      if (loadingPromise) {
        console.log('loadSummaries: 已有加载进行中，跳过');
        return loadingPromise;
      }
      
      console.log('loadSummaries: 开始加载，isAuthenticated =', isAuthenticated.value);
      libraryLoading.value = true;
      const endpoint = isAuthenticated.value ? '/summaries' : '/api/public/summaries';
      console.log('loadSummaries: 使用端点', endpoint);
      
      // 创建新的加载 Promise
      loadingPromise = axios.get(endpoint)
        .then(res => {
          console.log('loadSummaries: 收到响应', res.data);
          if (res.data && res.data.summaries) {
            summaries.value = res.data.summaries;
            console.log('loadSummaries: 加载成功，获得', summaries.value.length, '篇文章');
          } else {
            console.warn('loadSummaries: 响应格式异常', res.data);
            summaries.value = [];
          }
        })
        .catch(err => {
          console.error('加载摘要列表失败:', err);
          showToast('加载摘要列表失败', 'danger');
          // 保持现有数据不变，避免清空列表
        })
        .finally(() => {
          libraryLoading.value = false;
          loadingPromise = null; // 清除 Promise 引用
        });
      
      return loadingPromise;
    };

    const loadSummary = async (filename, pushState = true) => {
      try {
        readingError.value = '';
        readingContent.value = ''; // 清空旧内容
        currentView.value = 'read'; // 切换到阅读视图以显示加载状态

        // URL编码文件名以处理特殊字符
        const encodedFilename = encodeURIComponent(filename);

        // 根据认证状态选择端点
        const endpoint = isAuthenticated.value 
          ? `/summaries/${encodedFilename}` 
          : `/api/public/summaries/${encodedFilename}`;
        
        const res = await axios.get(endpoint);
        
        // 查找当前文档的hash（从summaries列表中查找）
        let docHash = '';
        const summary = summaries.value.find(s => s.filename === filename);
        if (summary && summary.hash) {
          docHash = summary.hash;
        }
        
        if (pushState) {
          // 在非分享视图中，更新URL
          if (!isAuthenticated.value) {
            history.pushState({ filename }, '', `/documents/${encodedFilename}`);
          }
        }
        viewSummary(res.data.title, res.data.content, filename, res.data.video_url, docHash, res.data.versions);
      } catch (err) {
        console.error('加载摘要失败:', err);
        const errorMessage = err.response?.data?.detail || '加载文章失败';
        readingError.value = errorMessage;
        showToast(errorMessage, 'danger');
        currentView.value = 'read'; // 确保停留在阅读视图显示错误
      }
    };
    
    const loadSummaryByHash = async (docHash, pushState = true) => {
      try {
        readingError.value = '';
        readingContent.value = ''; // 清空旧内容
        currentView.value = 'read'; // 切换到阅读视图以显示加载状态

        // 根据认证状态选择端点，使用hash端点
        const endpoint = `/api/public/doc/${docHash}`;
        
        const res = await axios.get(endpoint);
        
        if (pushState) {
          // 更新URL为短链接格式
          history.pushState({ hash: docHash }, '', `/d/${docHash}`);
        }
        viewSummary(res.data.title, res.data.content, res.data.filename, res.data.video_url, docHash, res.data.versions);
      } catch (err) {
        console.error('加载摘要失败:', err);
        const errorMessage = err.response?.data?.detail || '加载文章失败';
        readingError.value = errorMessage;
        showToast(errorMessage, 'danger');
        currentView.value = 'read'; // 确保停留在阅读视图显示错误
      }
    };
    
    const viewSummary = (title, content, filename, videoUrl = '', docHash, versions = []) => {
      documentTitle.value = title;
      readingFilename.value = filename; // 跟踪当前文件名
      readingVideoUrl.value = videoUrl; // 保存视频链接
      readingHash.value = docHash; // 保存文档的hash
      
      // 处理版本信息
      documentVersions.value = versions;
      if (versions.length > 0) {
        // 从versions中找到当前文件对应的版本
        const currentFile = versions.find(v => v.filename === filename);
        currentVersion.value = currentFile ? currentFile.version : 0;
        
        // 尝试从localStorage恢复用户的版本偏好
        const savedPrefs = localStorage.getItem('version_prefs');
        if (savedPrefs && videoUrl) {
          try {
            const prefs = JSON.parse(savedPrefs);
            const videoId = extractYoutubeVideoId(videoUrl);
            if (videoId && prefs[`video_${videoId}`]) {
              const preferredVersion = prefs[`video_${videoId}`].preferred;
              // 检查偏好版本是否存在
              if (versions.some(v => v.version === preferredVersion)) {
                // 如果偏好版本不是当前版本，则切换
                if (preferredVersion !== currentVersion.value) {
                  switchVersion(preferredVersion);
                  return; // 切换版本会重新调用viewSummary，所以直接返回
                }
              }
            }
          } catch (e) {
            console.error('读取版本偏好失败:', e);
          }
        }
      } else {
        // 没有版本信息，设置为默认值
        currentVersion.value = 0;
      }
      
      // 切换文档时关闭视频播放器
      if (showVideoPlayer.value) {
        closeVideoPlayer();
      }

      // 在解析前，移除 YAML Front Matter
      const cleanContent = content.replace(/^---[\s\S]*?---/, '').trim();
      
      const { html, tocHtml: tocString } = renderMarkdownWithToc(cleanContent);
      readingContent.value = html;
      tocHtml.value = tocString;
      currentView.value = 'read';

      nextTick(() => {
        // Re-run highlight.js on the new content
        document.querySelectorAll('.prose-tech pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
        adjustTocWidth();
      });
    };

    // 版本切换相关函数
    const toggleVersionDropdown = () => {
      showVersionDropdown.value = !showVersionDropdown.value;
    };
    
    const switchVersion = async (version) => {
      // 找到对应版本的文件名
      const versionInfo = documentVersions.value.find(v => v.version === version);
      if (!versionInfo) {
        console.error('版本信息未找到:', version);
        return;
      }
      
      // 保存用户的版本偏好
      if (readingVideoUrl.value) {
        const videoId = extractYoutubeVideoId(readingVideoUrl.value);
        if (videoId) {
          const savedPrefs = localStorage.getItem('version_prefs') || '{}';
          const prefs = JSON.parse(savedPrefs);
          prefs[`video_${videoId}`] = {
            preferred: version,
            lastView: Date.now()
          };
          localStorage.setItem('version_prefs', JSON.stringify(prefs));
        }
      }
      
      // 关闭版本下拉菜单
      showVersionDropdown.value = false;
      
      // 加载新版本
      await loadSummary(versionInfo.filename, false);
    };

    // 辅助函数：从YouTube URL中提取视频ID
    const extractYoutubeVideoId = (url) => {
      if (!url) return null;
      
      // 支持多种YouTube URL格式
      const patterns = [
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)/,
        /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^?]+)/,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^?]+)/,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([^?]+)/
      ];
      
      for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
          return match[1];
        }
      }
      
      return null;
    };

    // 下载PDF功能
    const downloadPDF = async () => {
      if (!readingFilename.value) {
        showToast('无法下载：文件名未找到', 'danger');
        return;
      }

      pdfDownloading.value = true;
      
      try {
        // URL编码文件名
        const encodedFilename = encodeURIComponent(readingFilename.value);
        const pdfUrl = `/api/public/summaries/${encodedFilename}/pdf`;
        
        // 创建临时链接并触发下载
        const link = document.createElement('a');
        link.href = pdfUrl;
        link.download = readingFilename.value.replace('.md', '.pdf');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 显示成功提示
        showToast('PDF下载已开始', 'success');
      } catch (error) {
        console.error('下载PDF失败:', error);
        showToast('下载PDF失败', 'danger');
      } finally {
        pdfDownloading.value = false;
      }
    };

    // --- 计算属性和工具函数 ---
    const categorizedSummaries = computed(() => {
      const reinvent = [];
      const other = [];
      if (summaries.value && Array.isArray(summaries.value)) {
        summaries.value.forEach(summary => {
          if (!summary) return; // 跳过空对象
          
          // 使用后端提供的 is_reinvent 字段来判断
          if (summary.is_reinvent === true) {
              reinvent.push(summary);
          } else {
              other.push(summary);
          }
        });
      }
      return { reinvent, other };
    });

    // 可用年份列表（从re:Invent文章中提取）
    const availableYears = computed(() => {
      const years = new Set();
      categorizedSummaries.value.reinvent.forEach(summary => {
        // 从title_en中提取年份
        const yearMatch = summary.title_en && summary.title_en.match(/\b(20\d{2})\b/);
        if (yearMatch) {
          years.add(yearMatch[1]);
        } else if (summary.upload_date) {
          // 如果title没有年份，从upload_date获取
          years.add(summary.upload_date.substring(0, 4));
        }
      });
      // 将Set转换为数组并排序（降序）
      return Array.from(years).sort((a, b) => b - a);
    });

    // 筛选后的re:Invent文章
    const filteredReinventSummaries = computed(() => {
      let filtered = categorizedSummaries.value.reinvent;
      
      // 按级别筛选
      if (selectedLevel.value) {
        filtered = filtered.filter(summary => {
          if (!summary.level) return false;
          // 提取level中的数字部分
          const levelMatch = summary.level.match(/\d+/);
          const levelNum = levelMatch ? levelMatch[0] : '';
          return selectedLevel.value === 'Keynote' 
            ? summary.level === 'Keynote' 
            : levelNum === selectedLevel.value;
        });
      }
      
      // 按年份筛选
      if (selectedYear.value) {
        filtered = filtered.filter(summary => {
          const yearMatch = summary.title_en && summary.title_en.match(/\b(20\d{2})\b/);
          if (yearMatch) {
            return yearMatch[1] === selectedYear.value;
          } else if (summary.upload_date) {
            return summary.upload_date.substring(0, 4) === selectedYear.value;
          }
          return false;
        });
      }
      
      return filtered;
    });

    const showHeroSection = computed(() => {
      if (currentView.value === 'read') {
        return false;
      }
      // 为未登录用户显示
      if (!isAuthenticated.value) {
        return true;
      }
      // 为已登录用户在创建和库视图中显示
      if (isAuthenticated.value && (currentView.value === 'create' || currentView.value === 'library')) {
        return true;
      }
      return false;
    });

    // --- 数据转换与格式化 ---
    const formatWordCount = (wordCount) => {
      if (!wordCount) return '0 字';
      if (wordCount < 1000) {
        return `${wordCount} 字`;
      }
      return `${(wordCount / 1000).toFixed(1)}k 字`;
    };

    const calculateReadTime = (wordCount) => {
      if (!wordCount) return '小于 1 分钟';
      
      const wordsPerMinute = 500; // 设定中文阅读速度为 500 字/分钟
      const minutes = Math.ceil(wordCount / wordsPerMinute);
      
      if (minutes < 1) return '小于 1 分钟';
      return `约 ${minutes} 分钟`;
    };

    // --- 新增: 任务恢复逻辑 ---
    const restoreTask = async () => {
        const taskId = localStorage.getItem('active_task_id');
        const taskUrl = localStorage.getItem('active_task_url');
        if (taskId && taskUrl) {
            try {
                showToast('检测到未完成的分析任务，正在尝试恢复...', 'warning');
                url.value = taskUrl;
                logs.value = ['正在恢复任务...'];
                loading.value = true;
                
                // 通知后端我们要重连
                await axios.post('/summarize', { url: taskUrl, task_id: taskId });
                
                // 连接 WebSocket
                connectWebSocket(taskId);
            } catch(e) {
                console.error('任务恢复失败:', e);
                showToast('任务恢复失败', 'danger');
                clearActiveTask();
                loading.value = false;
            }
        }
    };

    const handleArticleClick = (event) => {
      // We only care about clicks on <a> tags
      if (event.target.tagName.toLowerCase() !== 'a') {
        return;
      }

      const link = event.target;
      const href = link.getAttribute('href');

      // We only care about internal anchor links (e.g., href="#some-id")
      if (!href || !href.startsWith('#')) {
        return;
      }

      event.preventDefault(); // Stop the browser's default jump
      const id = decodeURIComponent(href.substring(1)); // Decode the ID from URL-encoding
      
      const el = document.getElementById(id);
      if (!el) {
        return;
      }
      
      const articleContainer = document.querySelector('.mobile-reading .flex-1.overflow-y-auto');
      if (articleContainer) {
        const containerRect = articleContainer.getBoundingClientRect();
        const elementRect = el.getBoundingClientRect();
        const relativeTop = elementRect.top - containerRect.top;
        const newScrollTop = articleContainer.scrollTop + relativeTop - 20;

        articleContainer.scrollTo({
          top: newScrollTop,
          behavior: 'smooth'
        });
      } else {
        // Fallback if the container is not found for some reason
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    // 视频播放器相关方法
    const openVideoPlayer = () => {
      if (!readingVideoUrl.value) {
        showToast('视频链接不可用', 'warning');
        return;
      }
      
      const videoId = extractYoutubeVideoId(readingVideoUrl.value);
      if (!videoId) {
        showToast('无法解析视频ID', 'danger');
        return;
      }
      
      currentVideoId.value = videoId;
      currentVideoTitle.value = documentTitle.value || '视频播放器';
      showVideoPlayer.value = true;
      videoPlayerMinimized.value = false;
      
      // 计算初始位置 - 出现在TOC区域下方
      if (window.innerWidth <= 768) {
        // 移动端：使用默认的屏幕尺寸
        videoPlayerSize.value = { width: window.innerWidth * 0.9, height: window.innerHeight * 0.5 };
        // 设置在屏幕底部居中
        const leftPos = (window.innerWidth - videoPlayerSize.value.width) / 2;
        videoPlayerPosition.value = { 
          x: leftPos, 
          y: window.innerHeight - videoPlayerSize.value.height - 20 
        };
      } else {
        // 桌面端：定位在TOC区域下方
        videoPlayerSize.value = { width: 480, height: 320 };
        
        // 获取TOC的宽度和位置
        const tocSidebar = document.querySelector('.toc-sidebar');
        let leftPos = 20; // 默认左边距
        
        if (showToc.value && tocSidebar) {
          // 如果TOC可见，放在TOC下方
          const tocRect = tocSidebar.getBoundingClientRect();
          leftPos = tocRect.left + 20; // TOC左边距 + 一些padding
          
          // 确保不超出TOC宽度
          if (leftPos + videoPlayerSize.value.width > tocRect.right) {
            // 如果视频宽度超出TOC，调整宽度
            videoPlayerSize.value.width = Math.max(320, tocRect.width - 40);
            videoPlayerSize.value = { width: videoPlayerSize.value.width, height: videoPlayerSize.value.width / (16/9) };
          }
        }
        
        // 设置在顶部，留出一些空间给页面header
        videoPlayerPosition.value = { 
          x: leftPos, 
          y: 100 // 距离顶部100px，避免遮挡header
        };
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

    // 拖拽功能
    let isDraggingVideo = false;
    let dragOffset = { x: 0, y: 0 };
    let playerElement = null; // 缓存播放器元素

    // 调整大小功能
    let isResizingVideo = false;
    let resizeStartPos = { x: 0, y: 0 };
    let resizeStartSize = { width: 0, height: 0 };

    const startVideoResize = (e) => {
      e.preventDefault();
      e.stopPropagation();

      isResizingVideo = true;
      isVideoResizing.value = true;
      
      playerElement = e.target.closest('.floating-video-player');
      if (!playerElement) return;

      const rect = playerElement.getBoundingClientRect();
      resizeStartPos = { x: e.clientX, y: e.clientY };
      resizeStartSize = { width: rect.width, height: rect.height };

      document.addEventListener('mousemove', doVideoResize, true);
      document.addEventListener('mouseup', stopVideoResize, true);

      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'nwse-resize';
      const iframe = playerElement.querySelector('iframe');
      if (iframe) iframe.style.pointerEvents = 'none';
    };

    const doVideoResize = (e) => {
      if (!isResizingVideo || !playerElement) return;
      e.preventDefault();
      e.stopPropagation();

      const deltaX = e.clientX - resizeStartPos.x;
      const deltaY = e.clientY - resizeStartPos.y;
      
      let newWidth, newHeight;
      const aspectRatio = 16/9;

      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        newWidth = resizeStartSize.width + deltaX;
        newWidth = Math.max(320, newWidth);
        newHeight = newWidth / aspectRatio;
      } else {
        newHeight = resizeStartSize.height + deltaY;
        newHeight = Math.max(180, newHeight);
        newWidth = newHeight * aspectRatio;
      }

      const currentPos = videoPlayerPosition.value;
      const maxWidth = window.innerWidth - currentPos.x - 20;
      if (newWidth > maxWidth) {
        newWidth = maxWidth;
        newHeight = newWidth / aspectRatio;
      }
      
      const maxHeight = window.innerHeight - currentPos.y - 20;
      if (newHeight > maxHeight) {
        newHeight = maxHeight;
        newWidth = newHeight / aspectRatio;
      }
      
      playerElement.style.width = `${Math.round(newWidth)}px`;
      playerElement.style.height = `${Math.round(newHeight)}px`;
    };

    const stopVideoResize = (e) => {
      if (!isResizingVideo) return;
      isResizingVideo = false;
      isVideoResizing.value = false;

      if (playerElement) {
        const rect = playerElement.getBoundingClientRect();
        videoPlayerSize.value = {
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
        const iframe = playerElement.querySelector('iframe');
        if (iframe) iframe.style.pointerEvents = '';
      }
      
      document.removeEventListener('mousemove', doVideoResize, true);
      document.removeEventListener('mouseup', stopVideoResize, true);

      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      playerElement = null;
    };

    const startVideoDrag = (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      // 移除最小化时不能拖动的限制
      // if (videoPlayerMinimized.value) return;

      playerElement = e.target.closest('.floating-video-player');
      if (!playerElement) return;

      isDraggingVideo = true;
      isVideoDragging.value = true;
      
      const rect = playerElement.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      
      dragOffset.x = clientX - rect.left;
      dragOffset.y = clientY - rect.top;

      if (e.touches) {
        document.addEventListener('touchmove', doVideoDrag, { passive: false });
        document.addEventListener('touchend', stopVideoDrag, { passive: false });
      } else {
        document.addEventListener('mousemove', doVideoDrag, true);
        document.addEventListener('mouseup', stopVideoDrag, true);
      }
      
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'move';
    };

    const doVideoDrag = (e) => {
      if (!isDraggingVideo || !playerElement) return;
      e.preventDefault();
      
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      
      let newX = clientX - dragOffset.x;
      let newY = clientY - dragOffset.y;
      
      const rect = playerElement.getBoundingClientRect();
      const maxX = window.innerWidth - rect.width;
      const maxY = window.innerHeight - rect.height;
      
      newX = Math.max(0, Math.min(newX, maxX));
      newY = Math.max(0, Math.min(newY, maxY));
      
      // 直接操作 left/top 样式，不再使用 transform
      playerElement.style.left = `${newX}px`;
      playerElement.style.top = `${newY}px`;
    };

    const stopVideoDrag = (e) => {
      if (!isDraggingVideo) return;
      
      isDraggingVideo = false;
      isVideoDragging.value = false;
      
      if (playerElement) {
        // 从DOM获取最终位置并同步回Vue
        const rect = playerElement.getBoundingClientRect();
        videoPlayerPosition.value = { x: rect.left, y: rect.top };
        // 清理行内样式，让Vue的绑定接管
        playerElement.style.left = '';
        playerElement.style.top = '';
      }
      
      document.removeEventListener('mousemove', doVideoDrag, true);
      document.removeEventListener('mouseup', stopVideoDrag, true);
      document.removeEventListener('touchmove', doVideoDrag);
      document.removeEventListener('touchend', stopVideoDrag);
      
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      playerElement = null;
    };

    // --- 生命周期钩子 ---
    onMounted(() => {
      checkAuth();
      handleRouting(); // 处理初始URL路由
      restoreTask(); // 检查是否有任务需要恢复
      
      // 初始加载数据
      if (currentView.value === 'library' || !isAuthenticated.value) {
        loadSummaries();
      }

      // 移动端优化
      if (window.innerWidth < 768) {
        showToc.value = false;
      }
      
      // 添加点击外部关闭下拉菜单的监听器
      document.addEventListener('click', handleClickOutside);
    });

    // 组件卸载时移除监听器
    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside);
    });

    watch(currentView, (newView, oldView) => {
      // 当切换到笔记库视图时加载数据
      if (newView === 'library') {
        // 使用 nextTick 确保所有状态更新完成后再加载
        nextTick(() => {
          loadSummaries();
        });
      }
    });
    
    watch(isAuthenticated, (isAuth, wasAuth) => {
       // 这个 watch 会在 isAuthenticated 状态变化时触发
       // 只有在认证状态真正发生变化时才重新加载
       if (isAuth !== wasAuth && wasAuth !== undefined) {
         // 如果当前在笔记库视图，立即加载
         if (currentView.value === 'library') {
           nextTick(() => {
             loadSummaries();
           });
         }
       }
    });

    return {
      url,
      summary,
      title,
      rendered,
      logs,
      loading,
      progressPercent,
      startSummarize,
      isValidYoutubeUrl,
      summaries,
      libraryLoading,
      loadSummaries,
      loadSummary,
      loadSummaryByHash,
      categorizedSummaries,
      formatWordCount,
      calculateReadTime,
      readingContent,
      documentTitle,
      readingError,
      viewSummary,
      currentView,
      goBackToLibrary,
      showToc,
      toggleToc,
      tocHtml,
      handleTocClick,
      tocWidth,
      initDrag,
      isAuthenticated,
      showLogin,
      login,
      logout,
      toast,
      showToast,
      loginUsername,
      loginPassword,
      goHome,
      requireAuth,
      showHeroSection,
      handleArticleClick,
      readingVideoUrl,
      isShareView,
      pdfDownloading,
      downloadPDF,
      availableYears,
      filteredReinventSummaries,
      selectedLevel,
      selectedYear,
      showLevelDropdown,
      showYearDropdown,
      toggleLevelDropdown,
      toggleYearDropdown,
      handleClickOutside,
      selectLevel,
      selectYear,
      showVideoPlayer,
      videoPlayerMinimized,
      videoPlayerPosition,
      videoPlayerSize,
      currentVideoId,
      currentVideoTitle,
      openVideoPlayer,
      closeVideoPlayer,
      toggleVideoPlayerMinimize,
      startVideoDrag,
      doVideoDrag,
      stopVideoDrag,
      startVideoResize,
      doVideoResize,
      stopVideoResize,
      isVideoResizing,
      isVideoDragging,
      documentVersions,
      currentVersion,
      showVersionDropdown,
      hasMultipleVersions,
      toggleVersionDropdown,
      switchVersion
    };
  }
}).mount('#app'); 