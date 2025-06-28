import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import yaml

from .logger import get_logger

logger = logging.getLogger(__name__)

# 加载 .env 文件
load_dotenv()

# 获取项目根目录
# 在部署环境中，程序应该从正确的工作目录启动
# 工作目录应该包含 web/ 目录和 .env 文件
PROJECT_ROOT = Path.cwd().resolve()

# 验证是否在正确的目录
if not (PROJECT_ROOT / "web").exists():
    # 如果当前目录没有 web，尝试开发环境路径
    dev_root = Path(__file__).parent.parent.parent
    if (dev_root / "web").exists():
        PROJECT_ROOT = dev_root
    else:
        logger.error(f"错误：找不到 web 目录。当前目录：{PROJECT_ROOT}")
        logger.error("请确保从包含 web 目录的项目根目录运行程序")

# 加载 .env 文件
# 它会自动寻找项目根目录下的 .env 文件
env_path = PROJECT_ROOT / ".env"
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
PROMPT_FILE_PATH = PROJECT_ROOT / "prompt" / "youtbe-deep-summary.txt"

# --- 模型配置 ---
PREFERRED_MODEL = os.getenv("PREFERRED_MODEL", "Gemini")

# --- 下载配置 ---
DOWNLOAD_DIR = PROJECT_ROOT / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True) # 确保下载目录存在
SUBTITLE_DIR = DOWNLOAD_DIR / "subtitles"
SUBTITLE_DIR.mkdir(exist_ok=True) # 确保字幕目录存在
OUTPUT_DIR = DOWNLOAD_DIR / "summaries"
OUTPUT_DIR.mkdir(exist_ok=True) # 确保输出目录存在

# --- 认证配置 ---
ADMIN_USERNAME = os.getenv("USERNAME") or os.getenv("ADMIN_USERNAME") or "admin"
ADMIN_PASSWORD = os.getenv("PASSWORD") or os.getenv("ADMIN_PASSWORD") or "password"

# --- 基础路径 ---
# 定义输出目录
OUTPUT_DIR = PROJECT_ROOT / "downloads" / "summaries"
# 定义字幕下载目录
SUBTITLE_DIR = PROJECT_ROOT / "downloads" / "subtitles"
# 定义 Cookies 文件路径 (即使文件不存在也没关系，程序会检查)
COOKIES_FILE = PROJECT_ROOT / "cookies.txt"

# --- 并发控制 ---
# 在并行生成章节时，每个API调用之间的延迟（秒）
CHAPTER_GENERATION_DELAY_SECONDS = 0.5

def check_gemini_api_key():
    """检查 Gemini API Key 是否已配置"""
    if not GEMINI_API_KEY:
        logger.error("错误: GEMINI_API_KEY 未在 .env 文件中配置。")
        logger.error("请将 .env.example 复制为 .env 并填入您的 Google Gemini API 密钥。")
        return False
    return True 