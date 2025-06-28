/**
 * 事件总线
 * 用于组件间的事件通信
 */
class EventBus {
  constructor() {
    this.events = new Map();
  }
  
  /**
   * 监听事件
   * @param {string} event - 事件名称
   * @param {Function} handler - 事件处理函数
   * @returns {Function} - 取消监听的函数
   */
  on(event, handler) {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }
    
    this.events.get(event).add(handler);
    
    // 返回取消监听的函数
    return () => this.off(event, handler);
  }
  
  /**
   * 监听一次性事件
   * @param {string} event - 事件名称
   * @param {Function} handler - 事件处理函数
   */
  once(event, handler) {
    const wrapper = (...args) => {
      handler(...args);
      this.off(event, wrapper);
    };
    
    this.on(event, wrapper);
  }
  
  /**
   * 触发事件
   * @param {string} event - 事件名称
   * @param {...any} args - 事件参数
   */
  emit(event, ...args) {
    if (!this.events.has(event)) {
      return;
    }
    
    const handlers = this.events.get(event);
    handlers.forEach(handler => {
      try {
        handler(...args);
      } catch (error) {
        console.error(`Error in event handler for "${event}":`, error);
      }
    });
  }
  
  /**
   * 取消监听事件
   * @param {string} event - 事件名称
   * @param {Function} handler - 要取消的处理函数
   */
  off(event, handler) {
    if (!this.events.has(event)) {
      return;
    }
    
    const handlers = this.events.get(event);
    handlers.delete(handler);
    
    // 如果没有处理函数了，删除事件
    if (handlers.size === 0) {
      this.events.delete(event);
    }
  }
  
  /**
   * 清空所有事件监听
   */
  clear() {
    this.events.clear();
  }
}

// 创建全局事件总线实例
const eventBus = new EventBus();
window.eventBus = eventBus;

// ES6 模块导出
export default eventBus; 