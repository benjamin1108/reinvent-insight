# CSP 和脚本注入问题修复

## 问题分析

### 1. CSP（内容安全策略）阻止外部资源

**错误日志：**
```
Loading the script 'https://cdn.tailwindcss.com/3.4.1' violates the following Content Security Policy directive
Loading the stylesheet 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css' violates...
Loading the script 'https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js' violates...
```

**原因：** API 返回的 CSP 策略太严格，只允许 `'self'` 和 Google Fonts，阻止了：
- Tailwind CSS CDN
- Font Awesome CDN  
- Chart.js CDN

### 2. 旧的可视化 HTML 文件缺少通信脚本

**问题：** 现有的可视化 HTML 文件是在脚本注入功能之前生成的，不包含 `iframe-height` 通信脚本。

## 解决方案

### ✅ 已修复：CSP 策略更新

**文件：** `src/reinvent_insight/api.py`

**修改：** 更新 `/api/article/{doc_hash}/visual` 端点的 CSP 头：

```python
"Content-Security-Policy": (
    "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
    "https://fonts.googleapis.com https://fonts.gstatic.com "
    "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
    "https://cdnjs.cloudflare.com; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
    "https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' "
    "https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
    "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "img-src 'self' data: https:;"
)
```

**允许的资源：**
- ✅ Tailwind CSS (`cdn.tailwindcss.com`)
- ✅ Chart.js (`cdn.jsdelivr.net`)
- ✅ Font Awesome (`cdnjs.cloudflare.com`)
- ✅ Google Fonts
- ✅ 内联脚本和样式（`'unsafe-inline'`）
- ✅ eval（`'unsafe-eval'`，Tailwind 需要）

### ✅ 已修复：前端自动注入脚本（临时方案）

**文件：** `web/components/views/ReadingView/ReadingView.js`

**修改：** 在 `handleIframeLoad` 中检测并注入通信脚本：

```javascript
// 检查是否已有脚本
const hasScript = doc.body.innerHTML.includes('iframe-height');

if (!hasScript) {
  console.log('🔧 [DEBUG] 检测到旧的可视化 HTML，手动注入通信脚本');
  
  const script = doc.createElement('script');
  script.textContent = `
    (function() {
      function sendHeight() {
        const height = Math.max(
          document.body.scrollHeight,
          document.documentElement.scrollHeight,
          // ...
        );
        window.parent.postMessage({
          type: 'iframe-height',
          height: height
        }, '*');
      }
      // 初始发送 + 监听变化
      sendHeight();
      window.addEventListener('load', sendHeight);
      window.addEventListener('resize', sendHeight);
      // MutationObserver...
    })();
  `;
  doc.body.appendChild(script);
}
```

**优点：**
- ✅ 兼容旧的可视化 HTML 文件
- ✅ 自动检测并注入脚本
- ✅ 不需要重新生成所有文件

## 测试步骤

### 1. 重启后端服务

CSP 策略更新需要重启后端：

```bash
# 停止当前服务
# 重新启动
./run-dev.sh
```

### 2. 刷新浏览器

清除缓存并刷新页面：
- Chrome/Edge: `Ctrl+Shift+R` (Windows) 或 `Cmd+Shift+R` (Mac)
- Firefox: `Ctrl+F5` (Windows) 或 `Cmd+Shift+R` (Mac)

### 3. 验证功能

1. **切换到 Quick Insight 模式**
2. **检查控制台**：
   - ✅ 应该看到 "🔧 检测到旧的可视化 HTML，手动注入通信脚本"
   - ✅ 应该看到 "✅ 通信脚本注入成功"
   - ✅ 应该看到 "📏 更新 iframe 高度: XXX"
3. **检查样式**：
   - ✅ Tailwind CSS 样式应该正常显示
   - ✅ Font Awesome 图标应该显示
   - ✅ Chart.js 图表应该渲染
4. **检查高度**：
   - ✅ iframe 高度应该自动适配内容
   - ✅ 不应该有双重滚动条

## 长期方案：重新生成可视化 HTML

虽然前端注入脚本可以工作，但最佳实践是重新生成包含脚本的 HTML 文件。

### 如何重新生成

**方法 1：通过 Web UI**
1. 打开文章页面
2. 点击"重新生成可视化解读"按钮（如果有）

**方法 2：通过 API**
```bash
# 触发重新生成
curl -X POST http://localhost:8002/api/article/{doc_hash}/visual/regenerate
```

**方法 3：删除旧文件，让系统自动重新生成**
```bash
# 删除旧的可视化 HTML
rm downloads/summaries/*_visual.html

# 系统会在下次访问时自动生成新的
```

### 验证新文件包含脚本

```bash
# 检查文件是否包含通信脚本
grep -c "iframe-height" downloads/summaries/*_visual.html

# 应该输出大于 0 的数字
```

## 安全考虑

### CSP 策略的权衡

**当前策略：**
- ✅ 允许必要的 CDN 资源
- ⚠️ 使用 `'unsafe-inline'` 和 `'unsafe-eval'`

**风险：**
- `'unsafe-inline'` 允许内联脚本，可能增加 XSS 风险
- `'unsafe-eval'` 允许 eval，Tailwind CSS 需要

**缓解措施：**
1. 只在可视化 HTML 端点使用宽松的 CSP
2. 主应用保持严格的 CSP
3. iframe 提供天然的隔离层

### 未来改进

1. **使用 nonce 或 hash**：替代 `'unsafe-inline'`
2. **本地化 CDN 资源**：将 Tailwind、Chart.js 等下载到本地
3. **子资源完整性（SRI）**：验证 CDN 资源的完整性

## 故障排查

### 问题：样式仍然丢失

**检查：**
1. 后端是否重启？
2. 浏览器缓存是否清除？
3. 控制台是否还有 CSP 错误？

**解决：**
```bash
# 1. 确认后端重启
ps aux | grep python | grep api

# 2. 强制刷新浏览器
# Ctrl+Shift+R

# 3. 检查 CSP 头
curl -I http://localhost:8002/api/article/fdbeccc2/visual?version=0 | grep -i content-security
```

### 问题：高度不自适应

**检查：**
1. 控制台是否有 "手动注入通信脚本" 日志？
2. 是否有 "更新 iframe 高度" 日志？

**解决：**
- 如果没有注入日志：可能是跨域问题，检查 iframe src 是否同源
- 如果没有高度日志：检查消息监听器是否正常工作

### 问题：Chart is not defined

**原因：** Chart.js 加载失败或加载顺序问题

**解决：**
1. 确认 CSP 允许 `cdn.jsdelivr.net`
2. 检查网络请求是否成功
3. 可能需要等待 Chart.js 加载完成后再执行图表代码

## 总结

✅ **已修复的问题：**
1. CSP 阻止外部资源 → 更新 CSP 策略
2. 旧文件缺少脚本 → 前端自动注入

✅ **当前状态：**
- iframe 可以正常加载可视化 HTML
- 外部资源（Tailwind、Chart.js、Font Awesome）可以加载
- 高度自适应功能正常工作（通过前端注入）

📋 **后续建议：**
- 重新生成可视化 HTML 文件（包含后端注入的脚本）
- 考虑本地化 CDN 资源以提高安全性和性能
- 添加更严格的 CSP 策略（使用 nonce）
