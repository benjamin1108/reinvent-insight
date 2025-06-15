import logging
import re
from pathlib import Path
import yt_dlp
from . import config

logger = logging.getLogger(__name__)

def clean_filename(filename: str) -> str:
    """
    从文件名中移除无效字符。
    """
    # 移除非法字符
    cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)
    # 将多个空格替换为单个空格
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

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
            clean_title = clean_filename(video_title)
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
            
            # 保存清理过时间线的纯文本字幕文件
            clean_subtitle_path = config.SUBTITLE_DIR / f"{clean_title}_clean.txt"
            clean_subtitle_path.write_text(clean_text, encoding='utf-8')
            logger.info(f"清理后的纯文本字幕已保存到: {clean_subtitle_path}")
            
            return clean_text, subtitle_file, lang_code

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