# MCP Chrome DevTools 远程开发配置

## 环境要求

- **Node.js**: >= 20.19.0 LTS（系统级）
- **服务器**: ri.mindfree.top:1122 (用户: benjamin)

## 配置步骤

### 1. 本地电脑：启动 Chrome 调试模式

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug

# Windows
chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-debug

# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

### 2. 本地电脑：建立 SSH 反向隧道

```bash
ssh -R 9222:localhost:9222 -p 1122 benjamin@ri.mindfree.top
```

### 3. 服务器：验证连通性

```bash
curl -s http://localhost:9222/json/version
```

成功返回示例：
```json
{
  "Browser": "Chrome/143.0.7499.41",
  "Protocol-Version": "1.3",
  "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/xxx"
}
```

## MCP 配置文件

Cursor/IDE 中的 MCP 配置示例 (`mcp.json`):

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-ai/mcp-server-chrome-devtools@latest"
      ],
      "env": {
        "CDP_TARGET": "localhost:9222"
      }
    }
  }
}
```

### 配置说明

| 参数 | 说明 |
|-----|------|
| `CDP_TARGET` | Chrome DevTools Protocol 连接地址，通过 SSH 隧道后为 `localhost:9222` |
| `command` | 使用 npx 执行 MCP Server |
| `args` | MCP Server 包名，使用 `@latest` 确保最新版本 |

## Chrome 启动参数详解

| 参数 | 说明 |
|-----|------|
| `--remote-debugging-port=9222` | 启用远程调试并指定端口 |
| `--user-data-dir=/tmp/chrome-debug` | **必须**：指定独立的用户数据目录，避免与已运行的 Chrome 冲突 |
| `--disable-background-timer-throttling` | 可选：禁用后台定时器节流 |
| `--disable-backgrounding-occluded-windows` | 可选：禁用遮挡窗口的后台处理 |

## 常见问题

| 问题 | 解决方案 |
|-----|---------|
| Node 版本不足 | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt install -y nodejs` |
| Chrome 启动报错 `requires non-default data directory` | **必须**添加 `--user-data-dir=/tmp/chrome-debug` 参数 |
| SSH 隧道报错 `connect failed` | 确认本地 Chrome 已启动且 9222 端口在监听 |
| MCP Server 连接失败 | 检查 SSH 隧道状态，运行 `curl localhost:9222/json/version` 验证 |
