# Cookie 文件路径说明

## 路径配置总览

### 默认路径（基于项目根目录）

```
项目根目录/
├── .cookies              # Netscape 格式，主程序使用
├── .cookies.json         # JSON 格式，Cookie Manager 内部存储
└── cookies.txt           # 初始导入文件（手动从浏览器导出）
```

### 路径定义位置

**主配置文件**: `src/reinvent_insight/config.py`

```python
# 项目根目录（自动检测）
PROJECT_ROOT = Path.cwd().resolve()

# Cookie 文件路径
COOKIES_FILE = PROJECT_ROOT / ".cookies"           # 主程序使用
COOKIE_STORE_PATH = PROJECT_ROOT / ".cookies.json" # Cookie Manager 使用
```

**Cookie Manager 配置**: `src/reinvent_insight/cookie_models.py`

```python
class CookieManagerConfig(BaseModel):
    # Cookie 存储路径（JSON 格式）
    cookie_store_path: Path = Field(
        default=Path.cwd() / ".cookies.json"
    )
    
    # Netscape 格式导出路径（yt-dlp 使用）
    netscape_cookie_path: Path = Field(
        default=Path.cwd() / ".cookies"
    )
```

## 路径解析逻辑

### 1. 项目根目录检测

```python
# config.py
PROJECT_ROOT = Path.cwd().resolve()

# 验证是否在正确的目录
if not (PROJECT_ROOT / "web").exists():
    # 如果当前目录没有 web，尝试开发环境路径
    dev_root = Path(__file__).parent.parent.parent
    if (dev_root / "web").exists():
        PROJECT_ROOT = dev_root
```

**检测规则**：
1. 首先使用当前工作目录 (`Path.cwd()`)
2. 检查是否存在 `web/` 目录
3. 如果不存在，尝试使用代码文件的父目录
4. 确保找到包含 `web/` 的项目根目录

### 2. Cookie Manager 路径加载

```python
# cookie_models.py
@classmethod
def from_env(cls) -> "CookieManagerConfig":
    """从环境变量和主配置加载"""
    from . import config as app_config
    
    return cls(
        cookie_store_path=app_config.COOKIE_STORE_PATH,
        netscape_cookie_path=app_config.COOKIES_FILE,
        ...
    )
```

**加载顺序**：
1. 从主配置 (`config.py`) 读取路径
2. 主配置基于 `PROJECT_ROOT` 计算路径
3. 确保两个服务使用相同的路径

## 生产环境路径验证

### 检查当前路径

```bash
# 方法 1：使用 Python
python3 -c "
from pathlib import Path
from src.reinvent_insight import config
print(f'项目根目录: {config.PROJECT_ROOT}')
print(f'Cookie 文件: {config.COOKIES_FILE}')
print(f'Cookie Store: {config.COOKIE_STORE_PATH}')
print(f'Cookie 文件存在: {config.COOKIES_FILE.exists()}')
"

# 方法 2：使用 CLI
reinvent-insight cookie-manager status

# 方法 3：检查实际文件
ls -la .cookies .cookies.json
```

### 验证路径一致性

```bash
# 创建验证脚本
cat > verify_paths.py << 'EOF'
#!/usr/bin/env python3
from pathlib import Path
from src.reinvent_insight import config
from src.reinvent_insight.cookie_models import CookieManagerConfig

# 主程序配置
main_cookie_file = config.COOKIES_FILE
main_cookie_store = config.COOKIE_STORE_PATH

# Cookie Manager 配置
cm_config = CookieManagerConfig.from_env()
cm_cookie_file = cm_config.netscape_cookie_path
cm_cookie_store = cm_config.cookie_store_path

print("=" * 60)
print("路径一致性检查")
print("=" * 60)

print(f"\n主程序配置:")
print(f"  Cookie 文件: {main_cookie_file}")
print(f"  Cookie Store: {main_cookie_store}")

print(f"\nCookie Manager 配置:")
print(f"  Cookie 文件: {cm_cookie_file}")
print(f"  Cookie Store: {cm_cookie_store}")

print(f"\n路径一致性:")
print(f"  Cookie 文件一致: {main_cookie_file == cm_cookie_file} ✅" if main_cookie_file == cm_cookie_file else f"  Cookie 文件不一致: ❌")
print(f"  Cookie Store 一致: {main_cookie_store == cm_cookie_store} ✅" if main_cookie_store == cm_cookie_store else f"  Cookie Store 不一致: ❌")

print(f"\n文件存在性:")
print(f"  {main_cookie_file}: {'✅ 存在' if main_cookie_file.exists() else '❌ 不存在'}")
print(f"  {main_cookie_store}: {'✅ 存在' if main_cookie_store.exists() else '❌ 不存在'}")

print("=" * 60)
EOF

python3 verify_paths.py
```

