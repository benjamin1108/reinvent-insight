# 环境标识功能

## 功能说明

为了避免在开发环境和生产环境之间混淆，系统现在会自动检测并显示当前运行环境。

## 实现细节

### 1. 后端 API

新增了 `/api/env` 端点，返回环境信息：

```json
{
  "environment": "development",  // 或 "production"
  "project_root": "/path/to/project",
  "host": "0.0.0.0",
  "port": "8002",
  "version": "0.1.0",
  "is_development": true
}
```

环境判断逻辑：
- 优先检查环境变量 `ENVIRONMENT` 或 `ENV`
- 检查是否存在开发环境特有的文件（`.git`、`pyproject.toml`、`run-dev.sh`）
- 检查是否在虚拟环境中运行
- 如果明确设置了 `ENVIRONMENT=production`，强制为生产环境

### 2. 前端显示

#### 开发环境标识

在开发环境下，页面会显示以下特征：

1. **环境标签**
   - 右下角显示黄色的"开发环境"标签
   - 带有脉冲动画效果
   - 包含信息图标

2. **页面顶部边框**
   - 页面顶部有 3px 的黄色边框

3. **卡片光晕效果**
   - 所有 `.tech-gradient` 元素有微妙的黄色光晕

### 3. 环境变量设置

#### 开发环境（run-dev.sh）
```bash
ENVIRONMENT=development ENV=dev
```

#### 生产环境
- 使用 `redeploy.sh` 部署时，systemd 服务会自动设置 `ENVIRONMENT=production`
- 或手动设置环境变量：`export ENVIRONMENT=production`

## 使用指南

### 开发环境

1. 使用开发脚本启动：
   ```bash
   ./run-dev.sh
   ```

2. 页面特征：
   - 黄色环境标签
   - 黄色顶部边框
   - 卡片有黄色光晕

### 生产环境

1. 使用部署脚本：
   ```bash
   ./redeploy.sh
   ```

2. 页面特征：
   - 无环境标签
   - 正常的界面样式

## 样式定制

如需修改环境标识样式，编辑 `web/css/style.css` 中的相关类：

- `.dev-env-indicator` - 环境标签样式
- `body.dev-environment` - 开发环境下的 body 样式
- `@keyframes pulse` - 脉冲动画

## 故障排除

### 环境标识不显示

1. 检查 API 端点是否正常：
   ```bash
   curl http://localhost:8002/api/env
   ```

2. 查看浏览器控制台是否有错误

3. 确保前端代码已更新

### 环境判断错误

1. 检查环境变量：
   ```bash
   echo $ENVIRONMENT
   echo $ENV
   ```

2. 检查运行目录结构

3. 查看 API 返回的详细信息

## 安全考虑

- 环境信息 API 是公开的，不包含敏感信息
- 仅用于 UI 显示，不影响安全策略
- 生产环境不会暴露内部路径信息 