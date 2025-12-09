"""Cookie Manager CLI - 命令行接口"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .models import CookieManagerConfig
from .cookie_store import CookieStore
from .importer import CookieImporter
from .manager_service import (
    CookieManagerService,
    run_service_daemon,
    stop_service,
    get_service_status
)

logger = logging.getLogger(__name__)
console = Console()


@click.group()
def cookie_manager():
    """YouTube Cookie Manager - 自动维护 YouTube cookies"""
    pass


@cookie_manager.command()
@click.option('--daemon', is_flag=True, help='以守护进程模式在后台运行')
@click.option('--config', type=click.Path(exists=True), help='配置文件路径')
def start(daemon: bool, config: Optional[str]):
    """启动 Cookie Manager 服务"""
    try:
        # 加载配置
        if config:
            # TODO: 从文件加载配置
            cfg = CookieManagerConfig.from_env()
        else:
            cfg = CookieManagerConfig.from_env()
        
        if daemon:
            console.print("[yellow]以守护进程模式启动服务...[/yellow]")
            console.print("[dim]提示：使用 'reinvent-insight cookie-manager stop' 停止服务[/dim]")
            
            # 在后台运行
            asyncio.run(run_service_daemon(cfg))
        else:
            console.print("[yellow]启动服务（前台模式）...[/yellow]")
            console.print("[dim]按 Ctrl+C 停止服务[/dim]")
            
            # 前台运行
            service = CookieManagerService(cfg)
            service.setup_signal_handlers()
            asyncio.run(service.start())
    
    except KeyboardInterrupt:
        console.print("\n[yellow]服务已停止[/yellow]")
    except Exception as e:
        console.print(f"[red]启动服务失败: {e}[/red]")
        sys.exit(1)


@cookie_manager.command()
def stop():
    """停止 Cookie Manager 服务"""
    try:
        console.print("[yellow]正在停止服务...[/yellow]")
        
        success = stop_service()
        
        if success:
            console.print("[green]✓ 服务已停止[/green]")
        else:
            console.print("[yellow]服务未运行或已停止[/yellow]")
    
    except Exception as e:
        console.print(f"[red]停止服务失败: {e}[/red]")
        sys.exit(1)


@cookie_manager.command()
def restart():
    """重启 Cookie Manager 服务"""
    try:
        console.print("[yellow]正在重启服务...[/yellow]")
        
        # 停止服务
        stop_service()
        
        # 等待一下
        import time
        time.sleep(1)
        
        # 启动服务
        cfg = CookieManagerConfig.from_env()
        asyncio.run(run_service_daemon(cfg))
        
        console.print("[green]✓ 服务已重启[/green]")
    
    except Exception as e:
        console.print(f"[red]重启服务失败: {e}[/red]")
        sys.exit(1)


@cookie_manager.command()
@click.option('--json', 'output_json', is_flag=True, help='以 JSON 格式输出')
def status(output_json: bool):
    """查看 Cookie Manager 服务状态"""
    try:
        # 获取服务状态
        status_info = get_service_status()
        
        if output_json:
            # JSON 输出
            print(json.dumps(status_info, indent=2, ensure_ascii=False))
        else:
            # 美化输出
            if status_info['is_running']:
                console.print(f"[green]✓ 服务正在运行[/green]")
                console.print(f"  PID: {status_info.get('pid', 'N/A')}")
            else:
                console.print(f"[yellow]✗ 服务未运行[/yellow]")
                console.print(f"  {status_info.get('message', '')}")
            
            # 显示 cookie 信息
            try:
                cfg = CookieManagerConfig.from_env()
                store = CookieStore(cfg.cookie_store_path, cfg.netscape_cookie_path)
                
                cookies = store.load_cookies()
                metadata = store.get_metadata()
                
                console.print(f"\n[bold]Cookie 信息:[/bold]")
                console.print(f"  数量: {len(cookies)}")
                console.print(f"  有效性: {'✓ 有效' if store.is_valid() else '✗ 无效'}")
                console.print(f"  最后更新: {metadata.get('last_updated', 'N/A')}")
                console.print(f"  刷新次数: {metadata.get('refresh_count', 0)}")
            except Exception as e:
                console.print(f"\n[dim]无法获取 cookie 信息: {e}[/dim]")
    
    except Exception as e:
        console.print(f"[red]获取状态失败: {e}[/red]")
        sys.exit(1)


@cookie_manager.command()
@click.option('--json', 'output_json', is_flag=True, help='以 JSON 格式输出')
def health(output_json: bool):
    """
    执行完整的健康检查
    
    检查项目：
    - Cookie Manager 服务状态
    - Cookie 文件存在性和新鲜度
    - Cookie 内容有效性
    """
    try:
        from .health_checker import CookieHealthCheck
        
        checker = CookieHealthCheck()
        result = checker.perform_full_check()
        
        if output_json:
            # JSON 输出
            recommendations = checker.get_recommendations(result)
            output = {**result, "recommendations": recommendations}
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            # 美化输出
            checker.print_status_report(result)
            
            # 返回适当的退出码
            if result['overall_status'] == 'unhealthy':
                sys.exit(1)
            elif result['overall_status'] == 'degraded':
                sys.exit(2)
    
    except Exception as e:
        console.print(f"[red]健康检查失败: {e}[/red]")
        sys.exit(1)


@cookie_manager.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--format', type=click.Choice(['netscape', 'json', 'auto']), default='auto',
              help='Cookie 文件格式（默认自动检测）')
def import_cookies(file_path: str, format: str):
    """
    导入 cookies 文件
    
    支持的格式：
    - Netscape cookies.txt 格式（浏览器插件导出）
    - JSON 格式（Playwright/Selenium 导出）
    
    示例：
      reinvent-insight cookie-manager import cookies.txt
      reinvent-insight cookie-manager import cookies.json --format json
    """
    try:
        file_path = Path(file_path)
        console.print(f"[yellow]正在导入 cookies: {file_path}[/yellow]")
        
        # 创建导入器
        importer = CookieImporter()
        
        # 导入 cookies
        if format == 'auto':
            format = None  # 让导入器自动检测
        
        cookies, message = importer.import_cookies(file_path, format)
        
        console.print(f"[green]✓ {message}[/green]")
        
        # 保存到 Cookie Store
        cfg = CookieManagerConfig.from_env()
        store = CookieStore(cfg.cookie_store_path, cfg.netscape_cookie_path)
        
        from .models import CookieMetadata
        metadata = CookieMetadata(source="manual_import", validation_status="valid")
        
        store.save_cookies(cookies, metadata.model_dump())
        
        console.print(f"[green]✓ Cookies 已保存到 {cfg.cookie_store_path}[/green]")
        console.print(f"[green]✓ Netscape 格式已导出到 {cfg.netscape_cookie_path}[/green]")
        
        console.print("\n[dim]提示：使用 'reinvent-insight cookie-manager start' 启动自动刷新服务[/dim]")
    
    except ValueError as e:
        console.print(f"[red]✗ 导入失败: {e}[/red]")
        console.print("\n[yellow]建议：[/yellow]")
        console.print("1. 确保从已登录 YouTube 的浏览器导出 cookies")
        console.print("2. 推荐使用 'Get cookies.txt LOCALLY' 浏览器扩展")
        console.print("3. 确保 cookies 文件格式正确")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]导入失败: {e}[/red]")
        sys.exit(1)


@cookie_manager.command()
def refresh():
    """手动触发 cookie 刷新"""
    try:
        console.print("[yellow]正在刷新 cookies...[/yellow]")
        
        # 创建刷新器
        cfg = CookieManagerConfig.from_env()
        store = CookieStore(cfg.cookie_store_path, cfg.netscape_cookie_path)
        
        from .refresher import CookieRefresher
        refresher = CookieRefresher(
            cookie_store=store,
            browser_type=cfg.browser_type,
            browser_timeout=cfg.browser_timeout,
            headless=True,
            max_retry_count=cfg.max_retry_count
        )
        
        # 执行刷新
        success, message = asyncio.run(refresher.refresh())
        
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]刷新失败: {e}[/red]")
        sys.exit(1)


@cookie_manager.command()
@click.argument('output_path', type=click.Path())
@click.option('--format', type=click.Choice(['netscape', 'json']), default='netscape',
              help='导出格式（默认 netscape）')
def export(output_path: str, format: str):
    """
    导出当前 cookies
    
    示例：
      reinvent-insight cookie-manager export cookies_backup.txt
      reinvent-insight cookie-manager export cookies.json --format json
    """
    try:
        output_path = Path(output_path)
        console.print(f"[yellow]正在导出 cookies 到: {output_path}[/yellow]")
        
        # 加载 cookies
        cfg = CookieManagerConfig.from_env()
        store = CookieStore(cfg.cookie_store_path, cfg.netscape_cookie_path)
        
        cookies = store.load_cookies()
        if not cookies:
            console.print("[red]没有找到 cookies[/red]")
            sys.exit(1)
        
        # 导出
        if format == 'netscape':
            store.export_to_netscape(output_path)
        elif format == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]✓ 成功导出 {len(cookies)} 个 cookies[/green]")
    
    except Exception as e:
        console.print(f"[red]导出失败: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    cookie_manager()
