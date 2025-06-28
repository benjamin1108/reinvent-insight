# 组件单元测试系统

## 概述

这是 reinvent-insight 项目的全新组件单元测试系统，为每个前端组件提供独立的测试环境。

## 测试框架特点

1. **统一的测试模板** - 提供标准化的测试页面结构
2. **独立的测试环境** - 每个组件都有独立的测试页面
3. **交互式测试** - 支持实时交互和状态控制
4. **事件日志** - 记录组件事件和测试操作
5. **响应式设计** - 测试页面适配各种屏幕尺寸

## 已完成的测试

### 基础组件 (Shared)
- ✅ **TechButton** - `/test/test-tech-button.html`
  - 变体测试（primary, secondary, success, warning, danger）
  - 尺寸测试（sm, normal, lg）
  - 状态测试（loading, disabled）
  - 图标测试
  - 事件响应测试
  - 综合样式测试

- ✅ **ProgressBar** - `/test/test-progress-bar.html`
  - 基础进度条测试
  - 颜色变体测试
  - 条纹和动画效果
  - 尺寸和圆角测试
  - 动态进度模拟

- ✅ **VersionSelector** - `/test/test-version-selector.html`
  - 基础功能测试
  - 自定义版本列表
  - 禁用状态测试
  - 大量版本性能测试
  - 事件日志

### 通用组件 (Common)
- ✅ **LoginModal** - `/test/test-login-modal.html`
  - 基础功能测试
  - 错误处理测试
  - 响应式布局测试
  - 表单验证测试
  - 事件日志

- ✅ **Toast** - `/test/test-toast.html`
  - 基础类型测试（success, error, warning, info）
  - 自定义配置测试
  - 批量显示测试
  - 长文本测试
  - 持久化Toast测试

- ✅ **Filter** - `/test/test-filter.html`
  - 基础筛选功能
  - 实际筛选效果演示
  - 禁用状态测试
  - 动态年份列表
  - 事件日志

- ✅ **AppHeader** - `/test/test-app-header.html`
  - 未登录/已登录状态
  - 动态交互测试
  - 响应式布局测试
  - 侧边栏切换
  - 事件日志

- ✅ **SummaryCard** - `/test/test-summary-card.html`
  - 基础类型展示（reinvent/featured）
  - 动态内容控制
  - 多卡片布局测试
  - 事件处理
  - 动态添加/删除卡片

- ✅ **TableOfContents** - `/test/test-table-of-contents.html`
  - 基础功能测试
  - 动态内容管理
  - 滚动监听测试
  - 展开/折叠功能
  - 多级目录支持

- ✅ **VideoPlayer** - `/test/test-video-player.html`
  - 基础播放器功能
  - 自定义配置测试
  - 多播放器同步测试
  - API控制测试
  - 事件监听

### 视图组件 (Views)
- ✅ **CreateView** - `/test/test-create-view.html`
  - 基础渲染测试
  - 分析过程模拟
  - 错误状态测试
  - 事件处理测试

- ✅ **HeroSection** - `/test/test-hero-section.html`
  - 未登录/已登录状态
  - 动态状态切换
  - 模拟登录流程
  - 事件日志

- ✅ **LibraryView** - `/test/test-library-view.html`
  - 基础功能测试
  - 动态数据管理
  - 性能测试（大量数据）
  - 筛选和搜索功能
  - 示例数据加载

- ✅ **ReadingView** - `/test/test-reading-view.html`
  - 文章阅读界面
  - 目录导航功能
  - 版本切换功能
  - 响应式布局
  - 完整阅读体验

## 测试页面结构

每个测试页面都包含：

```html
<!-- 标准测试页面结构 -->
<div class="test-header">
  <!-- 组件名称和描述 -->
</div>

<div class="test-container">
  <!-- 测试用例1 -->
  <div class="test-case">
    <div class="test-case-header">
      <h2 class="test-case-title">测试用例名称</h2>
    </div>
    
    <div class="test-controls">
      <!-- 交互控制 -->
    </div>
    
    <div class="component-display">
      <!-- 组件实例 -->
    </div>
    
    <div class="test-output">
      <!-- 测试结果/日志 -->
    </div>
  </div>
  
  <!-- 更多测试用例... -->
</div>
```

## 如何创建新测试

1. 复制 `test-template.html` 文件
2. 修改组件信息和测试用例
3. 在组件加载部分注册要测试的组件
4. 实现具体的测试逻辑
5. 更新 `index.html` 添加测试链接

## 测试命名规范

- 测试文件命名：`test-[component-name].html`
- 组件名使用 kebab-case
- 测试用例按功能分组

## CSS 独立性

所有测试页面遵循以下CSS规范：
- 不引入旧的全局样式文件（如 `/css/style.css`）
- 只引入必要的基础样式（typography.css, effects.css, content.css）
- 测试页面专用样式使用内联 `<style>` 标签
- 组件样式由 ComponentLoader 自动加载

## 运行测试

1. 启动开发服务器（如果尚未运行）
2. 访问 `http://localhost:8002/test/`
3. 选择要测试的组件
4. 进行交互式测试

## 所有组件测试已完成！✅

### 新增完成的测试组件：
- ✅ **VersionSelector** - 版本选择器测试
- ✅ **AppHeader** - 应用头部测试
- ✅ **VideoPlayer** - 视频播放器测试
- ✅ **TableOfContents** - 目录组件测试
- ✅ **SummaryCard** - 摘要卡片测试
- ✅ **LibraryView** - 文档库视图测试
- ✅ **ReadingView** - 阅读视图测试
- ✅ **HeroSection** - 首页英雄区测试

**测试覆盖率：100%** - 所有核心组件均已创建完整的单元测试！

## 注意事项

1. **Toast组件** 是新增功能，原项目中没有对应的UI实现
2. 所有测试页面都应该是独立的，不依赖外部状态
3. 测试应该涵盖组件的所有主要功能和边界情况
4. 保持测试代码的清晰和可维护性 