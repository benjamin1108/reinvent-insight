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
      
      return componentDef;
    } catch (error) {
      console.error(`Error loading component ${name}:`, error);
      throw error;
    }
  }
  
  /**
   * 递归收集组件依赖
   * @param {Array} dependencies - 依赖配置数组
   * @param {Set} collected - 已收集的组件名集合
   * @param {Array} result - 结果数组
   */
  static async collectDependencies(dependencies, collected, result) {
    for (const depConfig of dependencies) {
      const [depName, depPath, depFileName] = Array.isArray(depConfig) ? depConfig : [depConfig.name, depConfig.path, depConfig.fileName];
      
      if (!collected.has(depName)) {
        collected.add(depName);
        
        // 先加载依赖组件以检查它的依赖
        const depComponent = await this.loadComponent(depName, depPath, depFileName);
        
        // 如果依赖组件还有依赖，递归收集
        if (depComponent.dependencies && Array.isArray(depComponent.dependencies)) {
          await this.collectDependencies(depComponent.dependencies, collected, result);
        }
        
        // 将当前依赖添加到结果中
        result.push([depName, depPath, depFileName]);
      }
    }
  }

  /**
   * 批量注册组件（支持自动依赖解析）
   * @param {Object} app - Vue应用实例
   * @param {Array} components - 组件配置数组 [[name, path, fileName?], ...]
   */
  static async registerComponents(app, components) {
    const allComponents = [];
    const collected = new Set();
    
    // 第一步：收集所有组件及其依赖
    for (const config of components) {
      const [name, path, fileName] = Array.isArray(config) ? config : [config.name, config.path, config.fileName];
      
      if (!collected.has(name)) {
        collected.add(name);
        
        // 加载主组件
        const component = await this.loadComponent(name, path, fileName);
        
        // 如果有依赖，递归收集依赖
        if (component.dependencies && Array.isArray(component.dependencies)) {
          await this.collectDependencies(component.dependencies, collected, allComponents);
        }
        
        // 主组件放在最后
        allComponents.push([name, path, fileName]);
      }
    }
    
    // 第二步：按顺序注册所有组件（依赖在前，主组件在后）
    const results = [];
    const total = allComponents.length;
    
    for (let i = 0; i < allComponents.length; i++) {
      const [name, path, fileName] = allComponents[i];
      try {
        const component = await this.loadComponent(name, path, fileName);
        app.component(name, component);
        results.push({ name, success: true });
      } catch (error) {
        console.error(`Failed to register component ${name}:`, error);
        results.push({ name, success: false });
      }
    }
    
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