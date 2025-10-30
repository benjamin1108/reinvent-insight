# Design Document: YouTube Cookie Auto-Refresh

## Overview

本设计文档描述了 YouTube Cookie 自动刷新系统的架构和实现细节。该系统通过 headless 浏览器定期刷新 YouTube cookies，确保字幕下载功能的持续可用性。系统采用模块化设计，作为独立服务运行，与现有的 `SubtitleDownloader` 组件无缝集成。

### 核心目标

1. 自动维护 YouTube cookies 的有效性
2. 支持从本地浏览器导入初始 cookies
3. 作为独立后台服务运行
4. 提供简单的命令行管理接口
5. 与现有系统无缝集成

### 技术选型

- **浏览器自动化**: Playwright（推荐）或 Selenium
  - Playwright 优势：更现代、性能更好、API 更简洁、内置等待机制
  - 支持 Chromium headless 模式
- **Cookie 存储**: JSON 文件格式
- **进程管理**: Python multiprocessing + PID 文件
- **定时任务**: APScheduler 库
- **日志**: 使用现有的 loguru 配置

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     用户本地环境                              │
│  ┌──────────────┐         ┌─────────────────┐              │
│  │ 本地浏览器    │ ──────> │ Cookie 导出插件  │              │
│  │ (已登录YT)   │         │ (cookies.txt)   │              │
│  └──────────────┘         └─────────────────┘              │
└─────────────────────────────────────┬───────────────────────┘
                                      │ 上传
                                      ↓
┌─────────────────────────────────────────────────────────────┐
│                     远程服务器                                │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Cookie Manager Service                        │ │
│  │                                                          │ │
│  │  ┌──────────────┐    ┌─────────────────┐              │ │
│  │  │ CLI Interface│    │ Cookie Importer │              │ │
│  │  │  - start     │───>│  - validate     │              │ │
│  │  │  - stop      │    │  - import       │              │ │
│  │  │  - status    │    └─────────────────┘              │ │
│  │  │  - import    │                                      │ │
│  │  │  - refresh   │    ┌─────────────────┐              │ │
│  │  └──────────────┘    │ Cookie Store    │              │ │
│  │                      │  (JSON file)    │              │ │
│  │  ┌──────────────┐    └─────────────────┘              │ │
│  │  │ Scheduler    │             ↕                        │ │
│  │  │ (APScheduler)│    ┌─────────────────┐              │ │
│  │  └──────┬───────┘    │ Cookie Refresher│              │ │
│  │         │            │  - Playwright   │              │ │
│  │         └──────────> │  - Headless     │              │ │
│  │                      │  - Validation   │              │ │
│  │                      └─────────────────┘              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Existing Subtitle Downloader                  │ │
│  │                                                          │ │
│  │  ┌──────────────┐    ┌─────────────────┐              │ │
│  │  │ yt-dlp       │───>│ Cookie Store    │              │ │
│  │  │ (读取cookies)│    │  (读取最新)     │              │ │
│  │  └──────────────┘    └─────────────────┘              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 组件说明

1. **CLI Interface**: 命令行接口，提供服务管理和 cookie 导入功能
2. **Cookie Importer**: 负责验证和导入 cookies
3. **Cookie Store**: JSON 文件存储，保存 cookies 和元数据
4. **Scheduler**: 定时任务调度器，管理刷新周期
5. **Cookie Refresher**: 核心刷新逻辑，使用 Playwright 访问 YouTube

## Components and Interfaces

### 1. Cookie Store

**文件路径**: `.cookies.json`（与现有 `.cookies` 文件同目录）

**数据结构**:
```json
{
  "cookies": [
    {
      "name": "CONSENT",
      "value": "YES+...",
      "domain": ".youtube.com",
      "path": "/",
      "expires": 1735689600,
      "httpOnly": false,
      "secure": true,
      "sameSite": "None"
    }
  ],
  "metadata": {
    "last_updated": "2024-10-28T10:30:00Z",
    "last_validated": "2024-10-28T10:30:00Z",
    "source": "manual_import",
    "refresh_count": 5,
    "validation_status": "valid"
  }
}
```

