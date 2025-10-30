# Cookie 系统快速参考

## 系统概览

```
Cookie Manager Service (后台服务)
         ↓ 定期刷新
    .cookies 文件
         ↑ 读取使用
主程序 (API/CLI)
```

## 命令速查

### 服务管理

```bash
# 启动服务（后台）
reinvent-insight cookie-manager start --daemon

# 启动服务（前台，用于调试）
reinvent-insight cookie-manager start

# 停止服务
reinvent-insight cookie-manager stop

# 重启服务
reinvent-insight cookie-manager restart

# 查看状态
reinvent-insight cookie-manager status

# 健康检查（新增）
reinvent-insight cookie-manager health
```

### Cookie 管理

```bash
# 导入 cookies
reinvent-insight cookie-manager import-cookies cookies.txt

# 手动刷新
reinvent-insight cookie-manager refresh

# 导出备份
reinvent-insight cookie-manager export cookies_backup.txt

# 导出为 JSON
reinvent-insight cookie-manager export cookies.json --format json
```

### 主程序使用

```bash
# Web 模式（自动使用 cookies）
reinvent-insight serve

# CLI 模式（自动使用 cookies）
reinvent-insight --url "https://youtube.com/watch?v=..."
```

## API 端点

### 公开端点

```bash
# 健康检查
GET /api/health

# 返回示例
{
  "status": "healthy",
  "timestamp": "2024-10-30T10:00:00",
  "components": {
    "api": {
      "status": "healthy",
      "message": "API 服务运行正常"
    },
    "cookies": {
      "status": "healthy",
      "service_running": true,
      "file_status": "fresh",
      "content_valid": true,
      "issues": [],
      "warnings": []
    }
  }
}
```

### 管理员端点（需要认证）

```bash
# 详细 Cookie 状态
GET /api/admin/cookie-status
Authorization: Bearer <token>

# 返回示例
{
  "overall_status": "healthy",
  "timestamp": "2024-10-30T10:00:00",
  "service": {...},
  "file": {...},
  "content": {...},
  "issues": [],
  "warnings": [],
  "recommendations": []
}
```

## 文件说明

### Cookie 文件

| 文件 | 格式 | 用途 | 更新方式 |
|------|------|------|----------|
| `.cookies` | Netscape | yt-dlp 使用 | Cookie Manager 自动更新 |
| `.cookies.json` | JSON | Cookie Manager 内部存储 | Cookie Manager 自动更新 |
| `cookies.txt` | Netscape | 初始导入 | 手动从浏览器导出 |

### 配置文件

```bash
# .env
COOKIE_REFRESH_INTERVAL=6          # 刷新间隔（小时）
COOKIE_BROWSER_TYPE=chromium       # 浏览器类型
```

## 工作流程

### 首次部署

```bash
# 1. 从浏览器导出 cookies
# 使用 "Get cookies.txt LOCALLY" 扩展

# 2. 上传到服务器
scp cookies.txt user@server:/path/to/project/

# 3. 导入 cookies
reinvent-insight cookie-manager import-cookies cookies.txt

# 4. 启动 Cookie Manager 服务
reinvent-insight cookie-manager start --daemon

# 5. 验证状态
reinvent-insight cookie-manager health

# 6. 启动主程序
reinvent-insight serve
```

### 日常运维

```bash
# 检查健康状态
reinvent-insight cookie-manager health

# 如果有问题，查看详细状态
reinvent-insight cookie-manager status

# 手动刷新（如果需要）
reinvent-insight cookie-manager refresh

# 备份 cookies
reinvent-insight cookie-manager export cookies_backup_$(date +%Y%m%d).txt
```

### 故障恢复

```bash
# 场景 1：服务停止
reinvent-insight cookie-manager start --daemon

# 场景 2：Cookies 失效
reinvent-insight cookie-manager refresh
# 如果刷新失败，重新导入
reinvent-insight cookie-manager import-cookies cookies.txt

# 场景 3：浏览器问题
playwright install chromium
```

## 监控集成

### 使用 systemd

```bash
# 查看服务状态
systemctl status cookie-manager

# 查看日志
journalctl -u cookie-manager -f
```

### 使用 Docker

```bash
# 查看容器状态
docker-compose ps cookie-manager

# 查看日志
docker-compose logs -f cookie-manager

# 健康检查
docker-compose exec cookie-manager reinvent-insight cookie-manager health
```

### 使用监控脚本

```bash
#!/bin/bash
# check_cookies.sh

# 执行健康检查
reinvent-insight cookie-manager health --json > /tmp/cookie_health.json

# 检查退出码
if [ $? -eq 0 ]; then
    echo "✅ Cookies 健康"
else
    echo "❌ Cookies 有问题"
    # 发送告警
    # curl -X POST https://your-alert-system/alert ...
fi
```

