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

    // fetch 类型的预加载通常需要 crossorigin
    // 仅在跨域 fetch 时添加 crossorigin='anonymous'，同源资源保持默认 (same-origin)
    if (options.crossorigin) {
      link.crossOrigin = options.crossorigin;
    } else if (as === 'fetch') {
      try {
        const url = new URL(href, location.href);
        if (url.origin !== location.origin) {
          link.crossOrigin = 'anonymous';
        }
      } catch (e) {
        // 若 URL 解析失败，保持默认行为
      }
    }

    document.head.appendChild(link);
    this.preloadedResources.add(key);

    console.log(`🔗 预加载资源: ${href} (${link.rel})`);
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

    console.log(`🔮 预取资源: ${href}`);
  }

  /**
   * 批量预加载组件资源
   * @param {Array} components - 组件配置数组
   */
  static preloadComponents(components) {
    for (const config of components) {
      const [name, path, fileName] = Array.isArray(config)
        ? config
        : [config.name, config.path, config.fileName];

      const actualFileName = fileName || name;

      // 预加载HTML和JS
      this.preload(`${path}/${actualFileName}.html`, 'fetch');
      this.preload(`${path}/${actualFileName}.js`, 'script', { type: 'module' });

      // CSS是可选的，使用prefetch
      this.prefetch(`${path}/${actualFileName}.css`);
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
