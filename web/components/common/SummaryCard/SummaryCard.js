/**
 * SummaryCard组件
 * 用于展示文章摘要卡片，支持两种类型：re:Invent和其他精选内容
 */
export default {
  props: {
    // 类型：'reinvent' 或 'other'
    summaryType: {
      type: String,
      default: 'other',
      validator: (value) => ['reinvent', 'other'].includes(value)
    },
    
    // 文章标题（英文）
    titleEn: {
      type: String,
      required: true
    },
    
    // 文章标题（中文）
    titleCn: {
      type: String,
      required: true
    },
    
    // 字数
    wordCount: {
      type: Number,
      default: 0
    },
    
    // 年份（可选，主要用于re:Invent）
    year: {
      type: [String, Number],
      default: ''
    },
    
    // 级别（可选，如 "Level 200 - 中级"）
    level: {
      type: String,
      default: ''
    },
    
    // 文档哈希值（用于跳转）
    hash: {
      type: String,
      required: true
    }
  },
  
  emits: ['click'],
  
  setup(props, { emit }) {
    const { computed } = Vue;
    
    // 格式化字数显示
    const formattedWordCount = computed(() => {
      const count = props.wordCount;
      if (!count) return '0 字';
      
      if (count >= 1000) {
        const k = (count / 1000).toFixed(count >= 10000 ? 0 : 1);
        return `${k}k 字`;
      }
      return `${count} 字`;
    });
    
    // 处理级别文本（提取级别数字和显示文本）
    const levelText = computed(() => {
      if (!props.level) return '';
      // 从 "Level 200 - 中级" 格式中提取 "Level 200"
      const parts = props.level.split(' - ');
      return parts[0];
    });
    
    // 内容类型文本
    const contentTypeText = computed(() => {
      return props.summaryType === 'reinvent' ? 're:Invent' : '精选内容';
    });
    
    // 内容类型图标
    const contentTypeIcon = computed(() => {
      return props.summaryType === 'reinvent' ? '🎯' : '📚';
    });
    
    // 处理点击事件
    const handleClick = () => {
      emit('click', {
        hash: props.hash,
        type: props.summaryType
      });
    };
    
    return {
      formattedWordCount,
      levelText,
      contentTypeText,
      contentTypeIcon,
      handleClick
    };
  }
}; 