## 健康状态说明

### 状态级别

| 状态 | 说明 | 退出码 | 影响 |
|------|------|--------|------|
| `healthy` | 一切正常 | 0 | 无 |
| `degraded` | 有警告但可用 | 2 | 可能影响性能 |
| `unhealthy` | 有严重问题 | 1 | 可能导致功能失败 |

### 常见问题

#### 服务未运行

```
⚠️  Cookie Manager 服务未运行
```

**影响**：Cookies 不会自动刷新，可能在几小时后失效

**解决**：
```bash
reinvent-insight cookie-manager start --daemon
```

#### Cookie 文件过期

```
⚠️  Cookie 文件接近过期 (13.5 小时)
```

**影响**：可能很快失效

**解决**：
```bash
reinvent-insight cookie-manager refresh
```

#### Cookie 内容无效

```
❌ Cookie 文件不包含 YouTube/Google cookies
```

**影响**：下载功能无法使用

**解决**：
```bash
reinvent-insight cookie-manager import-cookies cookies.txt
```

## 最佳实践

### 1. 定期备份

```bash
# 添加到 crontab
0 0 * * * /path/to/venv/bin/reinvent-insight cookie-manager export /backups/cookies-$(date +\%Y\%m\%d).txt
```

### 2. 监控告警

```bash
# 每小时检查一次
0 * * * * /path/to/check_cookies.sh
```

### 3. 日志轮转

```bash
# /etc/logrotate.d/cookie-manager
/path/to/logs/cookie_manager.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 4. 健康检查端点

```bash
# 在负载均衡器中配置
# Health Check URL: http://your-server:8000/api/health
# Interval: 30s
# Timeout: 10s
```

## 集成示例

### Python 代码

```python
from reinvent_insight.cookie_health_check import CookieHealthCheck

# 检查健康状态
checker = CookieHealthCheck()
result = checker.perform_full_check()

if result['overall_status'] != 'healthy':
    print("Cookie 有问题，请检查")
    checker.print_status_report(result)
```

### Shell 脚本

```bash
#!/bin/bash
# 在下载前检查 cookies

if ! reinvent-insight cookie-manager health --json | jq -e '.overall_status == "healthy"' > /dev/null; then
    echo "警告：Cookie 状态不健康"
    reinvent-insight cookie-manager health
    exit 1
fi

# 继续下载
reinvent-insight --url "$VIDEO_URL"
```

### HTTP 请求

```bash
# 检查健康状态
curl http://localhost:8000/api/health | jq

# 获取详细状态（需要认证）
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/admin/cookie-status | jq
```

## 故障排查清单

- [ ] Cookie Manager 服务是否运行？
  ```bash
  reinvent-insight cookie-manager status
  ```

- [ ] Cookie 文件是否存在？
  ```bash
  ls -lh .cookies
  ```

- [ ] Cookie 文件是否新鲜？
  ```bash
  stat .cookies
  ```

- [ ] Cookie 内容是否有效？
  ```bash
  grep youtube .cookies
  ```

- [ ] Playwright 浏览器是否安装？
  ```bash
  playwright install --dry-run chromium
  ```

- [ ] 系统依赖是否完整？
  ```bash
  ldd $(which chromium) | grep "not found"
  ```

- [ ] 日志中是否有错误？
  ```bash
  tail -100 logs/cookie_manager.log | grep ERROR
  ```

## 性能优化

### 调整刷新间隔

```bash
# .env
# 根据使用频率调整
COOKIE_REFRESH_INTERVAL=4  # 高频使用
COOKIE_REFRESH_INTERVAL=12 # 低频使用
```

### 使用更快的浏览器

```bash
# .env
COOKIE_BROWSER_TYPE=chromium  # 推荐，最快
# COOKIE_BROWSER_TYPE=firefox  # 备选
```

### 减少超时时间

```bash
# .env
COOKIE_BROWSER_TIMEOUT=20  # 默认 30 秒
```

## 安全建议

1. **保护 Cookie 文件**
   ```bash
   chmod 600 .cookies .cookies.json
   ```

2. **定期轮换**
   ```bash
   # 每周重新导入一次新的 cookies
   ```

3. **监控异常访问**
   ```bash
   # 检查日志中的失败尝试
   grep "验证失败" logs/cookie_manager.log
   ```

4. **使用专用账号**
   - 不要使用个人 Google 账号
   - 创建专门用于自动化的账号

## 相关文档

- [完整集成方案](COOKIE_MANAGER_INTEGRATION.md)
- [使用指南](COOKIE_MANAGER_GUIDE.md)
- [快速开始](../COOKIE_MANAGER_QUICKSTART.md)
