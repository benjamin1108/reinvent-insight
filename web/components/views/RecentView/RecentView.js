/**
 * RecentView组件
 * 最近文章页面，展示最近更新的文章时间轴
 */
export default {
  dependencies: [
    ['recent-timeline', '/components/common/RecentTimeline', 'RecentTimeline']
  ],
  
  props: {
    // 文章列表数据
    articles: {
      type: Array,
      default: () => []
    },
    
    // 加载状态
    loading: {
      type: Boolean,
      default: false
    },
    
    // 是否为访客模式
    isGuest: {
      type: Boolean,
      default: false
    }
  },
  
  emits: [
    'article-click'  // 文章点击事件
  ],
  
  setup(props, { emit }) {
    const { computed, ref, onMounted, onUnmounted, watch } = Vue;
    
    // 排序状态
    const sortOrder = ref('date-desc'); // 'date-desc' | 'date-asc' | 'title-asc' | 'title-desc'
    
    // 分页状态
    const pageSize = 15;
    const displayCount = ref(pageSize);
    const loadingMore = ref(false);
    
    // 排序后的完整文章列表
    const sortedArticles = computed(() => {
      let filtered = props.articles
        .filter(article => article && article.hash && (article.title_cn || article.title_en));
      
      // 应用排序
      switch (sortOrder.value) {
        case 'date-desc':
          filtered.sort((a, b) => {
            const dateA = new Date(a.modified_at || a.upload_date || 0);
            const dateB = new Date(b.modified_at || b.upload_date || 0);
            return dateB - dateA;
          });
          break;
        case 'date-asc':
          filtered.sort((a, b) => {
            const dateA = new Date(a.modified_at || a.upload_date || 0);
            const dateB = new Date(b.modified_at || b.upload_date || 0);
            return dateA - dateB;
          });
          break;
        case 'title-asc':
          filtered.sort((a, b) => {
            const titleA = (a.title_cn || a.title_en || '').toLowerCase();
            const titleB = (b.title_cn || b.title_en || '').toLowerCase();
            return titleA.localeCompare(titleB, 'zh-CN');
          });
          break;
        case 'title-desc':
          filtered.sort((a, b) => {
            const titleA = (a.title_cn || a.title_en || '').toLowerCase();
            const titleB = (b.title_cn || b.title_en || '').toLowerCase();
            return titleB.localeCompare(titleA, 'zh-CN');
          });
          break;
      }
      
      return filtered;
    });
    
    // 当前显示的文章列表（无限滚动）
    const recentArticles = computed(() => {
      return sortedArticles.value.slice(0, displayCount.value);
    });
    
    // 是否还有更多
    const hasMore = computed(() => {
      return displayCount.value < sortedArticles.value.length;
    });
    
    // 加载更多
    const loadMore = () => {
      if (loadingMore.value || !hasMore.value) return;
      loadingMore.value = true;
      setTimeout(() => {
        displayCount.value += pageSize;
        loadingMore.value = false;
      }, 100);
    };
    
    // 滚动监听
    const handleScroll = () => {
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      const windowHeight = window.innerHeight;
      const docHeight = document.documentElement.scrollHeight;
      
      // 距离底部 200px 时加载更多
      if (scrollTop + windowHeight >= docHeight - 200) {
        loadMore();
      }
    };
    
    // 排序变化时重置显示数量
    watch(sortOrder, () => {
      displayCount.value = pageSize;
    });
    
    onMounted(() => {
      window.addEventListener('scroll', handleScroll);
    });
    
    onUnmounted(() => {
      window.removeEventListener('scroll', handleScroll);
    });
    
    // 处理文章点击
    const handleArticleClick = (article) => {
      if (!article || !article.hash) {
        console.error('无效的文章数据:', article);
        return;
      }
      emit('article-click', article);
    };
    
    // 排序按钮点击处理
    const handleSortButtonClick = () => {
      // 循环切换排序方式
      const orders = ['date-desc', 'date-asc', 'title-asc', 'title-desc'];
      const currentIndex = orders.indexOf(sortOrder.value);
      const nextIndex = (currentIndex + 1) % orders.length;
      sortOrder.value = orders[nextIndex];
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
      recentArticles,
      handleArticleClick,
      handleSortButtonClick,
      sortOrder,
      getSortText,
      hasMore,
      loadingMore
    };
  }
};
