/**
 * SummaryCard组件
 * 用于展示文章摘要卡片，支持两种类型：re:Invent和其他精选内容
 */

// Import title utilities
import { processCardTitle } from '/utils/titleUtils.js';

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
    },
    
    // 是否在筛选后的区域中（用于智能标题处理）
    inFilteredSection: {
      type: Boolean,
      default: true  // 默认为true，因为通常在分类区域中显示
    },
    
    // 是否为已认证用户（用于显示删除按钮）
    isAuthenticated: {
      type: Boolean,
      default: false
    }
  },
  
  emits: ['click', 'delete'],
  
  setup(props, { emit }) {
    const { computed, ref } = Vue;
    
    // 删除确认状态
    const showDeleteConfirm = ref(false);
    const isDeleting = ref(false);
    
    // 处理后的显示标题（移除冗余前缀）
    const displayTitle = computed(() => {
      try {
        const processed = processCardTitle(
          props.titleEn,
          props.summaryType,
          props.inFilteredSection
        );
        // Fallback: if processed title is empty, use original
        return processed || props.titleEn || 'Untitled';
      } catch (error) {
        console.error('Error processing title:', error);
        return props.titleEn || 'Untitled';
      }
    });
    
    // 格式化字数显示
    const formattedWordCount = computed(() => {
      try {
        const count = props.wordCount;
        // Handle invalid or zero word count
        if (!count || count === 0 || isNaN(count)) return '—';
        
        if (count >= 1000) {
          const k = (count / 1000).toFixed(count >= 10000 ? 0 : 1);
          return `${k}k 字`;
        }
        return `${count} 字`;
      } catch (error) {
        console.error('Error formatting word count:', error);
        return '—';
      }
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
    const handleClick = (event) => {
      // 如果点击的是删除按钮区域，不触发卡片点击
      if (event.target.closest('.summary-card__delete-btn') || 
          event.target.closest('.summary-card__delete-confirm')) {
        return;
      }
      emit('click', {
        hash: props.hash,
        type: props.summaryType
      });
    };
    
    // 显示删除确认
    const showDeleteDialog = (event) => {
      event.stopPropagation();
      showDeleteConfirm.value = true;
    };
    
    // 取消删除
    const cancelDelete = (event) => {
      event.stopPropagation();
      showDeleteConfirm.value = false;
    };
    
    // 确认删除
    const confirmDelete = (event) => {
      event.stopPropagation();
      isDeleting.value = true;
      emit('delete', {
        hash: props.hash,
        titleCn: props.titleCn,
        titleEn: props.titleEn
      });
    };
    
    return {
      displayTitle,
      formattedWordCount,
      levelText,
      contentTypeText,
      contentTypeIcon,
      handleClick,
      showDeleteConfirm,
      isDeleting,
      showDeleteDialog,
      cancelDelete,
      confirmDelete
    };
  }
}; 