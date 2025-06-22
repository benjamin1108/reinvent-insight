import logging
import re
from pathlib import Path
import subprocess

from . import config

logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """清理文件名中的无效字符，替换为空格或下划线。"""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized

class SubtitleDownloader:
    """封装 yt-dlp 调用，用于下载和处理字幕。"""
    def __init__(self, url: str):
        self.url = url
        self.video_title = None

    def get_video_title(self) -> str | None:
        """仅获取视频标题，不进行下载。"""
        if self.video_title:
            return self.video_title
        
        try:
            logger.info(f"正在为链接获取标题: {self.url}")
            result = subprocess.run(
                ['yt-dlp', '--get-title', '--skip-download', '--no-playlist', self.url],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            title = result.stdout.strip()
            self.video_title = sanitize_filename(title)
            logger.info(f"获取到标题: {self.video_title}")
            return self.video_title
        except subprocess.CalledProcessError as e:
            logger.error(f"使用 yt-dlp 获取标题失败: {e.stderr}")
            return None
        except FileNotFoundError:
            logger.error("错误: 'yt-dlp' 命令未找到。请确保它已安装并位于系统的 PATH 中。")
            return None

    def download(self) -> tuple[str | None, Path | None, str | None]:
        """下载字幕并返回清理后的文本内容、文件路径和语言。"""
        if not self.video_title:
            self.get_video_title()
        
        if not self.video_title:
            return None, None, None

        expected_vtt_path = config.SUBTITLE_DIR / f"{self.video_title}.en.vtt"

        if expected_vtt_path.exists():
            logger.info(f"字幕文件已存在，直接使用: {expected_vtt_path.name}")
            subtitle_text = self.clean_vtt(expected_vtt_path.read_text(encoding="utf-8"))
            return subtitle_text, expected_vtt_path, "en (from cache)"

        logger.info(f"尝试下载英文 ('en') 字幕（优先人工，后备自动）...")
        try:
            # 增加 cookies 参数
            command = [
                'yt-dlp',
                '--write-sub',
                '--write-auto-sub',
                '--sub-lang', 'en',
                '--sub-format', 'vtt',
                '--skip-download',
                '--no-playlist',
                '-o', str(config.SUBTITLE_DIR / f"{self.video_title}.%(ext)s"),
            ]
            if config.COOKIES_FILE and config.COOKIES_FILE.exists():
                logger.info(f"使用 Cookies 文件: {config.COOKIES_FILE}")
                command.extend(['--cookies', str(config.COOKIES_FILE)])
            
            command.append(self.url)

            subprocess.run(
                command,
                capture_output=True, text=True, check=True, encoding='utf-8'
            )

            if expected_vtt_path.exists():
                logger.info(f"成功下载字幕: {expected_vtt_path.name}")
                logger.info(f"清理字幕文件: {expected_vtt_path.name}")
                subtitle_text = self.clean_vtt(expected_vtt_path.read_text(encoding="utf-8"))
                
                return subtitle_text, expected_vtt_path, "en (best available)"

        except subprocess.CalledProcessError as e:
            if "no subtitles available" not in e.stderr.lower():
                logger.warning(f"下载英文字幕失败: {e.stderr.strip()}")
            else:
                logger.info("视频没有可用的英文字幕。")
        except FileNotFoundError:
            logger.error("错误: 'yt-dlp' 命令未找到。请确保它已安装并位于系统的 PATH 中。")

        logger.error(f"所有类型的英文字幕都下载失败: {self.url}")
        return None, None, None

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