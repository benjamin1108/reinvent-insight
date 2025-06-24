import logging
import asyncio
import uuid
import argparse
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape

from . import config, downloader
from .api import serve as serve_web
from .logger import setup_logger
from .task_manager import manager as task_manager
from .workflow import run_deep_summary_workflow, reassemble_from_task_id
from .downloader import VideoMetadata

console = Console()
logger = logging.getLogger(__name__)

async def process_single_video(url: str, show_status: bool = True):
    """
    处理单个视频链接的核心逻辑，从下载到完成摘要。
    """
    if not url or not isinstance(url, str) or not url.strip():
        logger.warning(f"接收到无效的URL: '{url}'，已跳过。")
        return

    url = url.strip()
    console.print(Panel(f"开始处理视频链接: [link={url}]{url}[/link]", style="bold blue", expand=False))

    subtitle_text, metadata = None, None
    
    def download_action():
        nonlocal subtitle_text, metadata
        try:
            dl = downloader.SubtitleDownloader(url)
            subtitle_text, metadata = dl.download()

            if not subtitle_text or not metadata:
                console.print(f"\n[bold red]错误: 无法获取 '{url}' 的字幕或元数据，已跳过。[/bold red]")
                return False
            console.print(f"[bold green]成功为 '{escape(metadata.title)}' 下载字幕。[/bold green]")
            return True
        except Exception as e:
            console.print(f"\n[bold red]处理 '{url}' 时发生下载错误: {e}[/bold red]")
            return False

    if show_status:
        with console.status("[bold green]正在下载字幕...", spinner="dots"):
            success = download_action()
    else:
        console.print(f"开始下载 '{url}' 的字幕...")
        success = download_action()

    if not success:
        return
    
    if not metadata or not subtitle_text:
         console.print(f"\n[bold red]错误: 未能获取到 '{url}' 的视频元数据或字幕内容。[/bold red]")
         return

    task_id = str(uuid.uuid4())
    model_name = config.PREFERRED_MODEL
    content_for_summary = f"视频标题: {metadata.title}\n\n{subtitle_text}"
    
    await summary_workflow_async(task_id, model_name, content_for_summary, metadata, show_status=show_status)

    final_state = task_manager.get_task_state(task_id)
    if final_state and final_state.status == 'completed':
        output_path = final_state.result_path
        success_message = Text.from_markup(f"""[bold green]✓ 视频 '{escape(metadata.title)}' 处理完成！[/bold green]
摘要已成功保存到: [cyan]{escape(output_path)}[/cyan]
""")
        console.print(Panel(success_message, title="[bold]任务成功[/bold]", border_style="green"))
    else:
        error_message = "未知错误，任务未成功完成。"
        if final_state and final_state.logs:
            error_message = final_state.logs[-1]
        console.print(Panel(f"""[bold red]✗ 视频 '{escape(metadata.title)}' 处理失败。[/bold red]
原因: {escape(error_message)}""", title="[bold]任务失败[/bold]", border_style="red"))
        console.print("[yellow]请检查日志文件获取更详细的调试信息。[/yellow]")
    
    # 在任务之间添加一个小的延迟
    await asyncio.sleep(2)

    return url

def get_user_input():
    """通过交互式提示获取用户输入。"""
    console.print(Panel("欢迎使用 YouTube 视频字幕摘要工具", style="bold blue", expand=False))
    
    url = questionary.text(
        "请输入 YouTube 视频链接:",
        validate=lambda text: True if ("https://www.youtube.com/" in text or "https://youtu.be/"  in text or "http://www.youtube.com/" in text) else "请输入一个有效的 YouTube 链接。",
    ).ask()

    if not url:
        return None
        
    return url

async def summary_workflow_async(task_id: str, model_name: str, transcript: str, metadata: VideoMetadata, show_status: bool = True):
    """仅包含异步工作流的协程。"""
    safe_title = escape(metadata.title)
    console.print(Panel(f"任务ID: [bold cyan]{task_id}[/bold cyan]\n视频标题: [bold yellow]{safe_title}[/bold yellow]", 
                        title="[bold green]任务已创建[/bold green]", expand=False))
    
    # 创建异步任务
    workflow_task = asyncio.create_task(
        run_deep_summary_workflow(
            task_id=task_id,
            model_name=model_name,
            transcript=transcript,
            video_metadata=metadata
        )
    )
    task_manager.create_task(task_id, workflow_task)
    
    if show_status:
        with console.status(f"[bold green]正在使用 {model_name} 进行深度摘要...", spinner="earth") as status:
            while not workflow_task.done():
                task_state = task_manager.get_task_state(task_id)
                if task_state and task_state.logs:
                    latest_log = task_state.logs[-1]
                    status.update(f"[bold green]{latest_log}[/bold green]")
                await asyncio.sleep(1)
    else:
        # 在非状态显示模式下，我们只等待任务完成
        await workflow_task

