# reinvent-insight 部署脚本说明

本项目提供了以下自动化部署脚本，用于简化部署流程。

## 脚本概览

### 1. `redeploy.sh` - 生产环境自动化部署脚本

完整的自动化部署脚本，适用于生产环境。包含以下功能：

- 自动构建新版本
- 备份现有数据
- 停止旧服务
- 部署新版本
- 恢复数据
- 复制开发环境的文章到生产环境
- 配置并启动 systemd 服务

**使用方法：**
```bash
# 默认部署（包含备份）
./redeploy.sh

# 不备份现有数据
./redeploy.sh --no-backup

# 指定端口
./redeploy.sh --port 8080

# 指定主机地址
./redeploy.sh --host 127.0.0.1

# 组合使用
./redeploy.sh --port 8080 --host 0.0.0.0 --no-backup
```

**特点：**
- 自动备份 downloads 目录和 .env 文件
- 自动从开发环境（`~/reinvent-insight/downloads/summaries`）复制最新文章
- 自动配置 systemd 服务
- 支持平滑升级，最小化服务中断时间
- 部署到 `~/reinvent-insight-prod` 目录
- 复制文章时不会覆盖生产环境已有的文件

### 2. `quick-deploy.sh` - 快速测试部署脚本

简化版部署脚本，适用于开发测试环境。

**使用方法：**
```bash
./quick-deploy.sh
```

**特点：**
- 快速构建并部署到 `dist/test-deploy` 目录
- 使用端口 8002（避免与生产环境冲突）
- 自动创建测试用的 .env 文件
- 直接启动服务，方便测试

### 3. `clean-deploy.sh` - 清理脚本

用于清理构建文件和部署目录。

**使用方法：**
```bash
# 只清理构建文件和测试部署
./clean-deploy.sh

# 清理所有内容（包括生产部署，会提示确认）
./clean-deploy.sh --all
```

**特点：**
- 自动停止运行中的服务
- 清理构建产物
- 可选择性清理生产部署
- 清理前自动备份重要数据

### 4. `check-articles.sh` - 文章统计脚本

用于检查开发环境和生产环境的文章数量，方便了解同步状态。

**使用方法：**
```bash
./check-articles.sh
```

**特点：**
- 显示开发环境和生产环境的文章数量
- 列出最新的3篇文章
- 自动计算并显示两个环境的差异
- 提供同步建议

## 典型使用场景

### 场景 1：首次部署到生产环境

```bash
# 1. 确保在项目根目录
cd ~/reinvent-insight

# 2. 运行部署脚本
./redeploy.sh

# 3. 编辑配置文件
nano ~/reinvent-insight-prod/reinvent_insight-0.1.0/.env

# 4. 重启服务
sudo systemctl restart reinvent-insight
```

### 场景 2：更新生产环境

```bash
# 1. 拉取最新代码
git pull

# 2. 运行重新部署（会自动备份）
./redeploy.sh

# 服务会自动重启并使用新版本
```

### 场景 3：本地测试新功能

```bash
# 1. 开发新功能后
./quick-deploy.sh

# 2. 测试完成后清理
./clean-deploy.sh
```

### 场景 4：完全重置环境

```bash
# 清理所有部署（包括生产环境）
./clean-deploy.sh --all

# 重新部署
./redeploy.sh
```

### 场景 5：同步开发环境的文章到生产

```bash
# 在开发环境创建或更新文章后
cd ~/reinvent-insight

# 先检查文章数量差异
./check-articles.sh

# 运行部署脚本（会自动复制文章）
./redeploy.sh

# 脚本会显示：
# [INFO] 复制开发环境的文章...
# [SUCCESS] 已复制 X 篇文章从开发环境
# [SUCCESS] 部署环境总共有 Y 篇文章

# 再次检查确认同步成功
./check-articles.sh
```

## 目录结构

部署后的目录结构：

```
~/reinvent-insight-prod/
├── reinvent_insight-0.1.0.tar.gz  # 部署包
└── reinvent_insight-0.1.0/        # 解压后的应用
    ├── .venv-dist/                 # 虚拟环境
    ├── web/                        # 前端文件
    ├── downloads/                  # 下载的数据
    │   ├── subtitles/             # 字幕文件
    │   ├── summaries/             # 总结文件（包含从开发环境复制的）
    │   ├── pdfs/                  # PDF 文件
    │   └── tasks/                 # 任务临时文件
    └── .env                        # 配置文件
```

## 注意事项

1. **权限要求**：`redeploy.sh` 需要 sudo 权限来管理 systemd 服务
2. **端口冲突**：确保指定的端口未被占用
3. **配置文件**：首次部署后需要编辑 `.env` 文件设置正确的 API 密钥
4. **备份**：生产环境更新时默认会备份，备份目录格式为 `reinvent-insight-prod_backup_YYYYMMDD_HHMMSS`
5. **Python 版本**：需要 Python 3.8 或更高版本
6. **文章同步**：部署时会自动复制开发环境的文章，确保开发和生产内容一致

## 故障排查

### 服务无法启动
```bash
# 查看服务状态
sudo systemctl status reinvent-insight

# 查看详细日志
sudo journalctl -u reinvent-insight -n 100
```

### 端口被占用
```bash
# 查看端口占用
sudo lsof -i :8001

# 使用其他端口
./redeploy.sh --port 8002
```

### 权限问题
```bash
# 确保脚本有执行权限
chmod +x redeploy.sh quick-deploy.sh clean-deploy.sh
```

## 环境变量

部署脚本会读取以下环境变量（如果设置）：

### redeploy.sh 支持的环境变量
- `GEMINI_API_KEY`: Gemini API 密钥
- `ADMIN_USERNAME`: 管理员用户名
- `ADMIN_PASSWORD`: 管理员密码

如果这三个环境变量都设置了，脚本会自动创建 .env 文件并直接启动服务，无需手动干预：

```bash
export GEMINI_API_KEY="your-actual-api-key"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="secure-password"
./redeploy.sh
```

### quick-deploy.sh 支持的环境变量
- `GEMINI_API_KEY`: Gemini API 密钥（用于测试环境）

示例：
```bash
export GEMINI_API_KEY="your-actual-api-key"
./quick-deploy.sh
```

## 交互式配置

当首次部署且未设置环境变量时，`redeploy.sh` 会提供交互式配置：

1. 创建示例 .env 文件
2. 询问是否立即编辑（提供 nano/vim 选项）
3. 编辑完成后询问是否启动服务

这确保了用户有机会在服务启动前正确配置所有必需的参数。 