# Implementation Plan

- [x] 1. 创建 VisualInterpretationWorker 后端组件
  - 创建 `src/reinvent_insight/visual_worker.py` 文件
  - 实现 `VisualInterpretationWorker` 类，包含初始化方法和版本号提取
  - 实现 `_load_text2html_prompt()` 方法，读取 `prompt/text2html.txt` 文件
  - 实现 `_read_article_content()` 方法，读取深度解读并移除 YAML front matter
  - 实现 `_build_prompt()` 方法，组合 text2html 提示词和文章内容
  - 实现 `_generate_html()` 方法，调用 Gemini API 生成 HTML，包含重试逻辑（最多3次，指数退避）
  - 实现 `_validate_html()` 方法，验证生成的 HTML 包含必要标签（html, head, style, body）
  - 实现 `_save_html()` 方法，保存 HTML 文件并保持与深度解读相同的版本号
  - 实现 `_update_article_metadata()` 方法，更新文章 YAML front matter 中的可视化状态
  - 实现 `run()` 主方法，协调整个生成流程并处理错误
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.4, 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 2. 创建 VisualInterpretationWatcher 文件监测组件
  - 创建 `src/reinvent_insight/visual_watcher.py` 文件
  - 实现 `VisualInterpretationWatcher` 类，初始化监测目录和模型配置
  - 实现 `_load_processed_files()` 方法，从 `.visual_processed.json` 加载已处理文件列表
  - 实现 `_save_processed_files()` 方法，持久化已处理文件列表
  - 实现 `start_watching()` 方法，每30秒检查一次新文件或版本更新
  - 实现 `_check_new_files()` 方法，扫描目录中的所有 .md 文件
  - 实现 `_get_file_key()` 方法，生成文件唯一标识（包含修改时间）
  - 实现 `_should_generate_visual()` 方法，判断是否需要生成可视化（检查文件是否已处理、HTML是否存在、版本是否匹配）
  - 实现 `_get_visual_html_path()` 方法，根据 .md 文件名生成对应的 _visual.html 路径
  - 实现 `_extract_version()` 方法，从文件名中提取版本号
  - 实现 `_trigger_visual_generation()` 方法，创建并启动 VisualInterpretationWorker 任务
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.4, 3.5_

- [x] 3. 集成到 DeepSummaryWorkflow
  - 修改 `src/reinvent_insight/workflow.py` 文件
  - 在 `DeepSummaryWorkflow` 类中添加 `_start_visual_interpretation_task()` 方法
  - 在 `_assemble_final_report()` 方法末尾调用 `_start_visual_interpretation_task()`
  - 传递正确的参数：文章路径、版本号、模型名称
  - 确保可视化生成任务失败不影响深度解读的正常完成
  - 添加日志记录可视化任务的启动状态
  - _Requirements: 1.1, 1.2, 1.3, 3.4, 9.1, 9.2, 9.4_

- [x] 4. 启动文件监测器
  - 修改 `src/reinvent_insight/main.py` 或应用入口文件
  - 创建 `start_visual_watcher()` 异步函数
  - 检查 `config.VISUAL_INTERPRETATION_ENABLED` 配置开关
  - 初始化 `VisualInterpretationWatcher` 实例
  - 使用 `asyncio.create_task()` 在后台运行监测器
  - 在应用启动时调用 `start_visual_watcher()`
  - 添加日志记录监测器的启动状态
  - _Requirements: 1.1, 1.2, 9.5_

- [x] 5. 添加后端 API 端点
  - 修改 `src/reinvent_insight/api.py` 文件
  - 实现 `GET /api/article/{doc_hash}/visual` 端点，返回可视化 HTML 内容
  - 支持可选的 `version` 查询参数，根据版本号返回对应的可视化 HTML
  - 从 `hash_to_filename` 和 `hash_to_versions` 获取正确的文件名
  - 设置正确的响应头：Content-Type 为 text/html，Cache-Control，CSP
  - 实现 `GET /api/article/{doc_hash}/visual/status` 端点，返回可视化生成状态
  - 支持可选的 `version` 查询参数，返回指定版本的状态
  - 解析文章 YAML front matter 获取 visual_interpretation 信息
  - 返回状态信息：status, file, generated_at, version
  - 添加错误处理：404（文章未找到、版本未找到、HTML未生成）、500（服务器错误）
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 6. 添加配置选项
  - 修改 `src/reinvent_insight/config.py` 文件
  - 添加 `VISUAL_INTERPRETATION_ENABLED` 配置项（从环境变量读取，默认 true）
  - 添加 `TEXT2HTML_PROMPT_PATH` 配置项，指向 `prompt/text2html.txt`
  - 添加 `VISUAL_HTML_DIR` 配置项（默认与 OUTPUT_DIR 相同）
  - 确保配置项有合理的默认值和注释说明
  - _Requirements: 9.3, 9.5_

