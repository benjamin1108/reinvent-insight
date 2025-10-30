# Cookie Manager 与主程序集成方案

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        主程序 (Main Program)                      │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   API Server │    │  CLI Worker  │    │  Downloader  │      │
│  │  (FastAPI)   │    │   (Async)    │    │  (yt-dlp)    │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                    │               │
│         └───────────────────┴────────────────────┘               │
│                             │                                    │
│                             ▼                                    │
│                    ┌─────────────────┐                          │
│                    │  Cookie File    │◄─────────────┐           │
│                    │   (.cookies)    │              │           │
│                    └─────────────────┘              │           │
└─────────────────────────────────────────────────────┼───────────┘
                                                      │
                                                      │ 定期更新
                                                      │
┌─────────────────────────────────────────────────────┼───────────┐
│              Cookie Manager Service (独立服务)       │           │
│                                                      │           │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────▼───────┐  │
│  │  Scheduler   │───>│  Refresher   │───>│  Cookie Store   │  │
│  │  (定时任务)   │    │ (Playwright) │    │ (.cookies.json) │  │
│  └──────────────┘    └──────────────┘    └─────────┬───────┘  │
│                                                      │           │
│                                                      ▼           │
│                                            ┌─────────────────┐  │
│                                            │  Netscape File  │  │
│                                            │   (.cookies)    │  │
│                                            └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 工作原理

### 1. Cookie Manager Service（独立后台服务）

**职责**：
- 定期刷新 YouTube cookies，保持登录状态
- 使用 Playwright 模拟浏览器访问 YouTube
- 将刷新后的 cookies 保存为 Netscape 格式（`.cookies` 文件）

**运行方式**：
```bash
# 后台守护进程模式
reinvent-insight cookie-manager start --daemon

# 前台运行（用于调试）
reinvent-insight cookie-manager start
```

**配置**：
```bash
# .env 文件
COOKIE_REFRESH_INTERVAL=6          # 刷新间隔（小时）
COOKIE_BROWSER_TYPE=chromium       # 浏览器类型
```

### 2. 主程序（字幕下载和分析）

**职责**：
- 下载 YouTube 字幕
- 生成深度分析报告
- 提供 Web API 和 CLI 接口

**Cookie 使用**：
```python
# src/reinvent_insight/downloader.py
def _get_base_command(self) -> list[str]:
    command = ['yt-dlp', ...]
    
    # 读取 Cookie Manager 维护的 .cookies 文件
    if config.COOKIES_FILE and config.COOKIES_FILE.exists():
        command.extend(['--cookies', str(config.COOKIES_FILE)])
        logger.info(f"使用 Cookies 文件: {config.COOKIES_FILE}")
    
    return command
```

## 交互方式

### 方式一：文件共享（当前实现）✅

**优点**：
- 简单直接，无需额外通信机制
- 两个服务完全解耦
- Cookie Manager 可以独立重启，不影响主程序

**实现**：
1. Cookie Manager 定期刷新 cookies
2. 将 cookies 保存到 `.cookies` 文件（Netscape 格式）
3. 主程序在需要时读取 `.cookies` 文件
4. yt-dlp 使用该文件进行认证

**文件格式**：
```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1234567890	VISITOR_INFO1_LIVE	xxx
.youtube.com	TRUE	/	TRUE	1234567890	YSC	xxx
```

### 方式二：进程间通信（可选扩展）

如果需要更紧密的集成，可以考虑：

#### 选项 A：HTTP API

Cookie Manager 提供 REST API：

```python
# 在 cookie_manager_service.py 中添加
from fastapi import FastAPI

cookie_api = FastAPI()

@cookie_api.get("/api/cookies/status")
async def get_cookie_status():
    """获取 cookie 状态"""
    return service.get_status()

@cookie_api.post("/api/cookies/refresh")
async def trigger_refresh():
    """手动触发刷新"""
    success, message = await service.scheduler.trigger_manual_refresh()
    return {"success": success, "message": message}

@cookie_api.get("/api/cookies/export")
async def export_cookies():
    """导出 cookies（JSON 格式）"""
    cookies = service.cookie_store.load_cookies()
    return {"cookies": cookies}
```

