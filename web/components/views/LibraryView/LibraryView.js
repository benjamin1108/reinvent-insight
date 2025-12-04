/**
 * LibraryView组件
 * 笔记库展示界面，集成SummaryCard和Filter组件
 */
export default {
  dependencies: [
    ['summary-card', '/components/common/SummaryCard', 'SummaryCard'],
    ['level-filter', '/components/common/Filter', 'LevelFilter'],
    ['year-filter', '/components/common/Filter', 'YearFilter']
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
    },
    
    // 是否已认证（用于显示删除按钮）
    isAuthenticated: {
      type: Boolean,
      default: false
    }
  },
  
  emits: [
    'summary-click',
    'summary-delete',
    'level-change',
    'year-change',
    'sort-change'
  ],
  
  setup(props, { emit }) {
    const { ref, computed } = Vue;
    
    // 筛选状态
    const selectedLevel = ref('');
    const selectedYear = ref('');
    
    // 排序状态
    const sortOrder = ref(localStorage.getItem('librarySortOrder') || 'date-desc'); // 'date-desc' | 'date-asc' | 'title-asc' | 'title-desc'
    
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
      
      // 排序
      filtered = sortSummaries(filtered);
      
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
    
    // 排序函数
    const sortSummaries = (summaries) => {
      const sorted = [...summaries];
      
      switch (sortOrder.value) {
        case 'date-desc':
          // 按修改时间倒序（最新在前）
          return sorted.sort((a, b) => {
            const dateA = new Date(a.modified_at || a.upload_date || 0);
            const dateB = new Date(b.modified_at || b.upload_date || 0);
            return dateB - dateA;
          });
          
        case 'date-asc':
          // 按修改时间升序（最早在前）
          return sorted.sort((a, b) => {
            const dateA = new Date(a.modified_at || a.upload_date || 0);
            const dateB = new Date(b.modified_at || b.upload_date || 0);
            return dateA - dateB;
          });
          
        case 'title-asc':
          // 按标题升序
          return sorted.sort((a, b) => {
            const titleA = (a.title_cn || a.title_en || '').toLowerCase();
            const titleB = (b.title_cn || b.title_en || '').toLowerCase();
            return titleA.localeCompare(titleB, 'zh-CN');
          });
          
        case 'title-desc':
          // 按标题降序
          return sorted.sort((a, b) => {
            const titleA = (a.title_cn || a.title_en || '').toLowerCase();
            const titleB = (b.title_cn || b.title_en || '').toLowerCase();
            return titleB.localeCompare(titleA, 'zh-CN');
          });
          
        default:
          return sorted;
      }
    };
    
    // 其他精选内容也应用排序
    const sortedOtherSummaries = computed(() => {
      return sortSummaries(otherSummaries.value);
    });
    
    // 事件处理
    const handleSummaryClick = (data) => {
      emit('summary-click', data);
    };
    
    // 处理删除事件
    const handleSummaryDelete = (data) => {
      emit('summary-delete', data);
    };
    
    const handleLevelChange = (level) => {
      selectedLevel.value = level;
      emit('level-change', level);
    };
    
    const handleYearChange = (year) => {
      selectedYear.value = year;
      emit('year-change', year);
    };
    
    const handleSortChange = (order) => {
      sortOrder.value = order;
      emit('sort-change', order);
    };
    
    // 重置筛选
    const resetFilters = () => {
      selectedLevel.value = '';
      selectedYear.value = '';
    };
    
    // 排序按钮点击处理
    const handleSortButtonClick = () => {
      // 循环切换排序方式
      const orders = ['date-desc', 'date-asc', 'title-asc', 'title-desc'];
      const currentIndex = orders.indexOf(sortOrder.value);
      const nextIndex = (currentIndex + 1) % orders.length;
      handleSortChange(orders[nextIndex]);
    };
    
    // 获取排序文本
    const getSortText = computed(() => {
      const textMap = {
        'date-desc': '最新',
        'date-asc': '最早',
        'title-asc': '标题A-Z',
        'title-desc': '标题Z-A'
      };
      return textMap[sortOrder.value] || '排序';
    });
    
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
      sortedOtherSummaries,
      sortOrder,
      getSortText,
      
      // 方法
      extractYear,
      formatWordCount,
      handleSummaryClick,
      handleSummaryDelete,
      handleLevelChange,
      handleYearChange,
      handleSortChange,
      handleSortButtonClick,
      resetFilters
    };
  }
}; 