# 开发环境运行指南

## 快速开始

在项目根目录下运行：

```bash
chmod +x run-dev.sh  # 首次运行需要添加执行权限
./run-dev.sh
```

## 脚本功能

`run-dev.sh` 是一个自动化的开发环境启动脚本，它会：

1. **检查环境** - 确保在正确的项目目录
2. **创建/激活虚拟环境** - 自动管理 Python 虚拟环境
3. **安装依赖** - 以开发模式安装所有项目依赖
4. **检查配置** - 确保 `.env` 文件存在并配置正确
5. **创建目录** - 自动创建必要的工作目录
6. **启动服务器** - 使用热重载模式启动开发服务器

## 命令行选项

```bash
./run-dev.sh [选项]
```

可用选项：
- `--port PORT` - 指定端口号（默认：8001）
- `--host HOST` - 指定主机地址（默认：127.0.0.1）
- `--reload` - 启用热重载（默认启用）
- `--no-reload` - 禁用热重载

### 示例

```bash
# 使用默认配置启动
./run-dev.sh

# 在 8080 端口启动
./run-dev.sh --port 8080

# 允许外部访问（0.0.0.0）
./run-dev.sh --host 0.0.0.0

# 禁用热重载
./run-dev.sh --no-reload

# 组合使用
./run-dev.sh --host 0.0.0.0 --port 8080
```

## 开发模式特性

1. **热重载** - 代码修改后自动重启服务器
2. **详细日志** - 显示所有请求和错误信息
3. **开发模式安装** - 使用 `pip install -e .` 安装，代码修改立即生效
4. **本地访问** - 默认只允许本地访问（127.0.0.1）

## 与生产部署的区别

| 特性 | 开发环境 (run-dev.sh) | 生产环境 (redeploy.sh) |
|------|----------------------|------------------------|
| 安装方式 | 开发模式 (-e) | 打包安装 |
| 热重载 | 默认启用 | 不支持 |
| 默认地址 | 127.0.0.1 | 0.0.0.0 |
| systemd服务 | 不创建 | 自动配置 |
| 备份功能 | 无 | 自动备份 |
| 目录位置 | 项目根目录 | ~/reinvent-insight-prod |

## 故障排除

### 1. 权限错误
```bash
chmod +x run-dev.sh
```

### 2. Python 版本问题
确保使用 Python 3.9 或更高版本：
```bash
python3 --version
```

### 3. 依赖安装失败
手动激活虚拟环境并安装：
```bash
source .venv/bin/activate
pip install -e .
```

### 4. 端口已被占用
使用其他端口：
```bash
./run-dev.sh --port 8002
```

或查找占用端口的进程：
```bash
sudo lsof -i :8001
```

## 开发工作流

1. **启动开发服务器**
   ```bash
   ./run-dev.sh
   ```

2. **修改代码**
   - 编辑 `src/reinvent_insight/` 下的文件
   - 服务器会自动重启

3. **查看日志**
   - 日志会直接输出到终端
   - 使用 `Ctrl+C` 停止服务器

4. **测试 API**
   - 访问 http://localhost:8001
   - API 文档：http://localhost:8001/docs

5. **提交代码**
   ```bash
   git add .
   git commit -m "你的提交信息"
   git push
   ```

## 环境变量

开发环境需要配置 `.env` 文件：

```env
GEMINI_API_KEY=你的-gemini-api-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=你的密码
```

[[memory:8557045640939925221]]

## 注意事项

1. **不要在生产环境使用** - 这个脚本是专门为开发设计的
2. **保护 .env 文件** - 不要将包含真实 API 密钥的 .env 文件提交到 Git
3. **定期更新依赖** - 运行 `pip install --upgrade -e .` 更新依赖
4. **使用虚拟环境** - 脚本会自动管理虚拟环境，避免污染系统 Python 