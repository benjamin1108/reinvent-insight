import logging
import re
from pathlib import Path
import subprocess
import json
import time
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from . import config

logger = logging.getLogger(__name__)


class DownloadErrorType(Enum):
    """下载错误类型枚举"""
    NETWORK_TIMEOUT = "network_timeout"
    ACCESS_FORBIDDEN = "access_forbidden"
    NO_SUBTITLES = "no_subtitles"
    TOOL_MISSING = "tool_missing"
    INVALID_URL = "invalid_url"
    VIDEO_NOT_FOUND = "video_not_found"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


@dataclass
class DownloadError:
    """结构化的下载错误信息"""
    error_type: DownloadErrorType
    message: str
    technical_details: Optional[str] = None
    suggestions: Optional[List[str]] = None
    retry_after: Optional[int] = None  # 秒数
    
    def to_dict(self) -> dict:
        """转换为字典格式，用于 JSON 序列化"""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "technical_details": self.technical_details,
            "suggestions": self.suggestions,
            "retry_after": self.retry_after
        }


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 5.0  # 秒
    max_delay: float = 30.0  # 秒
    exponential_base: float = 2.0


class RetryStrategy:
    """重试策略管理器"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        
        # 定义不可重试的错误类型
        self.non_retryable_errors = {
            DownloadErrorType.NO_SUBTITLES,
            DownloadErrorType.VIDEO_NOT_FOUND,
            DownloadErrorType.TOOL_MISSING,
            DownloadErrorType.INVALID_URL,
        }
    
    def should_retry(self, error: DownloadError, attempt: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            error: 下载错误对象
            attempt: 当前尝试次数（从 0 开始）
            
        Returns:
            bool: 是否应该重试
        """
        # 检查是否达到最大重试次数
        if attempt >= self.config.max_attempts:
            return False
        
        # 检查错误类型是否可重试
        if error.error_type in self.non_retryable_errors:
            return False
        
        return True
    
    def get_delay(self, error: DownloadError, attempt: int) -> float:
        """
        计算重试延迟时间
        
        Args:
            error: 下载错误对象
            attempt: 当前尝试次数（从 0 开始）
            
        Returns:
            float: 延迟秒数
        """
        # 如果错误指定了重试延迟，使用指定的延迟
        if error.retry_after is not None:
            return float(error.retry_after)
        
        # 根据错误类型采用不同的重试策略
        if error.error_type == DownloadErrorType.NETWORK_TIMEOUT:
            # 指数退避策略
            delay = self.config.base_delay * (self.config.exponential_base ** attempt)
            return min(delay, self.config.max_delay)
        
        elif error.error_type == DownloadErrorType.ACCESS_FORBIDDEN:
            # 递增延迟策略 (5s, 10s, 15s)
            delay = self.config.base_delay * (attempt + 1)
            return min(delay, self.config.max_delay)
        
        elif error.error_type == DownloadErrorType.RATE_LIMITED:
            # 固定延迟 30 秒
            return 30.0
        
        else:
            # 默认使用指数退避
            delay = self.config.base_delay * (self.config.exponential_base ** attempt)
            return min(delay, self.config.max_delay)

