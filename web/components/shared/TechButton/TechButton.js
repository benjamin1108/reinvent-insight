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
    
    // 简单图标（文本/表情）
    icon: {
      type: String,
      default: ''
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
    
    // 前置SVG图标路径
    iconBefore: {
      type: String,
      default: ''
    },
    
    // 后置SVG图标路径
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
        'tech-button',
        `tech-button--${this.variant}`,
        {
          [`tech-button--${this.size}`]: this.size !== 'normal',
          'tech-button--icon': this.iconOnly,
          'tech-button--full-width': this.fullWidth,
          'tech-button--loading': this.loading,
          'tech-button--disabled': this.disabled
        }
      ];
    },
    
    iconClasses() {
      const baseClass = 'tech-button__icon';
      const classes = [baseClass];
      
      // 位置修饰符
      if (this.icon || this.iconBefore) {
        classes.push('tech-button__icon--before');
      } else if (this.iconAfter) {
        classes.push('tech-button__icon--after');
      }
      
      // 尺寸修饰符
      if (this.iconOnly) {
        classes.push(this.size === 'sm' ? 'tech-button__icon--sm' : 
                     this.size === 'lg' ? 'tech-button__icon--xl' : 
                     'tech-button__icon--lg');
      } else {
        classes.push(this.size === 'sm' ? 'tech-button__icon--sm' : 'tech-button__icon');
      }
      
      return classes;
    },
    
    spinnerClasses() {
      const classes = [
        'tech-button__spinner',
        'tech-button__spinner--spinning',
        'tech-button__icon',
        'tech-button__icon--before'
      ];
      
      // 添加尺寸修饰符
      if (this.size === 'sm') {
        classes.push('tech-button__icon--sm');
      } else if (this.size === 'lg' && !this.iconOnly) {
        // 非图标按钮的大尺寸使用标准图标尺寸
      }
      
      return classes;
    },
    
    textClasses() {
      return 'tech-button__text';
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