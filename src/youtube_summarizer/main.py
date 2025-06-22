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

async def summary_workflow_async(task_id: str, model_name: str, transcript: str, video_title: str):
    """仅包含异步工作流的协程。"""
    safe_title = escape(video_title)
    console.print(Panel(f"任务ID: [bold cyan]{task_id}[/bold cyan]\n视频标题: [bold yellow]{safe_title}[/bold yellow]", 
                        title="[bold green]任务已创建[/bold green]", expand=False))
    
    # 创建异步任务
    workflow_task = asyncio.create_task(
        run_deep_summary_workflow(
            task_id=task_id,
            model_name=model_name,
            transcript=transcript,
            video_title=video_title
        )
    )
    task_manager.create_task(task_id, workflow_task)
    
    with console.status(f"[bold green]正在使用 {model_name} 进行深度摘要...", spinner="earth") as status:
        while not workflow_task.done():
            task_state = task_manager.get_task_state(task_id)
            if task_state and task_state.logs:
                latest_log = task_state.logs[-1]
                status.update(f"[bold green]{latest_log}[/bold green]")
            await asyncio.sleep(1)

def run():
    """同步的程序入口点，负责处理同步IO和启动异步工作流。"""
    setup_logger(config.LOG_LEVEL)

    try:
        if not config.check_gemini_api_key():
            return

        # --- 同步部分 ---
        url = get_user_input()
        if not url:
            console.print("\n操作已取消。", style="yellow")
            return

        subtitle_text, video_title = None, None
        with console.status("[bold green]正在下载字幕...", spinner="dots") as status:
            try:
                dl = downloader.SubtitleDownloader(url)
                # download() 方法会先获取标题，再下载字幕
                subtitle_text, _, subtitle_lang = dl.download()
                video_title = dl.video_title # 从实例中获取标题

                if not subtitle_text:
                    console.print("\n[bold red]错误: 无法获取字幕，程序终止。[/bold red]")
                    return
                status.update(f"[bold green]成功下载 '{subtitle_lang}' 字幕。[/bold green]")
            except ValueError as e:
                console.print(f"\n[bold red]错误: {e}[/bold red]")
                return
        
        if not video_title or not subtitle_text:
             console.print("\n[bold red]错误: 未能获取到视频标题或字幕内容。[/bold red]")
             return

        # --- 异步部分 ---
        task_id = str(uuid.uuid4())
        model_name = config.PREFERRED_MODEL
        
        # 将标题和字幕拼接，为大模型提供更完整的上下文
        content_for_summary = f"视频标题: {video_title}\n\n{subtitle_text}"
        
        asyncio.run(summary_workflow_async(task_id, model_name, content_for_summary, video_title))

        # 检查最终结果
        final_state = task_manager.get_task_state(task_id)
        if final_state and final_state.status == 'completed':
            output_path = f"./tasks/{task_id}/final_report.md"
            success_message = Text.from_markup(f"""[bold green]✓ 任务完成！[/bold green]

摘要已成功保存到: [cyan]{escape(output_path)}[/cyan]
""")
            console.print(Panel(success_message, title="[bold]成功[/bold]", border_style="green"))
        else:
            error_message = "未知错误，任务未成功完成。"
            if final_state and final_state.logs:
                error_message = final_state.logs[-1]
            console.print(f"\n[bold red]错误: {escape(error_message)}[/bold red]")
            console.print("[yellow]请检查日志文件获取更详细的调试信息。[/yellow]")

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
        description="""YouTube 视频字幕深度摘要工具。

这是一个多功能的命令行工具，支持以下几种操作模式:
1. 交互式模式 (默认): 直接运行，不带任何参数，将引导您输入YouTube链接并开始摘要。
2. Web 服务器模式: 启动一个 Web UI 和 API 服务器。
3. 重新组装模式: 从已有的任务中间文件，重新生成最终报告。""",
        epilog="""使用 'python -m src.youtube_summarizer.main <子命令> --help' 来查看特定子命令的详细帮助。
例如: python -m src.youtube_summarizer.main web --help""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(
        dest='command', 
        title='可用的子命令',
        description='运行 "main.py <子命令> --help" 获取更多信息。'
    )

    # 默认交互式命令 (无子命令时)
    # run() 函数处理

    # 'web' 子命令
    parser_web = subparsers.add_parser('web', help='启动 Web UI 和 API 服务器。')
    parser_web.add_argument('--host', type=str, default='0.0.0.0', help='服务器监听的 IP 地址。')
    parser_web.add_argument('--port', type=int, default=8001, help='服务器监听的端口。')
    parser_web.add_argument('--reload', action='store_true', help='开启开发模式，代码变动时自动重启服务。')

    # 'reassemble' 子命令
    parser_reassemble = subparsers.add_parser('reassemble', help='根据任务ID重新组装报告。')
    parser_reassemble.add_argument('task_id', type=str, help='要重新组装的任务ID。')
    
    args = parser.parse_args()

    if args.command == 'web':
        console.print(f"准备启动 Web 服务器，监听于 [green]{args.host}:{args.port}[/green]...")
        if args.reload:
            console.print("[yellow]已开启开发模式 (自动重载)。[/yellow]")
        serve_web(host=args.host, port=args.port, reload=args.reload)
    elif args.command == 'reassemble':
        console.print(f"接收到重新组装任务，Task ID: [cyan]{args.task_id}[/cyan]")
        asyncio.run(reassemble_from_task_id(args.task_id))
    else:
        # 如果没有提供子命令，则运行默认的交互式程序
        run()

if __name__ == '__main__':
    cli() 