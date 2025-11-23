# 性能优化测试指南

## 快速测试

1. 启动开发服务器
2. 访问 `/test/test-performance-optimization.html`
3. 点击"运行加载测试"按钮
4. 查看性能指标

## 测试指标说明

### 优秀指标（绿色）
- 总加载时间 < 5秒
- 关键组件数 ≤ 3个
- 关键组件占比 ≤ 30%
- 单个组件加载时间 < 2秒

### 警告指标（黄色）
- 总加载时间 5-10秒
- 关键组件数 4-5个
- 关键组件占比 30-50%
- 单个组件加载时间 2-3秒

### 需要优化（红色）
- 总加载时间 > 10秒
- 关键组件数 > 5个
- 关键组件占比 > 50%
- 单个组件加载时间 > 3秒

## 对比测试

### 测试优化前的性能
1. 恢复 `web/js/app.js` 中的组件配置
2. 将所有主要视图组件改为 `critical: true`
3. 运行测试并记录结果

### 测试优化后的性能
1. 使用当前的组件配置（只有2个关键组件）
2. 运行测试并记录结果
3. 对比两次测试的差异

## 真实环境测试

### 本地测试
```bash
# 清除浏览器缓存
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete

# 访问主页
http://localhost:8000/

# 打开开发者工具
# 查看 Network 标签
# 查看 Performance 标签
```

### 慢速网络测试
1. 打开 Chrome DevTools
2. 切换到 Network 标签
3. 选择 "Slow 3G" 或 "Fast 3G"
4. 刷新页面
5. 观察加载时间

### 移动设备测试
1. 使用 Chrome DevTools 的设备模拟
2. 选择移动设备（如 iPhone 12）
3. 启用网络限速
4. 测试加载性能

## 性能监控命令

在浏览器控制台中运行：

```javascript
// 查看性能报告
window.PerformanceMonitor.printReport();

// 查看缓存统计
window.CacheManager.getStats();

// 导出性能数据（JSON格式）
console.log(window.PerformanceMonitor.export('json'));

// 导出性能数据（CSV格式）
console.log(window.PerformanceMonitor.export('csv'));

// 查看所有组件指标
window.PerformanceMonitor.getAllMetrics();

// 查看特定组件指标
window.PerformanceMonitor.getComponentMetrics('app-header');
```

## 预期结果

### 优化前
- 关键组件：6个
- 实际加载：16个组件
- 总加载时间：21.7秒
- 用户可交互：21.7秒后

### 优化后
- 关键组件：2个
- 实际加载：4-6个组件（首屏）
- 总加载时间：3-5秒
- 用户可交互：3-5秒后

### 改进幅度
- 加载时间减少：75-80%
- 首屏组件减少：60-70%
- 用户体验提升：显著

## 故障排查

### 如果加载仍然很慢

1. **检查网络连接**
   - 使用 DevTools Network 标签查看请求
   - 检查是否有失败的请求
   - 查看请求的等待时间（TTFB）

2. **检查服务器性能**
   - 确认服务器响应时间
   - 检查服务器日志
   - 确认没有资源404错误

3. **检查浏览器缓存**
   - 清除浏览器缓存
   - 禁用浏览器扩展
   - 尝试无痕模式

4. **检查组件代码**
   - 查看是否有组件加载失败
   - 检查控制台错误信息
   - 确认所有依赖都正确加载

### 如果出现组件加载失败

1. **检查文件路径**
   - 确认组件文件存在
   - 检查路径配置是否正确

2. **检查超时设置**
   - 如果网络慢，可能需要增加超时时间
   - 临时修改：`timeout: 10000`

3. **查看降级处理**
   - 检查是否使用了占位符组件
   - 查看控制台的降级日志

## 持续监控

建议在生产环境中：

1. 使用 Google Analytics 或类似工具监控页面加载时间
2. 设置性能预算（如：首屏加载 < 3秒）
3. 定期运行性能测试
4. 收集用户反馈

## 联系支持

如有问题，请查看：
- `PERFORMANCE_OPTIMIZATION.md` - 详细优化方案
- `web/js/core/README.md` - 核心模块文档
- 项目 Issues - 提交问题和建议