**接口**:
```python
class CookieStore:
    def __init__(self, store_path: Path)
    def load_cookies(self) -> list[dict]
    def save_cookies(self, cookies: list[dict], metadata: dict) -> None
    def get_metadata(self) -> dict
    def export_to_netscape(self, output_path: Path) -> None
    def is_valid(self) -> bool
```

### 2. Cookie Importer

**职责**: 从多种格式导入 cookies 并验证有效性

**支持格式**:
- Netscape cookies.txt 格式（浏览器插件导出的标准格式）
- JSON 格式（Playwright/Selenium 导出格式）

**接口**:
```python
class CookieImporter:
    def import_from_netscape(self, file_path: Path) -> list[dict]
    def import_from_json(self, file_path: Path) -> list[dict]
    def validate_cookies(self, cookies: list[dict]) -> tuple[bool, str]
    def detect_format(self, file_path: Path) -> str
```

**验证规则**:
- 必须包含 YouTube 域名的 cookies
- 必须包含关键认证字段（如 CONSENT, VISITOR_INFO1_LIVE 等）
- Cookie 未过期
- 格式正确

### 3. Cookie Refresher

**职责**: 使用 headless 浏览器刷新 cookies

**工作流程**:
```
1. 启动 Playwright Chromium (headless)
2. 创建新的浏览器上下文
3. 加载现有 cookies
4. 访问 YouTube 主页
5. 等待页面加载完成
6. 提取更新后的 cookies
7. 验证 cookies 有效性
8. 保存到 Cookie Store
9. 关闭浏览器
```

**接口**:
```python
class CookieRefresher:
    def __init__(self, cookie_store: CookieStore)
    async def refresh(self) -> tuple[bool, str]
    async def validate_cookies_online(self, cookies: list[dict]) -> bool
    def _setup_browser(self) -> Browser
    def _extract_cookies(self, context: BrowserContext) -> list[dict]
```

**错误处理**:
- 浏览器启动失败：记录错误，5分钟后重试
- 页面加载超时：增加超时时间重试
- Cookie 验证失败：保留旧 cookies，记录警告
- 连续失败 3 次：发送告警日志

### 4. Scheduler

**职责**: 管理定时刷新任务

**使用 APScheduler**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class CookieScheduler:
    def __init__(self, refresher: CookieRefresher, interval_hours: int)
    def start(self) -> None
    def stop(self) -> None
    def trigger_manual_refresh(self) -> None
    def get_next_run_time(self) -> datetime
```

**调度策略**:
- 默认间隔：6 小时
- 首次启动后立即验证 cookies
- 如果验证失败，30 分钟后重试
- 支持手动触发刷新

### 5. Service Manager

**职责**: 管理整个服务的生命周期

**接口**:
```python
class CookieManagerService:
    def __init__(self, config: CookieManagerConfig)
    async def start(self) -> None
    async def stop(self) -> None
    def get_status(self) -> dict
    def is_running(self) -> bool
```

**PID 文件管理**:
- 文件路径：`/tmp/youtube-cookie-manager.pid`
- 启动时检查 PID 文件，防止重复运行
- 正常退出时删除 PID 文件
- 支持强制停止（kill -9）

### 6. CLI Interface

**命令行工具**: `reinvent-insight cookie-manager`

**子命令**:

```bash
# 启动服务（前台运行，用于调试）
reinvent-insight cookie-manager start

# 启动服务（后台守护进程）
reinvent-insight cookie-manager start --daemon

# 停止服务
reinvent-insight cookie-manager stop

# 查看状态
reinvent-insight cookie-manager status

# 导入 cookies
reinvent-insight cookie-manager import <file_path>

# 手动触发刷新
reinvent-insight cookie-manager refresh

# 导出当前 cookies（用于备份或调试）
reinvent-insight cookie-manager export <output_path>
```

**实现**:
```python
import click

