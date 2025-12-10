/**
 * 统一日志管理器
 * 支持日志级别控制，生产环境默认只显示 warn 和 error
 * 
 * 使用方法:
 *   import { logger } from '/js/core/logger.js';
 *   logger.debug('调试信息');
 *   logger.info('一般信息');
 *   logger.warn('警告信息');
 *   logger.error('错误信息');
 * 
 * 开启调试模式:
 *   localStorage.setItem('DEBUG_MODE', 'true');
 *   location.reload();
 */

const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
};

// 从 localStorage 读取调试模式
const isDebugMode = () => {
  try {
    return localStorage.getItem('DEBUG_MODE') === 'true';
  } catch {
    return false;
  }
};

// 当前日志级别：调试模式显示所有，否则只显示 warn 和 error
const currentLevel = isDebugMode() ? LOG_LEVELS.DEBUG : LOG_LEVELS.WARN;

/**
 * 日志管理器
 */
export const logger = {
  /**
   * 调试日志 - 开发时使用，生产环境默认不显示
   */
  debug(...args) {
    if (currentLevel <= LOG_LEVELS.DEBUG) {
      console.log(...args);
    }
  },

  /**
   * 信息日志 - 重要状态变化，生产环境默认不显示
   */
  info(...args) {
    if (currentLevel <= LOG_LEVELS.INFO) {
      console.log(...args);
    }
  },

  /**
   * 警告日志 - 始终显示
   */
  warn(...args) {
    if (currentLevel <= LOG_LEVELS.WARN) {
      console.warn(...args);
    }
  },

  /**
   * 错误日志 - 始终显示
   */
  error(...args) {
    if (currentLevel <= LOG_LEVELS.ERROR) {
      console.error(...args);
    }
  },

  /**
   * 检查是否为调试模式
   */
  isDebug() {
    return currentLevel <= LOG_LEVELS.DEBUG;
  },

  /**
   * 开启调试模式
   */
  enableDebug() {
    localStorage.setItem('DEBUG_MODE', 'true');
    console.log('🔧 调试模式已开启，请刷新页面');
  },

  /**
   * 关闭调试模式
   */
  disableDebug() {
    localStorage.removeItem('DEBUG_MODE');
    console.log('🔧 调试模式已关闭，请刷新页面');
  }
};

// 暴露到全局，方便控制台使用
if (typeof window !== 'undefined') {
  window.logger = logger;
  
  // 调试模式提示
  if (isDebugMode()) {
    console.log('🔧 调试模式已开启 - 使用 logger.disableDebug() 关闭');
  }
}

export default logger;
