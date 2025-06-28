/**
 * TechButton组件
 * 统一的科技风格按钮组件，支持多种变体、尺寸和状态
 */
export default {
  props: {
    // 按钮变体
    variant: {
      type: String,
      default: 'secondary',
      validator: (value) => ['primary', 'secondary', 'success', 'warning', 'danger'].includes(value)
    },
    
    // 按钮尺寸
    size: {
      type: String,
      default: 'normal',
      validator: (value) => ['sm', 'normal', 'lg'].includes(value)
    },
    
    // 按钮类型
    type: {
      type: String,
      default: 'button',
      validator: (value) => ['button', 'submit', 'reset'].includes(value)
    },
    
    // 按钮文字
    text: {
      type: String,
      default: ''
    },
    
    // 加载状态文字
    loadingText: {
      type: String,
      default: '加载中...'
    },
    
    // 是否禁用
    disabled: {
      type: Boolean,
      default: false
    },
    
    // 是否加载中
    loading: {
      type: Boolean,
      default: false
    },
    
    // 前置图标路径
    iconBefore: {
      type: String,
      default: ''
    },
    
    // 后置图标路径
    iconAfter: {
      type: String,
      default: ''
    },
    
    // 悬停提示
    title: {
      type: String,
      default: ''
    },
    
    // 是否为图标按钮
    iconOnly: {
      type: Boolean,
      default: false
    },
    
    // 是否为全宽按钮
    fullWidth: {
      type: Boolean,
      default: false
    },
    
    // 自定义最小宽度
    minWidth: {
      type: String,
      default: ''
    }
  },
  
  emits: ['click'],
  
  computed: {
    buttonClasses() {
      return [
        'tech-btn',
        `tech-btn-${this.variant}`,
        {
          [`tech-btn-${this.size}`]: this.size !== 'normal',
          'tech-btn-icon': this.iconOnly,
          'w-full': this.fullWidth,
          'opacity-50 cursor-not-allowed': this.disabled || this.loading
        }
      ];
    },
    
    iconClasses() {
      if (this.iconOnly) {
        return this.size === 'sm' ? 'w-4 h-4' : this.size === 'lg' ? 'w-6 h-6' : 'w-5 h-5';
      }
      
      return this.size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';
    },
    
    textClasses() {
      return {
        'ml-1': this.iconBefore || this.loading,
        'mr-1': this.iconAfter
      };
    }
  },
  
  methods: {
    handleClick(event) {
      if (!this.disabled && !this.loading) {
        this.$emit('click', event);
      }
    }
  },
  
  mounted() {
    // 应用自定义最小宽度
    if (this.minWidth && this.$el) {
      this.$el.style.minWidth = this.minWidth;
    }
  }
}; 