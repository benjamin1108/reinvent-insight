#!/usr/bin/env python3
"""
Quick-Insight生成工具

命令行工具，用于将markdown文章转换为精美的HTML网页。
支持单文件生成、批量处理、增量更新等功能。

使用方法:
    python -m reinvent_insight.tools.generate_insights [OPTIONS] [FILES...]
    
示例:
    # 生成单个文件
    python -m reinvent_insight.tools.generate_insights article.md
    
    # 批量生成所有文章
    python -m reinvent_insight.tools.generate_insights --all
    
    # 强制重新生成
    python -m reinvent_insight.tools.generate_insights --force --all
    
    # 使用自定义品牌配置
    python -m reinvent_insight.tools.generate_insights --brand-config custom.json article.md
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.markup import escape

# 导入项目模块
try:
    from .. import config
    from ..text2html_generator import Text2HtmlGenerator, GenerationResult
    from ..text2html_prompts import get_prompts_manager
    from ..logger import setup_logger
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保从项目根目录运行此脚本")
    sys.exit(1)

console = Console()
logger = logging.getLogger(__name__)

class QuickInsightCLI:
    """Quick-Insight命令行工具主类"""
    
    def __init__(self):
        self.generator: Optional[Text2HtmlGenerator] = None
        self.progress: Optional[Progress] = None
        
    def setup_logging(self, verbose: bool = False):
        """设置日志系统"""
        log_level = "DEBUG" if verbose else "INFO"
        setup_logger(log_level)
    
    def load_brand_config(self, config_file: Optional[Path]) -> Optional[Dict]:
        """加载品牌配置文件"""
        if not config_file:
            return None
        
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                console.print(f"✅ 加载品牌配置: {config_file}")
                return custom_config
            else:
                console.print(f"⚠️  配置文件不存在: {config_file}")
                return None
        except Exception as e:
            console.print(f"❌ 加载配置文件失败: {e}")
            return None
    
    def init_generator(self, brand_config: Optional[Dict] = None, model_name: str = "Gemini", debug: bool = False):
        """初始化生成器"""
        try:
            self.generator = Text2HtmlGenerator(brand_config, model_name, debug)
            debug_info = "（调试模式）" if debug else ""
            console.print(f"✅ 生成器初始化成功，使用模型: {model_name}{debug_info}")
        except Exception as e:
            console.print(f"❌ 生成器初始化失败: {e}")
            sys.exit(1)
    
    def validate_api_key(self):
        """验证API密钥"""
        if not config.check_gemini_api_key():
            console.print("❌ Gemini API密钥未配置或无效")
            console.print("请在.env文件中配置GEMINI_API_KEY")
            sys.exit(1)
    
    def find_markdown_files(self, file_patterns: List[str]) -> List[Path]:
        """查找markdown文件"""
        md_files = []
        
        if not file_patterns:
            # 默认处理所有markdown文件
            md_files = list(config.OUTPUT_DIR.glob("*.md"))
        else:
            for pattern in file_patterns:
                path = Path(pattern)
                
                if path.is_absolute():
                    # 绝对路径
                    if path.exists() and path.suffix.lower() == '.md':
                        md_files.append(path)
                else:
                    # 相对路径，支持glob模式
                    if '*' in pattern or '?' in pattern:
                        # glob模式
                        md_files.extend(config.OUTPUT_DIR.glob(pattern))
                    else:
                        # 普通文件名
                        file_path = config.OUTPUT_DIR / pattern
                        if file_path.exists() and file_path.suffix.lower() == '.md':
                            md_files.append(file_path)
                        else:
                            console.print(f"⚠️  文件不存在或不是markdown文件: {pattern}")
        
        return [f for f in md_files if f.suffix.lower() == '.md']
    
    async def generate_single_with_progress(self, md_file: Path, task_id: TaskID, force: bool) -> GenerationResult:
        """带进度显示的单文件生成"""
        if self.progress:
            self.progress.update(task_id, description=f"处理 {md_file.name}")
        
        result = await self.generator.generate_single(md_file, force)
        
        if self.progress:
            if result.success:
                status = "✅ 成功" if not result.metadata.get('skipped') else "⏭️  跳过"
            else:
                status = "❌ 失败"
            
            self.progress.update(task_id, description=f"{status} {md_file.name}")
        
        return result
    
    async def generate_files(self, md_files: List[Path], force: bool = False, max_concurrent: int = 3):
        """生成文件（带进度显示）"""
        if not md_files:
            console.print("❌ 未找到要处理的markdown文件")
            return
        
        console.print(f"📝 找到 {len(md_files)} 个markdown文件")
        
        # 设置进度条
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            self.progress = progress
            
            # 创建总体进度任务
            main_task = progress.add_task("总体进度", total=len(md_files))
            
            # 并发控制
            semaphore = asyncio.Semaphore(max_concurrent)
            results = []
            
            async def process_with_semaphore(md_file: Path) -> GenerationResult:
                async with semaphore:
                    # 为每个文件创建子任务
                    task_id = progress.add_task(f"处理 {md_file.name}", total=1)
                    result = await self.generate_single_with_progress(md_file, task_id, force)
                    progress.update(task_id, completed=1)
                    progress.update(main_task, advance=1)
                    return result
            
            # 执行并发处理
            tasks = [process_with_semaphore(f) for f in md_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    final_results.append(GenerationResult(
                        success=False,
                        input_file=md_files[i],
                        error_message=f"处理异常: {str(result)}"
                    ))
                else:
                    final_results.append(result)
        
        # 显示结果统计
        self.show_results_summary(final_results)
    
    def show_results_summary(self, results: List[GenerationResult]):
        """显示结果统计"""
        successful = sum(1 for r in results if r.success and not r.metadata.get('skipped'))
        failed = sum(1 for r in results if not r.success)
        skipped = sum(1 for r in results if r.success and r.metadata.get('skipped'))
        
        # 创建统计表格
        table = Table(title="Quick-Insight生成结果统计")
        table.add_column("状态", style="bold")
        table.add_column("数量", justify="right")
        table.add_column("占比", justify="right")
        
        total = len(results)
        if total > 0:
            table.add_row("✅ 成功生成", str(successful), f"{successful/total*100:.1f}%")
            table.add_row("⏭️  跳过（无需更新）", str(skipped), f"{skipped/total*100:.1f}%")
            table.add_row("❌ 生成失败", str(failed), f"{failed/total*100:.1f}%")
            table.add_row("📝 总计", str(total), "100.0%")
        
        console.print(table)
        
        # 显示失败的详情
        if failed > 0:
            console.print("\n❌ 失败的文件:")
            for result in results:
                if not result.success:
                    console.print(f"  • {result.input_file.name}: {result.error_message}")
        
        # 显示输出目录
        if successful > 0:
            output_dir = self.generator.output_dir
            console.print(f"\n📁 生成的HTML文件保存在: {output_dir}")
            
            # 如果是调试模式，显示调试目录
            if self.generator.debug:
                debug_dir = self.generator.debug_dir
                console.print(f"🔍 调试文件保存在: {debug_dir}")
                console.print("   调试文件包含:")
                console.print("   • *_prompt.txt - AI提示词")
                console.print("   • *_response_*.html - AI返回内容")
    
    def show_templates_info(self):
        """显示可用的模板信息"""
        prompts_mgr = get_prompts_manager()
        templates = prompts_mgr.list_templates()
        
        table = Table(title="可用的Quick-Insight模板")
        table.add_column("模板名称", style="bold")
        table.add_column("适用场景")
        table.add_column("内容长度")
        
        template_descriptions = {
            "simple": "短文章（<1000字）",
            "base": "中等文章（1000-5000字）",
            "enhanced": "长文章（>5000字）",
            "external": "外部自定义模板"
        }
        
        for template_name in templates:
            info = prompts_mgr.get_template_info(template_name)
            description = template_descriptions.get(template_name, "自定义模板")
            content_length = f"{info.get('content_length', 0):,} 字符"
            table.add_row(template_name, description, content_length)
        
        console.print(table)
    
    def show_generator_stats(self):
        """显示生成器统计信息"""
        if not self.generator:
            console.print("❌ 生成器未初始化")
            return
        
        stats = self.generator.get_stats()
        
        panel_content = f"""
