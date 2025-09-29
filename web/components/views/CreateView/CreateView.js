/**
 * CreateView组件
 * YouTube链接输入和分析界面，支持URL输入、文件上传、进度显示和结果展示
 */
export default {
  dependencies: [
    ['tech-button', '/components/shared/TechButton', 'TechButton']
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
    }
  },
  
  emits: [
    'update:url',
    'start-analysis', 
    'view-summary',
    'file-selected',
    'mode-changed'
  ],
  
  setup(props, { emit }) {
    const { computed, ref } = Vue;
    
    // 文件上传相关
    const selectedFileName = ref('');
    const selectedFile = ref(null);
    const isDragging = ref(false);
    const fileInput = ref(null);
    
    // 输入模式管理
    const inputMode = ref('url'); // 'url' 或 'file'
    
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
        return '分析PDF文件';
      }
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
    
    // 处理开始分析
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
      if (file && file.type === 'application/pdf') {
        // 检查文件大小（50MB以内）
        if (file.size > 50 * 1024 * 1024) {
          alert('文件太大，请选择小于50MB的PDF文件。');
          return;
        }
        
        selectedFile.value = file;
        selectedFileName.value = file.name;
        emit('file-selected', file);
      } else {
        selectedFile.value = null;
        selectedFileName.value = '';
        if (file) {
          alert('请选择有效的PDF文件。');
        }
      }
    };
    
    // 处理文件拖拽
    const handleFileDrop = (event) => {
      event.preventDefault();
      isDragging.value = false;
      
      const files = event.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        if (file.type === 'application/pdf') {
          // 检查文件大小
          if (file.size > 50 * 1024 * 1024) {
            alert('文件太大，请选择小于50MB的PDF文件。');
            return;
          }
          
          selectedFile.value = file;
          selectedFileName.value = file.name;
          emit('file-selected', file);
        } else {
          alert('请选择有效的PDF文件。');
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
      switchInputMode,
      clearUrl,
      clearFile,
      triggerFileInput,
      handleStartAnalysis,
      handleFileUpload,
      handleFileDrop,
      formatFileSize,
      handleViewSummary
    };
  }
};