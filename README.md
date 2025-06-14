# YouTube 视频字幕摘要工具

本项目是一个命令行工具，可以使用 AI 大语言模型（当前支持 Gemini Pro）自动下载 YouTube 视频的英文字幕，并根据高度定制化的 Prompt 生成深度摘要笔记。

## 特性

- **自动字幕下载**: 使用 `yt-dlp` 从 YouTube 下载指定视频的字幕。
- **多模型支持**: 采用可扩展设计，当前已实现 Google Gemini Pro，并为 XAI、Alibaba 的模型预留了接口。
- **高度定制化 Prompt**: 通过独立的 `prompt.txt` 文件定义摘要逻辑，轻松调整输出风格和结构。
- **良好交互体验**: 基于 `questionary` 和 `rich` 库，提供清晰、美观的交互式命令行菜单。
- **可配置日志**: 支持设置不同的日志级别，方便调试。

## 安装与配置

**1. 克隆项目**

```bash
git clone <your-repo-url>
cd youtube-summarizer
```

**2. 安装 `uv` (如果尚未安装)**

`uv` 是一个极速的 Python 包安装和管理工具。

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**3. 创建虚拟环境并安装依赖**

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 使用 uv 安装依赖
uv pip install -e .
```

**4. 配置环境变量**

复制 `.env.example` 文件为 `.env`，并填入你的 API 密钥。

```bash
cp .env.example .env
```

然后编辑 `.env` 文件:
```
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

## 使用方法

在项目根目录下，直接运行以下命令启动交互式程序：

```bash
youtube-summarizer
```

程序会引导您输入 YouTube 视频链接、选择模型、并确认输出文件名。

## 项目结构

```
.
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── prompt/
│   └── youtbe-deep-summary.txt
└── src/
    └── youtube_summarizer/
        ├── __init__.py
        ├── main.py         # 主程序
        ├── config.py       # 配置模块
        ├── downloader.py   # 字幕下载模块
        ├── summarizer.py   # AI 摘要模块
        └── logger.py       # 日志配置模块
```