## 不同部署场景

### 场景 1：直接运行（开发/生产）

```bash
# 工作目录：项目根目录
cd /path/to/reinvent-insight

# 启动服务
reinvent-insight cookie-manager start --daemon
reinvent-insight serve

# 路径：
# - .cookies: /path/to/reinvent-insight/.cookies
# - .cookies.json: /path/to/reinvent-insight/.cookies.json
```

### 场景 2：systemd 服务

```ini
# /etc/systemd/system/cookie-manager.service
[Service]
WorkingDirectory=/path/to/reinvent-insight
ExecStart=/path/to/venv/bin/reinvent-insight cookie-manager start

# 路径：
# - .cookies: /path/to/reinvent-insight/.cookies
# - .cookies.json: /path/to/reinvent-insight/.cookies.json
```

**关键点**：`WorkingDirectory` 必须设置为项目根目录

### 场景 3：Docker 容器

```yaml
# docker-compose.yml
services:
  cookie-manager:
    working_dir: /app
    volumes:
      - ./cookies:/app/cookies
      - ./.cookies:/app/.cookies
      - ./.cookies.json:/app/.cookies.json

  main-app:
    working_dir: /app
    volumes:
      - ./.cookies:/app/.cookies:ro  # 只读挂载
```

**关键点**：
- 两个容器的 `working_dir` 都是 `/app`
- Cookie 文件通过 volume 共享
- 主程序只读挂载，防止误修改

### 场景 4：不同用户运行

```bash
# Cookie Manager 用户
sudo -u cookie-manager bash -c "
  cd /path/to/reinvent-insight
  reinvent-insight cookie-manager start --daemon
"

# 主程序用户
sudo -u webapp bash -c "
  cd /path/to/reinvent-insight
  reinvent-insight serve
"

# 确保文件权限
chmod 644 .cookies .cookies.json
chown cookie-manager:webapp .cookies .cookies.json
```

## 路径问题排查

### 问题 1：找不到 Cookie 文件

**症状**：
```
WARNING - Cookies 文件不存在: /path/to/.cookies
```

**排查步骤**：

```bash
# 1. 检查当前工作目录
pwd

# 2. 检查项目根目录检测
python3 -c "
from src.reinvent_insight import config
print(f'PROJECT_ROOT: {config.PROJECT_ROOT}')
print(f'web/ 存在: {(config.PROJECT_ROOT / \"web\").exists()}')
"

# 3. 检查 Cookie 文件路径
python3 -c "
from src.reinvent_insight import config
print(f'COOKIES_FILE: {config.COOKIES_FILE}')
print(f'文件存在: {config.COOKIES_FILE.exists()}')
"

# 4. 列出实际文件
ls -la .cookies* cookies.txt
```

**解决方案**：

```bash
# 方案 1：确保从项目根目录启动
cd /path/to/reinvent-insight
reinvent-insight serve

# 方案 2：创建符号链接
ln -s /actual/path/.cookies /expected/path/.cookies

# 方案 3：使用环境变量（如果支持）
export COOKIE_FILE_PATH=/custom/path/.cookies
```

### 问题 2：路径不一致

**症状**：
- Cookie Manager 更新了文件，但主程序读取的是旧文件
- 两个服务使用不同的 Cookie 文件