主程序调用：
```python
import httpx

async def get_fresh_cookies():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8001/api/cookies/export")
        return response.json()["cookies"]
```

#### 选项 B：Unix Socket

使用 Unix Domain Socket 进行本地通信：

```python
# Cookie Manager 端
import socket
import json

def start_socket_server():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind("/tmp/cookie-manager.sock")
    sock.listen(1)
    
    while True:
        conn, _ = sock.accept()
        data = conn.recv(1024).decode()
        
        if data == "GET_COOKIES":
            cookies = cookie_store.load_cookies()
            conn.send(json.dumps(cookies).encode())
        
        conn.close()

# 主程序端
def get_cookies_from_manager():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect("/tmp/cookie-manager.sock")
    sock.send(b"GET_COOKIES")
    data = sock.recv(4096).decode()
    sock.close()
    return json.loads(data)
```

#### 选项 C：共享内存（高性能）

使用 Python multiprocessing 的共享内存：

```python
from multiprocessing import shared_memory
import pickle

# Cookie Manager 写入
def update_shared_cookies(cookies):
    data = pickle.dumps(cookies)
    shm = shared_memory.SharedMemory(name="youtube_cookies", create=True, size=len(data))
    shm.buf[:len(data)] = data
    shm.close()

# 主程序读取
def read_shared_cookies():
    shm = shared_memory.SharedMemory(name="youtube_cookies")
    data = bytes(shm.buf[:])
    cookies = pickle.loads(data)
    shm.close()
    return cookies
```

## 推荐方案：文件共享 + 健康检查

### 当前实现（已完成）✅

```python
# 主程序使用 cookies
if config.COOKIES_FILE.exists():
    command.extend(['--cookies', str(config.COOKIES_FILE)])
```

### 建议增强：添加健康检查

在主程序中添加 Cookie Manager 健康检查：

```python
# src/reinvent_insight/downloader.py

def check_cookie_manager_status() -> dict:
    """检查 Cookie Manager 服务状态"""
    from .cookie_manager_service import get_service_status
    return get_service_status()

def ensure_fresh_cookies() -> bool:
    """确保 cookies 是新鲜的"""
    # 检查服务是否运行
    status = check_cookie_manager_status()
    
    if not status['is_running']:
        logger.warning("Cookie Manager 服务未运行")
        logger.info("提示：运行 'reinvent-insight cookie-manager start --daemon' 启动服务")
        return False
    
    # 检查 cookies 文件
    if not config.COOKIES_FILE.exists():
        logger.warning("Cookies 文件不存在")
        return False
    
    # 检查 cookies 新鲜度
    from datetime import datetime, timedelta
    import os
    
    file_mtime = datetime.fromtimestamp(os.path.getmtime(config.COOKIES_FILE))
    age = datetime.now() - file_mtime
    
    if age > timedelta(hours=12):
        logger.warning(f"Cookies 文件已过期 ({age.total_seconds() / 3600:.1f} 小时)")
        logger.info("Cookie Manager 将在下次调度时自动刷新")
    
    return True

# 在下载前调用
class SubtitleDownloader:
    def download_subtitle(self):
        # 检查 cookies 状态
        ensure_fresh_cookies()
        
        # 继续下载流程
        ...
```

## 部署和运维

### 启动顺序

```bash
# 1. 首次部署：导入 cookies
reinvent-insight cookie-manager import-cookies cookies.txt

# 2. 启动 Cookie Manager 服务（后台）
reinvent-insight cookie-manager start --daemon

# 3. 验证服务状态
reinvent-insight cookie-manager status

# 4. 启动主程序
reinvent-insight serve  # Web 模式
# 或
reinvent-insight --url "https://youtube.com/..."  # CLI 模式
```

### 使用 systemd 管理服务

创建 `/etc/systemd/system/cookie-manager.service`：

```ini
[Unit]
Description=YouTube Cookie Manager Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/venv/bin:/usr/bin"
ExecStart=/path/to/venv/bin/reinvent-insight cookie-manager start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable cookie-manager
sudo systemctl start cookie-manager
sudo systemctl status cookie-manager
```

