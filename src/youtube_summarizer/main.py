import logging
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import config, downloader, summarizer
from .logger import setup_logger

console = Console()
logger = logging.getLogger(__name__)

def get_user_input():
    """通过交互式提示获取用户输入。"""
    console.print(Panel("欢迎使用 YouTube 视频字幕摘要工具", style="bold blue", expand=False))
    
    url = questionary.text(
        "请输入 YouTube 视频链接:",
        validate=lambda text: True if ("https://www.youtube.com/" in text or "https://youtu.be/" in text) else "请输入一个有效的 YouTube 链接。",
    ).ask()

    if not url:
        return None
        
    return url

def run():
    """主程序运行函数。"""
    setup_logger(config.LOG_LEVEL)

    if not config.check_gemini_api_key():
        return

    try:
        url = get_user_input()

        if not url:
            console.print("\n操作已取消。", style="yellow")
            return

        model_name = config.PREFERRED_MODEL

        # 1. 下载字幕
        subtitle_text = None
        video_title = None
        with console.status("[bold green]正在下载字幕...", spinner="dots") as status:
            subtitle_text, subtitle_path, subtitle_lang = downloader.download_subtitles(url)
            if not subtitle_text:
                console.print("\n[bold red]错误: 无法获取字幕，程序终止。[/bold red]")
                return
            
            # 从字幕文件路径中提取视频标题
            video_title = subtitle_path.stem.split('.')[0]  # 移除语言代码和扩展名
            status.update(f"[bold green]成功下载 '{subtitle_lang}' 字幕。[/bold green]")

        # 2. 读取 Prompt
        try:
            prompt_text = config.PROMPT_FILE_PATH.read_text(encoding="utf-8")
            logger.info("成功加载 Prompt 文件。")
        except FileNotFoundError:
            console.print(f"\n[bold red]错误: Prompt 文件未找到于 {config.PROMPT_FILE_PATH}[/bold red]")
            return
            
        # 3. 获取摘要器并执行摘要
        summary_md = None
        with console.status(f"[bold green]正在使用 {model_name} 进行摘要，请稍候...", spinner="earth") as status:
            summarizer_instance = summarizer.get_summarizer(model_name)
            if not summarizer_instance:
                console.print(f"\n[bold red]错误: 无法初始化模型 {model_name}。[/bold red]")
                return
            
            summary_md = summarizer_instance.summarize(subtitle_text, prompt_text)
            if not summary_md:
                console.print("\n[bold red]错误: 生成摘要失败，请检查日志获取详细信息。[/bold red]")
                return

        # 4. 保存摘要
        output_filename = video_title
        output_path = config.OUTPUT_DIR / f"{output_filename}.md"
        output_path.write_text(summary_md, encoding="utf-8")

        success_message = Text.from_markup(f"""[bold green]✓ 任务完成！[/bold green]

摘要已成功保存到: [cyan]{output_path}[/cyan]
""")
        console.print(Panel(success_message, title="[bold]成功[/bold]", border_style="green"))

    except NotImplementedError:
        console.print(f"\n[bold yellow]提示: 您选择的模型 '{model_name}' 当前尚未支持。[/bold yellow]")
    except KeyboardInterrupt:
        console.print("\n\n操作被用户中断。程序退出。", style="bold yellow")
    except Exception as e:
        logger.error(f"程序发生意外错误: {e}", exc_info=True)
        console.print(f"\n[bold red]发生未知错误: {e}[/bold red]")
        console.print("[yellow]请检查日志文件获取更详细的调试信息。[/yellow]")


if __name__ == '__main__':
    run() 