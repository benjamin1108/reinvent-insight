import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 项目的根目录 (youtube-summarizer/)
# Path(__file__) -> .../src/youtube_summarizer/config.py
# .parent -> .../src/youtube_summarizer
# .parent -> .../src
# .parent -> .../
BASE_DIR = Path(__file__).parent.parent.parent

# 加载 .env 文件
# 它会自动寻找项目根目录下的 .env 文件
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info("成功加载 .env 文件。")
else:
    logger.warning(".env 文件未找到。请确保已创建并配置了 API 密钥。")

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
ALIBABA_API_KEY = os.getenv("ALIBABA_API_KEY")

# --- 日志配置 ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# --- Prompt 配置 ---
PROMPT_FILE_PATH = BASE_DIR / "prompt" / "youtbe-deep-summary.txt"

# --- 下载配置 ---
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True) # 确保下载目录存在
SUBTITLE_DIR = DOWNLOAD_DIR / "subtitles"
SUBTITLE_DIR.mkdir(exist_ok=True) # 确保字幕目录存在
OUTPUT_DIR = DOWNLOAD_DIR / "summaries"
OUTPUT_DIR.mkdir(exist_ok=True) # 确保输出目录存在


def check_gemini_api_key():
    """检查 Gemini API Key 是否已配置"""
    if not GEMINI_API_KEY:
        logger.error("错误: GEMINI_API_KEY 未在 .env 文件中配置。")
        logger.error("请将 .env.example 复制为 .env 并填入您的 Google Gemini API 密钥。")
        return False
    return True 