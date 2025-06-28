/**
 * 模块初始化脚本
 * 确保所有核心模块按正确顺序加载并初始化到全局对象
 */

// 等待 DOM 加载完成
const waitForDOM = () => new Promise(resolve => {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', resolve);
  } else {
    resolve();
  }
});

// 等待特定的全局对象可用
const waitForGlobal = (name, timeout = 5000) => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    
    const check = () => {
      if (window[name]) {
        resolve(window[name]);
      } else if (Date.now() - startTime > timeout) {
        reject(new Error(`${name} 加载超时`));
      } else {
        setTimeout(check, 10);
      }
    };
    
    check();
  });
};

// 初始化所有模块
export async function initModules() {
  try {
    await waitForDOM();
    
    // 等待核心模块
    await Promise.all([
      waitForGlobal('eventBus'),
      waitForGlobal('ComponentLoader'),
      waitForGlobal('useToast')
    ]);
    
    console.log('所有核心模块已加载完成');
    return true;
  } catch (error) {
    console.error('模块初始化失败:', error);
    return false;
  }
}

// 导出到全局
window.initModules = initModules;

export default initModules; 