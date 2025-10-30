# YouTube Cookie Manager

自动维护 YouTube cookies 的后台服务，确保字幕下载功能持续可用。

## 特性

- ✅ 自动定时刷新 cookies（默认 6 小时）
- ✅ 支持从浏览器导出的 cookies 文件导入（Netscape 和 JSON 格式）
- ✅ 使用 Playwright headless 浏览器自动刷新
- ✅ 错误恢复和重试机制
- ✅ 完整的命令行管理界面
- ✅ 与现有字幕下载器无缝集成

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
playwright install chromium
```

### 2. 导出并导入 Cookies

从浏览器导出 cookies（推荐使用 "Get cookies.txt LOCALLY" 扩展），然后导入：

```bash
reinvent-insight cookie-manager import cookies.txt
```

### 3. 启动服务

```bash
# 后台运行
reinvent-insight cookie-manager start --daemon

# 或前台运行（用于调试）
reinvent-insight cookie-manager start
```

### 4. 查看状态

```bash
reinvent-insight cookie-manager status
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `start [--daemon]` | 启动服务 |
| `stop` | 停止服务 |
| `restart` | 重启服务 |
| `status [--json]` | 查看状态 |
| `import <file>` | 导入 cookies |
| `refresh` | 手动刷新 |
| `export <file>` | 导出 cookies |

## 配置

在 `.env` 文件中配置：

```bash
COOKIE_REFRESH_INTERVAL=6  # 刷新间隔（小时）
COOKIE_BROWSER_TYPE=chromium  # 浏览器类型
```

## 架构

```
Cookie Manager Service
├── Cookie Store (JSON + Netscape 格式)
├── Cookie Importer (支持多种格式)
├── Cookie Refresher (Playwright 自动化)
├── Scheduler (APScheduler 定时任务)
└── CLI Interface (Click 命令行)
```

## 工作流程

1. **导入阶段**：从浏览器导出 cookies → 导入到系统
2. **刷新阶段**：定时启动 headless 浏览器 → 加载 cookies → 访问 YouTube → 提取更新的 cookies
3. **使用阶段**：字幕下载器自动使用最新的 cookies

## 文档

- [完整使用指南](./COOKIE_MANAGER_GUIDE.md)
- [设计文档](../.kiro/specs/youtube-cookie-auto-refresh/design.md)
- [需求文档](../.kiro/specs/youtube-cookie-auto-refresh/requirements.md)

## 测试

```bash
# 运行单元测试
pytest tests/test_cookie_*.py

# 运行集成测试
pytest tests/test_integration.py

# 运行所有测试
pytest tests/
```

## 故障排查

### 常见问题

1. **导入失败**：确保从已登录 YouTube 的浏览器导出 cookies
2. **刷新失败**：检查 Playwright 浏览器是否正确安装
3. **服务启动失败**：检查是否有残留的 PID 文件

详见 [使用指南](./COOKIE_MANAGER_GUIDE.md) 的故障排查部分。

## 技术栈

- **浏览器自动化**：Playwright
- **定时任务**：APScheduler
- **CLI**：Click
- **数据验证**：Pydantic
- **测试**：pytest

## 安全建议

- 设置 cookies 文件权限为 600
- 不要将 cookies 文件提交到版本控制
- 定期更新 cookies（每月至少一次）

## License

MIT