📊 生成器统计信息:
  • AI模型: {stats['ai_model']}
  • 品牌名称: {stats['brand_name']}
  • 输出目录: {stats['output_directory']}
  • 模板加载: {'✅' if stats['template_loaded'] else '❌'}
  
📈 处理统计:
  • 总处理数: {stats['total_processed']}
  • 成功数: {stats['successful']}
  • 失败数: {stats['failed']}
  • 跳过数: {stats['skipped']}
        """
        
        console.print(Panel(panel_content.strip(), title="Quick-Insight Generator", border_style="blue"))

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="Quick-Insight生成工具 - 将markdown文章转换为精美HTML网页",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s article.md                    # 生成单个文件
  %(prog)s --all                         # 批量生成所有文章
  %(prog)s --force article.md            # 强制重新生成
  %(prog)s --debug article.md            # 调试模式（保存提示词和AI返回内容）
  %(prog)s --templates                   # 查看可用模板
  %(prog)s --stats                       # 查看统计信息
  %(prog)s --brand-config custom.json    # 使用自定义品牌配置
        """
    )
    
    # 文件参数
    parser.add_argument(
        'files',
        nargs='*',
        help='要处理的markdown文件（支持glob模式）'
    )
    
    # 批量处理选项
    parser.add_argument(
        '--all',
        action='store_true',
        help='处理所有markdown文件'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新生成（忽略文件时间戳检查）'
    )
    
    # 配置选项
    parser.add_argument(
        '--brand-config',
        type=Path,
        help='自定义品牌配置文件路径（JSON格式）'
    )
    
    parser.add_argument(
        '--model',
        default='Gemini',
        help='AI模型名称（默认: Gemini）'
    )
    
    parser.add_argument(
        '--concurrent',
        type=int,
        default=3,
        help='最大并发数（默认: 3）'
    )
    
    # 信息选项
    parser.add_argument(
        '--templates',
        action='store_true',
        help='显示可用的模板信息'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='显示生成器统计信息'
    )
    
    # 日志选项
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='调试模式（保存AI提示词和返回内容到debug目录）'
    )
    
    return parser

