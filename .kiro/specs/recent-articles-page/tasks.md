# Implementation Plan

- [x] 1. 创建 RecentView 组件基础结构
  - 创建组件文件（JS、HTML、CSS）
  - 定义组件的 props、emits 和依赖
  - 实现基础的模板结构和样式
  - _Requirements: 1.3, 1.4, 5.1, 5.2, 5.3, 5.4_

- [x] 2. 实现 RecentView 组件逻辑
  - 实现文章列表的计算属性（排序和过滤）
  - 实现文章点击事件处理
  - 实现加载状态和空状态显示
  - 集成 RecentTimeline 组件
  - _Requirements: 1.3, 4.1, 4.2, 4.3, 4.4, 5.4, 6.1, 6.2, 6.3, 6.4_

- [x] 3. 修改 HeroSection 组件
  - 移除 recent-timeline 组件依赖
  - 移除 recentArticles 和 recentLoading props
  - 移除 article-click 事件处理
  - 移除时间轴相关的 HTML 和调试代码
  - 更新组件仅在未登录时显示的逻辑
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. 修改 AppHeader 组件
  - 在桌面端导航区添加"最近文章"按钮
  - 在移动端导航区添加"最近文章"按钮
  - 实现导航按钮的激活状态高亮
  - 确保视图切换事件正确触发
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. 修改 app.js 主应用逻辑
- [x] 5.1 清理状态和方法
  - 移除 recentArticles 和 recentLoading 状态变量
  - 移除 loadRecentArticles 方法
  - 从 onMounted 中移除 loadRecentArticles 调用
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 5.2 修改视图路由逻辑
  - 修改 getInitialView 方法，登录后默认返回 'recent'
  - 修改 login 方法，登录成功后设置 currentView 为 'recent'
  - 修改 goHome 方法，根据登录状态决定默认视图
  - 修改 showHeroSection 计算属性，仅在未登录时显示
  - _Requirements: 1.1, 1.2, 3.5_

- [x] 5.3 注册 RecentView 组件
  - 在 components 数组中添加 recent-view 组件注册
  - 确保组件加载顺序正确
  - _Requirements: 5.5_

- [x] 6. 修改 index.html 视图显示逻辑
  - 修改 hero-section 的显示条件为仅未登录时显示
  - 添加 recent-view 的显示区域和条件
  - 确保 recent-view 接收正确的 props
  - 确保 recent-view 的事件绑定正确
  - _Requirements: 1.1, 1.2, 3.5_

- [x] 7. 验证和测试
  - 验证登录后默认显示最近文章页面
  - 验证导航按钮切换功能正常
  - 验证 Hero Section 仅在未登录时显示
  - 验证最近文章页面显示正确的数据
  - 验证文章点击跳转到阅读视图
  - 验证移动端响应式布局正常
  - 验证浏览器前进后退功能正常
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.5, 4.1, 4.2, 4.3, 4.4, 6.1, 6.2, 6.3, 6.4_