@dataclass
class VideoMetadata:
    """封装从视频中提取的所有元数据。"""
    title: str
    upload_date: str  # YYYYMMDD
    video_url: str
    is_reinvent: bool = False
    course_code: Optional[str] = None
    level: Optional[str] = None
    # 内部使用字段
    sanitized_title: str = field(init=False, repr=False)

    def __post_init__(self):
        self.sanitized_title = sanitize_filename(self.title)
        self._parse_reinvent_info()

    def _parse_reinvent_info(self):
        """
        从标题中解析 re:Invent 相关信息。
        新逻辑：只要标题包含 "aws re:invent" 和年份，就认为是 re:Invent 视频。
        然后尝试解析课程代码。
        """
        # 主匹配：判断是否为 re:Invent 视频
        main_pattern = re.compile(r"aws\s+re:invent\s+\d{4}", re.IGNORECASE)
        if main_pattern.search(self.title):
            self.is_reinvent = True

            # 首先检查是否为Keynote
            if re.search(r"keynote", self.title, re.IGNORECASE):
                self.level = "Keynote"
                # Keynote可能没有课程代码，但尝试解析
                course_pattern = re.compile(
                    r"\(([A-Z]{3,}\d{2,3}[A-Z0-9-]*)\)",
                    re.IGNORECASE
                )
                course_match = course_pattern.search(self.title)
                if course_match:
                    self.course_code = course_match.group(1).upper()
            else:
                # 非Keynote视频，尝试解析课程代码和级别
                course_pattern = re.compile(
                    r"\(([A-Z]{3,}(\d{2,3})[A-Z0-9-]*)\)",
                    re.IGNORECASE
                )
                course_match = course_pattern.search(self.title)
                if course_match:
                    self.course_code = course_match.group(1).upper()
                    level_digits = course_match.group(2)
                    # 根据课程编号的第一个数字判断级别
                    first_digit = level_digits[0]
                    if first_digit == '1':
                        self.level = "100"
                    elif first_digit == '2':
                        self.level = "200"
                    elif first_digit == '3':
                        self.level = "300"
                    elif first_digit == '4':
                        self.level = "400"
                    else:
                        self.level = "100"  # 默认为基础级别


def sanitize_filename(filename: str) -> str:
    """清理文件名中的无效字符，替换为空格或下划线。"""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized


def classify_download_error(
    stderr: str = "",
    returncode: int = 0,
    exception: Optional[Exception] = None
) -> DownloadError:
    """
    根据 yt-dlp 的输出分类错误
    
    Args:
        stderr: yt-dlp 的错误输出
        returncode: 进程返回码
        exception: Python 异常对象（如果有）
        
    Returns:
        DownloadError: 结构化的错误信息
    """
    stderr_lower = stderr.lower() if stderr else ""
    
    # 检查工具是否缺失
    if exception and isinstance(exception, FileNotFoundError):
        return DownloadError(
            error_type=DownloadErrorType.TOOL_MISSING,
            message="yt-dlp 工具未安装或未找到",
            technical_details=str(exception),
            suggestions=[
                "安装 yt-dlp: pip install yt-dlp",
                "或使用系统包管理器安装",
                "确保 yt-dlp 在系统 PATH 中"
            ]
        )
    
    # 检查 403 错误
    if "403" in stderr or "forbidden" in stderr_lower:
        return DownloadError(
            error_type=DownloadErrorType.ACCESS_FORBIDDEN,
            message="YouTube 服务器拒绝了访问请求",
            technical_details=stderr[:500] if stderr else None,
            suggestions=[
                "更新 Cookie 文件（运行 cookie 管理器）",
                "检查网络连接和代理设置",
                "稍后重试（可能是临时限制）"
            ]
        )
    
    # 检查网络超时
    if any(keyword in stderr_lower for keyword in ["timeout", "timed out", "connection reset"]):
        return DownloadError(
            error_type=DownloadErrorType.NETWORK_TIMEOUT,
            message="网络连接超时",
            technical_details=stderr[:500] if stderr else None,
            suggestions=[
                "检查网络连接是否正常",
                "尝试使用 VPN 或更换网络",
                "稍后重试"
            ]
        )
    
    # 检查限流错误
    if "429" in stderr or "rate limit" in stderr_lower or "too many requests" in stderr_lower:
        return DownloadError(
            error_type=DownloadErrorType.RATE_LIMITED,
            message="请求过于频繁，已被限流",
            technical_details=stderr[:500] if stderr else None,
            suggestions=[
                "等待 30 秒后重试",
                "减少并发下载数量"
            ],
            retry_after=30
        )
    
    # 检查视频不存在
    if any(keyword in stderr_lower for keyword in ["not found", "404", "video unavailable", "private video", "private"]):
        return DownloadError(
            error_type=DownloadErrorType.VIDEO_NOT_FOUND,
            message="视频不存在或无法访问",
            technical_details=stderr[:500] if stderr else None,
            suggestions=[
                "检查 URL 是否正确",
                "视频可能已被删除或设为私密",
                "确认视频在您的地区可访问"
            ]
        )
    
    # 检查无字幕
    if "subtitles" in stderr_lower or "captions" in stderr_lower:
        return DownloadError(
            error_type=DownloadErrorType.NO_SUBTITLES,
            message="该视频没有可用的字幕",
            technical_details=stderr[:500] if stderr else None,
            suggestions=[
                "该视频可能没有上传字幕",
                "尝试其他视频"
            ]
        )
    
    # 未知错误
    return DownloadError(
        error_type=DownloadErrorType.UNKNOWN,
        message="下载过程中发生未知错误",
        technical_details=stderr[:500] if stderr else (str(exception) if exception else None),
        suggestions=[
            "查看技术详情了解更多信息",
            "尝试重新下载",
            "如果问题持续，请联系技术支持"
        ]
    )

