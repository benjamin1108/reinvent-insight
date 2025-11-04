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
    const { computed } = Vue;
    
    // 最近文章列表（按修改时间排序，取前10篇）
    const recentArticles = computed(() => {
      return props.articles
        .filter(article => article && article.hash && (article.title_cn || article.title_en))
        .sort((a, b) => b.modified_at - a.modified_at)
        .slice(0, 10);
    });
    
    // 处理文章点击
    const handleArticleClick = (article) => {
      if (!article || !article.hash) {
        console.error('无效的文章数据:', article);
        return;
      }
      emit('article-click', article);
    };
    
    return {
      recentArticles,
      handleArticleClick
    };
  }
};
