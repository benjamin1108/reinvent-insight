/**
 * ResourceHints - 资源预加载提示管理器
 * 使用 <link rel="preload"> 和 <link rel="prefetch"> 优化资源加载
 */
class ResourceHints {
  static preloadedResources = new Set();
  static prefetchedResources = new Set();

  /**
   * 预加载关键资源（高优先级）
   * @param {string} href - 资源URL
   * @param {string} as - 资源类型 ('script', 'style', 'fetch')
   * @param {Object} options - 选项
   */
  static preload(href, as = 'fetch', options = {}) {
    const key = `${href}-${as}`;

    if (this.preloadedResources.has(key)) {
      return; // 已经预加载过
    }

    const link = document.createElement('link');

    // 处理 ES Modules
    if (options.type === 'module') {
      link.rel = 'modulepreload';
      // modulepreload 不需要 as 属性，也不需要 type="module" (这是给 script 标签用的)
    } else {
      link.rel = 'preload';
      link.as = as;

      if (options.type) {
        link.type = options.type;
      }
    }

    link.href = href;

    // 🔧 修复 CORS 问题：为同源 fetch 请求设置正确的 crossorigin
    // fetch() 使用 credentials: 'omit' 时，preload 也必须匹配
    if (options.crossorigin !== undefined) {
      if (options.crossorigin) {
        link.crossOrigin = options.crossorigin;
      }
      // 如果 crossorigin 为 false，则不设置该属性
    } else if (as === 'fetch') {
      // 🔑 关键修复：同源 fetch 也需要设置 crossorigin='anonymous' 以匹配 credentials: 'omit'
      link.crossOrigin = 'anonymous';
    }

    document.head.appendChild(link);
    this.preloadedResources.add(key);

  }

  /**
   * 预取资源（低优先级，空闲时加载）
   * @param {string} href - 资源URL
   */
  static prefetch(href) {
    if (this.prefetchedResources.has(href)) {
      return;
    }

    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = href;

    document.head.appendChild(link);
    this.prefetchedResources.add(href);
  }

  /**
   * 批量预加载组件资源
   * @param {Array} components - 组件配置数组
   */
  static preloadComponents(components) {
    // 🔧 优化：只预加载 JS 模块，减少未使用的预加载警告
    for (const config of components) {
      const [name, path, fileName] = Array.isArray(config)
        ? config
        : [config.name, config.path, config.fileName];

      const actualFileName = fileName || name;

      // 只预加载 JS 模块（最关键）
      this.preload(`${path}/${actualFileName}.js`, 'script', { type: 'module' });

      // HTML 和 CSS 让浏览器自然加载，不强制预加载
    }
  }

  /**
   * 清除所有预加载提示
   */
  static clear() {
    // 移除所有preload和prefetch链接
    document.querySelectorAll('link[rel="preload"], link[rel="prefetch"]').forEach(link => {
      if (this.preloadedResources.has(`${link.href}-${link.as}`) ||
        this.prefetchedResources.has(link.href)) {
        link.remove();
      }
    });

    this.preloadedResources.clear();
    this.prefetchedResources.clear();
  }
}

// 导出到全局
window.ResourceHints = ResourceHints;
