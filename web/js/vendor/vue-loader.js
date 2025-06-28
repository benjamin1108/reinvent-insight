/**
 * Vue.js 智能加载器
 * 优先使用CDN，失败时自动切换到本地文件
 */
(function() {
  'use strict';
  
  // CDN列表（按优先级排序）
  const CDN_URLS = [
    'https://unpkg.com/vue@3.3.4/dist/vue.global.prod.js',
    'https://cdn.jsdelivr.net/npm/vue@3.3.4/dist/vue.global.prod.js'
  ];
  
  // 本地备用文件
  const LOCAL_URL = '/js/vendor/vue.global.prod.min.js';
  
  // 加载超时时间（毫秒）
  const TIMEOUT = 5000;
  
  let currentIndex = 0;
  
  /**
   * 加载脚本
   */
  function loadScript(url, timeout = TIMEOUT) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = url;
      script.async = true;
      
      // 设置超时
      const timer = setTimeout(() => {
        script.remove();
        reject(new Error(`Loading timeout: ${url}`));
      }, timeout);
      
      script.onload = () => {
        clearTimeout(timer);
        console.log(`✅ Vue.js loaded from: ${url}`);
        resolve();
      };
      
      script.onerror = () => {
        clearTimeout(timer);
        script.remove();
        reject(new Error(`Loading failed: ${url}`));
      };
      
      document.head.appendChild(script);
    });
  }
  
  /**
   * 尝试加载Vue.js
   */
  async function loadVue() {
    // 如果Vue已经存在，直接返回
    if (window.Vue) {
      console.log('✅ Vue.js already loaded');
      return;
    }
    
    // 显示加载状态
    console.log('🚀 Loading Vue.js...');
    
    // 尝试CDN
    for (let i = 0; i < CDN_URLS.length; i++) {
      try {
        await loadScript(CDN_URLS[i]);
        return; // 成功加载，退出
      } catch (error) {
        console.warn(`⚠️ CDN failed: ${CDN_URLS[i]}`, error.message);
      }
    }
    
    // 所有CDN都失败，尝试本地文件
    try {
      console.log('🔄 All CDNs failed, trying local file...');
      await loadScript(LOCAL_URL);
    } catch (error) {
      console.error('❌ Failed to load Vue.js from all sources:', error);
      
      // 显示错误信息给用户
      const errorDiv = document.createElement('div');
      errorDiv.innerHTML = `
        <div style="
          position: fixed; 
          top: 50%; 
          left: 50%; 
          transform: translate(-50%, -50%);
          background: #fee; 
          border: 2px solid #f00; 
          padding: 20px; 
          border-radius: 8px;
          z-index: 9999;
          font-family: Arial, sans-serif;
        ">
          <h3>❌ Vue.js 加载失败</h3>
          <p>请检查网络连接或联系管理员</p>
          <button onclick="location.reload()" style="
            background: #007cba; 
            color: white; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px;
            cursor: pointer;
          ">重新加载</button>
        </div>
      `;
      document.body.appendChild(errorDiv);
      
      throw error;
    }
  }
  
  // 开始加载
  loadVue().catch(console.error);
})(); 