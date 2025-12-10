/**
 * LoadingStrategy - 组件加载策略管理器
 * 实现不同的加载策略（关键组件优先、懒加载等）
 */
class LoadingStrategy {
  /**
   * 分类组件为关键和非关键
   * @param {Array} components - 组件配置数组
   * @returns {Object} { critical: [], nonCritical: [] }
   */
  static categorizeComponents(components) {
    const critical = [];
    const nonCritical = [];

    for (const config of components) {
      // 支持两种配置格式
      const componentConfig = Array.isArray(config)
        ? { name: config[0], path: config[1], fileName: config[2] }
        : config;

      // 检查是否为关键组件
      const isCritical = componentConfig.critical === true ||
        componentConfig.priority <= 3; // 优先级1-3视为关键

      if (isCritical) {
        critical.push(config);
      } else {
        nonCritical.push(config);
      }
    }

    // 按优先级排序
    const sortByPriority = (a, b) => {
      const priorityA = Array.isArray(a) ? (a[3]?.priority || 10) : (a.priority || 10);
      const priorityB = Array.isArray(b) ? (b[3]?.priority || 10) : (b.priority || 10);
      return priorityA - priorityB;
    };

    critical.sort(sortByPriority);
    nonCritical.sort(sortByPriority);

    return { critical, nonCritical };
  }

  /**
   * 关键组件优先加载策略
   * @param {Object} app - Vue应用实例
   * @param {Array} components - 组件配置数组
   * @param {Object} options - 加载选项
   * @returns {Promise<Array>}
   */
  static async loadCriticalFirst(app, components, options = {}) {
    const {
      onProgress = null,
      onCriticalComplete = null,
      useCache = true,
      timeout = 10000
    } = options;


    // 分类组件
    const { critical, nonCritical } = this.categorizeComponents(components);


    const allResults = [];

    // 第一阶段：并行加载所有关键组件
    if (critical.length > 0) {

      const criticalResults = await window.ComponentLoader.registerComponents(
        app,
        critical,
        {
          parallel: true,
          useCache,
          timeout,
          onProgress: (loaded, total, name) => {
            if (onProgress) {
              onProgress(loaded, critical.length + nonCritical.length, name, 'critical');
            }
          }
        }
      );

      allResults.push(...criticalResults);


      // 通知关键组件加载完成
      if (onCriticalComplete) {
        onCriticalComplete(criticalResults);
      }
    }

    // 第二阶段：后台加载非关键组件
    if (nonCritical.length > 0) {

      // 使用requestIdleCallback在空闲时加载
      if (window.requestIdleCallback) {
        await new Promise(resolve => {
          window.requestIdleCallback(async () => {
            const nonCriticalResults = await window.ComponentLoader.registerComponents(
              app,
              nonCritical,
              {
                parallel: true,
                useCache,
                timeout,
                onProgress: (loaded, total, name) => {
                  if (onProgress) {
                    onProgress(
                      critical.length + loaded,
                      critical.length + nonCritical.length,
                      name,
                      'non-critical'
                    );
                  }
                }
              }
            );

            allResults.push(...nonCriticalResults);


            resolve();
          });
        });
      } else {
        // 降级：直接加载
        const nonCriticalResults = await window.ComponentLoader.registerComponents(
          app,
          nonCritical,
          {
            parallel: true,
            useCache,
            timeout,
            onProgress: (loaded, total, name) => {
              if (onProgress) {
                onProgress(
                  critical.length + loaded,
                  critical.length + nonCritical.length,
                  name,
                  'non-critical'
                );
              }
            }
          }
        );

        allResults.push(...nonCriticalResults);

      }
    }

    return allResults;
  }

  /**
   * 懒加载策略
   * @param {Object} app - Vue应用实例
   * @param {Array} components - 组件配置数组
   * @param {Object} options - 加载选项
   * @returns {Promise<Array>}
   */
  static async loadLazy(app, components, options = {}) {
    const {
      onProgress = null,
      useCache = true,
      timeout = 10000,
      delay = 1000 // 延迟加载时间
    } = options;


    // 延迟加载
    await new Promise(resolve => setTimeout(resolve, delay));

    return await window.ComponentLoader.registerComponents(app, components, {
      parallel: true,
      useCache,
      timeout,
      onProgress
    });
  }

  /**
   * 预测性加载策略（基于用户行为）
   * @param {Object} app - Vue应用实例
   * @param {Array} components - 组件配置数组
   * @param {Object} context - 上下文信息
   * @returns {Promise<Array>}
   */
  static async loadPredictive(app, components, context = {}) {
    const {
      currentView = 'library',
      isAuthenticated = false,
      onProgress = null
    } = context;


    // 根据当前视图预测需要的组件
    const predictions = this._predictComponents(currentView, isAuthenticated);

    // 过滤出预测需要的组件
    const predictedComponents = components.filter(config => {
      const name = Array.isArray(config) ? config[0] : config.name;
      return predictions.includes(name);
    });

    if (predictedComponents.length > 0) {

      // 预加载预测的组件
      await window.ComponentLoader.preloadComponents(predictedComponents, {
        useCache: true,
        timeout: 10000
      });
    }

    // 加载所有组件
    return await window.ComponentLoader.registerComponents(app, components, {
      parallel: true,
      useCache: true,
      onProgress
    });
  }

  /**
   * 预测需要的组件
   * @private
   */
  static _predictComponents(currentView, isAuthenticated) {
    const predictions = [];

    // 基础组件总是需要
    predictions.push('app-header', 'toast-container');

    // 根据视图预测
    switch (currentView) {
      case 'library':
        predictions.push('library-view', 'hero-section');
        break;
      case 'recent':
        predictions.push('recent-view');
        break;
      case 'read':
        predictions.push('reading-view', 'video-player');
        break;
      case 'create':
        if (isAuthenticated) {
          predictions.push('create-view');
        }
        break;
    }

    // 认证相关
    if (!isAuthenticated) {
      predictions.push('login-modal');
    }

    return predictions;
  }

  /**
   * 获取加载策略建议
   * @param {Array} components - 组件配置数组
   * @returns {Object} 策略建议
   */
  static getStrategyRecommendation(components) {
    const { critical, nonCritical } = this.categorizeComponents(components);

    const totalComponents = components.length;
    const criticalRatio = critical.length / totalComponents;

    let recommendedStrategy = 'parallel';
    let reason = '所有组件同等重要，建议并行加载';

    if (criticalRatio > 0 && criticalRatio < 1) {
      recommendedStrategy = 'critical-first';
      reason = `有 ${critical.length} 个关键组件和 ${nonCritical.length} 个非关键组件，建议关键组件优先加载`;
    } else if (totalComponents > 10) {
      recommendedStrategy = 'critical-first';
      reason = `组件数量较多 (${totalComponents} 个)，建议关键组件优先加载以提升首屏速度`;
    }

    return {
      strategy: recommendedStrategy,
      reason,
      critical: critical.length,
      nonCritical: nonCritical.length,
      total: totalComponents
    };
  }
}

// 导出到全局
window.LoadingStrategy = LoadingStrategy;