- [x] 7. 创建 ModeToggle 前端组件
  - 创建 `web/components/shared/ModeToggle/` 目录
  - 创建 `ModeToggle.js` 文件，定义组件逻辑
  - 定义 props：currentMode, visualAvailable, visualStatus
  - 定义 emits：mode-change
  - 定义 modes 数据：Deep Insight 和 Quick Insight
  - 实现 `isQuickModeDisabled` 计算属性，根据可视化状态禁用 Quick Insight
  - 实现 `quickModeTooltip` 计算属性，显示不同状态的提示信息
  - 实现 `handleModeChange()` 方法，触发 mode-change 事件
  - 创建 `ModeToggle.html` 模板文件
  - 创建 `ModeToggle.css` 样式文件，实现 Tab 风格的按钮组
  - 添加激活状态样式、禁用状态样式、Hover 效果
  - 实现响应式布局，移动端适配
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8. 更新 ReadingView 组件
  - [x] 8.1 添加状态管理
    - 修改 `web/components/views/ReadingView/ReadingView.js` 文件
    - 在 data() 中添加新字段：displayMode, visualAvailable, visualStatus, visualHtmlUrl, isFullscreen, currentVersion
    - 添加 shouldShowToc 计算属性，Deep Insight 模式显示目录
    - 添加 shouldShowFullscreenExit 计算属性，Quick Insight 全屏模式显示退出按钮
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 6.1, 6.4_
  
  - [x] 8.2 实现模式切换逻辑
    - 实现 `checkVisualStatus()` 方法，检查当前版本的可视化状态
    - 实现 `handleModeChange()` 方法，处理 Deep/Quick Insight 切换
    - 实现 `handleVersionChange()` 方法，同步切换可视化版本
    - 切换到 Quick Insight 时自动进入全屏（桌面端）
    - 切换到 Deep Insight 时自动退出全屏
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1_
  
  - [x] 8.3 实现全屏控制
    - 实现 `enterFullscreen()` 方法，使用 Fullscreen API 进入全屏
    - 实现 `exitFullscreen()` 方法，退出全屏模式
    - 实现 `handleFullscreenChange()` 方法，监听全屏状态变化
    - 实现 `handleEscapeKey()` 方法，处理 ESC 键退出全屏
    - 检测浏览器是否支持全屏 API，不支持时降级处理
    - 移动设备不自动进入全屏
    - _Requirements: 6.1, 6.2, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 8.4 更新模板和样式
    - 修改 `web/components/views/ReadingView/ReadingView.html` 模板
    - 在文章标题上方添加 ModeToggle 组件
    - 使用 v-if 条件渲染 Deep Insight 和 Quick Insight 视图
    - Quick Insight 使用 iframe 渲染可视化 HTML
    - 添加全屏退出按钮（仅在全屏模式显示）
    - 根据 shouldShowToc 控制目录侧边栏显示/隐藏
    - 修改 `web/components/views/ReadingView/ReadingView.css` 样式
    - 添加全屏容器样式
    - 添加 iframe 样式（全宽、全高、无边框）
    - 添加退出按钮样式（右上角、明显可见）
    - 添加模式切换的过渡动画
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.2, 6.3, 6.4, 7.2_

- [x] 9. 集成到 app.js
  - 修改 `web/js/app.js` 文件
  - 在 ReadingView 的数据中添加新字段：displayMode, visualAvailable, visualStatus, currentVersion
  - 实现 `handleDisplayModeChange()` 方法，处理模式切换事件
  - 实现 `handleVersionChange()` 方法，同步更新可视化版本
  - 在文章加载时调用 `checkVisualStatus()`
  - 监听 SSE 消息，接收可视化生成完成通知
  - 确保现有功能不受影响（版本选择、目录滚动等）
  - _Requirements: 4.1, 4.2, 5.1, 5.2, 8.1, 8.2, 8.3_