**排查步骤**：

```bash
# 运行验证脚本
python3 verify_paths.py

# 检查文件修改时间
stat .cookies .cookies.json

# 检查是否有多个副本
find / -name ".cookies" 2>/dev/null
```

**解决方案**：

```bash
# 确保两个服务从同一目录启动
cd /path/to/reinvent-insight

# 重启服务
reinvent-insight cookie-manager restart
systemctl restart main-app
```

### 问题 3：权限问题

**症状**：
```
PermissionError: [Errno 13] Permission denied: '.cookies'
```

**排查步骤**：

```bash
# 检查文件权限
ls -la .cookies .cookies.json

# 检查目录权限
ls -ld .

# 检查进程用户
ps aux | grep reinvent-insight
```

**解决方案**：

```bash
# 方案 1：修改文件权限
chmod 644 .cookies .cookies.json

# 方案 2：修改所有者
chown $USER:$USER .cookies .cookies.json

# 方案 3：使用相同用户运行
sudo -u webapp reinvent-insight cookie-manager start --daemon
sudo -u webapp reinvent-insight serve
```

## 环境变量配置（可选）

虽然当前实现使用固定路径，但可以通过修改代码支持环境变量：

```bash
# .env
COOKIE_FILE_PATH=/custom/path/.cookies
COOKIE_STORE_PATH=/custom/path/.cookies.json
```

```python
# config.py (修改后)
COOKIES_FILE = Path(os.getenv("COOKIE_FILE_PATH", PROJECT_ROOT / ".cookies"))
COOKIE_STORE_PATH = Path(os.getenv("COOKIE_STORE_PATH", PROJECT_ROOT / ".cookies.json"))
```

## 最佳实践

### 1. 使用绝对路径（生产环境）

```python
# 在生产环境配置中
COOKIES_FILE = Path("/var/lib/reinvent-insight/.cookies")
COOKIE_STORE_PATH = Path("/var/lib/reinvent-insight/.cookies.json")
```

### 2. 统一工作目录

```bash
# 所有服务都从项目根目录启动
cd /path/to/reinvent-insight
reinvent-insight cookie-manager start --daemon
reinvent-insight serve
```

### 3. 使用符号链接

```bash
# 如果需要在不同位置访问
ln -s /var/lib/reinvent-insight/.cookies /path/to/project/.cookies
```

### 4. 定期验证

```bash
# 添加到监控脚本
#!/bin/bash
python3 verify_paths.py
if [ $? -ne 0 ]; then
    echo "路径配置有问题" | mail -s "Alert" admin@example.com
fi
```

## 总结

### 当前配置（默认）

| 文件 | 路径 | 用途 | 更新者 |
|------|------|------|--------|
| `.cookies` | `PROJECT_ROOT/.cookies` | yt-dlp 使用 | Cookie Manager |
| `.cookies.json` | `PROJECT_ROOT/.cookies.json` | 内部存储 | Cookie Manager |
| `cookies.txt` | `PROJECT_ROOT/cookies.txt` | 初始导入 | 手动 |

### 路径一致性保证

✅ **两个服务使用相同的路径**
- Cookie Manager 从 `config.py` 读取路径
- 主程序也从 `config.py` 读取路径
- 都基于 `PROJECT_ROOT` 计算

✅ **自动路径检测**
- 基于当前工作目录
- 验证 `web/` 目录存在
- 支持开发和生产环境

✅ **文件共享机制**
- Cookie Manager 写入 `.cookies`
- 主程序读取 `.cookies`
- 通过文件系统自动同步

### 生产环境建议

1. **确保工作目录正确**
   ```bash
   cd /path/to/reinvent-insight
   ```

2. **验证路径一致性**
   ```bash
   python3 verify_paths.py
   ```

3. **检查文件权限**
   ```bash
   ls -la .cookies .cookies.json
   ```

4. **定期监控**
   ```bash
   reinvent-insight cookie-manager health
   ```

只要确保两个服务都从项目根目录启动，路径就会自动一致！