### 使用 Docker Compose

```yaml
version: '3.8'

services:
  cookie-manager:
    build: .
    command: reinvent-insight cookie-manager start
    volumes:
      - ./cookies:/app/cookies
      - ./.cookies:/app/.cookies
      - ./.cookies.json:/app/.cookies.json
    environment:
      - COOKIE_REFRESH_INTERVAL=6
      - COOKIE_BROWSER_TYPE=chromium
    restart: always
    healthcheck:
      test: ["CMD", "reinvent-insight", "cookie-manager", "status"]
      interval: 30s
      timeout: 10s
      retries: 3

  main-app:
    build: .
    command: reinvent-insight serve
    ports:
      - "8000:8000"
    volumes:
      - ./cookies:/app/cookies
      - ./.cookies:/app/.cookies:ro  # 只读
      - ./downloads:/app/downloads
    depends_on:
      - cookie-manager
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: always
```

### 监控和告警

```python
# 添加到主程序的健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    from .cookie_manager_service import get_service_status
    
    cookie_status = get_service_status()
    
    return {
        "status": "healthy" if cookie_status['is_running'] else "degraded",
        "cookie_manager": cookie_status,
        "timestamp": datetime.now().isoformat()
    }
```

## 故障处理

### 场景 1：Cookie Manager 服务停止

**检测**：
```bash
reinvent-insight cookie-manager status
# 输出：服务未运行
```

**影响**：
- 主程序仍可使用现有的 `.cookies` 文件
- Cookies 不会自动刷新，可能在几小时后失效

**解决**：
```bash
# 重启服务
reinvent-insight cookie-manager start --daemon
```

### 场景 2：Cookies 失效

**检测**：
- yt-dlp 下载失败，提示认证错误
- Cookie Manager 日志显示验证失败

**解决**：
```bash
# 1. 手动触发刷新
reinvent-insight cookie-manager refresh

# 2. 如果刷新失败，重新导入 cookies
reinvent-insight cookie-manager import-cookies cookies.txt

# 3. 重启服务
reinvent-insight cookie-manager restart
```

### 场景 3：浏览器启动失败

**检测**：
- Cookie Manager 日志显示 Playwright 错误

**解决**：
```bash
# 重新安装浏览器
playwright install chromium

# 安装系统依赖（Ubuntu/Debian）
sudo apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
```

## 最佳实践

### 1. 定期备份 Cookies

```bash
# 添加到 crontab
0 0 * * * cp /path/to/.cookies /path/to/backups/cookies-$(date +\%Y\%m\%d).txt
```

### 2. 监控 Cookie 新鲜度

```python
# 添加监控脚本
import os
from datetime import datetime, timedelta
from pathlib import Path

def check_cookie_freshness():
    cookie_file = Path(".cookies")
    
    if not cookie_file.exists():
        print("❌ Cookie 文件不存在")
        return False
    
    mtime = datetime.fromtimestamp(os.path.getmtime(cookie_file))
    age = datetime.now() - mtime
    
    if age > timedelta(hours=12):
        print(f"⚠️  Cookie 文件已过期 ({age.total_seconds() / 3600:.1f} 小时)")
        return False
    
    print(f"✅ Cookie 文件新鲜 ({age.total_seconds() / 3600:.1f} 小时)")
    return True
```

### 3. 日志轮转

```python
# 在 logger.py 中配置
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/cookie_manager.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## 总结

**当前实现**：
- ✅ Cookie Manager 作为独立服务运行
- ✅ 通过文件共享（`.cookies`）与主程序交互
- ✅ 定期自动刷新 cookies
- ✅ 支持手动触发刷新
- ✅ 完整的错误恢复机制

**优势**：
- 简单可靠，无需复杂的进程间通信
- 服务解耦，可独立部署和维护
- 符合 Unix 哲学：做好一件事

**建议增强**：
- 在主程序中添加 Cookie Manager 健康检查
- 添加监控和告警机制
- 使用 systemd 或 Docker 管理服务生命周期

这个架构已经非常完善，可以直接用于生产环境！
