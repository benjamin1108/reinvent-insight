import logging
import re
from pathlib import Path
import subprocess
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from . import config

logger = logging.getLogger(__name__)

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

class SubtitleDownloader:
    """封装 yt-dlp 调用，用于下载和处理字幕。"""
    def __init__(self, url: str):
        self.url = url
        self.metadata: Optional[VideoMetadata] = None

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

    def _download_subtitles_with_retry(self, subtitle_langs: list[str]) -> bool:
        """使用重试机制下载字幕。"""
        for lang in subtitle_langs:
            for attempt in range(config.DOWNLOAD_RETRY_COUNT + 1):
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
                        return True
                    
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.strip() if e.stderr else str(e)
                    
                    if "403" in error_msg or "Forbidden" in error_msg:
                        logger.warning(f"遇到 403 错误，等待后重试...")
                        if attempt < config.DOWNLOAD_RETRY_COUNT:
                            time.sleep(5 * (attempt + 1))  # 递增等待时间
                            continue
                    
                    if "no subtitles available" in error_msg.lower():
                        logger.info(f"视频没有可用的 {lang} 字幕")
                        break
                    
                    logger.warning(f"下载 {lang} 字幕失败 (第 {attempt + 1} 次): {error_msg}")
                    if attempt < config.DOWNLOAD_RETRY_COUNT:
                        time.sleep(3 * (attempt + 1))
                        continue
                    
                except FileNotFoundError:
                    logger.error("错误: 'yt-dlp' 命令未找到。请确保它已安装并位于系统的 PATH 中。")
                    return False
                
                # 如果所有重试都失败了，尝试下一种语言
                break
        
        return False

    def download(self) -> tuple[str | None, VideoMetadata | None]:
        """下载字幕并返回清理后的文本内容和完整的元数据对象。"""
        if not self._fetch_metadata() or not self.metadata:
            return None, None

        expected_vtt_path = config.SUBTITLE_DIR / f"{self.metadata.sanitized_title}.en.vtt"

        # 检查是否已经存在字幕文件
        if expected_vtt_path.exists():
            logger.info(f"字幕文件已存在，直接使用: {expected_vtt_path.name}")
            subtitle_text = self.clean_vtt(expected_vtt_path.read_text(encoding="utf-8"))
            return subtitle_text, self.metadata

        # 尝试下载字幕，按优先级排序
        subtitle_languages = ['en', 'en-US', 'en-GB']
        
        if self._download_subtitles_with_retry(subtitle_languages):
            # 找到下载的字幕文件
            for lang in subtitle_languages:
                vtt_path = config.SUBTITLE_DIR / f"{self.metadata.sanitized_title}.{lang}.vtt"
                if vtt_path.exists():
                    logger.info(f"使用 {lang} 字幕文件: {vtt_path.name}")
                    subtitle_text = self.clean_vtt(vtt_path.read_text(encoding="utf-8"))
                    return subtitle_text, self.metadata
        
        logger.error(f"所有尝试都失败，无法下载字幕: {self.url}")
        return None, None

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