import logging
import re
from pathlib import Path
import yt_dlp
from . import config
import subprocess

logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """清理文件名中的无效字符，替换为空格或下划线。"""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized

def extract_text_from_srt(srt_content: str) -> str:
    """
    从 SRT 字幕文件中提取纯文本，移除序号和时间戳。
    SRT 格式更简洁，处理起来比 VTT 更高效。
    
    Args:
        srt_content (str): SRT 格式的字幕内容
        
    Returns:
        str: 清理后的纯文本字幕
    """
    lines = srt_content.split('\n')
    text_lines = []
    
    for line in lines:
        line = line.strip()
        
        # 跳过空行
        if not line:
            continue
            
        # 跳过纯数字行 (字幕序号)
        if line.isdigit():
            continue
            
        # 跳过时间戳行 (格式: 00:00:00,000 --> 00:00:00,000)
        if '-->' in line and re.match(r'\d{2}:\d{2}:\d{2},\d{3}', line):
            continue
            
        # 移除 HTML 标签（如果有的话）
        line = re.sub(r'<[^>]+>', '', line)
        
        # 移除常见的字幕格式标记
        line = re.sub(r'[\{\}]', '', line)  # 移除大括号
        line = re.sub(r'\\[nN]', ' ', line)  # 将换行符转为空格
        
        line = line.strip()
        if line and line not in text_lines:  # 避免重复行
            text_lines.append(line)
    
    # 将所有文本行连接成一个段落，用空格分隔
    clean_text = ' '.join(text_lines)
    
    # 清理多余的空格
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

def extract_text_from_vtt(vtt_content: str) -> str:
    """
    从 VTT 字幕文件中提取纯文本，移除时间戳和格式标签。
    
    Args:
        vtt_content (str): VTT 格式的字幕内容
        
    Returns:
        str: 清理后的纯文本字幕
    """
    lines = vtt_content.split('\n')
    text_lines = []
    
    for line in lines:
        line = line.strip()
        
        # 跳过空行
        if not line:
            continue
            
        # 跳过 VTT 头部信息
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
            
        # 跳过时间戳行 (格式: 00:00:00.000 --> 00:00:00.000)
        if '-->' in line and re.match(r'\d{2}:\d{2}:\d{2}\.\d{3}', line):
            continue
            
        # 跳过纯数字行 (字幕序号)
        if line.isdigit():
            continue
            
        # 移除 HTML 标签和格式标记
        line = re.sub(r'<[^>]+>', '', line)
        line = re.sub(r'&[a-zA-Z]+;', '', line)  # 移除 HTML 实体
        
        # 移除字幕中的位置信息 (如 align:start position:0%)
        line = re.sub(r'\b(align|position|size|line):[^\s]+', '', line)
        
        line = line.strip()
        if line and line not in text_lines:  # 避免重复行
            text_lines.append(line)
    
    # 将所有文本行连接成一个段落，用空格分隔
    clean_text = ' '.join(text_lines)
    
    # 清理多余的空格
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

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
            subprocess.run(
                [
                    'yt-dlp',
                    '--write-sub',
                    '--write-auto-sub',
                    '--sub-lang', 'en',
                    '--sub-format', 'vtt',
                    '--skip-download',
                    '--no-playlist',
                    '-o', str(config.SUBTITLE_DIR / f"{self.video_title}.%(ext)s"),
                    self.url
                ],
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

def download_subtitles(url: str) -> tuple[str | None, Path | None, str | None]:
    """
    使用 yt-dlp 下载指定 YouTube URL 的英文字幕。
    优先级: 1. 英文人工字幕, 2. 英文自动字幕
    使用 SRT 格式以简化后续文本处理。

    Args:
        url (str): YouTube 视频的 URL.

    Returns:
        A tuple containing:
        - str: 字幕的纯文本内容，如果失败则为 None.
        - Path: 字幕文件的路径，如果失败则为 None.
        - str: 下载的字幕语言代码 (e.g., "en")，如果失败则为 None.
    """
    logger.info(f"开始处理 URL: {url}")

    try:
        # 先获取视频信息，特别是标题
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', 'untitled_video')
            clean_title = sanitize_filename(video_title)
            logger.info(f"获取到视频标题: {video_title}")

        output_path = config.SUBTITLE_DIR / f"{clean_title}.%(ext)s"

        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],  # 只下载英文字幕
            'subtitlesformat': 'srt',  # 指定使用 SRT 格式
            'skip_download': True,
            'outtmpl': str(output_path),
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("正在下载字幕 (SRT 格式)...")
            error_code = ydl.download([url])

            if error_code != 0:
                logger.error("yt-dlp 下载时返回错误码。")
                return None, None, None

            # 查找下载的字幕文件 (先尝试 srt，再尝试 vtt)
            logger.debug(f"在目录中查找字幕文件: {config.SUBTITLE_DIR}")
            all_files = list(config.SUBTITLE_DIR.glob(f"{clean_title}*"))
            logger.debug(f"找到的所有相关文件: {[f.name for f in all_files]}")
            
            subtitle_file = next(config.SUBTITLE_DIR.glob(f"{clean_title}*.srt"), None)
            if not subtitle_file:
                # 如果没有找到 SRT，尝试 VTT
                subtitle_file = next(config.SUBTITLE_DIR.glob(f"{clean_title}*.vtt"), None)
                logger.info("未找到 SRT 格式，尝试使用 VTT 格式")

            if not subtitle_file or not subtitle_file.exists():
                logger.error(f"字幕下载失败或未找到。检查视频是否有英文字幕。")
                logger.error(f"查找的文件模式: {clean_title}*.srt 和 {clean_title}*.vtt")
                return None, None, None

            # 从文件名推断语言代码
            lang_code = subtitle_file.suffixes[-2].strip('.') if len(subtitle_file.suffixes) > 1 else 'unknown'
            logger.success(f"字幕 ({lang_code}) 成功下载到: {subtitle_file}")

            # 读取并清理字幕内容
            subtitle_content = subtitle_file.read_text(encoding='utf-8')
            
            # 根据文件扩展名选择合适的处理函数
            if subtitle_file.suffix.lower() == '.srt':
                clean_text = extract_text_from_srt(subtitle_content)
                logger.info(f"使用 SRT 格式处理")
            else:  # .vtt 或其他格式
                clean_text = extract_text_from_vtt(subtitle_content)
                logger.info(f"使用 VTT 格式处理")
            
            logger.info(f"原始字幕长度: {len(subtitle_content)} 字符，清理后: {len(clean_text)} 字符")

            # 在最前面加上视频标题，便于模型理解
            clean_text_with_title = f"【视频标题】{video_title}\n" + clean_text
            
            # 保存清理过时间线的纯文本字幕文件（带标题）
            clean_subtitle_path = config.SUBTITLE_DIR / f"{clean_title}_clean.txt"
            clean_subtitle_path.write_text(clean_text_with_title, encoding='utf-8')
            logger.info(f"清理后的纯文本字幕已保存到: {clean_subtitle_path}")
            
            return clean_text_with_title, subtitle_file, lang_code

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"下载错误: {e}")
        if "is not a valid URL" in str(e):
            logger.error("提供的 URL 无效。请输入一个有效的 YouTube 视频链接。")
        elif "Private video" in str(e):
            logger.error("这是一个私有视频，无法访问。")
        elif "Video unavailable" in str(e):
            logger.error("该视频不可用。")
        else:
            logger.error("请检查网络连接和视频 URL 是否正确。")
        return None, None, None
    except Exception as e:
        logger.error(f"处理字幕时发生未知错误: {e}", exc_info=True)
        return None, None, None 