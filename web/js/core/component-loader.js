/**
 * 组件加载器（增强版）
 * 用于动态加载Vue组件的HTML、CSS和JS文件
 * 支持并行加载、缓存管理和性能监控
 */
class ComponentLoader {
  static cache = new Map();
  static MAX_CONCURRENT = 6; // 最大并发请求数
  
  /**
   * 加载单个组件（增强版，支持缓存和性能监控）
   * @param {string} name - 组件名称（用于Vue注册）
   * @param {string} path - 组件路径
   * @param {string} [fileName] - 实际文件名（可选，默认使用name）
   * @param {Object} [options] - 加载选项
   * @returns {Promise<Object>} - 组件定义对象
   */
  static async loadComponent(name, path, fileName = null, options = {}) {
    const {
      useCache = true,
      version = null,
      timeout = 10000
    } = options;
    
    const actualFileName = fileName || name;
    const cacheKey = `${path}/${actualFileName}`;
    const startTime = performance.now();
    
    // 开始性能监控
    if (window.PerformanceMonitor) {
      window.PerformanceMonitor.start(`component-${name}`);
    }
    
    try {
      // 检查CacheManager缓存
      if (useCache && window.CacheManager) {
        const cached = window.CacheManager.get(cacheKey);
        if (cached && (!version || window.CacheManager.checkVersion(cacheKey, version))) {
          const loadTime = performance.now() - startTime;
          
          // 记录性能指标
          if (window.PerformanceMonitor) {
            window.PerformanceMonitor.end(`component-${name}`);
            window.PerformanceMonitor.recordComponentLoad(name, {
              loadTime,
              cacheHit: true,
              startTime,
              endTime: performance.now()
            });
          }
          
          return cached;
        }
      }
      
      // 检查旧的内存缓存（向后兼容）
      if (useCache && this.cache.has(cacheKey)) {
        const cached = this.cache.get(cacheKey);
        const loadTime = performance.now() - startTime;
        
        if (window.PerformanceMonitor) {
          window.PerformanceMonitor.end(`component-${name}`);
          window.PerformanceMonitor.recordComponentLoad(name, {
            loadTime,
            cacheHit: true,
            startTime,
            endTime: performance.now()
          });
        }
        
        return cached;
      }
      
      // 创建超时Promise
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Component load timeout: ${name}`)), timeout);
      });
      
      // 并行加载HTML和CSS
      const loadPromise = Promise.all([
        fetch(`${path}/${actualFileName}.html`),
        fetch(`${path}/${actualFileName}.css`).catch(() => null) // CSS可选
      ]);
      
      const [htmlResponse, cssResponse] = await Promise.race([loadPromise, timeoutPromise]);
      
      if (!htmlResponse.ok) {
        throw new Error(`Failed to load component HTML: ${name} (${htmlResponse.status})`);
      }
      
      const html = await htmlResponse.text();
      const css = cssResponse?.ok ? await cssResponse.text() : '';
      
      // 动态导入JS模块
      const jsModule = await import(`${path}/${actualFileName}.js`);
      
      // 计算文件大小
      const fileSize = new Blob([html, css]).size;
      
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
      
      // 存入CacheManager
      if (useCache && window.CacheManager) {
        window.CacheManager.set(cacheKey, componentDef, {
          version,
          metadata: { path, fileName: actualFileName }
        });
      }
      
      // 存入旧缓存（向后兼容）
      this.cache.set(cacheKey, componentDef);
      
      const loadTime = performance.now() - startTime;
      
      // 记录性能指标
      if (window.PerformanceMonitor) {
        window.PerformanceMonitor.end(`component-${name}`);
        window.PerformanceMonitor.recordComponentLoad(name, {
          loadTime,
          cacheHit: false,
          fileSize,
          startTime,
          endTime: performance.now()
        });
      }
      
      return componentDef;
    } catch (error) {
      const loadTime = performance.now() - startTime;
      
      // 记录错误
      if (window.PerformanceMonitor) {
        window.PerformanceMonitor.end(`component-${name}`);
        window.PerformanceMonitor.recordError(name, error);
      }
      
      console.error(`Error loading component ${name}:`, error);
      
      // 尝试降级处理
      console.log(`🔄 尝试降级处理组件: ${name}`);
      
      // 1. 尝试从缓存恢复
      const recovered = this.tryRecoverFromCache(name, path, actualFileName);
      if (recovered) {
        return recovered;
      }
      
      // 2. 使用占位符组件
      console.warn(`⚠️ 使用占位符组件: ${name}`);
      const placeholder = this.createPlaceholderComponent(name);
      
      // 缓存占位符以避免重复创建
      if (window.CacheManager) {
        window.CacheManager.set(cacheKey, placeholder, {
          ttl: 60000, // 1分钟后过期
          metadata: { isPlaceholder: true }
        });
      }
      
      return placeholder;
    }
  }
  
  /**
   * 并行加载多个组件
   * @param {Array} components - 组件配置数组
   * @param {Object} options - 加载选项
   * @returns {Promise<Array>} 组件定义数组
   */
  static async loadComponentsParallel(components, options = {}) {
    const {
      maxConcurrent = this.MAX_CONCURRENT,
      onProgress = null,
      continueOnError = true
    } = options;
    
    // 分批加载以控制并发数
    const batches = [];
    for (let i = 0; i < components.length; i += maxConcurrent) {
      batches.push(components.slice(i, i + maxConcurrent));
    }
    
    const results = [];
    let loaded = 0;
    
    for (const batch of batches) {
      const batchPromises = batch.map(config => {
        const [name, path, fileName] = Array.isArray(config) 
          ? config 
          : [config.name, config.path, config.fileName];
        
        return this.loadComponent(name, path, fileName, options)
          .then(component => {
            loaded++;
            if (onProgress) {
              onProgress(loaded, components.length, name);
            }
            return { success: true, name, component };
          })
          .catch(error => {
            loaded++;
            if (onProgress) {
              onProgress(loaded, components.length, name);
            }
            return { success: false, name, error };
          });
      });
      
      if (continueOnError) {
        const batchResults = await Promise.allSettled(batchPromises);
        results.push(...batchResults.map(r => r.value || r.reason));
      } else {
        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults);
      }
    }
    
    return results;
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
   * 批量注册组件（增强版，支持并行加载和进度回调）
   * @param {Object} app - Vue应用实例
   * @param {Array} components - 组件配置数组 [[name, path, fileName?], ...]
   * @param {Object} options - 加载选项
   * @returns {Promise<Array>} 加载结果
   */
  static async registerComponents(app, components, options = {}) {
    const {
      parallel = true,
      useCache = true,
      onProgress = null,
      timeout = 10000,
      continueOnError = true
    } = options;
    
    // 开始总体性能监控
    if (window.PerformanceMonitor) {
      window.PerformanceMonitor.start('total-component-loading');
    }
    
    const allComponents = [];
    const collected = new Set();
    const componentMap = new Map(); // 存储已加载的组件
    
    // 第一步：收集所有组件及其依赖
    if (parallel) {
      // 并行加载所有主组件
      const loadResults = await this.loadComponentsParallel(components, {
        useCache,
        timeout,
        onProgress,
        continueOnError
      });
      
      // 处理加载结果并收集依赖
      for (const result of loadResults) {
        if (result.success) {
          const { name, component } = result;
          collected.add(name);
          componentMap.set(name, component);
          
          // 如果有依赖，递归收集依赖
          if (component.dependencies && Array.isArray(component.dependencies)) {
            await this.collectDependencies(component.dependencies, collected, allComponents);
          }
          
          // 从原始配置中找到对应的配置
          const config = components.find(c => {
            const [n] = Array.isArray(c) ? c : [c.name];
            return n === name;
          });
          
          if (config) {
            const [, path, fileName] = Array.isArray(config) 
              ? config 
              : [config.name, config.path, config.fileName];
            allComponents.push([name, path, fileName]);
          }
        }
      }
    } else {
      // 串行加载（原有逻辑）
      for (const config of components) {
        const [name, path, fileName] = Array.isArray(config) 
          ? config 
          : [config.name, config.path, config.fileName];
        
        if (!collected.has(name)) {
          collected.add(name);
          
          try {
            // 加载主组件
            const component = await this.loadComponent(name, path, fileName, { useCache, timeout });
            componentMap.set(name, component);
            
            // 如果有依赖，递归收集依赖
            if (component.dependencies && Array.isArray(component.dependencies)) {
              await this.collectDependencies(component.dependencies, collected, allComponents);
            }
            
            // 主组件放在最后
            allComponents.push([name, path, fileName]);
          } catch (error) {
            console.error(`Failed to load component ${name}:`, error);
            if (!continueOnError) {
              throw error;
            }
          }
        }
      }
    }
    
    // 第二步：按顺序注册所有组件（依赖在前，主组件在后）
    const results = [];
    const total = allComponents.length;
    
    for (let i = 0; i < allComponents.length; i++) {
      const [name, path, fileName] = allComponents[i];
      
      try {
        // 从缓存或componentMap获取组件
        let component = componentMap.get(name);
        if (!component) {
          component = await this.loadComponent(name, path, fileName, { useCache, timeout });
        }
        
        // 注册到Vue
        app.component(name, component);
        results.push({ name, success: true });
        
        // 调用进度回调
        if (onProgress) {
          onProgress(i + 1, total, name);
        }
      } catch (error) {
        console.error(`Failed to register component ${name}:`, error);
        results.push({ name, success: false, error: error.message });
        
        if (!continueOnError) {
          throw error;
        }
      }
    }
    
    // 结束总体性能监控
    if (window.PerformanceMonitor) {
      const totalTime = window.PerformanceMonitor.end('total-component-loading');
      console.log(`✅ 组件加载完成: ${results.length} 个组件，耗时 ${totalTime.toFixed(2)}ms`);
      
      // 打印性能报告
      if (window.PerformanceMonitor.verbose) {
        window.PerformanceMonitor.printReport();
      }
    }
    
    const failed = results.filter(r => !r.success);
    
    if (failed.length > 0) {
      console.warn(`⚠️ ${failed.length} 个组件加载失败:`, failed.map(f => f.name));
    }
    
    return results;
  }
  
  /**
   * 预加载组件（不注册）
   * @param {Array} components - 组件配置数组
   * @param {Object} options - 加载选项
   * @returns {Promise<void>}
   */
  static async preloadComponents(components, options = {}) {
    const {
      useCache = true,
      timeout = 10000
    } = options;
    
    console.log(`🔄 预加载 ${components.length} 个组件...`);
    
    await this.loadComponentsParallel(components, {
      useCache,
      timeout,
      continueOnError: true
    });
    
    console.log(`✅ 预加载完成`);
  }
  
  /**
   * 创建占位符组件（用于降级处理）
   * @param {string} name - 组件名称
   * @returns {Object} 占位符组件定义
   */
  static createPlaceholderComponent(name) {
    return {
      name,
      template: `
        <div class="component-placeholder" style="padding: 20px; text-align: center; color: #9ca3af;">
          <div style="font-size: 14px;">组件加载失败: ${name}</div>
          <div style="font-size: 12px; margin-top: 8px;">请刷新页面重试</div>
        </div>
      `,
      setup() {
        console.warn(`使用占位符组件: ${name}`);
        return {};
      }
    };
  }
  
  /**
   * 尝试从缓存恢复组件
   * @param {string} name - 组件名称
   * @param {string} path - 组件路径
   * @param {string} fileName - 文件名
   * @returns {Object|null} 组件定义或null
   */
  static tryRecoverFromCache(name, path, fileName) {
    const actualFileName = fileName || name;
    const cacheKey = `${path}/${actualFileName}`;
    
    // 尝试从CacheManager恢复
    if (window.CacheManager) {
      const cached = window.CacheManager.get(cacheKey);
      if (cached) {
        console.log(`✅ 从CacheManager恢复组件: ${name}`);
        return cached;
      }
    }
    
    // 尝试从旧缓存恢复
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      console.log(`✅ 从内存缓存恢复组件: ${name}`);
      return cached;
    }
    
    return null;
  }
  
  /**
   * 清空组件缓存
   */
  static clearCache() {
    this.cache.clear();
    
    if (window.CacheManager) {
      window.CacheManager.clear();
    }
  }
}

// 导出组件加载器
window.ComponentLoader = ComponentLoader; 