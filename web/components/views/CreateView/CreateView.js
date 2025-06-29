/**
 * CreateView组件
 * YouTube链接输入和分析界面，支持URL输入、进度显示和结果展示
 * 使用BEM命名规范，完全独立的组件样式
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
    'view-summary'
  ],
  
  setup(props, { emit }) {
    const { computed } = Vue;
    
    // URL双向绑定
    const url = computed({
      get: () => props.url,
      set: (value) => emit('update:url', value)
    });
    
    // 验证YouTube URL
    const isValidUrl = computed(() => {
      if (!props.url) return false;
      
      const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/)|youtu\.be\/)/;
      return youtubeRegex.test(props.url);
    });
    
    // 处理开始分析
    const handleStartAnalysis = () => {
      if (!props.loading && props.url && isValidUrl.value) {
        emit('start-analysis', props.url);
      }
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
      handleStartAnalysis,
      handleViewSummary
    };
  }
}; 