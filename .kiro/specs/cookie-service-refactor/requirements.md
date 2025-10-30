# Requirements Document

## Introduction

本功能旨在重构 Cookie 服务的部署和配置方式，将 Cookie 服务从主部署脚本中分离出来，形成独立的部署脚本，并统一 Cookie 文件的存储位置到用户主目录（~/.cookies），同时提供交互式的初始 Cookie 导入功能。

## Glossary

- **Cookie Service**: Cookie Manager 服务，负责自动刷新和维护 YouTube cookies
- **Web Service**: reinvent-insight 主 Web 服务，提供视频分析和内容处理功能
- **Deployment Script**: 部署脚本，用于自动化安装和配置服务
- **Cookie Store**: Cookie 存储位置，保存 cookies 的文件路径
- **Netscape Format**: Netscape cookie 文件格式，yt-dlp 使用的标准格式
- **Interactive Editor**: 交互式文本编辑器（如 nano、vim），用于编辑配置文件

## Requirements

### Requirement 1

**User Story:** 作为系统管理员，我希望 Cookie 服务有独立的部署脚本，以便我可以单独部署和管理 Cookie 服务，而不影响主 Web 服务。

#### Acceptance Criteria

1. WHEN 执行主部署脚本时，THE Deployment Script SHALL NOT 包含 Cookie 服务的部署代码
2. THE System SHALL 提供独立的 Cookie 服务部署脚本（deploy-cookie-service.sh）
3. THE Cookie Service Deployment Script SHALL 支持完整的服务安装、配置和启动流程
4. THE Cookie Service Deployment Script SHALL 创建独立的 systemd 服务单元文件
5. WHEN Cookie 服务部署完成后，THE System SHALL 能够独立启动、停止和重启 Cookie 服务

### Requirement 2

**User Story:** 作为系统管理员，我希望 Cookie 文件统一存储在用户主目录下，以便多个服务实例可以共享同一套 cookies，简化管理。

#### Acceptance Criteria

1. THE Cookie Service SHALL 在用户主目录下生成 cookie 文件（~/.cookies）
2. THE Cookie Service SHALL 在用户主目录下生成 JSON 格式的 cookie 存储文件（~/.cookies.json）
3. THE Web Service SHALL 从 ~/.cookies 目录读取 Netscape 格式的 cookies
4. THE Cookie Store Configuration SHALL 使用 ~/.cookies 作为默认 Netscape 格式文件路径
5. THE Cookie Store Configuration SHALL 使用 ~/.cookies.json 作为默认 JSON 存储路径

### Requirement 3

**User Story:** 作为系统管理员，我希望部署脚本提供交互式的初始 Cookie 导入功能，以便我可以在部署时方便地配置初始 cookies。

#### Acceptance Criteria

1. WHEN 部署 Cookie 服务时，IF 不存在 cookie 文件，THEN THE Deployment Script SHALL 提示用户导入初始 cookies
2. THE Deployment Script SHALL 提供文本编辑器选项（nano、vim）供用户输入 cookies
3. THE Deployment Script SHALL 支持从现有文件导入 cookies
4. THE Deployment Script SHALL 支持跳过初始导入，稍后手动配置
5. WHEN 用户选择文本编辑器输入时，THE Script SHALL 创建临时文件并打开编辑器
6. WHEN 用户完成编辑后，THE Script SHALL 验证 cookie 格式并导入到系统

### Requirement 4

**User Story:** 作为开发者，我希望配置文件能够正确引用新的 Cookie 存储路径，以便应用程序能够从统一位置读取 cookies。

#### Acceptance Criteria

1. THE config.py SHALL 将 COOKIES_FILE 配置更新为 Path.home() / ".cookies"
2. THE config.py SHALL 将 COOKIE_STORE_PATH 配置更新为 Path.home() / ".cookies.json"
3. THE CookieStore Class SHALL 默认使用用户主目录下的路径初始化
4. WHEN 应用程序启动时，THE System SHALL 能够从 ~/.cookies 读取 cookies
5. WHEN Cookie Manager 刷新 cookies 时，THE System SHALL 更新 ~/.cookies 和 ~/.cookies.json

### Requirement 5

**User Story:** 作为系统管理员，我希望主部署脚本保持简洁，只负责 Web 服务的部署，以便维护和理解更容易。

#### Acceptance Criteria

1. THE Main Deployment Script SHALL 移除所有 Cookie 服务相关的部署代码
2. THE Main Deployment Script SHALL 移除 start_cookie_service 函数
3. THE Main Deployment Script SHALL 在部署信息中提示用户如何单独部署 Cookie 服务
4. THE Main Deployment Script SHALL 保持向后兼容，不影响现有的 Web 服务部署流程
5. THE Main Deployment Script SHALL 在部署完成后提供 Cookie 服务部署脚本的使用说明
