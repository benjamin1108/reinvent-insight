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
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# --- 日志配置 ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# --- Prompt 配置 ---
PROMPT_FILE_PATH = PROJECT_ROOT / "prompt" / "youtbe-deep-summary.txt"

# --- 模型配置 ---
# 注意：模型配置已迁移到 config/model_config.yaml
# 请使用 model_config.get_model_client(task_type) 获取模型客户端
# PREFERRED_MODEL 已废弃，保留用于向后兼容
PREFERRED_MODEL = os.getenv("PREFERRED_MODEL", "Gemini")

# 模型配置文件路径
MODEL_CONFIG_PATH = PROJECT_ROOT / "config" / "model_config.yaml"

# --- 下载配置 ---
DOWNLOAD_DIR = PROJECT_ROOT / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True) # 确保下载目录存在
SUBTITLE_DIR = DOWNLOAD_DIR / "subtitles"
SUBTITLE_DIR.mkdir(exist_ok=True) # 确保字幕目录存在
OUTPUT_DIR = DOWNLOAD_DIR / "summaries"
OUTPUT_DIR.mkdir(exist_ok=True) # 确保输出目录存在
TTS_TEXT_DIR = DOWNLOAD_DIR / "tts_texts"
TTS_TEXT_DIR.mkdir(exist_ok=True) # 确保 TTS 文本目录存在

