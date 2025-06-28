/**
 * 组件加载器
 * 用于动态加载Vue组件的HTML、CSS和JS文件
 */
class ComponentLoader {
  static cache = new Map();
  
  /**
   * 加载单个组件
   * @param {string} name - 组件名称（用于Vue注册）
   * @param {string} path - 组件路径
   * @param {string} [fileName] - 实际文件名（可选，默认使用name）
   * @returns {Promise<Object>} - 组件定义对象
   */
  static async loadComponent(name, path, fileName = null) {
    const actualFileName = fileName || name;
    const cacheKey = `${path}/${actualFileName}`;
    
    // 检查缓存
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }
    
    try {
      // 并行加载HTML和CSS
      const [htmlResponse, cssResponse] = await Promise.all([
        fetch(`${path}/${actualFileName}.html`),
        fetch(`${path}/${actualFileName}.css`).catch(() => null) // CSS可选
      ]);
      
      if (!htmlResponse.ok) {
        throw new Error(`Failed to load component HTML: ${name}`);
      }
      
      const html = await htmlResponse.text();
      const css = cssResponse?.ok ? await cssResponse.text() : '';
      
      // 动态导入JS模块
      const jsModule = await import(`${path}/${actualFileName}.js`);
      
      // 注入组件样式
      if (css && !document.querySelector(`[data-component-style="${name}"]`)) {
        const style = document.createElement('style');
        style.setAttribute('data-component-style', name);
        style.textContent = css;
        document.head.appendChild(style);
      }
      
      // 创建组件定义
      const componentDef = {
        name,
        template: html,
        ...jsModule.default
      };
      
      // 缓存组件
      this.cache.set(cacheKey, componentDef);
      
      console.log(`Component ${name} loaded successfully`);
      return componentDef;
    } catch (error) {
      console.error(`Error loading component ${name}:`, error);
      throw error;
    }
  }
  
  /**
   * 批量注册组件
   * @param {Object} app - Vue应用实例
   * @param {Array} components - 组件配置数组 [[name, path, fileName?], ...]
   */
  static async registerComponents(app, components) {
    const loadPromises = components.map(async (config) => {
      const [name, path, fileName] = Array.isArray(config) ? config : [config.name, config.path, config.fileName];
      try {
        const component = await this.loadComponent(name, path, fileName);
        app.component(name, component);
        return { name, success: true };
      } catch (error) {
        console.error(`Failed to register component ${name}:`, error);
        return { name, success: false, error };
      }
    });
    
    const results = await Promise.all(loadPromises);
    const failed = results.filter(r => !r.success);
    
    if (failed.length > 0) {
      console.warn('Failed to load components:', failed.map(f => f.name));
    }
    
    return results;
  }
  
  /**
   * 清空组件缓存
   */
  static clearCache() {
    this.cache.clear();
  }
}

// 导出组件加载器
window.ComponentLoader = ComponentLoader; 