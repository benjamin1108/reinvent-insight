/**
 * AppHeader组件
 * 应用顶部导航栏，支持普通页面和阅读页面两种模式
 */
export default {
  dependencies: [
    ['tech-button', '/components/shared/TechButton', 'TechButton'],
    ['recent-articles-dropdown', '/components/common/RecentArticlesDropdown', 'RecentArticlesDropdown']
  ],
  props: {
    // Header模式：normal（普通页面）或 reading（阅读页面）
    mode: {
      type: String,
      default: 'normal',
      validator: (value) => ['normal', 'reading'].includes(value)
    },
    
    // 是否已认证
    isAuthenticated: {
      type: Boolean,
      default: false
    },
    
    // 是否为分享页面
    isShareView: {
      type: Boolean,
      default: false
    },
    
    // 当前视图
    currentView: {
      type: String,
      default: 'home'
    },
    
    // 是否显示测试Toast按钮（临时）
    showTestToast: {
      type: Boolean,
      default: false
    },
    
    // === 阅读模式特有props ===
    
    // 目录显示状态
    showToc: {
      type: Boolean,
      default: true
    },
    
    // 视频URL
    readingVideoUrl: {
      type: String,
      default: ''
    },
    
    // PDF下载状态
    pdfDownloading: {
      type: Boolean,
      default: false
    }
  },
  
  emits: [
    'home-click',        // 点击首页/品牌标识
    'view-change',       // 视图切换
    'login-show',        // 显示登录框
    'logout',           // 退出登录
    'test-toast',       // 测试Toast（临时）
    'back-to-library',  // 返回笔记库
    'open-video',       // 打开视频播放器
    'download-pdf',     // 下载PDF
    'toggle-toc',       // 切换目录
    'recent-article-click'  // 近期文章点击
  ],
  
  setup(props, { emit }) {
    const { ref, onMounted, onUnmounted } = Vue;
    
    // 近期解读相关状态
    const showRecentDropdown = ref(false);
    const recentArticles = ref([]);
    const recentArticlesLoading = ref(false);
    let hoverTimer = null;
    
    // 数据缓存
    const recentArticlesCache = {
      data: null,
      timestamp: 0,
      ttl: 5 * 60 * 1000 // 5分钟缓存
    };
    
    // 加载最近文章
    const loadRecentArticles = async () => {
      const now = Date.now();
      
      // 检查缓存
      if (recentArticlesCache.data && 
          now - recentArticlesCache.timestamp < recentArticlesCache.ttl) {
        recentArticles.value = recentArticlesCache.data;
        return;
      }
      
      recentArticlesLoading.value = true;
      try {
        const response = await axios.get('/api/public/summaries');
        const allArticles = response.data.summaries || [];
        
        // 过滤有效数据并按修改时间排序，取前10篇
        const validArticles = allArticles.filter(article => 
          article && article.hash && (article.title_cn || article.title_en)
        );
        
        const sortedArticles = validArticles
          .sort((a, b) => b.modified_at - a.modified_at)
          .slice(0, 10);
        
        // 更新缓存
        recentArticlesCache.data = sortedArticles;
        recentArticlesCache.timestamp = now;
        recentArticles.value = sortedArticles;
      } catch (error) {
        console.error('加载最近文章失败:', error);
        recentArticles.value = [];
      } finally {
        recentArticlesLoading.value = false;
      }
    };
    
    // 处理鼠标进入"近期解读"按钮
    const handleRecentButtonEnter = () => {
      clearTimeout(hoverTimer);
      showRecentDropdown.value = true;
      if (recentArticles.value.length === 0 && !recentArticlesLoading.value) {
        loadRecentArticles();
      }
    };
    
    // 处理鼠标离开按钮
    const handleRecentButtonLeave = () => {
      hoverTimer = setTimeout(() => {
        showRecentDropdown.value = false;
      }, 300);
    };
    
    // 处理鼠标进入下拉列表
    const handleRecentDropdownEnter = () => {
      clearTimeout(hoverTimer);
    };
    
    // 处理鼠标离开下拉列表
    const handleRecentDropdownLeave = () => {
      hoverTimer = setTimeout(() => {
        showRecentDropdown.value = false;
      }, 300);
    };
    
    // 移动端点击按钮
    const handleRecentButtonClick = () => {
      showRecentDropdown.value = !showRecentDropdown.value;
      if (showRecentDropdown.value && recentArticles.value.length === 0 && !recentArticlesLoading.value) {
        loadRecentArticles();
      }
    };
    
    // 处理文章点击
    const handleRecentArticleClick = (article) => {
      showRecentDropdown.value = false;
      emit('recent-article-click', article);
    };
    
    // 点击外部区域关闭下拉列表（移动端）
    const handleClickOutside = (event) => {
      const recentWrapper = event.target.closest('.app-header__recent-wrapper');
      if (!recentWrapper && showRecentDropdown.value) {
        showRecentDropdown.value = false;
      }
    };
    
    // 组件挂载时添加事件监听
    onMounted(() => {
      document.addEventListener('click', handleClickOutside);
    });
    
    // 组件卸载时移除事件监听
    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside);
      clearTimeout(hoverTimer);
    });
    
    // 事件处理方法
    const handleHomeClick = () => {
      emit('home-click');
    };
    
    const handleViewChange = (view) => {
      emit('view-change', view);
    };
    
    const handleLoginShow = () => {
      emit('login-show');
    };
    
    const handleLogout = () => {
      emit('logout');
    };
    
    const handleTestToast = () => {
      emit('test-toast');
    };
    
    const handleBackToLibrary = () => {
      emit('back-to-library');
    };
    
    const handleOpenVideo = () => {
      emit('open-video');
    };
    
    const handleDownloadPDF = () => {
      emit('download-pdf');
    };
    
    const handleToggleToc = () => {
      emit('toggle-toc');
    };
    
    return {
      // 近期解读状态
      showRecentDropdown,
      recentArticles,
      recentArticlesLoading,
      
      // 近期解读方法
      handleRecentButtonEnter,
      handleRecentButtonLeave,
      handleRecentDropdownEnter,
      handleRecentDropdownLeave,
      handleRecentButtonClick,
      handleRecentArticleClick,
      
      // 事件处理方法
      handleHomeClick,
      handleViewChange,
      handleLoginShow,
      handleLogout,
      handleTestToast,
      handleBackToLibrary,
      handleOpenVideo,
      handleDownloadPDF,
      handleToggleToc
    };
  }
}; 