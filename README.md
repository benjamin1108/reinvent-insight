# Reinvent Insight - YouTube视频深度分析平台

> 基于 **yt-dlp + AI多模型**，集成 **CLI工具**、**Web API** 和 **现代化前端界面**，一键下载并智能总结 YouTube 字幕，生成可替代观看的视频深度笔记。

## ✨ 功能亮点

### 🎯 核心能力
- **自动字幕获取**: 智能优先级下载 *人工英文字幕* → *自动英文字幕*
- **AI多模型支持**: 内置 `Gemini 2.5 Pro`、`XAI`、`Alibaba` 模型，可插拔切换
- **Token优化设计**: 清洗字幕去除时间戳和元数据，字符量缩减80%+，大幅降低API成本
- **推理模式增强**: 通过System Instruction + Reasoning Prompt引导模型逐步推理

### 🚀 多端交互
- **CLI交互界面**: `questionary + rich` 提供中文友好菜单和彩色日志输出
- **Web API服务**: 基于 `FastAPI` 的RESTful API，支持异步任务处理
- **现代化前端**: 科技感UI设计，实时WebSocket通信，markdown渲染
- **摘要分享系统**: 生成分享链接，支持摘要内容的在线查看

### 🔧 企业级特性
- **用户认证**: 简易Bearer Token认证机制
- **任务管理**: 后台异步任务处理，WebSocket实时进度推送
- **文件管理**: 完整的摘要文件列表、查看、分享功能
- **配置灵活**: 支持环境变量配置，多级日志控制

## 📂 项目架构

```
reinvent-insight/
├── 📦 依赖管理
│   ├── pyproject.toml          # uv项目配置 + 依赖声明
│   └── uv.lock                 # 依赖锁定文件
├── 🔧 配置文件
│   ├── .env                    # 环境变量配置
│   └── .gitignore              # Git忽略规则
├── 📝 Prompt模板
│   └── prompt/
│       └── youtbe-deep-summary.txt  # AI深度摘要Prompt
├── 💾 数据目录
│   └── downloads/
│       ├── subtitles/          # 字幕文件存储
│       └── summaries/          # 摘要文件存储
├── 🎨 前端界面
│   └── web/
│       ├── index.html          # 主界面 (1084行)
│       └── share.html          # 分享页面 (567行)
├── 🖥️ 后端服务
│   └── src/youtube_summarizer/
│       ├── __init__.py         # 包初始化
│       ├── config.py           # 配置管理 (56行)
│       ├── logger.py           # 日志系统 (53行)
│       ├── downloader.py       # 字幕下载器 (221行)
│       ├── summarizer.py       # AI摘要器 (137行)
│       ├── main.py             # CLI入口 (99行)
│       └── api.py              # Web API服务 (350行)
└── 🧪 测试目录
    └── test/                   # 测试代码存放
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repo-url>
cd reinvent-insight

# 安装 uv (Python包管理器)
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# 或者
pip install uv                                     # 使用pip安装
```

### 2. 项目初始化

```bash
# 创建虚拟环境并安装依赖
uv venv                         # 创建 .venv 虚拟环境
source .venv/bin/activate       # 激活虚拟环境 (Linux/macOS)
# .venv\Scripts\activate        # Windows激活命令

uv pip install -e .             # 安装项目 (生成CLI命令)
```

### 3. 配置API密钥

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
vim .env
```

**环境变量说明:**
```bash
# === AI模型API密钥 ===
GEMINI_API_KEY="your-gemini-api-key"         # Google Gemini (必需)
XAI_API_KEY="your-xai-api-key"               # XAI (可选)
ALIBABA_API_KEY="your-alibaba-api-key"       # 阿里云 (可选)

# === 系统配置 ===
LOG_LEVEL="INFO"                             # 日志级别: DEBUG/INFO/WARNING/ERROR
PREFERRED_MODEL="Gemini"                     # 默认模型: Gemini/XAI/Alibaba

# === Web服务认证 ===
ADMIN_USERNAME="admin"                       # Web界面用户名
ADMIN_PASSWORD="your-secure-password"        # Web界面密码
```

## 🎮 使用方式

### 方式一：CLI命令行界面

```bash
# 方式1: 已安装脚本命令
youtube-summarizer

# 方式2: 直接运行模块
uv run python src/youtube_summarizer/main.py
```

**交互式操作流程:**
1. 选择AI模型 (Gemini/XAI/Alibaba)
2. 输入YouTube视频链接
3. 等待字幕下载和AI分析
4. 查看生成的Markdown摘要文件

### 方式二：Web服务界面

```bash
# 启动Web API服务器
uvicorn src.youtube_summarizer.api:app --host 0.0.0.0 --port 8000 --reload

# 访问Web界面
# 主界面: http://localhost:8000/web/index.html
# API文档: http://localhost:8000/docs
```

**Web界面功能:**
- 🔐 **用户登录**: 使用配置的用户名密码登录
- 📺 **视频摘要**: 输入YouTube链接，实时查看处理进度
- 📋 **摘要管理**: 查看所有历史摘要文件列表
- 🔗 **分享链接**: 生成摘要分享链接，无需登录即可查看
- 💫 **科技感UI**: 现代化深色主题，代码高亮，响应式设计

## ⚙️ 高级配置

### 模型参数调整
编辑 `src/youtube_summarizer/summarizer.py`:
```python
generation_config = genai.types.GenerationConfig(
    temperature=0.7,        # 创造性 (0-1)
    top_p=0.9,             # 核采样
    top_k=40,              # Top-K采样
    max_output_tokens=8192, # 最大输出长度
)
```

### 自定义Prompt模板
编辑 `prompt/youtbe-deep-summary.txt` 文件，定制AI分析角度和输出格式。

### 日志配置
```bash
# .env 文件中设置
LOG_LEVEL="DEBUG"    # 详细调试信息
LOG_LEVEL="INFO"     # 一般信息 (推荐)
LOG_LEVEL="WARNING"  # 仅警告和错误
LOG_LEVEL="ERROR"    # 仅错误信息
```

## 🤝 开发贡献

### 本地开发
```bash
# 开发模式安装
uv pip install -e ".[dev]"

# 运行测试
pytest test/

# 代码格式化
ruff format src/

# 类型检查
mypy src/
```

### 新增AI模型
1. 在 `src/youtube_summarizer/summarizer.py` 中添加新的摘要器类
2. 在 `config.py` 中添加对应的API密钥配置
3. 更新 `main.py` 中的模型选择菜单

## 📄 许可协议

本项目基于 **MIT License** 开源协议。

---

**⭐ 如果这个项目对你有帮助，请给我们一个Star！**

**🐛 发现问题？** [提交Issue](https://github.com/your-repo/issues)  
**💡 功能建议？** [发起Discussion](https://github.com/your-repo/discussions)