def normalize_youtube_url(url: str) -> tuple[str, dict]:
    """
    标准化 YouTube URL，移除不必要的参数，并提取元数据。
    
    支持的格式：
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&t=2209s
    - https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID
    - https://youtu.be/VIDEO_ID
    - https://youtu.be/VIDEO_ID?si=SHARE_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    
    Args:
        url: 原始 YouTube URL
        
    Returns:
        tuple: (标准化的URL, 元数据字典)
        元数据包含: video_id, timestamp, playlist_id, share_id 等
        
    Raises:
        ValueError: 如果 URL 格式无效
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL 必须是非空字符串")
    
    url = url.strip()
    metadata = {}
    video_id = None
    
    # 优先级1: 匹配嵌入式格式 youtube.com/embed/VIDEO_ID
    embed_pattern = re.compile(
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})(?:[?/].*)?',
        re.IGNORECASE
    )
    embed_match = embed_pattern.match(url)
    if embed_match:
        video_id = embed_match.group(1)
        logger.debug(f"匹配到嵌入式格式，video_id: {video_id}")
    
    # 优先级2: 匹配短链接格式 youtu.be/VIDEO_ID
    if not video_id:
        short_pattern = re.compile(
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})(?:\?(.*))?',
            re.IGNORECASE
        )
        short_match = short_pattern.match(url)
        if short_match:
            video_id = short_match.group(1)
            query_string = short_match.group(2)
            logger.debug(f"匹配到短链接格式，video_id: {video_id}")
            
            # 解析查询参数
            if query_string:
                params = dict(param.split('=', 1) for param in query_string.split('&') if '=' in param)
                if 'si' in params:
                    metadata['share_id'] = params['si']
                if 't' in params:
                    metadata['timestamp'] = params['t']
    
    # 优先级3: 匹配标准格式 youtube.com/watch?v=VIDEO_ID
    if not video_id:
        standard_pattern = re.compile(
            r'(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?(.+)',
            re.IGNORECASE
        )
        standard_match = standard_pattern.match(url)
        if standard_match:
            query_string = standard_match.group(1)
            params = dict(param.split('=', 1) for param in query_string.split('&') if '=' in param)
            
            if 'v' in params:
                video_id = params['v'][:11]  # 确保只取前11位
                logger.debug(f"匹配到标准格式，video_id: {video_id}")
                
                # 提取其他参数
                if 't' in params:
                    metadata['timestamp'] = params['t']
                if 'list' in params:
                    metadata['playlist_id'] = params['list']
                if 'index' in params:
                    metadata['playlist_index'] = params['index']
    
    # 验证 video_id
    if not video_id:
        error_msg = f"无法从 URL 中提取有效的视频 ID: {url}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # 验证 video_id 格式（11位字母数字、下划线、连字符）
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        error_msg = f"提取的视频 ID 格式无效: {video_id}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    metadata['video_id'] = video_id
    normalized_url = f"https://www.youtube.com/watch?v={video_id}"
    
    logger.info(f"URL 标准化成功: {url} -> {normalized_url}")
    if metadata:
        logger.debug(f"提取的元数据: {metadata}")
    
    return normalized_url, metadata

class SubtitleDownloader:
    """封装 yt-dlp 调用，用于下载和处理字幕。"""
    def __init__(self, url: str):
        # 标准化 URL，移除不必要的参数
        self.original_url = url
        try:
            self.url, self.url_metadata = normalize_youtube_url(url)
            logger.info(f"标准化后的 URL: {self.url}")
            if self.url_metadata:
                logger.debug(f"URL 元数据: {self.url_metadata}")
        except ValueError as e:
            logger.error(f"URL 标准化失败: {e}")
            raise
        self.metadata: Optional[VideoMetadata] = None
        self.retry_strategy = RetryStrategy()
        self.error_history: List[DownloadError] = []

    def _get_base_command(self) -> list[str]:
        """获取基础的 yt-dlp 命令参数，包含反爬虫选项。"""
        # 在下载前检查 cookie 健康状态
        from .cookie_health_check import check_and_warn
        check_and_warn()
        
        command = [
            'yt-dlp',
            '--no-playlist',
            '--user-agent', config.YT_DLP_USER_AGENT,
            '--socket-timeout', str(config.DOWNLOAD_TIMEOUT),
            '--retries', str(config.DOWNLOAD_RETRY_COUNT),
            '--fragment-retries', str(config.DOWNLOAD_RETRY_COUNT),
            '--extractor-retries', str(config.DOWNLOAD_RETRY_COUNT),
            '--sleep-interval', '1',
            '--max-sleep-interval', '3',
            '--sleep-subtitles', '1',
        ]
        
        # 添加 cookies 文件
        if config.COOKIES_FILE and config.COOKIES_FILE.exists():
            command.extend(['--cookies', str(config.COOKIES_FILE)])
            logger.info(f"使用 Cookies 文件: {config.COOKIES_FILE}")
        else:
            logger.warning(f"Cookies 文件不存在: {config.COOKIES_FILE}")
        
        return command

    def _fetch_metadata(self) -> bool:
        """使用 yt-dlp --dump-json 获取并解析所有元数据。"""
        try:
            logger.info(f"正在为链接获取元数据: {self.url}")
            command = self._get_base_command()
            command.extend(['--dump-json'])
            command.append(self.url)

            result = subprocess.run(
                command,
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            data = json.loads(result.stdout)
            
            self.metadata = VideoMetadata(
                title=data.get('title', 'Unknown Title'),
                upload_date=data.get('upload_date', '19700101'), # YYYYMMDD
                video_url=data.get('webpage_url', self.url)
            )
            logger.info(f"成功获取元数据: {self.metadata.title}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"使用 yt-dlp 获取元数据失败: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("错误: 'yt-dlp' 命令未找到。请确保它已安装并位于系统的 PATH 中。")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"解析 yt-dlp 输出的 JSON 失败: {e}")
            return False

    def _download_subtitles_with_retry(self, subtitle_langs: list[str]) -> tuple[bool, Optional[DownloadError]]:
        """
        使用重试机制下载字幕。
        
        Returns:
            tuple: (是否成功, 错误对象)
        """
        for lang in subtitle_langs:
            attempt = 0
            while attempt <= self.retry_strategy.config.max_attempts:
                try:
                    logger.info(f"尝试下载 {lang} 字幕 (第 {attempt + 1} 次)...")
                    
                    command = self._get_base_command()
                    command.extend([
                        '--write-sub',
                        '--write-auto-sub',
                        '--sub-lang', lang,
                        '--sub-format', 'vtt',
                        '--skip-download',
                        '-o', str(config.SUBTITLE_DIR / f"{self.metadata.sanitized_title}.%(ext)s"),
                    ])
                    command.append(self.url)

                    result = subprocess.run(
                        command,
                        capture_output=True, text=True, check=True, encoding='utf-8'
                    )
                    
                    # 检查是否成功下载了字幕文件
                    expected_vtt_path = config.SUBTITLE_DIR / f"{self.metadata.sanitized_title}.{lang}.vtt"
                    if expected_vtt_path.exists():
                        logger.info(f"成功下载 {lang} 字幕: {expected_vtt_path.name}")
                        return True, None
                    
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.strip() if e.stderr else str(e)
                    
                    # 分类错误
                    download_error = classify_download_error(
                        stderr=error_msg,
                        returncode=e.returncode
                    )
                    self.error_history.append(download_error)
                    
                    logger.warning(
                        f"下载 {lang} 字幕失败 (第 {attempt + 1} 次): "
                        f"{download_error.error_type.value} - {download_error.message}"
                    )
                    
                    # 如果是无字幕错误，尝试下一种语言
                    if download_error.error_type == DownloadErrorType.NO_SUBTITLES:
                        logger.info(f"视频没有可用的 {lang} 字幕，尝试下一种语言")
                        break
                    
                    # 判断是否应该重试
                    if not self.retry_strategy.should_retry(download_error, attempt):
                        logger.error(f"错误不可重试或已达到最大重试次数")
                        return False, download_error
                    
                    # 计算延迟时间并等待
                    delay = self.retry_strategy.get_delay(download_error, attempt)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    
                    attempt += 1
                    continue
                    
                except FileNotFoundError as e:
                    download_error = classify_download_error(exception=e)
                    self.error_history.append(download_error)
                    logger.error(f"工具缺失: {download_error.message}")
                    return False, download_error
                
                # 如果成功但没有返回，说明文件不存在，继续重试
                attempt += 1
        
        # 所有语言都尝试失败
        last_error = self.error_history[-1] if self.error_history else DownloadError(
            error_type=DownloadErrorType.UNKNOWN,
            message="所有尝试都失败，无法下载字幕",
            suggestions=["检查视频是否有字幕", "尝试其他视频"]
        )
        return False, last_error

    def download(self) -> tuple[str | None, VideoMetadata | None, DownloadError | None]:
        """
        下载字幕并返回清理后的文本内容和完整的元数据对象。
        
        Returns:
            tuple: (字幕文本, 视频元数据, 错误信息)
            如果成功，错误信息为 None
            如果失败，字幕文本和元数据为 None
        """
        # 获取元数据
        if not self._fetch_metadata() or not self.metadata:
            error = DownloadError(
                error_type=DownloadErrorType.UNKNOWN,
                message="无法获取视频元数据",
                suggestions=["检查 URL 是否正确", "检查网络连接"]
            )
            return None, None, error

        expected_vtt_path = config.SUBTITLE_DIR / f"{self.metadata.sanitized_title}.en.vtt"

        # 检查是否已经存在字幕文件
        if expected_vtt_path.exists():
            logger.info(f"字幕文件已存在，直接使用: {expected_vtt_path.name}")
            subtitle_text = self.clean_vtt(expected_vtt_path.read_text(encoding="utf-8"))
            return subtitle_text, self.metadata, None

        # 尝试下载字幕，按优先级排序
        subtitle_languages = ['en', 'en-US', 'en-GB']
        
        success, error = self._download_subtitles_with_retry(subtitle_languages)
        
        if success:
            # 找到下载的字幕文件
            for lang in subtitle_languages:
                vtt_path = config.SUBTITLE_DIR / f"{self.metadata.sanitized_title}.{lang}.vtt"
                if vtt_path.exists():
                    logger.info(f"使用 {lang} 字幕文件: {vtt_path.name}")
                    subtitle_text = self.clean_vtt(vtt_path.read_text(encoding="utf-8"))
                    return subtitle_text, self.metadata, None
        
        # 下载失败
        logger.error(f"所有尝试都失败，无法下载字幕: {self.url}")
        if error:
            logger.error(f"最终错误: {error.error_type.value} - {error.message}")
        
        return None, None, error

    @staticmethod
    def clean_vtt(vtt_content: str) -> str:
        """清理 VTT 字幕文件内容，移除时间戳和元数据，只保留纯文本。"""
        lines = vtt_content.splitlines()
        text_lines = []
        for line in lines:
            if "WEBVTT" in line or "Kind:" in line or "Language:" in line or "-->" in line or not line.strip():
                continue
            cleaned_line = re.sub(r'<[^>]+>', '', line)
            text_lines.append(cleaned_line.strip())
        
        unique_lines = []
        for line in text_lines:
            if not unique_lines or unique_lines[-1] != line:
                unique_lines.append(line)
                
        return "\n".join(unique_lines) 