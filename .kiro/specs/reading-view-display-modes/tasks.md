# Implementation Plan

- [x] 1. 创建 ModeSelector 组件
  - 创建 ModeSelector.js、ModeSelector.html 和 ModeSelector.css 文件
  - 实现模式选择器的基本结构，包含三个按钮（核心要点、精简摘要、完整解读）
  - 添加 props 定义（currentMode, modes）和 emits 定义（mode-change）
  - 实现按钮点击事件处理，触发 mode-change 事件
  - 添加激活状态的视觉样式（渐变色底部边框 + 高亮文字）
  - 实现响应式布局，移动端使用图标 + 缩写文字
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1_

- [x] 2. 创建 CoreSummaryView 占位组件
  - 创建 CoreSummaryView.js、CoreSummaryView.html 和 CoreSummaryView.css 文件
  - 实现占位内容的卡片式布局
  - 添加 props 定义（summaryData），并在注释中说明预期的数据结构
  - 显示"核心要点功能即将推出"的友好提示信息
  - 使用主题色渐变背景和图标装饰
  - 确保样式与现有设计风格一致
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 6.4_

- [x] 3. 创建 SimplifiedTextView 占位组件
  - 创建 SimplifiedTextView.js、SimplifiedTextView.html 和 SimplifiedTextView.css 文件
  - 实现简洁的文本布局
  - 添加 props 定义（simplifiedContent），并在注释中说明预期的数据格式
  - 显示"精简摘要功能即将推出"的友好提示信息
  - 使用较大字体（18px）和宽松行距（1.8）
  - 限制最大宽度（800px）以提升可读性
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 6.4_

- [x] 4. 更新 ReadingView 组件集成模式切换
  - [x] 4.1 在 ReadingView.js 中添加新的 props（coreSummary, simplifiedText, initialDisplayMode）
    - 添加 props 定义并设置默认值
    - 在注释中说明后端数据结构的预期格式
    - _Requirements: 6.2, 6.5_
  
  - [x] 4.2 在 ReadingView.js 中添加状态管理
    - 创建 displayMode 响应式状态，默认值为 'full-analysis'
    - 创建 shouldShowToc 计算属性，根据 displayMode 决定是否显示目录
    - 添加 handleDisplayModeChange 方法处理模式切换
    - 添加 mode-change emit 事件定义
    - _Requirements: 2.3, 2.4, 3.5, 4.5, 5.3, 6.3_
  
  - [x] 4.3 在 ReadingView.js 中注册新组件依赖
    - 在 dependencies 数组中添加 ModeSelector、CoreSummaryView 和 SimplifiedTextView
    - 确保组件路径正确
    - _Requirements: 6.1_
  
  - [x] 4.4 更新 ReadingView.html 模板
    - 在文章标题上方添加 ModeSelector 组件
    - 使用 v-if 条件渲染三种内容视图（CoreSummaryView, SimplifiedTextView, FullAnalysisView）
    - 根据 shouldShowToc 控制目录侧边栏的显示/隐藏
    - 为内容切换添加 Vue transition 组件实现过渡动画
    - _Requirements: 1.1, 2.2, 2.3, 3.5, 4.5, 5.1, 5.2, 5.3_
  
  - [x] 4.5 更新 ReadingView.css 样式
    - 添加模式选择器的容器样式
    - 添加内容切换的过渡动画样式（fade + transform）
    - 调整布局以适应新的模式选择器
    - 确保移动端响应式布局正常
    - 添加 prefers-reduced-motion 媒体查询以支持降级动画
    - _Requirements: 1.4, 1.5, 2.2, 7.1, 7.2, 7.4, 7.5_

- [x] 5. 更新 app.js 集成新功能
  - 在 ReadingView 的数据对象中添加 displayMode、coreSummary 和 simplifiedText 字段
  - 添加 handleDisplayModeChange 方法处理模式切换事件
  - 在方法中添加注释说明后续如何触发后端数据加载
  - 确保现有的 ReadingView 功能（版本选择、目录滚动等）不受影响
  - _Requirements: 5.1, 5.2, 5.4, 6.3_

- [x] 6. 添加错误处理和用户反馈
  - 在 ReadingView.js 的 handleDisplayModeChange 方法中添加 try-catch 错误处理
  - 模式切换失败时保持当前模式不变
  - 使用 Toast 组件显示错误提示信息
  - 在控制台记录错误日志
  - _Requirements: 2.5_

- [x] 7. 测试和验证
  - [x] 7.1 手动测试三种模式的切换流畅性
    - 测试每种模式的切换是否正常工作
    - 验证过渡动画是否平滑
    - 确认模式状态在切换后正确保持
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 7.1, 7.2, 7.3_
  
  - [x] 7.2 测试目录侧边栏的显示/隐藏逻辑
    - 验证"完整解读"模式下目录正常显示
    - 验证"核心要点"和"精简摘要"模式下目录正确隐藏
    - 测试目录的所有现有功能（滚动高亮、点击跳转等）
    - _Requirements: 3.5, 4.5, 5.3_
  
  - [x] 7.3 测试移动端响应式布局
    - 在不同屏幕尺寸下测试模式选择器的显示
    - 验证移动端使用图标 + 缩写文字
    - 测试触摸交互的响应性
    - _Requirements: 1.5_
  
  - [x] 7.4 测试浏览器兼容性
    - 在 Chrome、Firefox、Safari 和 Edge 中测试
    - 验证 CSS 过渡动画在各浏览器中的表现
    - 测试降级方案（prefers-reduced-motion）
    - _Requirements: 7.4, 7.5_
  
  - [x] 7.5 测试与现有功能的兼容性
    - 验证版本选择器功能正常
    - 测试文章内锚点链接跳转
    - 确认滚动高亮功能不受影响
    - 测试键盘快捷键（Ctrl+T 切换目录）
    - _Requirements: 5.2_

- [x] 8. 代码优化和文档
  - 添加代码注释说明各组件的职责和用法
  - 在关键位置添加 TODO 注释标记后续需要添加后端逻辑的地方
  - 确保代码符合现有的代码风格和命名规范
  - 验证所有文件的导入路径正确
  - _Requirements: 6.1, 6.5_
