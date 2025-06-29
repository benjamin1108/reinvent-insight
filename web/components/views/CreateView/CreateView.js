/**
 * CreateView组件
 * YouTube链接输入和分析界面，支持URL输入、进度显示和结果展示
 * 使用BEM命名规范，完全独立的组件样式
 */
export default {
  dependencies: [
    ['tech-button', '/components/shared/TechButton', 'TechButton'],
    ['progress-bar', '/components/shared/ProgressBar', 'ProgressBar']
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
    
    // 进度百分比
    progressPercent: {
      type: Number,
      default: 0
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
    
    // 分析结果
    summary: {
      type: String,
      default: ''
    },
    
    // 文章标题
    title: {
      type: String,
      default: ''
    },
    
    // 渲染的HTML内容
    rendered: {
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
    
    // 是否显示进度条
    const showProgressBar = computed(() => {
      return props.loading || props.progressPercent > 0;
    });
    
    // 直接使用后端清理过的内容
    const cleanRendered = computed(() => {
      // 后端已经清理了元数据，直接返回
      return props.rendered || '';
    });
    
    // 处理开始分析
    const handleStartAnalysis = () => {
      if (!props.loading && props.url && isValidUrl.value) {
        emit('start-analysis', props.url);
      }
    };
    
    // 处理查看摘要
    const handleViewSummary = () => {
      emit('view-summary', {
        title: props.title,
        summary: props.summary,
        rendered: cleanRendered.value
      });
    };
    
    return {
      url,
      isValidUrl,
      showProgressBar,
      cleanRendered,
      handleStartAnalysis,
      handleViewSummary
    };
  }
}; 