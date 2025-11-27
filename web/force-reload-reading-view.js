// 强制重新加载 ReadingView 样式
(function() {
  console.log('🔄 强制清除 ReadingView 样式缓存...');
  
  // 1. 移除旧的样式标签
  const oldStyle = document.querySelector('[data-component-style="reading-view"]');
  if (oldStyle) {
    oldStyle.remove();
    console.log('✅ 已移除旧样式标签');
  }
  
  // 2. 清除 CacheManager 缓存
  if (window.CacheManager) {
    const keys = ['reading-view', '/components/views/ReadingView/ReadingView'];
    keys.forEach(key => {
      window.CacheManager.delete(key);
      console.log(`✅ 已清除缓存: ${key}`);
    });
  }
  
  // 3. 清除 ComponentLoader 缓存
  if (window.ComponentLoader && window.ComponentLoader.cache) {
    window.ComponentLoader.cache.forEach((value, key) => {
      if (key.includes('ReadingView')) {
        window.ComponentLoader.cache.delete(key);
        console.log(`✅ 已清除 ComponentLoader 缓存: ${key}`);
      }
    });
  }
  
  console.log('✅ ReadingView 缓存清除完成，请刷新页面');
})();
