/**
 * CacheManager - 组件缓存管理器
 * 管理组件的内存缓存，支持TTL和版本控制
 */
class CacheManager {
  static cache = new Map();
  static stats = {
    hits: 0,
    misses: 0,
    sets: 0,
    clears: 0
  };
  
  /**
   * 获取缓存的组件
   * @param {string} key - 缓存键
   * @returns {Object|null} 组件定义或null
   */
  static get(key) {
    const entry = this.cache.get(key);
    
    if (!entry) {
      this.stats.misses++;
      return null;
    }
    
    // 检查是否过期
    if (!this.isValid(key)) {
      this.cache.delete(key);
      this.stats.misses++;
      return null;
    }
    
    // 更新命中次数
    entry.hits++;
    entry.lastAccess = Date.now();
    this.stats.hits++;
    
    return entry.component;
  }
  
  /**
   * 设置组件缓存
   * @param {string} key - 缓存键
   * @param {Object} component - 组件定义
   * @param {Object} options - 缓存选项
   */
  static set(key, component, options = {}) {
    const {
      ttl = 3600000,      // 默认1小时
      version = null,
      metadata = {}
    } = options;
    
    const entry = {
      component,
      version,
      timestamp: Date.now(),
      ttl,
      hits: 0,
      lastAccess: Date.now(),
      size: this._estimateSize(component),
      metadata
    };
    
    this.cache.set(key, entry);
    this.stats.sets++;
  }
  
  /**
   * 检查缓存是否有效
   * @param {string} key - 缓存键
   * @returns {boolean}
   */
  static isValid(key) {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return false;
    }
    
    // 检查TTL
    const age = Date.now() - entry.timestamp;
    if (age > entry.ttl) {
      return false;
    }
    
    return true;
  }
  
  /**
   * 检查版本是否匹配
   * @param {string} key - 缓存键
   * @param {string} version - 版本号
   * @returns {boolean}
   */
  static checkVersion(key, version) {
    const entry = this.cache.get(key);
    
    if (!entry || !entry.version) {
      return true; // 没有版本信息，认为匹配
    }
    
    return entry.version === version;
  }
  
  /**
   * 清空缓存
   * @param {string} [key] - 可选的缓存键，不提供则清空所有
   */
  static clear(key = null) {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
    this.stats.clears++;
  }
  
  /**
   * 获取缓存统计信息
   * @returns {Object} 统计信息
   */
  static getStats() {
    const totalRequests = this.stats.hits + this.stats.misses;
    const hitRate = totalRequests > 0 ? this.stats.hits / totalRequests : 0;
    
    // 计算总缓存大小
    let totalSize = 0;
    let entryCount = 0;
    
    for (const entry of this.cache.values()) {
      totalSize += entry.size;
      entryCount++;
    }
    
    return {
      hits: this.stats.hits,
      misses: this.stats.misses,
      sets: this.stats.sets,
      clears: this.stats.clears,
      hitRate: hitRate,
      entryCount: entryCount,
      totalSize: totalSize,
      averageSize: entryCount > 0 ? totalSize / entryCount : 0
    };
  }
  
  /**
   * 获取所有缓存键
   * @returns {Array<string>}
   */
  static keys() {
    return Array.from(this.cache.keys());
  }
  
  /**
   * 获取缓存条目详情
   * @param {string} key - 缓存键
   * @returns {Object|null}
   */
  static getEntry(key) {
    const entry = this.cache.get(key);
    if (!entry) {
      return null;
    }
    
    return {
      key,
      version: entry.version,
      timestamp: entry.timestamp,
      age: Date.now() - entry.timestamp,
      ttl: entry.ttl,
      hits: entry.hits,
      lastAccess: entry.lastAccess,
      size: entry.size,
      valid: this.isValid(key),
      metadata: entry.metadata
    };
  }
  
  /**
   * 清理过期缓存
   * @returns {number} 清理的条目数
   */
  static cleanup() {
    let cleaned = 0;
    
    for (const [key, entry] of this.cache.entries()) {
      const age = Date.now() - entry.timestamp;
      if (age > entry.ttl) {
        this.cache.delete(key);
        cleaned++;
      }
    }
    
    return cleaned;
  }
  
  /**
   * 重置统计信息
   */
  static resetStats() {
    this.stats = {
      hits: 0,
      misses: 0,
      sets: 0,
      clears: 0
    };
  }
  
  /**
   * 估算组件大小（字节）
   * @private
   */
  static _estimateSize(component) {
    try {
      const str = JSON.stringify(component);
      return new Blob([str]).size;
    } catch (e) {
      return 0;
    }
  }
  
  /**
   * 导出缓存数据（用于调试）
   * @returns {Object}
   */
  static export() {
    const data = {};
    
    for (const [key, entry] of this.cache.entries()) {
      data[key] = {
        version: entry.version,
        timestamp: entry.timestamp,
        age: Date.now() - entry.timestamp,
        ttl: entry.ttl,
        hits: entry.hits,
        size: entry.size,
        valid: this.isValid(key)
      };
    }
    
    return {
      entries: data,
      stats: this.getStats()
    };
  }
}

// 导出到全局
window.CacheManager = CacheManager;

// 定期清理过期缓存（每5分钟）
setInterval(() => {
  const cleaned = CacheManager.cleanup();
  if (cleaned > 0) {
    console.log(`🧹 CacheManager: 清理了 ${cleaned} 个过期缓存条目`);
  }
}, 5 * 60 * 1000);
