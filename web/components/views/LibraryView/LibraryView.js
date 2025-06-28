/**
 * LibraryView组件
 * 笔记库展示界面，集成SummaryCard和Filter组件
 */
export default {
  dependencies: [
    ['summary-card', '/components/common/SummaryCard', 'SummaryCard'],
    ['level-filter', '/components/common/Filter/LevelFilter', 'LevelFilter'],
    ['year-filter', '/components/common/Filter/YearFilter', 'YearFilter']
  ],
  
  props: {
    // 摘要数据列表
    summaries: {
      type: Array,
      default: () => []
    },
    
    // 加载状态
    loading: {
      type: Boolean,
      default: false
    },
    
    // 加载文本
    loadingText: {
      type: String,
      default: '加载笔记中...'
    },
    
    // 空状态标题
    emptyTitle: {
      type: String,
      default: '笔记库为空'
    },
    
    // 空状态消息
    emptyMessage: {
      type: String,
      default: '创建您的第一篇深度解读笔记吧！'
    },
    
    // 是否为访客模式
    isGuest: {
      type: Boolean,
      default: false
    }
  },
  
  emits: [
    'summary-click',
    'level-change',
    'year-change'
  ],
  
  setup(props, { emit }) {
    const { ref, computed } = Vue;
    
    // 筛选状态
    const selectedLevel = ref('');
    const selectedYear = ref('');
    
    // 数据分类
    const reinventSummaries = computed(() => {
      return props.summaries.filter(summary => {
        return isReinventSummary(summary);
      });
    });
    
    const otherSummaries = computed(() => {
      return props.summaries.filter(summary => {
        return !isReinventSummary(summary);
      });
    });
    
    // 判断是否为re:Invent摘要
    const isReinventSummary = (summary) => {
      const titleEn = summary.title_en || '';
      return titleEn.toLowerCase().includes('reinvent') || 
             titleEn.toLowerCase().includes('re:invent');
    };
    
    // 提取年份信息
    const extractYear = (summary) => {
      // 从英文标题中提取年份
      const titleMatch = summary.title_en && summary.title_en.match(/\b(20\d{2})\b/);
      if (titleMatch) {
        return titleMatch[1];
      }
      
      // 从上传日期中提取年份
      if (summary.upload_date) {
        return summary.upload_date.substring(0, 4);
      }
      
      return '';
    };
    
    // 获取可用年份列表
    const availableYears = computed(() => {
      const years = new Set();
      reinventSummaries.value.forEach(summary => {
        const year = extractYear(summary);
        if (year) {
          years.add(year);
        }
      });
      return Array.from(years).sort((a, b) => b - a); // 降序排列
    });
    
    // 筛选后的re:Invent摘要
    const filteredReinventSummaries = computed(() => {
      let filtered = reinventSummaries.value;
      
      // 级别筛选
      if (selectedLevel.value) {
        filtered = filtered.filter(summary => {
          if (!summary.level) return selectedLevel.value === 'Keynote';
          
          if (selectedLevel.value === 'Keynote') {
            return summary.level.toLowerCase().includes('keynote');
          }
          
          const levelMatch = summary.level.match(/\d+/);
          return levelMatch && levelMatch[0] === selectedLevel.value;
        });
      }
      
      // 年份筛选
      if (selectedYear.value) {
        filtered = filtered.filter(summary => {
          const year = extractYear(summary);
          return year === selectedYear.value;
        });
      }
      
      return filtered;
    });
    
    // 筛选后的re:Invent数量
    const filteredReinventCount = computed(() => {
      return filteredReinventSummaries.value.length;
    });
    
    // 格式化字数
    const formatWordCount = (count) => {
      if (!count) return '0';
      if (count >= 10000) {
        return `${(count / 10000).toFixed(1)}万`;
      }
      return count.toString();
    };
    
    // 事件处理
    const handleSummaryClick = (data) => {
      emit('summary-click', data);
    };
    
    const handleLevelChange = (level) => {
      selectedLevel.value = level;
      emit('level-change', level);
    };
    
    const handleYearChange = (year) => {
      selectedYear.value = year;
      emit('year-change', year);
    };
    
    // 重置筛选
    const resetFilters = () => {
      selectedLevel.value = '';
      selectedYear.value = '';
    };
    
    return {
      // 筛选状态
      selectedLevel,
      selectedYear,
      
      // 计算属性
      reinventSummaries,
      otherSummaries,
      filteredReinventSummaries,
      filteredReinventCount,
      availableYears,
      
      // 方法
      extractYear,
      formatWordCount,
      handleSummaryClick,
      handleLevelChange,
      handleYearChange,
      resetFilters
    };
  }
}; 