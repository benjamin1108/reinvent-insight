"""
一个独立的批处理脚本，用于读取 todo.txt 文件中的 YouTube 链接，
并以多线程方式批量生成摘要。
"""

import sys
import time
import logging
import concurrent.futures
from pathlib import Path

# 将 src 目录添加到 Python 路径中，以便可以导入 youtube_summarizer 模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel

# 现在可以安全地从 youtube_summarizer 导入
from youtube_summarizer import config, downloader, summarizer
from youtube_summarizer.logger import setup_logger
from youtube_summarizer.markdown_processor import process_markdown_file

console = Console()
logger = logging.getLogger(__name__)

# --- 配置 ---
TODO_FILE_PATH = project_root / "downloads" / "todo.txt"
MAX_WORKERS = 5  # 可根据需要调整并发线程数
DELAY_BETWEEN_TASKS = 1  # 秒，防止 API 限流


def parse_todo_file(path: Path) -> list[str]:
    """解析 todo.txt 文件，提取所有 YouTube 链接。"""
    if not path.exists():
        console.print(f"[bold red]错误: 任务文件未找到于 {path}[/bold red]")
        return []

    urls = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "youtube.com/watch?v=" in line or "youtu.be/" in line:
                urls.append(line)
    
    console.print(f"从任务文件中发现 {len(urls)} 个链接。")
    return urls


def process_url(url: str):
    """处理单个 URL：下载、摘要、保存，并处理跳过逻辑。"""
    try:
        # 1. 预检查：获取视频标题以确定输出文件名
        # 使用现有的下载器逻辑来获取标题，但不下载字幕，仅获取信息
        temp_downloader = downloader.SubtitleDownloader(url)
        video_title = temp_downloader.get_video_title()
        
        if not video_title:
            console.print(f"[[bold yellow]跳过[/bold yellow]] 无法获取链接的标题: {url}")
            return

        # 2. 检查文件是否存在
        output_filename = downloader.sanitize_filename(video_title)
        output_path = config.OUTPUT_DIR / f"{output_filename}.md"
        
        if output_path.exists():
            console.print(f"[[bold cyan]跳过[/bold cyan]] 摘要已存在: [dim]{output_path.name}[/dim]")
            return

        console.print(f"[[bold blue]处理中[/bold blue]] 正在处理: [dim]{video_title}[/dim]")
        
        # 3. 下载字幕 (这次是实际下载)
        subtitle_text, _, subtitle_lang = temp_downloader.download()
        if not subtitle_text:
            console.print(f"[[bold red]失败[/bold red]] 无法下载字幕: [dim]{video_title}[/dim]")
            return
        
        # 4. 读取 Prompt
        prompt_text = config.PROMPT_FILE_PATH.read_text(encoding="utf-8")
        
        # 5. 生成摘要
        model_name = config.PREFERRED_MODEL
        summarizer_instance = summarizer.get_summarizer(model_name)
        summary_md = summarizer_instance.summarize(subtitle_text, prompt_text)
        
        if not summary_md:
            console.print(f"[[bold red]失败[/bold red]] 生成摘要失败: [dim]{video_title}[/dim]")
            return
            
        # 6. 保存摘要
        output_path.write_text(summary_md, encoding="utf-8")
        
        # 7. 后处理：添加章节分隔符
        try:
            if process_markdown_file(output_path):
                console.print(f"[[bold green]✓ 成功[/bold green]] 已保存并格式化摘要: [cyan]{output_path.name}[/cyan]")
            else:
                console.print(f"[[bold green]✓ 成功[/bold green]] 已保存摘要: [cyan]{output_path.name}[/cyan] [yellow](格式化失败)[/yellow]")
        except Exception as e:
            logger.warning(f"文档后处理失败: {e}")
            console.print(f"[[bold green]✓ 成功[/bold green]] 已保存摘要: [cyan]{output_path.name}[/cyan] [yellow](格式化出错)[/yellow]")
        
    except Exception as e:
        logger.error(f"处理链接 {url} 时发生严重错误: {e}", exc_info=True)
        console.print(f"[[bold red]错误[/bold red]] 处理链接 {url} 时发生异常: {e}")


def main():
    """主函数，编排整个批处理流程。"""
    setup_logger(config.LOG_LEVEL)

    if not config.check_gemini_api_key():
        return

    console.print(Panel("YouTube 摘要批量处理脚本", style="bold blue", expand=False))
    
    urls = parse_todo_file(TODO_FILE_PATH)
    if not urls:
        return

    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 使用 future 对象来跟踪每个任务的状态
        futures = []
        for url in urls:
            futures.append(executor.submit(process_url, url))
            time.sleep(DELAY_BETWEEN_TASKS) # 在提交每个任务后稍作延迟
            
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            # 可以在这里处理每个任务的结果或异常，但 process_url 内部已处理
            pass

    end_time = time.time()
    console.print(f"\n[bold green]所有任务处理完毕，总耗时: {end_time - start_time:.2f} 秒。[/bold green]")


if __name__ == "__main__":
    main() 