async def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 创建CLI实例
    cli = QuickInsightCLI()
    
    # 设置日志
    cli.setup_logging(args.verbose)
    
    # 静默模式
    if args.quiet:
        console.quiet = True
    
    # 显示欢迎信息
    if not args.quiet:
        console.print(Panel(
            "🚀 Quick-Insight Generator\n"
            "将markdown文章转换为精美的HTML网页",
            title="reinvent-insight",
            border_style="cyan"
        ))
    
    try:
        # 验证API密钥
        cli.validate_api_key()
        
        # 加载品牌配置
        brand_config = cli.load_brand_config(args.brand_config)
        
        # 初始化生成器
        cli.init_generator(brand_config, args.model, args.debug)
        
        # 处理信息查询命令
        if args.templates:
            cli.show_templates_info()
            return
        
        if args.stats:
            cli.show_generator_stats()
            return
        
        # 确定要处理的文件
        if args.all:
            file_patterns = []
        else:
            file_patterns = args.files
        
        if not args.all and not args.files:
            console.print("❌ 请指定要处理的文件，或使用 --all 处理所有文件")
            parser.print_help()
            return
        
        # 查找文件
        md_files = cli.find_markdown_files(file_patterns)
        
        if not md_files:
            console.print("❌ 未找到要处理的markdown文件")
            return
        
        # 执行生成
        await cli.generate_files(md_files, args.force, args.concurrent)
        
    except KeyboardInterrupt:
        console.print("\n⚠️  用户中断操作")
    except Exception as e:
        console.print(f"❌ 程序执行错误: {e}")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 