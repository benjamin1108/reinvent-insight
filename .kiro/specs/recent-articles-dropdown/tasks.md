# Implementation Plan

- [x] 1. 创建RecentArticlesDropdown组件基础结构
  - 创建组件目录和文件（HTML、JS、CSS、README）
  - 实现组件的基本props和events定义
  - 实现时间格式化工具函数formatRelativeTime
  - _Requirements: 1.1, 2.1, 3.4, 3.5_

- [x] 2. 实现下拉列表UI和样式
  - 编写HTML模板，包含文章列表和空状态
  - 实现科技风格的CSS样式（背景、边框、阴影）
  - 实现文章条目的悬停高亮效果
  - 实现淡入动画效果
  - _Requirements: 2.4, 2.5, 3.4, 3.5, 4.3_

- [x] 3. 实现响应式布局
  - 添加移动端适配样式（最大宽度、触摸目标尺寸）
  - 添加极小屏幕适配样式
  - 测试不同屏幕尺寸下的显示效果
  - _Requirements: 1.3, 5.2, 5.4, 5.5_

- [x] 4. 修改AppHeader组件集成"近期解读"按钮
  - 在AppHeader.html中添加"近期解读"按钮和下拉列表容器
  - 在AppHeader.js中添加状态管理（showRecentDropdown、recentArticles等）
  - 实现鼠标悬停交互逻辑（handleRecentButtonEnter、handleRecentButtonLeave）
  - 添加RecentArticlesDropdown组件依赖
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 5. 实现数据加载和处理逻辑
  - 实现loadRecentArticles方法，调用/api/public/summaries接口
  - 实现数据排序逻辑（按modified_at倒序）
  - 实现数据过滤逻辑（取前10篇）
  - 添加数据缓存机制（5分钟TTL）
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 6. 实现文章点击导航功能
  - 在RecentArticlesDropdown中实现article-click事件
  - 在AppHeader中处理文章点击事件
  - 实现点击后关闭下拉列表
  - 使用hash值构建导航URL（/d/{hash}）
  - _Requirements: 4.1, 4.2, 4.4, 4.5_

- [x] 7. 实现错误处理和边界情况
  - 添加API请求失败的错误处理
  - 添加数据格式异常的验证和过滤
  - 添加时间戳无效的处理
  - 实现空列表状态显示
  - _Requirements: 3.6_

- [x] 8. 实现移动端交互优化
  - 添加移动端点击按钮显示下拉列表的逻辑
  - 添加点击外部区域关闭下拉列表的逻辑
  - 确保触摸目标尺寸符合要求（最小44px）
  - _Requirements: 5.1, 5.3, 5.4_

- [x] 9. 添加可访问性支持
  - 添加ARIA属性（role、aria-label）
  - 实现键盘导航支持（Tab、Enter、Space）
  - 实现焦点管理
  - _Requirements: 1.1, 2.1, 4.1_

- [ ]* 10. 编写组件文档和测试
  - 编写RecentArticlesDropdown的README文档
  - 更新AppHeader的README文档
  - 编写使用示例和注意事项
  - _Requirements: 1.1, 2.1, 3.1_

- [x] 11. 集成测试和调试
  - 测试鼠标悬停交互流程
  - 测试数据加载和显示
  - 测试文章点击导航
  - 测试移动端和桌面端响应式布局
  - 测试错误场景和边界情况
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_
