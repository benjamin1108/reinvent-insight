/**
 * AppHeader组件
 * 应用顶部导航栏，支持普通页面和阅读页面两种模式
 */
export default {
  dependencies: [
    ['tech-button', '/components/shared/TechButton', 'TechButton'],
    ['simple-audio-button', '/components/shared/SimpleAudioButton', 'SimpleAudioButton'],
    ['mode-toggle', '/components/shared/ModeToggle', 'ModeToggle']
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
    
    // 是否为管理员
    isAdmin: {
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
    },
    
    // Markdown下载状态
    markdownDownloading: {
      type: Boolean,
      default: false
    },
    
    // 当前显示模式 (deep/quick)
    displayMode: {
      type: String,
      default: 'deep'
    },
    
    // 长图生成状态
    longImageGenerating: {
      type: Boolean,
      default: false
    },
    
    // Visual Insight 是否可用
    visualAvailable: {
      type: Boolean,
      default: false
    },
    
    // Visual 状态
    visualStatus: {
      type: String,
      default: 'pending'
    },
    
    // === 音频播放相关props ===
    
    // 文章哈希值（用于TTS）
    articleHash: {
      type: String,
      default: ''
    },
    
    // 文章文本（用于TTS）
    articleText: {
      type: String,
      default: ''
    }
  },
  
  emits: [
    'home-click',        // 点击首页/品牌标识
    'view-change',       // 视图切换
    'login-show',        // 显示登录框
    'logout',           // 退出登录
    'test-toast',       // 测试Toast（临时）
    'admin-click',      // 跳转管理页面
    'back-to-library',  // 返回笔记库
    'open-video',       // 打开视频播放器
    'download-pdf',     // 下载PDF
    'download-markdown', // 下载Markdown
    'toggle-toc',        // 切换目录
    'download-long-image', // 下载长图
    'mode-change'         // 模式切换
  ],
  
  setup(props, { emit }) {
    const { watch, ref, onMounted } = Vue;
    
    // 配置状态
    const audioButtonEnabled = ref(true); // 默认显示
    
    // 加载配置
    onMounted(async () => {
      try {
        const response = await fetch('/api/config');
        if (response.ok) {
          const config = await response.json();
          audioButtonEnabled.value = config.tts_audio_button_enabled;
        }
      } catch (error) {
        console.error('加载配置失败:', error);
        // 加载失败时默认显示
        audioButtonEnabled.value = true;
      }
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
    
    const handleDownloadMarkdown = () => {
      emit('download-markdown');
    };
    
    const handleToggleToc = () => {
      emit('toggle-toc');
    };
    
    const handleDownloadLongImage = () => {
      emit('download-long-image');
    };
    
    const handleModeChange = (mode) => {
      emit('mode-change', mode);
    };
    
    const handleAdminClick = () => {
      emit('admin-click');
    };
    
    return {
      // 配置状态
      audioButtonEnabled,
      // 事件处理方法
      handleHomeClick,
      handleViewChange,
      handleLoginShow,
      handleLogout,
      handleTestToast,
      handleAdminClick,
      handleBackToLibrary,
      handleOpenVideo,
      handleDownloadPDF,
      handleDownloadMarkdown,
      handleToggleToc,
      handleDownloadLongImage,
      handleModeChange
    };
  }
}; 