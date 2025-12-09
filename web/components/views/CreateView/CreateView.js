/**
 * CreateView组件
 * YouTube链接输入和分析界面，支持URL输入、文件上传、进度显示和结果展示
 */
export default {
  dependencies: [
    ['tech-button', '/components/shared/TechButton', 'TechButton'],
    ['connection-status', '/components/common/ConnectionStatus', 'ConnectionStatus']
  ],
  
  props: {
    // YouTube URL
    url: {
      type: String,
      default: ''
    },
    
    // 加载状态
    loading: {
      type: Boolean,
      default: false
    },
    
    // 日志数组
    logs: {
      type: Array,
      default: () => []
    },
    
    // 最终确定的日志
    finalizedLogs: {
      type: Array,
      default: () => []
    },
    
    // 文章标题
    title: {
      type: String,
      default: ''
    },
    
    // 创建的文档 hash
    createdDocHash: {
      type: String,
      default: ''
    },
    
    // 连接状态
    connectionState: {
      type: String,
      default: 'disconnected'
    },
    
    // 重连次数
    reconnectAttempt: {
      type: Number,
      default: 0
    },
    
    // 当前错误信息
    currentError: {
      type: Object,
      default: null
    },
    
    // 是否展开错误详情
    showErrorDetails: {
      type: Boolean,
      default: false
    }
  },
  
  emits: [
    'update:url',
    'start-analysis', 
    'view-summary',
    'file-selected',
    'mode-changed',
    'manual-reconnect'
  ],
  
  setup(props, { emit }) {
    const { computed, ref, watch } = Vue;
    
    // 错误处理辅助函数（从全局获取）
    const getErrorIcon = window.getErrorIcon || ((type) => '⚠️');
    const getErrorColor = window.getErrorColor || ((type) => '#6b7280');
    const getErrorTitle = window.getErrorTitle || ((type) => '错误');
    
    // 文件上传相关
    const selectedFileName = ref('');
    const selectedFile = ref(null);
    const isDragging = ref(false);
    const fileInput = ref(null);
    
    // 输入模式管理
    const inputMode = ref('url'); // 'url' 或 'file'
    
    // 重复检测相关状态
    const showDuplicateWarning = ref(false);
    const existingVideo = ref(null);
    const isCheckingDuplicate = ref(false);
    
    // URL双向绑定
    const url = computed({
      get: () => props.url,
      set: (value) => emit('update:url', value)
    });
    
    // 验证URL类型
    const isValidUrl = computed(() => {
      if (!props.url) return false;
      
      // 支持YouTube、普通网页和PDF链接
      const validPatterns = [
        /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/)|youtu\.be\/)/,
        /^https?:\/\/.+/  // 任何HTTPS链接
      ];
      
      return validPatterns.some(pattern => pattern.test(props.url));
    });
    
    // 能否开始分析
    const canStartAnalysis = computed(() => {
      if (props.loading) return false;
      if (inputMode.value === 'url') {
        return props.url && props.url.trim().length > 0;
      } else {
        return selectedFile.value !== null;
      }
    });
    
    // 分析按钮文本
    const getAnalysisButtonText = computed(() => {
      if (inputMode.value === 'url') {
        return '分析链接内容';
      } else {
        return '分析文档文件';
      }
    });
    
    // 获取文件类型标签
    const getFileTypeLabel = computed(() => {
      if (!selectedFile.value) return '';
      const ext = selectedFileName.value.split('.').pop().toUpperCase();
      const typeMap = {
        'TXT': '文本文档',
        'MD': 'Markdown 文档',
        'PDF': 'PDF 文档',
        'DOCX': 'Word 文档'
      };
      return typeMap[ext] || ext + ' 文件';
    });
    
    // 获取文件图标类名
    const getFileIconClass = computed(() => {
      if (!selectedFile.value) return '';
      const ext = selectedFileName.value.split('.').pop().toLowerCase();
      return `create-view__file-icon--${ext}`;
    });
    
    // 切换输入模式
    const switchInputMode = (mode) => {
      inputMode.value = mode;
      // 切换模式时清空另一种模式的数据
      if (mode === 'url') {
        clearFile();
      } else {
        clearUrl();
      }
    };
    
    // 清空URL
    const clearUrl = () => {
      url.value = '';
    };
    
    // 清空文件
    const clearFile = () => {
      selectedFile.value = null;
      selectedFileName.value = '';
      if (fileInput.value) {
        fileInput.value.value = '';
      }
    };
    
    // 触发文件选择
    const triggerFileInput = () => {
      if (fileInput.value) {
        fileInput.value.click();
      }
    };
    
    // 提取YouTube video_id
    const extractVideoId = (url) => {
      if (!url) return null;
      
      // 匹配各种 YouTube URL 格式
      const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/,
        /youtube\.com\/v\/([a-zA-Z0-9_-]{11})/
      ];
      
      for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
          return match[1];
        }
      }
      
      return null;
    };
    
    // 检查视频是否已存在
    const checkVideoExists = async (url) => {
      try {
        const videoId = extractVideoId(url);
        if (!videoId) {
          showDuplicateWarning.value = false;
          return { exists: false };
        }
        
        isCheckingDuplicate.value = true;
        
        // 调用检查API
        const response = await fetch(`/api/public/summary/${videoId}`);
        const data = await response.json();
        
        if (data.exists) {
          // 视频已存在
          existingVideo.value = {
            hash: data.hash,
            title: data.title
          };
          
          showDuplicateWarning.value = true;
          return data;
        } else {
          showDuplicateWarning.value = false;
          existingVideo.value = null;
        }
        
        return { exists: false };
      } catch (error) {
        console.error('检查视频失败:', error);
        showDuplicateWarning.value = false;
        return { exists: false };
      } finally {
        isCheckingDuplicate.value = false;
      }
    };
    
    // 防抖函数
    let debounceTimer = null;
    const debouncedCheckVideo = (url) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        checkVideoExists(url);
      }, 500);
    };
    
    // 监听URL变化
    watch(() => props.url, (newUrl) => {
      if (newUrl && isValidUrl.value && inputMode.value === 'url') {
        debouncedCheckVideo(newUrl);
      } else {
        showDuplicateWarning.value = false;
      }
    });
    
    // 查看已有版本
    const viewExistingAnalysis = () => {
      if (existingVideo.value && existingVideo.value.hash) {
        emit('view-summary', {
          hash: existingVideo.value.hash
        });
      }
    };
    
    // 强制重新解读
    const forceReanalyze = () => {
      showDuplicateWarning.value = false;
      // 发起分析，带上force标记
      const analysisData = {
        url: props.url,
        force: true
      };
      emit('start-analysis', analysisData);
    };
    const handleStartAnalysis = () => {
      if (!canStartAnalysis.value) return;
      
      const analysisData = {
        url: inputMode.value === 'url' ? props.url : '',
        file: inputMode.value === 'file' ? selectedFile.value : null
      };
      emit('start-analysis', analysisData);
    };
    
    // 处理文件上传
    const handleFileUpload = (event) => {
      const file = event.target.files[0];
      if (!file) return;
      
      // 支持的文件类型
      const supportedTypes = {
        'text/plain': { ext: '.txt', maxSize: 10 * 1024 * 1024, name: 'TXT' },
        'text/markdown': { ext: '.md', maxSize: 10 * 1024 * 1024, name: 'Markdown' },
        'application/pdf': { ext: '.pdf', maxSize: 50 * 1024 * 1024, name: 'PDF' },
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { ext: '.docx', maxSize: 50 * 1024 * 1024, name: 'Word' }
      };
      
      // 通过文件扩展名判断（更可靠）
      const fileName = file.name.toLowerCase();
      let fileType = null;
      
      if (fileName.endsWith('.txt')) {
        fileType = supportedTypes['text/plain'];
      } else if (fileName.endsWith('.md')) {
        fileType = supportedTypes['text/markdown'];
      } else if (fileName.endsWith('.pdf')) {
        fileType = supportedTypes['application/pdf'];
      } else if (fileName.endsWith('.docx')) {
        fileType = supportedTypes['application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      }
      
      if (fileType) {
        // 检查文件大小
        if (file.size > fileType.maxSize) {
          const maxSizeMB = fileType.maxSize / (1024 * 1024);
          alert(`文件太大，${fileType.name} 文件最大支持 ${maxSizeMB}MB。`);
          return;
        }
        
        selectedFile.value = file;
        selectedFileName.value = file.name;
        emit('file-selected', file);
      } else {
        selectedFile.value = null;
        selectedFileName.value = '';
        alert('请选择支持的文件格式：TXT、MD、PDF 或 DOCX。');
      }
    };
    
    // 处理文件拖拽
    const handleFileDrop = (event) => {
      event.preventDefault();
      isDragging.value = false;
      
      const files = event.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        const fileName = file.name.toLowerCase();
        
        // 支持的文件类型
        const supportedTypes = {
          '.txt': { maxSize: 10 * 1024 * 1024, name: 'TXT' },
          '.md': { maxSize: 10 * 1024 * 1024, name: 'Markdown' },
          '.pdf': { maxSize: 50 * 1024 * 1024, name: 'PDF' },
          '.docx': { maxSize: 50 * 1024 * 1024, name: 'Word' }
        };
        
        let fileType = null;
        for (const [ext, config] of Object.entries(supportedTypes)) {
          if (fileName.endsWith(ext)) {
            fileType = config;
            break;
          }
        }
        
        if (fileType) {
          // 检查文件大小
          if (file.size > fileType.maxSize) {
            const maxSizeMB = fileType.maxSize / (1024 * 1024);
            alert(`文件太大，${fileType.name} 文件最大支持 ${maxSizeMB}MB。`);
            return;
          }
          
          selectedFile.value = file;
          selectedFileName.value = file.name;
          emit('file-selected', file);
        } else {
          alert('请选择支持的文件格式：TXT、MD、PDF 或 DOCX。');
        }
      }
    };
    
    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    
    // 处理查看摘要
    const handleViewSummary = () => {
      // 优先使用 hash 进行导航
      if (props.createdDocHash) {
        emit('view-summary', {
          hash: props.createdDocHash
        });
      } else if (props.title) {
        // 如果没有 hash，至少传递标题
        emit('view-summary', {
          title: props.title
        });
      }
    };
    
    return {
      url,
      isValidUrl,
      selectedFileName,
      selectedFile,
      isDragging,
      fileInput,
      inputMode,
      canStartAnalysis,
      getAnalysisButtonText,
      getFileTypeLabel,
      getFileIconClass,
      switchInputMode,
      clearUrl,
      clearFile,
      triggerFileInput,
      handleStartAnalysis,
      handleFileUpload,
      handleFileDrop,
      formatFileSize,
      handleViewSummary,
      // 错误处理方法
      getErrorIcon,
      getErrorColor,
      getErrorTitle,
      // 重复检测相关
      showDuplicateWarning,
      existingVideo,
      isCheckingDuplicate,
      viewExistingAnalysis,
      forceReanalyze
    };
  }
};