@click.group()
def cookie_manager():
    """YouTube Cookie Manager - 自动维护 YouTube cookies"""
    pass

@cookie_manager.command()
@click.option('--daemon', is_flag=True, help='以守护进程模式运行')
def start(daemon: bool):
    """启动 Cookie Manager 服务"""
    pass

@cookie_manager.command()
def stop():
    """停止 Cookie Manager 服务"""
    pass

# ... 其他命令
```

## Data Models

### Configuration Model

```python
from pydantic import BaseModel, Field
from pathlib import Path

class CookieManagerConfig(BaseModel):
    """Cookie Manager 配置"""
    
    # Cookie 存储路径
    cookie_store_path: Path = Field(
        default=Path.cwd() / ".cookies.json",
        description="Cookie 存储文件路径"
    )
    
    # Netscape 格式导出路径（用于 yt-dlp）
    netscape_cookie_path: Path = Field(
        default=Path.cwd() / ".cookies",
        description="Netscape 格式 cookie 文件路径（yt-dlp 使用）"
    )
    
    # 刷新间隔（小时）
    refresh_interval_hours: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Cookie 刷新间隔（小时）"
    )
    
    # 浏览器类型
    browser_type: str = Field(
        default="chromium",
        description="浏览器类型：chromium, firefox, webkit"
    )
    
    # 浏览器超时时间（秒）
    browser_timeout: int = Field(
        default=30,
        description="浏览器操作超时时间（秒）"
    )
    
    # 重试配置
    max_retry_count: int = Field(
        default=3,
        description="连续失败最大重试次数"
    )
    
    retry_delay_minutes: int = Field(
        default=5,
        description="重试延迟时间（分钟）"
    )
    
    # PID 文件路径
    pid_file_path: Path = Field(
        default=Path("/tmp/youtube-cookie-manager.pid"),
        description="PID 文件路径"
    )
    
    # 日志级别
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    @classmethod
    def from_env(cls) -> "CookieManagerConfig":
        """从环境变量加载配置"""
        import os
        return cls(
            refresh_interval_hours=int(os.getenv("COOKIE_REFRESH_INTERVAL", "6")),
            browser_type=os.getenv("COOKIE_BROWSER_TYPE", "chromium"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
```

### Cookie Model

```python
from pydantic import BaseModel
from typing import Optional

class Cookie(BaseModel):
    """单个 Cookie 数据模型"""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[float] = None
    httpOnly: bool = False
    secure: bool = False
    sameSite: Optional[str] = None
    
    def to_netscape_line(self) -> str:
        """转换为 Netscape cookies.txt 格式的一行"""
        return "\t".join([
            self.domain,
            "TRUE" if self.domain.startswith(".") else "FALSE",
            self.path,
            "TRUE" if self.secure else "FALSE",
            str(int(self.expires)) if self.expires else "0",
            self.name,
            self.value
        ])
```

## Error Handling

### 错误分类和处理策略

| 错误类型 | 处理策略 | 日志级别 | 用户通知 |
|---------|---------|---------|---------|
| 浏览器启动失败 | 5分钟后重试，最多3次 | ERROR | 连续失败后告警 |
| 页面加载超时 | 增加超时时间重试 | WARNING | 无 |
| Cookie 验证失败 | 保留旧 cookies，下次刷新重试 | WARNING | 无 |
| Cookie 导入格式错误 | 立即返回错误信息 | ERROR | 显示详细错误 |
| PID 文件冲突 | 检查进程是否存在，提示用户 | ERROR | 显示冲突信息 |
| 配置文件错误 | 使用默认配置，记录警告 | WARNING | 提示使用默认值 |
| 连续刷新失败（3次） | 停止自动刷新，等待手动干预 | CRITICAL | 发送告警日志 |

### 错误恢复机制

```python
class ErrorRecovery:
    """错误恢复策略"""
    
    def __init__(self):
        self.failure_count = 0
        self.last_failure_time = None
    
    def should_retry(self) -> bool:
        """判断是否应该重试"""
        if self.failure_count >= 3:
            return False
        return True
    
    def get_retry_delay(self) -> int:
        """获取重试延迟时间（秒）"""
        return min(300 * (2 ** self.failure_count), 3600)  # 指数退避，最多1小时
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
    
    def reset(self):
        """重置失败计数"""
        self.failure_count = 0
        self.last_failure_time = None
```

## Testing Strategy

### 单元测试

**测试范围**:
- Cookie Store 的读写操作
- Cookie Importer 的格式解析和验证
- Configuration 的加载和验证
- Cookie 格式转换（JSON ↔ Netscape）

**测试工具**: pytest

**示例测试**:
```python
def test_cookie_store_save_and_load():
    """测试 cookie 存储和加载"""
    store = CookieStore(Path("/tmp/test_cookies.json"))
    cookies = [{"name": "test", "value": "value", "domain": ".youtube.com"}]
    metadata = {"last_updated": "2024-10-28T10:00:00Z"}
    
    store.save_cookies(cookies, metadata)
    loaded_cookies = store.load_cookies()
    
    assert len(loaded_cookies) == 1
    assert loaded_cookies[0]["name"] == "test"

def test_cookie_importer_netscape_format():
    """测试 Netscape 格式导入"""
    importer = CookieImporter()
    cookies = importer.import_from_netscape(Path("test_cookies.txt"))
    
    assert len(cookies) > 0
    assert all("domain" in c for c in cookies)
```

### 集成测试

**测试场景**:
1. 完整的 cookie 导入流程
2. Cookie 刷新流程（使用测试 cookies）
3. 服务启动和停止
4. 定时任务触发

**Mock 策略**:
- Mock Playwright 浏览器操作
- Mock YouTube 响应
- 使用测试 cookie 数据

### 手动测试清单

- [ ] 从 Chrome 导出 cookies 并成功导入
- [ ] 从 Firefox 导出 cookies 并成功导入
- [ ] 服务启动后能正常刷新 cookies
- [ ] yt-dlp 能使用刷新后的 cookies 下载字幕
- [ ] 服务异常退出后能正常重启
- [ ] 手动刷新命令能立即触发刷新
- [ ] 状态命令能正确显示服务状态

## Integration with Existing System

### 与 SubtitleDownloader 集成

**当前实现**:
```python
# src/reinvent_insight/downloader.py
COOKIES_FILE = PROJECT_ROOT / ".cookies"

if config.COOKIES_FILE and config.COOKIES_FILE.exists():
    command.extend(['--cookies', str(config.COOKIES_FILE)])
```

**集成方案**:
1. Cookie Manager 将 cookies 同时保存为两种格式：
   - `.cookies.json`（内部使用，包含元数据）
   - `.cookies`（Netscape 格式，供 yt-dlp 使用）

2. SubtitleDownloader 无需修改，继续使用 `.cookies` 文件

3. Cookie Manager 每次刷新后自动更新两个文件

**实现代码**:
```python
class CookieStore:
    def save_cookies(self, cookies: list[dict], metadata: dict) -> None:
        """保存 cookies 到 JSON 和 Netscape 格式"""
        # 保存 JSON 格式（内部使用）
        data = {"cookies": cookies, "metadata": metadata}
        self.store_path.write_text(json.dumps(data, indent=2))
        
        # 同时导出为 Netscape 格式（供 yt-dlp 使用）
        self.export_to_netscape(self.netscape_path)
        
        logger.info(f"Cookies 已保存到 {self.store_path} 和 {self.netscape_path}")
```

### 配置文件扩展

在 `.env` 文件中添加新的配置项：

```bash
# Cookie Manager 配置
COOKIE_REFRESH_INTERVAL=6  # 刷新间隔（小时）
COOKIE_BROWSER_TYPE=chromium  # 浏览器类型
```

在 `config.py` 中添加：

```python
# --- Cookie Manager 配置 ---
COOKIE_REFRESH_INTERVAL = int(os.getenv("COOKIE_REFRESH_INTERVAL", "6"))
COOKIE_BROWSER_TYPE = os.getenv("COOKIE_BROWSER_TYPE", "chromium")
COOKIE_STORE_PATH = PROJECT_ROOT / ".cookies.json"
```

## Deployment Considerations

### 依赖安装

更新 `pyproject.toml`:

```toml
dependencies = [
    # ... 现有依赖 ...
    "playwright>=1.40.0",
    "apscheduler>=3.10.4",
    "click>=8.1.7",
]
```

安装 Playwright 浏览器：

```bash
# 安装 Python 包
pip install playwright

# 安装浏览器二进制文件
playwright install chromium
```

### 系统服务配置（可选）

使用 systemd 将 Cookie Manager 配置为系统服务：

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
```

### 监控和日志

**日志文件**:
- 位置：`logs/cookie_manager.log`
- 轮转：每天或达到 10MB
- 保留：最近 7 天

**监控指标**:
- Cookie 刷新成功率
- 刷新延迟时间
- 连续失败次数
- 服务运行时长

**告警条件**:
- 连续 3 次刷新失败
- Cookie 即将过期（< 24 小时）
- 服务异常退出

## Security Considerations

### Cookie 安全

1. **文件权限**:
   - `.cookies.json` 和 `.cookies` 文件权限设置为 600（仅所有者可读写）
   - PID 文件权限设置为 644

2. **敏感信息保护**:
   - Cookie 文件不应提交到版本控制（已在 .gitignore 中）
   - 日志中不记录完整的 cookie 值，仅记录名称和域名

3. **传输安全**:
   - 从本地上传 cookies 文件时使用 SCP 或 SFTP
   - 建议使用 SSH 密钥认证

### 浏览器安全

1. **Headless 模式**:
   - 始终在 headless 模式下运行（除首次导入）
   - 禁用不必要的浏览器功能

2. **网络隔离**:
   - 仅访问 YouTube 域名
   - 可选：配置代理或防火墙规则

## Performance Optimization

### 资源使用

**内存**:
- Playwright Chromium: ~100-200MB
- Python 进程: ~50MB
- 总计: ~150-250MB

**CPU**:
- 刷新时短暂使用（5-10秒）
- 空闲时几乎无 CPU 占用

**磁盘**:
- Cookie 文件: < 1MB
- 日志文件: ~10MB（轮转后）
- Playwright 缓存: ~300MB（一次性）

### 优化策略

1. **浏览器复用**:
   - 考虑保持浏览器实例运行，避免频繁启动
   - 权衡：内存占用 vs 启动时间

2. **并发控制**:
   - 单实例运行，避免资源竞争
   - PID 文件防止重复启动

3. **缓存策略**:
   - Cookie 验证结果缓存 5 分钟
   - 避免频繁的网络请求

## Future Enhancements

### Phase 2 功能（可选）

1. **多账号支持**:
   - 支持管理多个 YouTube 账号的 cookies
   - 轮换使用不同账号避免限流

2. **Web 管理界面**:
   - 查看 cookie 状态
   - 手动触发刷新
   - 查看刷新历史

3. **智能刷新**:
   - 根据 cookie 过期时间动态调整刷新频率
   - 检测到失效时立即刷新

4. **通知集成**:
   - 邮件通知
   - Slack/Discord webhook
   - 系统通知

5. **备份和恢复**:
   - 自动备份有效的 cookies
   - 失败时自动回滚到上一个有效版本

## Documentation

### 用户文档

需要创建以下文档：

1. **快速开始指南**:
   - 如何从浏览器导出 cookies
   - 如何导入和启动服务
   - 常见问题排查

2. **命令行参考**:
   - 所有命令的详细说明
   - 参数和选项说明
   - 使用示例

3. **配置指南**:
   - 所有配置项说明
   - 推荐配置
   - 高级配置

4. **故障排查**:
   - 常见错误和解决方案
   - 日志分析
   - 调试技巧

### 开发者文档

1. **架构文档**（本文档）
2. **API 文档**（自动生成）
3. **贡献指南**
4. **测试指南**
