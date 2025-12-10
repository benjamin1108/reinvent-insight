/**
 * 文档列表缓存管理器
 * 
 * 使用 localStorage 缓存文档列表，减少 API 调用
 * 通过 cache_version 判断数据是否需要更新
 */

const CACHE_KEY = 'reinvent_summaries_cache';
const CACHE_VERSION_KEY = 'reinvent_summaries_version';
const CACHE_TIMESTAMP_KEY = 'reinvent_summaries_timestamp';

// 缓存有效期（毫秒）- 默认 5 分钟
const CACHE_TTL = 5 * 60 * 1000;

/**
 * 获取缓存的文档列表
 * @returns {Object|null} 缓存数据或 null
 */
export function getCachedSummaries() {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    const timestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);
    
    if (!cached || !timestamp) {
      return null;
    }
    
    // 检查缓存是否过期
    const cacheAge = Date.now() - parseInt(timestamp, 10);
    if (cacheAge > CACHE_TTL) {
      return null;
    }
    
    return JSON.parse(cached);
  } catch (error) {
    console.warn('[SummariesCache] 读取缓存失败:', error);
    return null;
  }
}

/**
 * 获取缓存的版本号
 * @returns {number} 缓存版本号
 */
export function getCachedVersion() {
  try {
    const version = localStorage.getItem(CACHE_VERSION_KEY);
    return version ? parseInt(version, 10) : 0;
  } catch (error) {
    return 0;
  }
}

/**
 * 保存文档列表到缓存
 * @param {Array} summaries 文档列表
 * @param {number} version 缓存版本号
 */
export function cacheSummaries(summaries, version) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(summaries));
    localStorage.setItem(CACHE_VERSION_KEY, String(version));
    localStorage.setItem(CACHE_TIMESTAMP_KEY, String(Date.now()));
  } catch (error) {
    console.warn('[SummariesCache] 保存缓存失败:', error);
    // 如果存储失败（可能是空间不足），尝试清理旧缓存
    clearSummariesCache();
  }
}

/**
 * 清除文档列表缓存
 */
export function clearSummariesCache() {
  try {
    localStorage.removeItem(CACHE_KEY);
    localStorage.removeItem(CACHE_VERSION_KEY);
    localStorage.removeItem(CACHE_TIMESTAMP_KEY);
  } catch (error) {
    console.warn('[SummariesCache] 清除缓存失败:', error);
  }
}

/**
 * 检查服务器缓存版本是否更新
 * @returns {Promise<{needsUpdate: boolean, serverVersion: number}>}
 */
export async function checkCacheVersion() {
  try {
    const response = await axios.get('/api/public/cache-info');
    const serverVersion = response.data.cache_version || 0;
    const cachedVersion = getCachedVersion();
    
    return {
      needsUpdate: serverVersion !== cachedVersion,
      serverVersion
    };
  } catch (error) {
    console.warn('[SummariesCache] 检查版本失败:', error);
    // 检查失败时，默认需要更新
    return { needsUpdate: true, serverVersion: 0 };
  }
}

/**
 * 智能加载文档列表
 * 
 * 策略：
 * 1. 先检查本地缓存，如果有效则立即返回
 * 2. 后台检查服务器版本，如有更新则刷新
 * 
 * @param {Object} options 选项
 * @param {boolean} options.forceRefresh 强制刷新
 * @param {Function} options.onCacheHit 缓存命中时的回调
 * @param {Function} options.onDataUpdate 数据更新时的回调
 * @returns {Promise<Array>} 文档列表
 */
export async function loadSummariesWithCache(options = {}) {
  const { forceRefresh = false, onCacheHit = null, onDataUpdate = null } = options;
  
  // 1. 尝试使用缓存
  if (!forceRefresh) {
    const cached = getCachedSummaries();
    if (cached && Array.isArray(cached)) {
      // 缓存命中，先返回缓存数据
      if (onCacheHit) {
        onCacheHit(cached);
      }
      
      // 后台检查是否需要更新
      checkCacheVersion().then(({ needsUpdate, serverVersion }) => {
        if (needsUpdate) {
          // 需要更新，后台拉取新数据
          fetchAndCacheSummaries().then(newData => {
            if (onDataUpdate && newData) {
              onDataUpdate(newData);
            }
          });
        }
      });
      
      return cached;
    }
  }
  
  // 2. 缓存无效或强制刷新，从服务器获取
  return await fetchAndCacheSummaries();
}

/**
 * 从服务器获取并缓存文档列表
 * @returns {Promise<Array>}
 */
export async function fetchAndCacheSummaries() {
  try {
    const response = await axios.get('/api/public/summaries');
    const summaries = response.data.summaries || [];
    const version = response.data.cache_version || 0;
    
    // 缓存数据
    cacheSummaries(summaries, version);
    
    return summaries;
  } catch (error) {
    console.error('[SummariesCache] 获取数据失败:', error);
    throw error;
  }
}

/**
 * 获取缓存统计信息
 * @returns {Object} 缓存统计
 */
export function getCacheStats() {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    const timestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);
    const version = getCachedVersion();
    
    return {
      hasCached: !!cached,
      version,
      cacheAge: timestamp ? Date.now() - parseInt(timestamp, 10) : null,
      cacheSize: cached ? cached.length : 0,
      isValid: !!getCachedSummaries()
    };
  } catch (error) {
    return {
      hasCached: false,
      version: 0,
      cacheAge: null,
      cacheSize: 0,
      isValid: false
    };
  }
}

// 默认导出
export default {
  getCachedSummaries,
  getCachedVersion,
  cacheSummaries,
  clearSummariesCache,
  checkCacheVersion,
  loadSummariesWithCache,
  fetchAndCacheSummaries,
  getCacheStats
};
