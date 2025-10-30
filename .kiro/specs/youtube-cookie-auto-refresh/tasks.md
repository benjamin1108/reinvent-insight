# Implementation Plan

- [x] 1. 创建核心数据模型和配置
  - 实现 Cookie 和 CookieManagerConfig 的 Pydantic 模型
  - 添加配置加载和验证逻辑
  - 在 config.py 中添加 Cookie Manager 相关配置项
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 2. 实现 Cookie Store 组件
  - 创建 `src/reinvent_insight/cookie_store.py` 文件
  - 实现 CookieStore 类的基本结构和初始化方法
- [x] 2.1 实现 Cookie 存储和加载功能
  - 实现 `load_cookies()` 方法从 JSON 文件读取 cookies
  - 实现 `save_cookies()` 方法保存 cookies 和元数据到 JSON 文件
  - 实现 `get_metadata()` 方法获取 cookie 元数据
  - _Requirements: 1.4, 2.1_

- [x] 2.2 实现 Netscape 格式导出功能
  - 实现 `export_to_netscape()` 方法将 cookies 转换为 Netscape 格式
  - 确保导出的文件与 yt-dlp 兼容
  - 实现 Cookie 模型的 `to_netscape_line()` 方法
  - _Requirements: 2.1, 2.4_

- [x] 2.3 实现 Cookie 验证功能
  - 实现 `is_valid()` 方法检查 cookies 是否有效
  - 验证必需的 YouTube 认证字段是否存在
  - 检查 cookies 是否过期
  - _Requirements: 1.4, 2.3_

- [x] 3. 实现 Cookie Importer 组件
  - 创建 `src/reinvent_insight/cookie_importer.py` 文件
  - 实现 CookieImporter 类的基本结构
- [x] 3.1 实现 Netscape 格式导入
  - 实现 `import_from_netscape()` 方法解析 Netscape cookies.txt 格式
  - 处理各种格式变体和注释行
  - 转换为统一的 Cookie 数据结构
  - _Requirements: 1.2, 8.1, 8.2_

- [x] 3.2 实现 JSON 格式导入
  - 实现 `import_from_json()` 方法解析 JSON 格式 cookies
  - 支持 Playwright 和 Selenium 导出的 JSON 格式
  - 标准化字段名称
  - _Requirements: 1.3_

- [x] 3.3 实现格式检测和验证
  - 实现 `detect_format()` 方法自动识别文件格式
  - 实现 `validate_cookies()` 方法验证导入的 cookies
  - 检查必需的 YouTube 域名和认证字段
  - 提供详细的错误信息和建议
  - _Requirements: 1.4, 8.3, 8.4_

- [x] 4. 实现 Cookie Refresher 组件
  - 创建 `src/reinvent_insight/cookie_refresher.py` 文件
  - 实现 CookieRefresher 类的基本结构
  - 添加 Playwright 依赖到 pyproject.toml
- [x] 4.1 实现浏览器初始化和配置
  - 实现 `_setup_browser()` 方法启动 Playwright 浏览器
  - 配置 headless 模式和浏览器选项
  - 实现浏览器超时和错误处理
  - _Requirements: 1.5, 3.2, 4.1_

- [x] 4.2 实现 Cookie 刷新核心逻辑
  - 实现 `refresh()` 异步方法执行完整的刷新流程
  - 加载现有 cookies 到浏览器上下文
  - 访问 YouTube 主页并等待加载完成
  - 提取更新后的 cookies
  - _Requirements: 1.6, 1.7_

- [x] 4.3 实现 Cookie 在线验证
  - 实现 `validate_cookies_online()` 方法验证 cookies 有效性
  - 使用 cookies 访问 YouTube 并检查响应
  - 实现 `_extract_cookies()` 方法从浏览器上下文提取 cookies
  - _Requirements: 1.6, 2.3_

- [x] 4.4 实现错误处理和重试机制
  - 实现浏览器启动失败的重试逻辑
  - 实现页面加载超时处理
  - 实现 Cookie 提取失败时保留旧 cookies
  - 添加详细的错误日志记录
  - _Requirements: 4.1, 4.2, 4.3, 4.5_

- [x] 5. 实现 Scheduler 组件
  - 创建 `src/reinvent_insight/cookie_scheduler.py` 文件
  - 添加 APScheduler 依赖到 pyproject.toml
  - 实现 CookieScheduler 类的基本结构
- [x] 5.1 实现定时任务调度
  - 实现 `start()` 方法启动定时任务
  - 配置刷新间隔和调度策略
  - 实现 `stop()` 方法停止调度器
  - 实现 `get_next_run_time()` 方法获取下次运行时间
  - _Requirements: 1.7, 3.1_

