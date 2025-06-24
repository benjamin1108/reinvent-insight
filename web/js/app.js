const { createApp, ref, onMounted, computed, nextTick, watch } = Vue;

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
    const currentStep = ref(0);
    const totalSteps = 7; // 根据后端逻辑调整

    // 笔记库状态
    const summaries = ref([]);
    const libraryLoading = ref(false);

    // 阅读视图状态
    const readingContent = ref('');
    const documentTitle = ref('');
    const readingError = ref('');
    const showToc = ref(true);
    const tocHtml = ref('');
    const tocWidth = ref(416); // 26rem = 416px
    const readingFilename = ref(''); // 新增：当前阅读的文件名

    // 视图控制
    const currentView = ref('library'); // 默认视图 'create', 'library', 'read'
    const isShareView = ref(false); // 新增：是否为分享视图
    
    // 认证状态
    const isAuthenticated = ref(false);
    const showLogin = ref(false);
    const loginUsername = ref('');
    const loginPassword = ref('');

    // 分享状态
    const shareLoading = ref(false);
    
    // Toast 状态
    const toast = ref({
        show: false,
        message: '',
        type: 'success' // 'success', 'danger', 'warning'
    });

    // --- 路由处理 ---
    const handleRouting = () => {
      const path = window.location.pathname;
      const params = new URLSearchParams(window.location.search);
      const shareHash = params.get('share');

      if (shareHash) {
        isShareView.value = true;
        loadSharedSummary(shareHash);
      } else {
        isShareView.value = false;
        const docMatch = path.match(/\/documents\/(.+)/);

        if (docMatch) {
          const filename = decodeURIComponent(docMatch[1]);
          loadSummary(filename, false); // false: 不要推入历史记录，因为我们已经在这个URL上
        } else {
          // 如果不是文档URL，则显示笔记库
          currentView.value = 'library';
          if (isAuthenticated.value && summaries.value.length === 0) {
            loadSummaries();
          }
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
        // 登录后，如果当前在笔记库视图，则加载笔记
        // 登录后总是切换到笔记库视图并加载
        currentView.value = 'library';
        loadSummaries();
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
      toast.value = { show: true, message, type };
      setTimeout(() => {
        toast.value.show = false;
      }, duration);
    };
    
    const goHome = () => {
      if (isShareView.value) {
        window.location.href = '/';
        return;
      }
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

    // 处理目录点击
    const handleTocClick = (event) => {
      const target = event.target;
      if (target.tagName.toLowerCase() === 'a' && target.dataset.target) {
        event.preventDefault();
        const id = target.dataset.target;
        const el = document.getElementById(id);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
      const h3Headings = [...doc.body.querySelectorAll('h3')];
      
      if (h3Headings.length > 0) {
        // 在列表前手动添加目录标题
        let tocHtmlContent = '<h3>主要目录</h3><ul>';
        h3Headings.forEach(h => {
            const text = h.textContent.replace(/\s*\(#.+\)$/g, '').trim();
            const id = h.id; // 使用我们刚刚分配的ID
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
        currentStep.value = 0;

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
          } else {
            logs.value.push(data.message);
            currentStep.value += 1;
            progressPercent.value = Math.min(99, (currentStep.value / totalSteps) * 100);
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
      libraryLoading.value = true;
      try {
        const endpoint = isAuthenticated.value ? '/summaries' : '/api/public/summaries';
        const res = await axios.get(endpoint);
        summaries.value = res.data.summaries;
      } catch (err) {
        console.error('加载摘要列表失败:', err);
        if (isAuthenticated.value) {
          if (err.response && err.response.status === 401) {
            showToast('请先登录以浏览笔记库', 'warning');
            showLogin.value = true;
          } else {
            showToast('加载笔记列表失败', 'danger');
          }
        }
      } finally {
        libraryLoading.value = false;
      }
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
        
        if (pushState) {
          // 在非分享视图中，更新URL
          if (!isShareView.value) {
            history.pushState({ filename }, '', `/documents/${encodedFilename}`);
          }
        }
        viewSummary(res.data.title, res.data.content, filename);
      } catch (err) {
        console.error('加载摘要失败:', err);
        const errorMessage = err.response?.data?.detail || '加载文章失败';
        readingError.value = errorMessage;
        showToast(errorMessage, 'danger');
        currentView.value = 'read'; // 确保停留在阅读视图显示错误
      }
    };
    
    const viewSummary = (title, content, filename) => {
      documentTitle.value = title;
      readingFilename.value = filename; // 跟踪当前文件名
      
      const { html, tocHtml: tocString } = renderMarkdownWithToc(content);
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
    
    const loadSharedSummary = async (shareHash) => {
      try {
        readingError.value = '';
        const res = await axios.get(`/api/share/${shareHash}`);
        viewSummary(res.data.title, res.data.content, res.data.filename);
      } catch (err) {
        console.error('加载分享内容失败:', err);
        readingError.value = err.response?.data?.detail || '加载分享内容失败';
        currentView.value = 'read'; // 确保在阅读视图中显示错误
      }
    };

    const shareDocument = async () => {
      requireAuth(async () => {
        if (!readingFilename.value) return;
        shareLoading.value = true;
        
        let shareUrl = '';
        try {
          // Step 1: Get the share link from the backend
          const res = await axios.post('/api/share', { filename: readingFilename.value });
          const shareHash = res.data.share_hash;
          shareUrl = `${window.location.origin}/?share=${shareHash}`;

          // Step 2: Try to copy to clipboard
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(shareUrl);
            showToast('分享链接已复制到剪贴板！', 'success');
          } else {
            // Fallback for insecure contexts (HTTP) or older browsers
            showToast('已生成链接，请手动复制', 'success');
            prompt("请手动复制链接:", shareUrl);
          }
        } catch (err) {
          console.error('创建或复制分享链接失败: ', err);
          
          // If the error happened during copy, shareUrl will be available.
          // If it happened during API call, it won't.
          if (shareUrl) {
              showToast('自动复制失败，请手动复制', 'warning');
              prompt("请手动复制链接:", shareUrl);
          } else {
              showToast(err.response?.data?.detail || '创建分享链接失败', 'danger');
          }
        } finally {
          shareLoading.value = false;
        }
      });
    };


    // --- 计算属性和工具函数 ---
    const categorizedSummaries = computed(() => {
      const reinvent = [];
      const other = [];
      summaries.value.forEach(s => {
        if (s.title_en.toLowerCase().includes('reinvent') || s.title_cn.toLowerCase().includes('reinvent')) {
          reinvent.push(s);
        } else {
          other.push(s);
        }
      });
      return { reinvent, other };
    });

    const showHeroSection = computed(() => {
      if (isShareView.value || currentView.value === 'read') {
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

    // --- 生命周期钩子 ---
    onMounted(() => {
      checkAuth();
      handleRouting(); // 处理初始URL路由
      restoreTask(); // 检查是否有任务需要恢复
      loadSummaries(); // **重要：始终加载摘要**

      // 移动端优化
      if (window.innerWidth < 768) {
        showToc.value = false;
      }
    });

    watch(currentView, (newView, oldView) => {
      // 仅当从非笔记库视图切换到笔记库时才加载
      if (newView === 'library' && isAuthenticated.value) {
        loadSummaries();
      }
    });
    
    watch(isAuthenticated, (isAuth, wasAuth) => {
       // 仅当状态从未认证变为认证时执行
      if (isAuth && !wasAuth) {
        currentView.value = 'library'; // 登录后跳转到库
        loadSummaries();
      }
      // 当从认证变为未认证时（登出）
      if (!isAuth && wasAuth) {
        summaries.value = []; // 清空可能存在的私人数据
        loadSummaries(); // 重新加载公共数据
        currentView.value = 'library'; // 指向公共展示页
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
      shareDocument,
      shareLoading,
      toast,
      showToast,
      loginUsername,
      loginPassword,
      currentStep,
      totalSteps,
      isShareView,
      goHome,
      requireAuth,
      showHeroSection
    };
  }
}).mount('#app'); 