- [x] 10. 添加事件监听和生命周期管理
  - 在 ReadingView 的 mounted() 钩子中添加事件监听
  - 监听 fullscreenchange 事件
  - 监听 keydown 事件（ESC 键）
  - 监听 SSE 的 visual-generation-complete 事件
  - 在 beforeUnmount() 钩子中移除所有事件监听器
  - 确保正确清理资源，避免内存泄漏
  - _Requirements: 7.1, 7.3, 7.4, 7.5, 8.3_

- [x] 11. 错误处理和用户反馈
  - 在 VisualInterpretationWorker 中添加详细的错误日志
  - 在 API 端点中添加友好的错误消息
  - 在前端显示可视化生成失败的提示
  - 提供"重新生成"按钮（可选功能）
  - 确保可视化生成失败不影响深度解读的正常使用
  - 在控制台记录详细的调试信息
  - _Requirements: 1.5, 8.1, 8.2, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5, 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 12. 测试和验证
  - [x] 12.1 测试后端可视化生成
    - 手动触发深度解读生成，验证可视化任务自动启动
    - 检查生成的 HTML 文件格式正确
    - 验证版本号正确匹配（article_v2.md → article_v2_visual.html）
    - 测试文章元数据正确更新
    - 测试 API 端点返回正确的 HTML 和状态
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4_
  
  - [x] 12.2 测试文件监测器
    - 创建新的深度解读文件，验证监测器自动触发生成
    - 更新现有文件（新版本），验证监测器检测到变化
    - 验证 `.visual_processed.json` 正确记录已处理文件
    - 测试监测器的错误恢复机制
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.4, 3.5_
  
  - [x] 12.3 测试前端模式切换
    - 测试 Deep Insight 和 Quick Insight 之间的切换
    - 验证切换动画流畅
    - 测试目录侧边栏正确显示/隐藏
    - 验证可视化 HTML 正确加载和渲染
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 12.4 测试全屏功能
    - 测试切换到 Quick Insight 时自动进入全屏（桌面端）
    - 测试 ESC 键退出全屏
    - 测试退出按钮功能
    - 测试切换到 Deep Insight 时自动退出全屏
    - 验证移动端不自动进入全屏
    - 测试浏览器不支持全屏 API 的降级处理
    - _Requirements: 6.1, 6.2, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 12.5 测试版本同步
    - 测试切换深度解读版本时，可视化版本自动同步
    - 验证不同版本的可视化 HTML 正确加载
    - 测试版本切换时的状态更新
    - 验证 URL 参数正确传递版本号
    - _Requirements: 3.4, 5.1, 5.2, 12.1, 12.2_
  
  - [x] 12.6 测试错误场景
    - 测试可视化生成失败时的错误提示
    - 测试 HTML 文件不存在时的处理
    - 测试 API 调用失败的重试机制
    - 测试网络错误的用户反馈
    - 验证错误不影响深度解读的正常使用
    - _Requirements: 1.5, 8.1, 8.2, 8.4, 9.1, 9.2, 9.3, 13.1, 13.2, 13.3, 13.4, 13.5_
  
  - [x] 12.7 测试浏览器兼容性
    - 在 Chrome 中测试所有功能
    - 在 Firefox 中测试所有功能
    - 在 Safari 中测试所有功能
    - 在 Edge 中测试所有功能
    - 测试移动端浏览器（iOS Safari, Chrome Mobile）
    - _Requirements: 6.5, 7.1, 7.2, 7.3_

- [x] 13. 性能优化
  - 验证可视化生成不阻塞深度解读完成
  - 测试文件监测器的 CPU 和内存占用
  - 优化 HTML 文件大小（考虑压缩）
  - 测试 iframe 加载性能
  - 验证全屏切换的流畅性
  - 测试多个并发生成任务的处理
  - _Requirements: 1.2, 12.1, 12.2, 12.3, 12.4_

- [x] 14. 文档和代码注释
  - 在 VisualInterpretationWorker 中添加详细的文档字符串
  - 在 VisualInterpretationWatcher 中添加详细的文档字符串
  - 在前端组件中添加注释说明关键逻辑
  - 更新 README 或用户文档，说明可视化解读功能
  - 添加配置说明文档
  - 记录已知问题和限制
  - _Requirements: 所有需求_
