# YouTube Cookie Manager 使用指南

## 简介

YouTube Cookie Manager 是一个自动维护 YouTube cookies 的后台服务，通过定期刷新 cookies 确保字幕下载功能的持续可用性。

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -e .

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 从浏览器导出 Cookies

#### 方法一：使用浏览器扩展（推荐）

1. 安装浏览器扩展：
   - Chrome/Edge: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. 在浏览器中登录 YouTube

3. 访问 YouTube 页面，点击扩展图标

4. 选择 "Export" 或"导出"，保存为 `cookies.txt`

#### 方法二：使用开发者工具（高级）

1. 在浏览器中登录 YouTube
2. 按 F12 打开开发者工具
3. 切换到 "Application" 或 "存储" 标签
4. 找到 Cookies → https://www.youtube.com
5. 手动复制所需的 cookies（不推荐，容易出错）

### 3. 导入 Cookies 到服务器

将导出的 cookies 文件上传到服务器：

```bash
# 使用 scp 上传
scp cookies.txt user@server:/path/to/project/

# 或使用 sftp
sftp user@server
put cookies.txt /path/to/project/
```

### 4. 导入 Cookies

```bash
reinvent-insight cookie-manager import cookies.txt
```

成功后会显示：
```
✓ 成功验证 XX 个 YouTube cookies
✓ Cookies 已保存到 .cookies.json
✓ Netscape 格式已导出到 .cookies
```

### 5. 启动服务

#### 前台运行（用于测试）

```bash
reinvent-insight cookie-manager start
```

按 Ctrl+C 停止服务。

#### 后台运行（推荐）

```bash
reinvent-insight cookie-manager start --daemon
```

### 6. 查看状态

```bash
reinvent-insight cookie-manager status
```

输出示例：
```
✓ 服务正在运行
  PID: 12345

Cookie 信息:
  数量: 25
  有效性: ✓ 有效
  最后更新: 2024-10-28T10:30:00Z
  刷新次数: 5
```

## 命令参考

### start - 启动服务

```bash
reinvent-insight cookie-manager start [--daemon]
```

选项：
- `--daemon`: 以守护进程模式在后台运行

### stop - 停止服务

```bash
reinvent-insight cookie-manager stop
```

### restart - 重启服务

```bash
reinvent-insight cookie-manager restart
```

### status - 查看状态

```bash
reinvent-insight cookie-manager status [--json]
```

选项：
- `--json`: 以 JSON 格式输出状态信息

### import - 导入 Cookies

```bash
reinvent-insight cookie-manager import <file_path> [--format <format>]
```

参数：
- `file_path`: Cookies 文件路径

选项：
- `--format`: 文件格式，可选值：`netscape`、`json`、`auto`（默认自动检测）

示例：
```bash
# 自动检测格式
reinvent-insight cookie-manager import cookies.txt

# 指定格式
reinvent-insight cookie-manager import cookies.json --format json
```

### refresh - 手动刷新

```bash
reinvent-insight cookie-manager refresh
```

立即执行一次 cookie 刷新，不影响定时刷新调度。

### export - 导出 Cookies

```bash
reinvent-insight cookie-manager export <output_path> [--format <format>]
```

参数：
- `output_path`: 输出文件路径

选项：
- `--format`: 导出格式，可选值：`netscape`（默认）、`json`

示例：
```bash
# 导出为 Netscape 格式
reinvent-insight cookie-manager export cookies_backup.txt

# 导出为 JSON 格式
reinvent-insight cookie-manager export cookies.json --format json
```

## 配置

### 环境变量

在 `.env` 文件中配置：

```bash
# Cookie 刷新间隔（小时）
COOKIE_REFRESH_INTERVAL=6

# 浏览器类型 (chromium, firefox, webkit)
COOKIE_BROWSER_TYPE=chromium
```

### 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| COOKIE_REFRESH_INTERVAL | 6 | Cookie 刷新间隔（小时） |
| COOKIE_BROWSER_TYPE | chromium | 浏览器类型 |

