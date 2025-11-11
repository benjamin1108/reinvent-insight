# 组件加载系统文档

## 概述

本系统提供了一套完整的Vue组件动态加载解决方案，包括并行加载、缓存管理、性能监控和智能加载策略。

## 核心模块

### 1. CacheManager - 缓存管理器

管理组件的内存缓存，支持TTL和版本控制。

**主要功能：**
- 组件缓存存取
- TTL（生存时间）管理
- 版本控制
- 缓存统计

**使用示例：**

```javascript
// 存储组件
CacheManager.set('my-component', componentDef, {
  ttl: 3600000,  // 1小时
  version: '1.0.0'
});

// 获取组件
const component = CacheManager.get('my-component');

// 检查版本
const isValid = CacheManager.checkVersion('my-component', '1.0.0');

// 获取统计信息
const stats = CacheManager.getStats();
console.log(`缓存命中率: ${(stats.hitRate * 100).toFixed(1)}%`);
```

### 2. PerformanceMonitor - 性能监控器

监控和记录组件加载性能指标。

**主要功能：**
- 计时功能
- 组件加载指标记录
- 性能报告生成
- 性能警告检测

**使用示例：**

```javascript
// 开始计时
PerformanceMonitor.start('my-operation');

// 执行操作...

// 结束计时
const duration = PerformanceMonitor.end('my-operation');

// 记录组件加载
PerformanceMonitor.recordComponentLoad('my-component', {
  loadTime: 123,
  cacheHit: true,
  fileSize: 1024
});

// 获取性能报告
const report = PerformanceMonitor.getReport();
console.log(`平均加载时间: ${report.averageLoadTime.toFixed(2)}ms`);

// 打印报告
PerformanceMonitor.printReport();
```

### 3. ComponentLoader - 组件加载器（增强版）

动态加载Vue组件，支持并行加载、缓存和性能监控。

**主要功能：**
- 单个组件加载
- 并行批量加载
- 自动依赖解析
- 缓存集成
- 性能监控集成
- 降级处理

**使用示例：**

```javascript
// 加载单个组件
const component = await ComponentLoader.loadComponent(
  'my-component',
  '/components/MyComponent',
  'MyComponent',
  {
    useCache: true,
    version: '1.0.0',
    timeout: 10000
  }
);

// 并行加载多个组件
const results = await ComponentLoader.loadComponentsParallel(
  [
    ['comp1', '/components/Comp1', 'Comp1'],
    ['comp2', '/components/Comp2', 'Comp2']
  ],
  {
    maxConcurrent: 6,
    onProgress: (loaded, total, name) => {
      console.log(`加载进度: ${loaded}/${total} - ${name}`);
    }
  }
);

// 批量注册组件
const results = await ComponentLoader.registerComponents(
  app,
  components,
  {
    parallel: true,
    useCache: true,
    onProgress: (loaded, total, name) => {
      console.log(`${loaded}/${total}: ${name}`);
    }
  }
);

// 预加载组件
await ComponentLoader.preloadComponents(components);
```

### 4. LoadingStrategy - 加载策略管理器

实现不同的组件加载策略。

**主要功能：**
- 组件分类（关键/非关键）
- 关键组件优先加载
- 懒加载
- 预测性加载

**使用示例：**

```javascript
// 组件配置
const components = [
  {
    name: 'app-header',
    path: '/components/AppHeader',
    fileName: 'AppHeader',
    critical: true,
    priority: 1
  },
  {
    name: 'footer',
    path: '/components/Footer',
    fileName: 'Footer',
    critical: false,
    priority: 5
  }
];

// 关键组件优先加载
await LoadingStrategy.loadCriticalFirst(app, components, {
  onProgress: (loaded, total, name, phase) => {
    console.log(`[${phase}] ${loaded}/${total}: ${name}`);
  },
  onCriticalComplete: (results) => {
    console.log('关键组件加载完成，可以显示页面了');
  }
});

// 获取策略建议
const recommendation = LoadingStrategy.getStrategyRecommendation(components);
console.log(`建议策略: ${recommendation.strategy}`);
console.log(`原因: ${recommendation.reason}`);
```

