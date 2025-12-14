#!/usr/bin/env python3
"""批量重新生成 Visual Insight

遍历指定目录下的所有文章，重新生成 Visual HTML。

使用方式:
    # 处理默认目录 (output/)
    python scripts/regenerate_visuals.py
    
    # 处理指定目录
    python scripts/regenerate_visuals.py --dir /path/to/articles
    
    # 只处理特定文件
    python scripts/regenerate_visuals.py --file output/article.md
    
    # 强制重新生成（即使已存在）
    python scripts/regenerate_visuals.py --force
    
    # 并发控制
    python scripts/regenerate_visuals.py --concurrency 2
    
    # 跳过最近N天内生成的
    python scripts/regenerate_visuals.py --skip-recent 7
"""

import os
import sys
import re
import time
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reinvent_insight.core import config
from reinvent_insight.services.analysis.visual_worker import VisualInterpretationWorker
from reinvent_insight.services.analysis.task_manager import manager as task_manager


def find_task_dir_for_article(article_path: Path) -> Optional[str]:
    """查找文章对应的 task_dir"""
    import yaml
    
    try:
        from reinvent_insight.domain.workflows.base import TASKS_ROOT_DIR
        tasks_root = Path(TASKS_ROOT_DIR) if isinstance(TASKS_ROOT_DIR, str) else TASKS_ROOT_DIR
    except Exception:
        return None
    
    # 1. 优先从文章元数据中获取
    try:
        content = article_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                if metadata and metadata.get("task_dir"):
                    return metadata["task_dir"]
    except Exception as e:
        logger.debug(f"读取文章元数据失败: {e}")
    
    # 2. 通过日期目录匹配
    if not tasks_root.exists():
        return None
    
    article_title = None
    try:
        content = article_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                article_title = metadata.get("title_cn") or metadata.get("title")
    except:
        pass
    
    # 遍历日期目录
    try:
        for date_dir in sorted(tasks_root.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            for task_dir in date_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                
                outline_file = task_dir / "outline.md"
                if not outline_file.exists():
                    continue
                
                try:
                    import json
                    outline_content = outline_file.read_text(encoding="utf-8")
                    json_match = re.search(r'```json\s*(.*?)\s*```', outline_content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        outline_data = json.loads(json_str)
                        outline_title = outline_data.get("title_cn") or outline_data.get("title")
                        
                        if outline_title and article_title and outline_title == article_title:
                            return str(task_dir)
                except:
                    pass
    except Exception as e:
        logger.debug(f"查找 task_dir 失败: {e}")
    
    return None


def extract_version(filename: str) -> int:
    """从文件名提取版本号"""
    version_match = re.search(r'_v(\d+)', filename)
    return int(version_match.group(1)) if version_match else 0


def get_visual_html_path(article_path: Path) -> Path:
    """获取 Visual HTML 路径"""
    base_name = article_path.stem
    version_match = re.match(r'^(.+)_v(\d+)$', base_name)
    
    if version_match:
        html_filename = f"{version_match.group(1)}_v{version_match.group(2)}_visual.html"
    else:
        html_filename = f"{base_name}_visual.html"
    
    return article_path.parent / html_filename


def should_skip_article(article_path: Path, force: bool, skip_recent_days: int) -> tuple[bool, str]:
    """判断是否应该跳过该文章"""
    # 检查是否是有效的文章（非 visual、非临时文件）
    if "_visual" in article_path.stem:
        return True, "是 visual 文件"
    
    if article_path.stem.startswith("."):
        return True, "是隐藏文件"
    
    # 检查文章内容是否有效
    try:
        content = article_path.read_text(encoding="utf-8")
        if len(content) < 100:
            return True, "内容太短"
        if "## " not in content:
            return True, "无章节结构"
    except Exception as e:
        return True, f"读取失败: {e}"
    
    # 检查是否已有 Visual HTML
    visual_path = get_visual_html_path(article_path)
    if visual_path.exists():
        if force:
            return False, ""
        
        # 检查是否在最近N天内生成
        if skip_recent_days > 0:
            mtime = datetime.fromtimestamp(visual_path.stat().st_mtime)
            if datetime.now() - mtime < timedelta(days=skip_recent_days):
                return True, f"最近 {skip_recent_days} 天内已生成"
        else:
            return True, "已存在 Visual HTML"
    
    return False, ""


async def regenerate_visual(article_path: Path, dry_run: bool = False) -> bool:
    """重新生成单个文章的 Visual"""
    try:
        # 生成任务ID
        base_name = article_path.stem
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            base_name = version_match.group(1)
        
        normalized_name = base_name.replace(' ', '_').replace('–', '-')[:50]
        task_id = f"visual_regen_{normalized_name}_{int(time.time())}"
        
        # 提取版本号
        version = extract_version(article_path.stem)
        
        # 查找 task_dir
        task_dir = find_task_dir_for_article(article_path)
        
        if dry_run:
            logger.info(f"[DRY-RUN] 将生成: {article_path.name} (版本: {version}, task_dir: {task_dir or '无'})")
            return True
        
        logger.info(f"开始生成: {article_path.name} (版本: {version})")
        
        # 创建工作器
        worker = VisualInterpretationWorker(
            task_id=task_id,
            article_path=str(article_path),
            version=version,
            task_dir=task_dir
        )
        
        # 执行生成
        result = await worker.run()
        
        if result:
            logger.info(f"✓ 生成成功: {article_path.name}")
            return True
        else:
            logger.error(f"✗ 生成失败: {article_path.name}")
            return False
            
    except Exception as e:
        logger.error(f"✗ 生成异常: {article_path.name} - {e}")
        return False


async def process_batch(
    articles: List[Path], 
    concurrency: int, 
    dry_run: bool,
    delay: float
) -> tuple[int, int]:
    """批量处理文章"""
    semaphore = asyncio.Semaphore(concurrency)
    success_count = 0
    fail_count = 0
    
    async def process_with_semaphore(article_path: Path, index: int):
        nonlocal success_count, fail_count
        async with semaphore:
            logger.info(f"[{index + 1}/{len(articles)}] 处理: {article_path.name}")
            result = await regenerate_visual(article_path, dry_run)
            if result:
                success_count += 1
            else:
                fail_count += 1
            
            # 延迟，避免 API 限流
            if delay > 0 and not dry_run:
                await asyncio.sleep(delay)
    
    tasks = [
        process_with_semaphore(article, i) 
        for i, article in enumerate(articles)
    ]
    
    await asyncio.gather(*tasks)
    
    return success_count, fail_count


def main():
    parser = argparse.ArgumentParser(
        description="批量重新生成 Visual Insight",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--dir", "-d",
        type=str,
        default=None,
        help="文章目录路径（默认使用 OUTPUT_DIR）"
    )
    
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="处理单个文件"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成（即使已存在）"
    )
    
    parser.add_argument(
        "--skip-recent",
        type=int,
        default=0,
        help="跳过最近N天内生成的 Visual（默认: 0，不跳过）"
    )
    
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=1,
        help="并发数（默认: 1）"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="每次生成后的延迟秒数（默认: 2.0）"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示将要处理的文件，不实际执行"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示跳过文件的详细原因"
    )
    
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.md",
        help="文件匹配模式（默认: *.md）"
    )
    
    args = parser.parse_args()
    
    # 确定目录
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {args.file}")
            sys.exit(1)
        articles = [file_path]
    else:
        if args.dir:
            target_dir = Path(args.dir)
        else:
            target_dir = config.OUTPUT_DIR
        
        if not target_dir.exists():
            print(f"❌ 目录不存在: {target_dir}")
            sys.exit(1)
        
        # 获取所有文章
        all_files = list(target_dir.glob(args.pattern))
        articles = []
        skipped = []
        
        for f in sorted(all_files):
            skip, reason = should_skip_article(f, args.force, args.skip_recent)
            if skip:
                skipped.append((f.name, reason))
                if args.verbose:
                    logger.info(f"跳过: {f.name} - {reason}")
            else:
                articles.append(f)
    
    # 显示统计
    print(f"\n{'='*60}")
    print(f"Visual Insight 批量重新生成")
    print(f"{'='*60}")
    print(f"目标目录: {args.dir or config.OUTPUT_DIR}")
    print(f"待处理文件: {len(articles)}")
    if not args.file:
        print(f"跳过文件: {len(skipped)}")
    print(f"并发数: {args.concurrency}")
    print(f"强制重新生成: {'是' if args.force else '否'}")
    print(f"{'='*60}\n")
    
    if not articles:
        print("没有需要处理的文件")
        sys.exit(0)
    
    # 显示将要处理的文件
    print("将处理以下文件:")
    for i, article in enumerate(articles[:20]):
        print(f"  {i+1}. {article.name}")
    if len(articles) > 20:
        print(f"  ... 还有 {len(articles) - 20} 个文件")
    print()
    
    if args.dry_run:
        print("[DRY-RUN 模式] 不会实际执行生成")
        print()
    
    # 确认
    if not args.dry_run and len(articles) > 1:
        confirm = input(f"确认处理 {len(articles)} 个文件? [y/N]: ")
        if confirm.lower() != 'y':
            print("已取消")
            sys.exit(0)
    
    # 执行
    start_time = time.time()
    success, fail = asyncio.run(
        process_batch(articles, args.concurrency, args.dry_run, args.delay)
    )
    elapsed = time.time() - start_time
    
    # 结果统计
    print(f"\n{'='*60}")
    print(f"处理完成！")
    print(f"{'='*60}")
    print(f"成功: {success}")
    print(f"失败: {fail}")
    print(f"耗时: {elapsed:.1f}秒")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