- [x] 5.2 实现手动触发和失败重试
  - 实现 `trigger_manual_refresh()` 方法支持手动刷新
  - 实现连续失败检测和告警逻辑
  - 实现失败后的延迟重试机制
  - _Requirements: 4.4, 6.1, 6.2, 6.4_

- [x] 6. 实现 Service Manager 组件
  - 创建 `src/reinvent_insight/cookie_manager_service.py` 文件
  - 实现 CookieManagerService 类整合所有组件
- [x] 6.1 实现服务生命周期管理
  - 实现 `start()` 异步方法启动服务
  - 初始化所有组件（Store, Refresher, Scheduler）
  - 实现 `stop()` 异步方法优雅关闭服务
  - 实现 `get_status()` 方法返回服务状态信息
  - _Requirements: 5.1, 5.2, 5.4_

- [x] 6.2 实现 PID 文件管理
  - 实现 PID 文件的创建和检查
  - 防止服务重复启动
  - 实现服务退出时清理 PID 文件
  - 处理异常退出的 PID 文件残留
  - _Requirements: 5.3_

- [x] 6.3 实现守护进程模式
  - 实现后台守护进程启动逻辑
  - 处理信号（SIGTERM, SIGINT）实现优雅关闭
  - 重定向标准输出到日志文件
  - _Requirements: 5.5_

- [x] 7. 实现 CLI 命令行接口
  - 创建 `src/reinvent_insight/cookie_manager_cli.py` 文件
  - 添加 click 依赖到 pyproject.toml（如果尚未添加）
  - 实现主命令组 `cookie-manager`
- [x] 7.1 实现服务管理命令
  - 实现 `start` 命令启动服务（支持 --daemon 选项）
  - 实现 `stop` 命令停止服务
  - 实现 `status` 命令查看服务状态
  - 实现 `restart` 命令重启服务
  - _Requirements: 5.2_

- [x] 7.2 实现 Cookie 管理命令
  - 实现 `import` 命令导入 cookies 文件
  - 实现 `refresh` 命令手动触发刷新
  - 实现 `export` 命令导出当前 cookies
  - 添加命令参数验证和帮助信息
  - _Requirements: 1.1, 6.1, 6.2, 7.1, 7.2_

- [x] 7.3 集成到主 CLI 入口
  - 在 `src/reinvent_insight/main.py` 中注册 cookie-manager 命令组
  - 更新 pyproject.toml 中的 entry_points（如果需要）
  - 确保命令可以通过 `reinvent-insight cookie-manager` 调用
  - _Requirements: 5.2_

- [x] 8. 实现错误恢复机制
  - 创建 `src/reinvent_insight/error_recovery.py` 文件
  - 实现 ErrorRecovery 类管理失败计数和重试策略
  - 实现指数退避算法计算重试延迟
  - 集成到 CookieRefresher 和 Scheduler 中
  - _Requirements: 4.1, 4.3, 4.4_

- [x] 9. 配置和环境变量集成
  - 更新 `.env.example` 添加 Cookie Manager 配置示例
  - 在 `src/reinvent_insight/config.py` 中添加配置加载逻辑
  - 实现配置验证和默认值处理 
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 10. 日志和监控集成
  - 配置 Cookie Manager 专用的日志记录器
  - 实现关键操作的日志记录（启动、刷新、失败等）
  - 实现告警日志（连续失败、cookies 即将过期）
  - 确保日志格式与现有系统一致
  - _Requirements: 4.2, 4.4, 4.5, 7.4_

- [x] 11. 与现有系统集成
  - 验证 SubtitleDownloader 能正确读取更新后的 .cookies 文件
  - 确保 Cookie Store 同时维护 JSON 和 Netscape 两种格式
  - 测试 yt-dlp 使用刷新后的 cookies 下载字幕
  - _Requirements: 2.1, 2.4_

- [x] 12. 创建用户文档
  - 创建 `docs/COOKIE_MANAGER_GUIDE.md` 快速开始指南
  - 编写如何从浏览器导出 cookies 的步骤说明
  - 编写命令行参考文档
  - 编写常见问题和故障排查指南
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 13. 编写单元测试
  - 为 CookieStore 编写测试（存储、加载、导出）
  - 为 CookieImporter 编写测试（格式解析、验证）
  - 为配置加载编写测试
  - 为 Cookie 格式转换编写测试
  - _Requirements: 所有需求_

- [x] 14. 编写集成测试
  - 测试完整的 cookie 导入流程
  - 测试 cookie 刷新流程（使用 mock）
  - 测试服务启动和停止
  - 测试定时任务触发
  - _Requirements: 所有需求_