## 组件配置格式

### 基础格式（数组）

```javascript
['component-name', '/path/to/component', 'FileName']
```

### 增强格式（对象）

```javascript
{
  name: 'component-name',      // 组件名称
  path: '/path/to/component',  // 组件路径
  fileName: 'FileName',        // 文件名
  critical: true,              // 是否为关键组件
  priority: 1,                 // 优先级（1-10，越小越高）
  version: '1.0.0'            // 版本号
}
```

## 性能优化建议

### 1. 标记关键组件

将首屏必需的组件标记为关键组件：

```javascript
{
  name: 'app-header',
  critical: true,
  priority: 1
}
```

### 2. 使用关键组件优先加载策略

```javascript
await LoadingStrategy.loadCriticalFirst(app, components, {
  onCriticalComplete: () => {
    // 关键组件加载完成，立即显示页面
    showApp();
  }
});
```

### 3. 启用缓存

```javascript
await ComponentLoader.registerComponents(app, components, {
  useCache: true  // 启用缓存
});
```

### 4. 预加载非关键组件

```javascript
// 在空闲时预加载
requestIdleCallback(() => {
  ComponentLoader.preloadComponents(nonCriticalComponents);
});
```

### 5. 监控性能

```javascript
// 启用详细日志（开发环境）
PerformanceMonitor.setVerbose(true);

// 定期检查性能报告
const report = PerformanceMonitor.getReport();
if (report.averageLoadTime > 500) {
  console.warn('组件加载较慢，需要优化');
}
```

## 性能基准

### 目标指标

- **首次加载**: < 3秒
- **缓存加载**: < 1秒
- **缓存命中率**: > 80%
- **单个组件加载**: < 500ms

### 检查性能

```javascript
// 获取性能报告
const report = PerformanceMonitor.getReport();

console.log(`总加载时间: ${report.totalLoadTime.toFixed(2)}ms`);
console.log(`平均加载时间: ${report.averageLoadTime.toFixed(2)}ms`);
console.log(`缓存命中率: ${(report.cacheHitRate * 100).toFixed(1)}%`);

// 检查是否达标
if (report.totalLoadTime < 3000) {
  console.log('✅ 加载时间达标');
} else {
  console.warn('⚠️ 加载时间超标，需要优化');
}
```

## 故障排查

### 组件加载失败

1. 检查网络请求是否成功
2. 查看浏览器控制台错误信息
3. 检查组件文件路径是否正确
4. 查看PerformanceMonitor的错误记录

```javascript
const report = PerformanceMonitor.getReport();
console.log('加载错误:', report.errors);
```

### 缓存问题

1. 清除缓存重试

```javascript
CacheManager.clear();
ComponentLoader.clearCache();
```

2. 检查缓存统计

```javascript
const stats = CacheManager.getStats();
console.log('缓存统计:', stats);
```

### 性能问题

1. 查看最慢的组件

```javascript
const report = PerformanceMonitor.getReport();
console.log('最慢组件:', report.slowestComponent);
```

2. 导出性能报告分析

```javascript
const json = PerformanceMonitor.export('json');
console.log(json);
```

## 开发环境配置

### 启用详细日志

```javascript
PerformanceMonitor.setVerbose(true);
```

### 禁用缓存（便于调试）

```javascript
await ComponentLoader.registerComponents(app, components, {
  useCache: false
});
```

### 查看加载时间线

```javascript
const report = PerformanceMonitor.getReport();
console.table(report.timeline);
```

## 生产环境配置

### 启用缓存

```javascript
await ComponentLoader.registerComponents(app, components, {
  useCache: true,
  timeout: 10000
});
```

### 使用关键组件优先加载

```javascript
await LoadingStrategy.loadCriticalFirst(app, components);
```

### 定期清理过期缓存

缓存管理器会自动每5分钟清理一次过期缓存，无需手动处理。

## API参考

详细的API文档请参考各模块的JSDoc注释。

## 测试

运行性能测试：

```
访问 /test/performance-test.html
```

运行单元测试：

```
访问 /test/cache-manager.test.js
```
