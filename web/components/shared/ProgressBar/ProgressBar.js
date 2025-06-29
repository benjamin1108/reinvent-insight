/**
 * ProgressBar组件
 * 用于显示任务进度
 */
export default {
  props: {
    // 进度百分比 (0-100)
    percent: {
      type: Number,
      required: true,
      validator: (value) => value >= 0 && value <= 100
    },
    // 进度条高度
    height: {
      type: String,
      default: '8px'
    },
    // 进度条颜色（支持渐变）
    color: {
      type: String,
      default: 'gradient' // 可选: gradient, primary, success, warning, error
    },
    // 是否显示进度文本
    showText: {
      type: Boolean,
      default: false
    },
    // 文本位置
    textPosition: {
      type: String,
      default: 'inside', // 可选: inside, outside
      validator: (value) => ['inside', 'outside'].includes(value)
    },
    // 是否显示条纹动画
    striped: {
      type: Boolean,
      default: false
    },
    // 是否为动画条纹
    animated: {
      type: Boolean,
      default: false
    },
    // 圆角大小
    rounded: {
      type: String,
      default: 'full' // 可选: none, sm, md, lg, full
    }
  },
  
  setup(props) {
    const { computed } = Vue;
    
    // 计算进度条颜色类或样式
    const progressColorClass = computed(() => {
      const colorMap = {
        'primary': 'progress-bar__fill--cyan',
        'success': 'progress-bar__fill--green',
        'warning': 'progress-bar__fill--yellow',
        'error': 'progress-bar__fill--red'
      };
      return colorMap[props.color] || '';
    });
    
    const progressColorStyle = computed(() => {
      if (props.color === 'gradient') {
        return 'background: linear-gradient(to right, #06b6d4, #3b82f6)';
      }
      // 支持自定义颜色
      if (!progressColorClass.value && props.color) {
        return `background-color: ${props.color}`;
      }
      return '';
    });
    
    // 计算圆角类（应用到wrapper上）
    const roundedClass = computed(() => {
      const roundedMap = {
        'none': 'progress-bar--rounded-none',
        'sm': 'progress-bar--rounded-sm',
        'md': 'progress-bar--rounded-md',
        'lg': 'progress-bar--rounded-lg',
        'full': 'progress-bar--rounded-full'
      };
      return roundedMap[props.rounded] || 'progress-bar--rounded-full';
    });
    
    // 格式化进度文本
    const progressText = computed(() => {
      return `${Math.round(props.percent)}%`;
    });
    
    // 条纹样式类
    const stripedClass = computed(() => {
      if (!props.striped) return '';
      return props.animated ? 'progress-bar__fill--striped progress-bar__fill--animated' : 'progress-bar__fill--striped';
    });
    
    // 文本颜色已内置在CSS中，不需要单独的类
    const textColorClass = computed(() => {
      return '';
    });
    
    // 完成状态（100%时触发动画）
    const isComplete = computed(() => props.percent >= 100);
    
    return {
      progressColorClass,
      progressColorStyle,
      roundedClass,
      progressText,
      stripedClass,
      textColorClass,
      isComplete
    };
  }
}; 