def run_interactive_mode():
    """仅运行交互式模式的函数。"""
    try:
        if not config.check_gemini_api_key():
            return

        url = get_user_input()
        if not url:
            console.print("\n操作已取消。", style="yellow")
            return
        
        asyncio.run(process_single_video(url, show_status=True))

    except NotImplementedError:
        console.print(f"\n[bold yellow]提示: 您选择的模型 '{config.PREFERRED_MODEL}' 当前尚未支持。[/bold yellow]")
    except KeyboardInterrupt:
        console.print("\n\n操作被用户中断。程序退出。", style="bold yellow")
    except Exception as e:
        logger.error(f"程序发生意外错误: {e}", exc_info=True)
        console.print(f"\n[bold red]发生未知错误: {escape(str(e))}[/bold red]")
        console.print("[yellow]请检查日志文件获取更详细的调试信息。[/yellow]")

def cli():
    """定义和处理命令行参数"""
    parser = argparse.ArgumentParser(
        description="""YouTube 视频字幕深度摘要工具。""",
        epilog="""使用 'python -m src.youtube_summarizer.main <子命令> --help' 来查看特定子命令的详细帮助。
例如: python -m src.youtube_summarizer.main --file my_videos.txt""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # --- 顶层参数 ---
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--url', type=str, help='直接提供单个 YouTube 视频链接进行处理。')
    group.add_argument('--file', type=str, help='提供一个文件路径，文件中每行包含一个 YouTube 视频链接进行批量处理。')
    parser.add_argument('-c', '--concurrency', type=int, default=3, help='批量处理时的最大并发任务数。 (默认: 3)')

    # --- 子命令 ---
    subparsers = parser.add_subparsers(
        dest='command', 
        title='可用的子命令',
        description='运行 "main.py <子命令> --help" 获取更多信息。'
    )

    # 'web' 子命令
    parser_web = subparsers.add_parser('web', help='启动 Web UI 和 API 服务器。')
    parser_web.add_argument('--host', type=str, default='0.0.0.0', help='服务器监听的 IP 地址。')
    parser_web.add_argument('--port', type=int, default=8001, help='服务器监听的端口。')
    parser_web.add_argument('--reload', action='store_true', help='开启开发模式，代码变动时自动重启服务。')

    # 'reassemble' 子命令
    parser_reassemble = subparsers.add_parser('reassemble', help='根据任务ID重新组装报告。')
    parser_reassemble.add_argument('task_id', type=str, help='要重新组装的任务ID。')
    
    args = parser.parse_args()

    # 根据参数决定执行哪个任务
    setup_logger(config.LOG_LEVEL)

    if args.url:
        if not config.check_gemini_api_key(): return
        asyncio.run(process_single_video(args.url, show_status=True))

    elif args.file:
        if not config.check_gemini_api_key(): return
        console.print(f"[bold]进入批量处理模式，文件: [green]{args.file}[/green][/bold]")
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            if not urls:
                console.print(f"[bold yellow]警告: 文件 '{args.file}' 为空或不包含任何有效链接。[/bold yellow]")
                return

            console.print(f"共发现 {len(urls)} 个链接，将以最大并发数 {args.concurrency} 开始处理...")
            
            async def batch_process(urls: list[str], concurrency: int):
                semaphore = asyncio.Semaphore(concurrency)
                tasks = []

                async def process_with_semaphore(url: str, index: int):
                    async with semaphore:
                        console.rule(f"[bold cyan]开始处理第 {index+1}/{len(urls)} 个视频[/bold cyan]")
                        await process_single_video(url, show_status=False)

                for i, url in enumerate(urls):
                    task = process_with_semaphore(url, i)
                    tasks.append(task)
                
                await asyncio.gather(*tasks)

            asyncio.run(batch_process(urls, args.concurrency))
            console.rule("[bold green]🎉 所有视频处理完毕! 🎉[/bold green]")

        except FileNotFoundError:
            console.print(f"\n[bold red]错误: 文件未找到 -> {args.file}[/bold red]")
        except Exception as e:
            logger.error(f"批量处理文件时发生错误: {e}", exc_info=True)
            console.print(f"\n[bold red]批量处理时发生未知错误: {escape(str(e))}[/bold red]")

    elif args.command == 'web':
        console.print(f"准备启动 Web 服务器，监听于 [green]{args.host}:{args.port}[/green]...")
        if args.reload:
            console.print("[yellow]已开启开发模式 (自动重载)。[/yellow]")
        serve_web(host=args.host, port=args.port, reload=args.reload)
    elif args.command == 'reassemble':
        console.print(f"接收到重新组装任务，Task ID: [cyan]{args.task_id}[/cyan]")
        asyncio.run(reassemble_from_task_id(args.task_id))
    else:
        # 如果没有提供任何参数或子命令，则运行默认的交互式程序
        run_interactive_mode()

if __name__ == '__main__':
    cli() 