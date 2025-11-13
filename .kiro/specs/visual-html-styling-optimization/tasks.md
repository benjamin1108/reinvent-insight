# Implementation Plan

- [x] 1. 更新 text2html.txt 提示词 - 配色方案规范
  - 在提示词中添加"配色方案规范"章节，明确指定主题色（#22d3ee, #3b82f6, #8b5cf6）
  - 定义深色模式的背景色、文本色、边框色等完整配色规范
  - 定义浅色模式的配色规范
  - 添加对比度要求（WCAG AA标准，至少4.5:1）
  - 添加"禁止使用的颜色"列表，防止AI使用其他配色方案
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. 更新 text2html.txt 提示词 - CDN资源优化
  - 将Font Awesome CDN替换为字节跳动CDN（lf3-cdn-tos.bytecdntp.com）
  - 将Tailwind CSS CDN替换为字节跳动CDN（lf6-cdn-tos.bytecdntp.com）
  - 移除Google Fonts链接，改为使用系统字体栈
  - 定义正文字体栈：'Inter', 'PingFang SC', 'SF Pro Text', 'Hiragino Sans GB', 'Microsoft YaHei', 'Segoe UI', sans-serif
  - 定义标题字体栈：'Outfit', 'PingFang SC', 'SF Pro Display', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif
  - 定义代码字体栈：'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', 'SFMono-Regular', Menlo, monospace
  - 添加备用CDN方案（bootcdn.net, unpkg.com）
  - _Requirements: 2.1, 2.2, 2.3_


- [x] 3. 更新 text2html.txt 提示词 - 降级策略和模式切换
  - 添加CDN降级策略说明，要求AI实现onerror fallback
  - 要求关键样式内联到HTML中，确保无网络时也能显示
  - 添加深色/浅色模式切换实现规范
  - 要求默认跟随系统设置（prefers-color-scheme）
  - 要求提供手动切换按钮，状态保存到localStorage
  - 要求切换时使用平滑过渡动画（transition: all 0.3s ease）
  - _Requirements: 2.4, 2.5_

- [ ] 4. 生成测试HTML并验证配色方案
  - 选择2-3篇现有的深度解读文章
  - 使用更新后的提示词重新生成可视化HTML
  - 在浏览器中打开生成的HTML，视觉检查配色是否使用了指定的主题色
  - 检查HTML源码，确认颜色代码是否为#22d3ee, #3b82f6, #8b5cf6
  - 使用对比度检查工具验证文本对比度是否≥4.5:1
  - 测试深色/浅色模式切换功能是否正常
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 5. 验证CDN资源加载和降级功能
  - 在浏览器开发者工具中检查Network面板，确认所有外部资源使用了国内CDN
  - 确认没有加载Google Fonts
  - 测试CDN加载速度，确保在中国大陆网络环境下快速加载
  - 使用开发者工具阻止外部资源加载，测试降级功能
  - 确认在无网络情况下，页面仍能通过内联样式正常显示
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 6. 跨浏览器和响应式测试
  - 在Chrome/Edge中测试生成的HTML显示效果
  - 在Firefox中测试显示效果
  - 在移动端浏览器（Chrome Mobile）中测试响应式布局
  - 确认在不同浏览器中配色、字体渲染、主题切换功能一致
  - _Requirements: 1.5, 2.3_

- [ ] 7. 文档更新和使用说明
  - 更新相关文档，说明新的配色规范和CDN策略
  - 记录提示词修改的详细内容
  - 提供重新生成旧文章可视化版本的操作指南
  - _Requirements: 1.1, 2.1_