## 常见问题

### 1. 导入 Cookies 失败

**错误信息**：`没有找到 YouTube 域名的 cookies`

**解决方案**：
- 确保从已登录 YouTube 的浏览器导出 cookies
- 检查 cookies 文件格式是否正确
- 尝试重新登录 YouTube 后再导出

### 2. 服务启动失败

**错误信息**：`服务已在运行（PID 文件存在）`

**解决方案**：
```bash
# 停止现有服务
reinvent-insight cookie-manager stop

# 或者检查进程是否真的在运行
ps aux | grep cookie-manager

# 如果进程不存在，删除残留的 PID 文件
rm /tmp/youtube-cookie-manager.pid
```

### 3. Cookies 刷新失败

**错误信息**：`刷新 cookies 失败: 浏览器启动失败`

**解决方案**：
```bash
# 确保 Playwright 浏览器已安装
playwright install chromium

# 检查系统依赖
# Ubuntu/Debian
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2
```

### 4. 连续刷新失败

**错误信息**：`连续刷新失败次数过多，已停止自动刷新`

**解决方案**：
1. 检查网络连接
2. 检查 YouTube 是否可访问
3. 重新导入新的 cookies：
   ```bash
   reinvent-insight cookie-manager import new_cookies.txt
   ```
4. 重启服务：
   ```bash
   reinvent-insight cookie-manager restart
   ```

### 5. 字幕下载仍然失败

**可能原因**：
- Cookies 已过期但服务未运行
- Cookies 文件权限问题

**解决方案**：
```bash
# 检查服务状态
reinvent-insight cookie-manager status

# 检查 cookies 文件
ls -la .cookies .cookies.json

# 手动刷新
reinvent-insight cookie-manager refresh

# 如果仍然失败，重新导入 cookies
reinvent-insight cookie-manager import cookies.txt
```

## 故障排查

### 查看日志

日志文件位置：`logs/cookie_manager.log`

```bash
# 查看最新日志
tail -f logs/cookie_manager.log

# 搜索错误
grep ERROR logs/cookie_manager.log
```

### 调试模式

设置日志级别为 DEBUG：

```bash
# 在 .env 文件中
LOG_LEVEL=DEBUG
```

### 测试 Cookies 有效性

```bash
# 手动刷新测试
reinvent-insight cookie-manager refresh

# 查看详细状态
reinvent-insight cookie-manager status --json
```

## 最佳实践

### 1. 定期备份 Cookies

```bash
# 每周备份一次
reinvent-insight cookie-manager export cookies_backup_$(date +%Y%m%d).txt
```

### 2. 监控服务状态

使用 cron 定期检查服务状态：

```bash
# 添加到 crontab
0 */6 * * * /path/to/venv/bin/reinvent-insight cookie-manager status || /path/to/venv/bin/reinvent-insight cookie-manager start --daemon
```

### 3. 使用 systemd 管理服务（可选）

创建 systemd 服务文件：

```ini
# /etc/systemd/system/youtube-cookie-manager.service
[Unit]
Description=YouTube Cookie Manager Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/reinvent-insight cookie-manager start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl enable youtube-cookie-manager
sudo systemctl start youtube-cookie-manager
sudo systemctl status youtube-cookie-manager
```

### 4. 安全建议

- 设置 cookies 文件权限为 600：
  ```bash
  chmod 600 .cookies .cookies.json
  ```

- 不要将 cookies 文件提交到版本控制

- 定期更新 cookies（每月至少一次）

## 技术支持

如果遇到问题：

1. 查看日志文件
2. 检查 GitHub Issues
3. 提交新的 Issue 并附上：
   - 错误信息
   - 日志文件（删除敏感信息）
   - 系统环境信息

## 更新日志

### v0.1.0 (2024-10-28)

- 初始版本
- 支持 Netscape 和 JSON 格式导入
- 自动定时刷新
- 命令行管理界面
- 错误恢复机制
