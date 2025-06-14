# YouTube 视频字幕深度摘要工具

> 基于 **yt-dlp + Gemini 2.5 Pro**，一键下载并智能总结 YouTube 字幕，生成可替代观看的视频深度笔记。

## ✨ 功能亮点

1. **自动字幕获取**  
   - 优先下载 *人工中文字幕* → *人工英文字幕* → *自动英文字幕*  
   - 同步支持 `vtt / srt` 双格式；若无 srt 自动回退 vtt
2. **Token 友好**  
   - 清洗字幕去掉时间戳 & 元数据，字符量缩减 80%+，大幅降低 API 成本
3. **多模型可插拔**  
   - 默认 `Gemini-2.5-pro-preview`（已开启推理模式）  
   - 预留 XAI / Alibaba 接口，后续可扩展
4. **交互式 CLI**  
   - `questionary + rich` 提供中文友好菜单 & 彩色日志
5. **可配置日志**  
   - `.env` 一行切换 `DEBUG / INFO / WARNING` 级别
6. **智能命名**  
   - 自动用 *清理后的视频标题* 作为 Markdown 文件名，可手动覆盖

## 📂 项目结构

```
.
├── pyproject.toml          # uv 依赖管理
├── README.md               # 当前文件
├── prompt/
│   └── youtbe-deep-summary.txt  # 深度摘要 Prompt 模板
└── src/
    └── youtube_summarizer/
        ├── __init__.py
        ├── config.py        # 环境变量 & 路径
        ├── logger.py        # rich 日志封装
        ├── downloader.py    # 字幕下载 & 清洗
        ├── summarizer.py    # 智能摘要（支持推理模式）
        └── main.py          # CLI 入口
```

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <repo-url>
cd youtube-summarizer
```

### 2. 安装 `uv`
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS / Linux
```

### 3. 创建虚拟环境 & 安装依赖
```bash
uv venv                    # 创建 .venv
source .venv/bin/activate  # 激活
uv pip install -e .        # 安装本项目（生成 youtube-summarizer 命令）
```

### 4. 配置环境变量
```bash
cp .env.example .env
vim .env
# 填入 Google Gemini API Key
GEMINI_API_KEY="sk-xxxx"
# 可选：日志级别
LOG_LEVEL="INFO"   # DEBUG / INFO / WARNING / ERROR
```

### 5. 运行
```bash
# 方式一（已生成脚本）
youtube-summarizer

# 方式二（不安装脚本）
uv run python src/youtube_summarizer/main.py
```

跟随 CLI 提示输入视频地址，即可在 `downloads/summaries` 目录生成 `*.md` 深度笔记。

## 🛠 常用参数
| 场景 | 配置方法 |
| ---- | -------- |
| 切换模型 | 在 CLI 中选择（默认 Gemini） |
| 开启调试日志 | `.env` 设置 `LOG_LEVEL=DEBUG` |
| 自定义 Prompt | 编辑 `prompt/youtbe-deep-summary.txt` |
| 修改下载目录 | `config.py` 中 `DOWNLOAD_DIR` 常量 |

## 🤖 推理模式说明
- 通过 **System Instruction** + **Reasoning Prompt** 双保险，引导模型进行 *逐步推理*  
- 生成配置：`temperature=0.7 / top_p=0.9 / top_k=40 / max_tokens=8192`  
- 如需关闭推理，可在 `summarizer.py` 将 `reasoning_prompt` 换回简单模板

## 💡 故障排查
| 问题 | 解决方案 |
| ---- | -------- |
| 无法获取字幕 | 检查视频是否公开字幕；尝试代理；查看 `downloads/subtitles` 目录文件 |
| 404 model not found | 确认 `.env` 中 API Key 有权限；检查 `summarizer.py` 模型名称 |
| CLI 卡住或乱码 | 终端需支持 UTF-8；Windows 请使用 `PowerShell 7+` 或 `Windows Terminal` |

## 📜 许可协议

本项目遵循 **MIT License**，请自由 Fork / 修改 / 商用，但需保留原作者署名。