# --- 认证配置 ---
# 优先读取 .env 中的 ADMIN_USERNAME / ADMIN_PASSWORD，避免被系统级 USERNAME / PASSWORD 覆盖
def _get_stripped_env(*keys, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            return value.strip()
    return default

ADMIN_USERNAME = _get_stripped_env("ADMIN_USERNAME", "USERNAME", default="admin")
ADMIN_PASSWORD = _get_stripped_env("ADMIN_PASSWORD", "PASSWORD", default="password")
# 密码哈希（优先使用，比明文密码更安全）
ADMIN_PASSWORD_HASH = _get_stripped_env("ADMIN_PASSWORD_HASH", default="")

# --- 基础路径 ---
# 定义输出目录
OUTPUT_DIR = PROJECT_ROOT / "downloads" / "summaries"
# 定义字幕下载目录
SUBTITLE_DIR = PROJECT_ROOT / "downloads" / "subtitles"
# 定义 Cookies 文件路径 - 使用用户主目录统一存储
COOKIES_FILE = Path.home() / ".cookies"

# --- 下载配置 ---
# yt-dlp 用户代理，模拟真实浏览器
YT_DLP_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 下载重试次数
DOWNLOAD_RETRY_COUNT = 3

# 下载超时时间（秒）
DOWNLOAD_TIMEOUT = 60

# --- 并发控制 ---
# 在并行生成章节时，每个API调用之间的延迟（秒）
CHAPTER_GENERATION_DELAY_SECONDS = 0.5

# --- 任务队列配置 ---
# 最大并发分析任务数（同时运行的 worker 数量）
MAX_CONCURRENT_ANALYSIS_TASKS = int(os.getenv("MAX_CONCURRENT_ANALYSIS_TASKS", "3"))

# 任务队列最大长度（等待中的任务数量限制）
ANALYSIS_QUEUE_MAX_SIZE = int(os.getenv("ANALYSIS_QUEUE_MAX_SIZE", "100"))

# 任务超时时间（秒）- 单个分析任务的最大执行时间
ANALYSIS_TASK_TIMEOUT = int(os.getenv("ANALYSIS_TASK_TIMEOUT", "3600"))  # 默认 1 小时

# --- Cookie Manager 配置 ---
# Cookie 刷新间隔（小时）
COOKIE_REFRESH_INTERVAL = int(os.getenv("COOKIE_REFRESH_INTERVAL", "6"))
# 浏览器类型
COOKIE_BROWSER_TYPE = os.getenv("COOKIE_BROWSER_TYPE", "chromium")
# Cookie Store 路径 - 使用用户主目录统一存储
COOKIE_STORE_PATH = Path.home() / ".cookies.json"

def check_gemini_api_key():
    """检查 Gemini API Key 是否已配置"""
    if not GEMINI_API_KEY:
        logger.error("错误: GEMINI_API_KEY 未在 .env 文件中配置。")
        logger.error("请将 .env.example 复制为 .env 并填入您的 Google Gemini API 密钥。")
        return False
    return True

def check_legacy_cookie_paths():
    """检查并提示迁移旧的 cookie 文件"""
    import shutil
    
    legacy_cookies = PROJECT_ROOT / ".cookies"
    legacy_store = PROJECT_ROOT / ".cookies.json"
    
    new_cookies = Path.home() / ".cookies"
    new_store = Path.home() / ".cookies.json"
    
    migrated = False
    
    # 检查并迁移 Netscape 格式的 cookies
    if legacy_cookies.exists() and not new_cookies.exists():
        try:
            shutil.copy2(legacy_cookies, new_cookies)
            new_cookies.chmod(0o600)  # 设置安全权限
            logger.info(f"已自动迁移 .cookies 到 {new_cookies}")
            migrated = True
        except Exception as e:
            logger.warning(f"无法自动迁移 .cookies: {e}")
            logger.info(f"请手动复制 {legacy_cookies} 到 {new_cookies}")
    
    # 检查并迁移 JSON 格式的 cookie store
    if legacy_store.exists() and not new_store.exists():
        try:
            shutil.copy2(legacy_store, new_store)
            new_store.chmod(0o600)  # 设置安全权限
            logger.info(f"已自动迁移 .cookies.json 到 {new_store}")
            migrated = True
        except Exception as e:
            logger.warning(f"无法自动迁移 .cookies.json: {e}")
            logger.info(f"请手动复制 {legacy_store} 到 {new_store}")
    
    # 如果有迁移，提示用户
    if migrated:
        logger.info("Cookie 文件已迁移到用户主目录")
        logger.info("旧文件已保留在项目目录，可以手动删除")
    
    # 如果旧文件存在但新文件也存在，只提示
    elif (legacy_cookies.exists() or legacy_store.exists()) and (new_cookies.exists() or new_store.exists()):
        logger.info("检测到项目目录下的旧 cookie 文件")
        logger.info(f"当前使用: {new_cookies}")
        logger.info(f"旧文件位置: {legacy_cookies}")
        logger.info("如果不再需要，可以删除项目目录下的旧 cookie 文件")

# --- 文档处理配置 ---
# 文本文件最大大小（字节）
MAX_TEXT_FILE_SIZE = int(os.getenv("MAX_TEXT_FILE_SIZE", str(10 * 1024 * 1024)))  # 默认 10MB

# 二进制文件最大大小（字节）
MAX_BINARY_FILE_SIZE = int(os.getenv("MAX_BINARY_FILE_SIZE", str(50 * 1024 * 1024)))  # 默认 50MB

# 支持的文本格式
SUPPORTED_TEXT_FORMATS = ['.txt', '.md']

# 支持的二进制格式
SUPPORTED_BINARY_FORMATS = ['.pdf', '.docx']

# --- 可视化解读配置 ---
# 是否启用可视化解读生成功能
VISUAL_INTERPRETATION_ENABLED = os.getenv("VISUAL_INTERPRETATION_ENABLED", "true").lower() == "true"

# text2html 提示词文件路径
TEXT2HTML_PROMPT_PATH = PROJECT_ROOT / "prompt" / "text2html.txt"

# 可视化 HTML 存储目录（与深度解读同目录）
VISUAL_HTML_DIR = OUTPUT_DIR

# --- Visual Long Image 配置 ---
# 是否启用长图生成功能
VISUAL_LONG_IMAGE_ENABLED = os.getenv("VISUAL_LONG_IMAGE_ENABLED", "true").lower() == "true"

# 长图存储目录
VISUAL_LONG_IMAGE_DIR = OUTPUT_DIR / "images"

# 截图视口宽度（像素）
# 默认 1080px 适合移动端分享，减少两侧留白
# 如需桌面端宽度，可设置为 1920
VISUAL_SCREENSHOT_VIEWPORT_WIDTH = int(os.getenv("VISUAL_SCREENSHOT_VIEWPORT_WIDTH", "1080"))

# 截图等待时间（秒，用于等待图表渲染）
VISUAL_SCREENSHOT_WAIT_TIME = int(os.getenv("VISUAL_SCREENSHOT_WAIT_TIME", "3"))

# 浏览器启动超时（秒）
VISUAL_SCREENSHOT_BROWSER_TIMEOUT = int(os.getenv("VISUAL_SCREENSHOT_BROWSER_TIMEOUT", "30"))

# --- 版本控制配置 ---
# 是否启用版本选择器
ENABLE_VERSION_SELECTOR = os.getenv("ENABLE_VERSION_SELECTOR", "false").lower() == "true"

# 版本显示策略: 'all' | 'latest_only' | 'latest_per_type'
VERSION_DISPLAY_STRATEGY = os.getenv("VERSION_DISPLAY_STRATEGY", "latest_only")

# 是否自动清理旧版本（Ultra模式下自动清理）
AUTO_CLEANUP_OLD_VERSIONS = os.getenv("AUTO_CLEANUP_OLD_VERSIONS", "true").lower() == "true"

# 保留的最大版本数
MAX_VERSIONS_TO_KEEP = int(os.getenv("MAX_VERSIONS_TO_KEEP", "1"))

# --- TTS 预生成配置 ---
# 是否启用 TTS 预生成服务（已禁用，改为按需生成）
TTS_PREGENERATE_ENABLED = os.getenv("TTS_PREGENERATE_ENABLED", "false").lower() == "true"

# 是否显示音频播放按钮（默认显示）
TTS_AUDIO_BUTTON_ENABLED = os.getenv("TTS_AUDIO_BUTTON_ENABLED", "true").lower() == "true"

# 任务队列最大长度
TTS_QUEUE_MAX_SIZE = int(os.getenv("TTS_QUEUE_MAX_SIZE", "100"))

# 任务间隔（秒）
TTS_WORKER_DELAY = float(os.getenv("TTS_WORKER_DELAY", "1.0"))

# 最大重试次数
TTS_MAX_RETRIES = int(os.getenv("TTS_MAX_RETRIES", "3"))

# 单任务超时（秒）
TTS_TASK_TIMEOUT = int(os.getenv("TTS_TASK_TIMEOUT", "600"))

# TTS 预处理规则版本
TTS_PREPROCESSING_VERSION = "1.0.0"
