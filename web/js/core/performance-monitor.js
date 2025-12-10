/**
 * PerformanceMonitor - 性能监控器
 * 监控和记录组件加载性能指标
 */
class PerformanceMonitor {
  static timers = new Map();
  static componentMetrics = new Map();
  static enabled = true;
  static verbose = false;
  
  /**
   * 开始监控
   * @param {string} label - 监控标签
   */
  static start(label) {
    if (!this.enabled) return;
    
    this.timers.set(label, {
      startTime: performance.now(),
      startMark: `${label}-start`
    });
    
    // 使用Performance API标记
    if (performance.mark) {
      performance.mark(`${label}-start`);
    }
  }
  
  /**
   * 结束监控并记录
   * @param {string} label - 监控标签
   * @returns {number} 耗时（毫秒）
   */
  static end(label) {
    if (!this.enabled) return 0;
    
    const timer = this.timers.get(label);
    if (!timer) {
      console.warn(`⚠️ PerformanceMonitor: 未找到计时器 "${label}"`);
      return 0;
    }
    
    const endTime = performance.now();
    const duration = endTime - timer.startTime;
    
    // 使用Performance API标记和测量
    if (performance.mark && performance.measure) {
      performance.mark(`${label}-end`);
      try {
        performance.measure(label, `${label}-start`, `${label}-end`);
      } catch (e) {
        // 忽略测量错误
      }
    }
    
    this.timers.delete(label);
    
    if (this.verbose) {
    }
    
    return duration;
  }
  
  /**
   * 记录组件加载指标
   * @param {string} componentName - 组件名称
   * @param {Object} metrics - 指标数据
   */
  static recordComponentLoad(componentName, metrics = {}) {
    if (!this.enabled) return;
    
    const {
      loadTime = 0,
      cacheHit = false,
      fileSize = 0,
      error = null,
      startTime = Date.now(),
      endTime = Date.now()
    } = metrics;
    
    const record = {
      componentName,
      loadTime,
      cacheHit,
      fileSize,
      error,
      startTime,
      endTime,
      timestamp: Date.now()
    };
    
    this.componentMetrics.set(componentName, record);
    
    // 输出详细日志
    if (this.verbose) {
      const cacheStatus = cacheHit ? '✅ 缓存' : '🌐 网络';
      const status = error ? '❌ 失败' : '✅ 成功';
      console.log(
        `📦 ${componentName}: ${status} ${cacheStatus} ${loadTime.toFixed(2)}ms ${fileSize > 0 ? `(${(fileSize / 1024).toFixed(2)}KB)` : ''}`
      );
    }
    
    // 检查性能警告
    this._checkWarnings(componentName, record);
  }
  
  /**
   * 记录错误
   * @param {string} componentName - 组件名称
   * @param {Error} error - 错误对象
   */
  static recordError(componentName, error) {
    this.recordComponentLoad(componentName, {
      error: error.message || String(error),
      loadTime: 0,
      cacheHit: false
    });
  }
  
  /**
   * 获取性能报告
   * @returns {Object} 性能报告
   */
  static getReport() {
    const metrics = Array.from(this.componentMetrics.values());
    
    if (metrics.length === 0) {
      return {
        totalLoadTime: 0,
        componentCount: 0,
        cacheHitRate: 0,
        averageLoadTime: 0,
        slowestComponent: null,
        errors: [],
        timeline: []
      };
    }
    
    // 计算总加载时间
    const totalLoadTime = metrics.reduce((sum, m) => sum + m.loadTime, 0);
    
    // 计算缓存命中率
    const cacheHits = metrics.filter(m => m.cacheHit).length;
    const cacheHitRate = cacheHits / metrics.length;
    
    // 计算平均加载时间
    const averageLoadTime = totalLoadTime / metrics.length;
    
    // 找出最慢的组件
    const slowestComponent = metrics.reduce((slowest, current) => {
      return current.loadTime > (slowest?.loadTime || 0) ? current : slowest;
    }, null);
    
    // 收集错误
    const errors = metrics
      .filter(m => m.error)
      .map(m => ({
        component: m.componentName,
        error: m.error,
        timestamp: m.timestamp
      }));
    
    // 构建时间线
    const timeline = metrics
      .sort((a, b) => a.startTime - b.startTime)
      .map(m => ({
        component: m.componentName,
        startTime: m.startTime,
        endTime: m.endTime,
        duration: m.loadTime,
        cacheHit: m.cacheHit
      }));
    
    return {
      totalLoadTime,
      componentCount: metrics.length,
      cacheHitRate,
      averageLoadTime,
      slowestComponent: slowestComponent ? {
        name: slowestComponent.componentName,
        loadTime: slowestComponent.loadTime
      } : null,
      errors,
      timeline
    };
  }
  
