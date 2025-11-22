/**
 * AppHeader组件
 * 应用顶部导航栏，支持普通页面和阅读页面两种模式
 */
export default {
  dependencies: [
    ['tech-button', '/components/shared/TechButton', 'TechButton'],
    ['simple-audio-button', '/components/shared/SimpleAudioButton', 'SimpleAudioButton']
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
    },
    
    // Markdown下载状态
    markdownDownloading: {
      type: Boolean,
      default: false
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
    'back-to-library',  // 返回笔记库
    'open-video',       // 打开视频播放器
    'download-pdf',     // 下载PDF
    'download-markdown', // 下载Markdown
    'toggle-toc'        // 切换目录
  ],
  
  setup(props, { emit }) {
    const { watch } = Vue;
    
    // 调试：监听音频相关props
    watch(() => [props.articleHash, props.articleText], ([hash, text]) => {
      console.log('🎵 [AppHeader] 音频props变化:');
      console.log('  - articleHash:', hash);
      console.log('  - articleTextLength:', text?.length || 0);
      console.log('  - hasHash:', !!hash);
      console.log('  - hasText:', !!text);
      console.log('  - 条件满足:', !!(hash && text));
      console.log('  - 当前时间:', new Date().toISOString());
    }, { immediate: true });
    
    // 单独监听articleText
    watch(() => props.articleText, (newText, oldText) => {
      console.log('📝 [AppHeader] articleText 单独变化:');
      console.log('  - 旧长度:', oldText?.length || 0);
      console.log('  - 新长度:', newText?.length || 0);
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
      console.log('🔵 [DEBUG] handleDownloadMarkdown 被调用');
      emit('download-markdown');
    };
    
    const handleToggleToc = () => {
      console.log('🔘 [HEADER] handleToggleToc 被调用');
      console.log('🔍 [HEADER] 当前 showToc prop:', props.showToc);
      emit('toggle-toc');
      console.log('✅ [HEADER] 已发送 toggle-toc 事件');
    };
    
    return {
      // 事件处理方法
      handleHomeClick,
      handleViewChange,
      handleLoginShow,
      handleLogout,
      handleTestToast,
      handleBackToLibrary,
      handleOpenVideo,
      handleDownloadPDF,
      handleDownloadMarkdown,
      handleToggleToc
    };
  }
}; 