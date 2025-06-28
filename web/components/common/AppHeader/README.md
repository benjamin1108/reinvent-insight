# AppHeader 组件

应用顶部导航栏组件，支持普通页面和阅读页面两种模式，具有完整的科技风格设计和响应式布局。

## 功能特性

- 🔄 **双模式支持**: 普通页面模式与阅读页面模式
- 👤 **认证状态管理**: 根据用户登录状态显示不同功能
- 📱 **响应式设计**: 完美适配桌面端和移动端
- 🎨 **科技风格**: 渐变背景、发光效果、动态交互
- 🧩 **组件化**: 完全独立，样式隔离
- ♿ **无障碍友好**: 支持高对比度和减少动画模式

## 组件结构

```
AppHeader/
├── AppHeader.html      # 组件模板
├── AppHeader.js        # 组件逻辑
├── AppHeader.css       # 组件样式（完全独立）
└── README.md          # 使用说明
```

## 使用方法

### 基础使用

```html
<app-header
  mode="normal"
  :is-authenticated="true"
  current-view="library"
  @home-click="handleHomeClick"
  @view-change="handleViewChange"
  @login-show="handleLoginShow"
  @logout="handleLogout">
</app-header>
```

### 阅读模式

```html
<app-header
  mode="reading"
  :is-authenticated="true"
  :show-toc="true"
  reading-video-url="https://youtube.com/watch?v=xxx"
  :pdf-downloading="false"
  @back-to-library="handleBackToLibrary"
  @open-video="handleOpenVideo"
  @download-pdf="handleDownloadPDF"
  @toggle-toc="handleToggleToc">
</app-header>
```

## Props

### 通用属性

| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|---------|------|
| `mode` | String | `'normal'` | Header模式：`'normal'` 或 `'reading'` |
| `isAuthenticated` | Boolean | `false` | 用户是否已认证 |
| `isShareView` | Boolean | `false` | 是否为分享页面 |
| `currentView` | String | `'home'` | 当前视图标识 |
| `showTestToast` | Boolean | `false` | 是否显示测试Toast按钮（临时） |

### 阅读模式专有属性

| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|---------|------|
| `showToc` | Boolean | `true` | 目录显示状态 |
| `readingVideoUrl` | String | `''` | 视频链接URL |
| `pdfDownloading` | Boolean | `false` | PDF下载状态 |

## Events

### 通用事件

| 事件名 | 参数 | 说明 |
|--------|------|------|
| `home-click` | - | 点击首页/品牌标识 |
| `view-change` | `view: string` | 视图切换 |
| `login-show` | - | 显示登录框 |
| `logout` | - | 用户退出登录 |
| `test-toast` | - | 测试Toast按钮点击 |

### 阅读模式专有事件

| 事件名 | 参数 | 说明 |
|--------|------|------|
| `back-to-library` | - | 返回笔记库 |
| `open-video` | - | 打开视频播放器 |
| `download-pdf` | - | 下载PDF |
| `toggle-toc` | - | 切换目录显示 |

## 功能说明

### 普通页面模式 (mode="normal")

**桌面端功能：**
- 品牌标识（可点击返回首页）
- 主导航按钮：创建深度解读、浏览笔记库
- 认证相关按钮：登录/退出
- 测试Toast按钮（可选）

**移动端适配：**
- 简化导航栏
- 移动端专用登录/退出按钮
- 折叠式导航菜单

### 阅读页面模式 (mode="reading")

**桌面端功能：**
- 品牌标识（可点击返回首页）
- 返回笔记库按钮
- 观看原视频按钮（有视频时显示）
- 下载PDF按钮（支持加载状态）
- 目录切换按钮

**移动端适配：**
- 简化版返回按钮
- 隐藏部分桌面端功能
- 优化触摸交互

## 样式特性

### 科技风格设计
- 渐变背景效果
- 发光边框动画
- 鼠标悬停动效
- 科技感按钮样式

### 响应式布局
- 桌面端：水平布局，完整功能
- 平板端：适配中等屏幕
- 移动端：垂直布局，简化功能
- 极小屏幕：进一步优化空间

### 无障碍支持
- 高对比度模式适配
- 减少动画模式支持
- 键盘导航友好
- 语义化HTML结构

## 开发指南

### 组件注册

```javascript
// 使用ComponentLoader注册
await ComponentLoader.registerComponents(app, [
  ['app-header', '/components/common/AppHeader', 'AppHeader']
]);
```

### 事件处理示例

```javascript
const handleViewChange = (view) => {
  console.log('切换到视图:', view);
  // 更新路由或状态
};

const handleDownloadPDF = () => {
  // 开始下载
  pdfDownloading.value = true;
  
  // 执行下载逻辑
  downloadService.downloadPDF()
    .then(() => {
      console.log('下载完成');
    })
    .finally(() => {
      pdfDownloading.value = false;
    });
};
```

### 状态管理

```javascript
const headerState = reactive({
  mode: 'normal',
  isAuthenticated: false,
  currentView: 'home',
  showToc: true,
  pdfDownloading: false
});

// 切换到阅读模式
const enterReadingMode = () => {
  headerState.mode = 'reading';
  headerState.currentView = 'read';
};
```

## 测试

运行测试页面来验证组件功能：

```bash
# 访问测试页面
http://localhost:8002/test/test-app-header.html
```

测试功能包括：
- 模式切换
- 状态变更
- 事件触发
- 响应式适配
- 交互反馈

## 注意事项

1. **独立样式**: 组件包含完整的CSS样式，无需依赖外部样式表
2. **事件冒泡**: 所有按钮点击都会正确触发对应事件
3. **性能优化**: 使用CSS transform而非改变布局属性来实现动画
4. **浏览器兼容**: 支持现代浏览器，IE11及以上
5. **移动端优化**: 专门针对触摸设备优化交互体验

## 版本历史

### v1.0.0
- 初始版本发布
- 支持普通页面和阅读页面两种模式
- 完整的响应式设计
- 科技风格UI
- 无障碍支持

## 相关组件

- `Toast`: 消息提示组件
- `LoginModal`: 登录模态框
- `VideoPlayer`: 视频播放器
- `TableOfContents`: 目录组件

## 技术支持

如有问题请查看：
1. 组件测试页面的调试信息
2. 浏览器开发者工具控制台
3. 项目文档的ES6模块规范说明 