  /**
   * 导出性能数据
   * @param {string} format - 导出格式 ('json' | 'csv')
   * @returns {string} 导出数据
   */
  static export(format = 'json') {
    const report = this.getReport();
    
    if (format === 'json') {
      return JSON.stringify(report, null, 2);
    } else if (format === 'csv') {
      const lines = ['Component,Load Time (ms),Cache Hit,File Size (bytes),Error'];
      
      for (const [name, metrics] of this.componentMetrics.entries()) {
        lines.push(
          `${name},${metrics.loadTime},${metrics.cacheHit},${metrics.fileSize},${metrics.error || ''}`
        );
      }
      
      return lines.join('\n');
    }
    
    return '';
  }
  
  /**
   * 清空性能数据
   */
  static clear() {
    this.timers.clear();
    this.componentMetrics.clear();
    
    // 清除Performance API的标记和测量
    if (performance.clearMarks) {
      performance.clearMarks();
    }
    if (performance.clearMeasures) {
      performance.clearMeasures();
    }
  }
  
  /**
   * 启用/禁用监控
   * @param {boolean} enabled
   */
  static setEnabled(enabled) {
    this.enabled = enabled;
  }
  
  /**
   * 启用/禁用详细日志
   * @param {boolean} verbose
   */
  static setVerbose(verbose) {
    this.verbose = verbose;
  }
  
  /**
   * 打印性能报告到控制台
   */
  static printReport() {
    const report = this.getReport();
    
    console.log(`总加载时间: ${report.totalLoadTime.toFixed(2)}ms`);
    console.log(`组件数量: ${report.componentCount}`);
    console.log(`缓存命中率: ${(report.cacheHitRate * 100).toFixed(1)}%`);
    console.log(`平均加载时间: ${report.averageLoadTime.toFixed(2)}ms`);
    
    if (report.slowestComponent) {
      console.log(`最慢组件: ${report.slowestComponent.name} (${report.slowestComponent.loadTime.toFixed(2)}ms)`);
    }
    
    if (report.errors.length > 0) {
      report.errors.forEach(err => {
        console.error(`${err.component}: ${err.error}`);
      });
    }
    
  }
  
  /**
   * 获取Performance API的性能条目
   * @returns {Array}
   */
  static getPerformanceEntries() {
    if (!performance.getEntriesByType) {
      return [];
    }
    
    return performance.getEntriesByType('measure');
  }
  
  /**
   * 检查性能警告
   * @private
   */
  static _checkWarnings(componentName, record) {
    const SLOW_THRESHOLD = 1000; // 1秒
    const VERY_SLOW_THRESHOLD = 3000; // 3秒
    
    if (record.error) {
      console.error(`❌ 组件加载失败: ${componentName} - ${record.error}`);
    } else if (record.loadTime > VERY_SLOW_THRESHOLD) {
      console.warn(`🐌 组件加载非常慢: ${componentName} (${record.loadTime.toFixed(2)}ms)`);
    } else if (record.loadTime > SLOW_THRESHOLD) {
      console.warn(`⚠️ 组件加载较慢: ${componentName} (${record.loadTime.toFixed(2)}ms)`);
    }
  }
  
  /**
   * 获取组件指标
   * @param {string} componentName - 组件名称
   * @returns {Object|null}
   */
  static getComponentMetrics(componentName) {
    return this.componentMetrics.get(componentName) || null;
  }
  
  /**
   * 获取所有组件指标
   * @returns {Array}
   */
  static getAllMetrics() {
    return Array.from(this.componentMetrics.values());
  }
}

// 导出到全局
window.PerformanceMonitor = PerformanceMonitor;

// 在开发环境启用详细日志
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  PerformanceMonitor.setVerbose(true);
}
