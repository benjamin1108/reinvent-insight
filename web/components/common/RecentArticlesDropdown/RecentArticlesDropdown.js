/**
 * RecentArticlesDropdown组件
 * 显示最近文章的下拉列表
 */

// 格式化为绝对日期
function formatAbsoluteDate(timestamp) {
  // 验证时间戳
  if (!timestamp || isNaN(timestamp) || timestamp <= 0) {
    return '未知时间';
  }
  
  // 将时间戳转换为Date对象
  const date = new Date(timestamp * 1000); // 时间戳是秒，需要转换为毫秒
  
  // 获取年月日
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  
  // 返回格式：2024-11-02
  return `${year}-${month}-${day}`;
}

export default {
  props: {
    // 是否显示下拉列表
    visible: {
      type: Boolean,
      default: false
    },
    
    // 文章列表数据
    articles: {
      type: Array,
      default: () => []
    },
    
    // 加载状态
    loading: {
      type: Boolean,
      default: false
    }
  },
  
  emits: [
    'article-click',  // 文章点击事件
    'mouseenter',     // 鼠标进入下拉区域
    'mouseleave'      // 鼠标离开下拉区域
  ],
  
  setup(props, { emit }) {
    const { computed } = Vue;
    
    // 处理后的文章列表（添加格式化时间）
    const processedArticles = computed(() => {
      return props.articles.map(article => ({
        ...article,
        formattedDate: formatAbsoluteDate(article.modified_at)
      }));
    });
    
    // 处理文章点击
    const handleArticleClick = (article) => {
      if (!article || !article.hash) {
        console.error('无效的文章数据:', article);
        return;
      }
      emit('article-click', article);
    };
    
    // 处理鼠标进入
    const handleMouseEnter = () => {
      emit('mouseenter');
    };
    
    // 处理鼠标离开
    const handleMouseLeave = () => {
      emit('mouseleave');
    };
    
    // 处理键盘事件
    const handleKeyDown = (event, article) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleArticleClick(article);
      }
    };
    
    return {
      processedArticles,
      handleArticleClick,
      handleMouseEnter,
      handleMouseLeave,
      handleKeyDown
    };
  }
};
