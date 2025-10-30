# Implementation Plan

- [x] 1. 更新配置文件以使用用户主目录路径
  - 修改 src/reinvent_insight/config.py，将 COOKIES_FILE 和 COOKIE_STORE_PATH 更新为使用 Path.home()
  - 添加 check_legacy_cookie_paths() 函数，检测并提示旧路径迁移
  - 在应用启动时调用迁移检查函数
  - _Requirements: 2.1, 2.2, 2.4, 4.1, 4.2_

- [x] 2. 更新 Cookie Store 类以支持新的默认路径
  - 修改 src/reinvent_insight/cookie_store.py 的 __init__ 方法
  - 将 store_path 和 netscape_path 参数设为可选，默认使用用户主目录
  - 确保目录自动创建逻辑正常工作
  - _Requirements: 2.1, 2.2, 4.3_

- [x] 3. 更新 Cookie Manager 配置模型
  - 修改 src/reinvent_insight/cookie_models.py 中的 CookieManagerConfig 类
  - 更新 cookie_store_path 和 netscape_cookie_path 的默认值为用户主目录路径
  - 确保 from_env() 方法正确处理新路径
  - _Requirements: 2.4, 2.5, 4.4_

- [x] 4. 创建独立的 Cookie 服务部署脚本
- [x] 4.1 创建脚本基础结构和配置
  - 创建 deploy-cookie-service.sh 文件
  - 添加脚本头部、颜色定义和默认配置变量
  - 实现命令行参数解析（--skip-cookie-import, --cookie-file, --dry-run）
  - 添加基础工具函数（print_info, print_success, print_warning, print_error）
  - _Requirements: 1.2, 1.3_

- [x] 4.2 实现环境检查模块
  - 实现 check_dependencies() 函数，检查 Python、pip、Playwright
  - 实现 check_and_install_dependencies() 函数，提供依赖安装选项
  - 添加系统权限检查
  - _Requirements: 1.3_

- [x] 4.3 实现交互式 Cookie 导入功能
  - 实现 interactive_cookie_import() 函数，显示导入选项菜单
  - 实现 import_with_editor() 函数，支持 nano/vim 编辑器
  - 实现 import_from_file() 函数，从现有文件导入
  - 实现 validate_cookie_format() 函数，验证 cookie 格式
  - 创建临时文件并在编辑后清理
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 4.4 实现服务部署模块
  - 实现 deploy_cookie_service() 函数
  - 创建虚拟环境和安装依赖
  - 安装 Playwright 浏览器
  - 创建 systemd 服务单元文件
  - 配置服务环境变量和工作目录
  - _Requirements: 1.3, 1.4_

- [x] 4.5 实现服务管理功能
  - 实现 start_cookie_service() 函数，启动服务并验证状态
  - 实现 stop_cookie_service() 函数，停止现有服务
  - 添加服务状态检查和错误处理
  - _Requirements: 1.5_

- [x] 4.6 实现部署信息展示
  - 实现 show_deployment_info() 函数
  - 显示服务状态、Cookie 信息、管理命令
  - 提供使用说明和故障排查提示
  - _Requirements: 1.3_

- [x] 5. 修改主部署脚本移除 Cookie 服务代码
- [x] 5.1 移除 Cookie 服务相关函数
  - 从 redeploy.sh 中删除 start_cookie_service() 函数
  - 移除 Playwright 浏览器安装代码
  - 移除 Cookie 服务的 systemd 配置代码
  - _Requirements: 5.1, 5.2_

- [x] 5.2 更新部署信息展示
  - 修改 show_deployment_info() 函数，移除 Cookie Manager 状态显示
  - 添加 Cookie 服务部署指引提示
  - 提供 deploy-cookie-service.sh 的使用说明
  - _Requirements: 5.3, 5.5_

- [x] 5.3 确保向后兼容性
  - 验证 Web 服务部署流程不受影响
  - 确保数据备份和恢复功能正常
  - 测试权限管理功能
  - _Requirements: 5.4_

- [x] 6. 添加路径迁移支持
  - 在 config.py 中实现 migrate_legacy_cookies() 函数
  - 检测项目目录下的旧 cookie 文件
  - 自动复制到新位置（如果新位置不存在）
  - 记录迁移日志并提示用户
  - _Requirements: 2.3, 4.5_

- [ ]* 7. 更新文档
  - 更新 README.md，说明新的 Cookie 服务部署方式
  - 创建 Cookie 服务部署指南文档
  - 更新现有的 Cookie Manager 文档，反映新的路径配置
  - 添加迁移指南，帮助现有用户升级
  - _Requirements: 1.1, 2.1, 3.1_

- [ ]* 8. 测试和验证
  - 测试全新部署场景（无现有 cookies）
  - 测试更新部署场景（已有 cookies）
  - 测试不同的 Cookie 导入方式（编辑器、文件、跳过）
  - 测试服务独立启动和停止
  - 测试 Web 服务读取共享 cookies
  - 验证路径迁移功能
  - 验证向后兼容性
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_
