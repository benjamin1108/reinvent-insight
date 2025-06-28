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
        'primary': 'bg-cyan-500',
        'success': 'bg-green-500',
        'warning': 'bg-yellow-500',
        'error': 'bg-red-500'
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
    
    // 计算圆角类
    const roundedClass = computed(() => {
      const roundedMap = {
        'none': 'rounded-none',
        'sm': 'rounded-sm',
        'md': 'rounded-md',
        'lg': 'rounded-lg',
        'full': 'rounded-full'
      };
      return roundedMap[props.rounded] || 'rounded-full';
    });
    
    // 格式化进度文本
    const progressText = computed(() => {
      return `${Math.round(props.percent)}%`;
    });
    
    // 条纹样式类
    const stripedClass = computed(() => {
      if (!props.striped) return '';
      return props.animated ? 'progress-bar-striped progress-bar-animated' : 'progress-bar-striped';
    });
    
    // 文本颜色（根据背景自动调整）
    const textColorClass = computed(() => {
      // 对于深色背景使用白色文本
      return 'text-white';
    });
    
    return {
      progressColorClass,
      progressColorStyle,
      roundedClass,
      progressText,
      stripedClass,
      textColorClass
    };
  }
}; 