#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 YouTube 视频标题脚本

将所有使用 AI 生成标题的文档修正为使用 YouTube 原始标题
优先级：YouTube 原始标题 > AI 生成标题

Usage:
    python -m reinvent_insight.tools.fix_youtube_titles [--dry-run]
"""

import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from reinvent_insight.core import config
from reinvent_insight.infrastructure.media.youtube_downloader import SubtitleDownloader


def extract_video_id(video_url: str) -> Optional[str]:
    """从 URL 提取 video_id"""
    patterns = [
        r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
    return None


def parse_yaml_metadata(content: str) -> Dict[str, Any]:
    """解析 YAML front matter"""
    yaml_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(yaml_pattern, content, re.DOTALL)
    
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except Exception as e:
            logger.warning(f"YAML 解析失败: {e}")
            return {}
    return {}


def update_yaml_metadata(content: str, new_metadata: Dict[str, Any]) -> str:
    """更新 YAML front matter"""
    yaml_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(yaml_pattern, content, re.DOTALL)
    
    if match:
        new_yaml = "---\n" + yaml.dump(new_metadata, allow_unicode=True, sort_keys=False).rstrip() + "\n---"
        return re.sub(yaml_pattern, new_yaml + "\n", content, count=1, flags=re.DOTALL)
    
    return content


def get_youtube_title(video_url: str) -> Optional[str]:
    """获取 YouTube 视频的原始标题"""
    try:
        video_id = extract_video_id(video_url)
        
        if not video_id:
            logger.warning(f"无法提取 video_id: {video_url}")
            return None
        
        # 构建完整 URL
        full_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # 创建下载器并获取元数据
        downloader = SubtitleDownloader(full_url)
        if downloader._fetch_metadata() and downloader.metadata:
            logger.info(f"成功获取 YouTube 标题: {downloader.metadata.title}")
            return downloader.metadata.title
        
        return None
        
    except Exception as e:
        logger.error(f"获取 YouTube 标题失败 {video_url}: {e}")
        return None


def process_file(md_file: Path, dry_run: bool = False) -> Dict[str, Any]:
    """处理单个文件
    
    Returns:
        处理结果统计
    """
    result = {
        "processed": False,
        "updated": False,
        "error": None,
        "old_title": None,
        "new_title": None
    }
    
    try:
        content = md_file.read_text(encoding="utf-8")
        metadata = parse_yaml_metadata(content)
        
        # 只处理 YouTube 视频（明确过滤非 YouTube URL）
        video_url = metadata.get("video_url", "")
        if not video_url:
            return result
        
        # 只处理 YouTube 链接
        is_youtube = (
            "youtube.com" in video_url or 
            "youtu.be" in video_url
        )
        if not is_youtube:
            logger.debug(f"跳过非 YouTube 文档: {video_url[:50]}...")
            return result
        
        # 检查是否需要更新
        current_title_en = metadata.get("title_en", "")
        
        # 如果没有 title_en，跳过
        if not current_title_en:
            return result
        
        result["processed"] = True
        result["old_title"] = current_title_en
        
        # 获取 YouTube 原始标题
        youtube_title = get_youtube_title(video_url)
        
        if not youtube_title:
            result["error"] = "无法获取 YouTube 标题"
            return result
        
        # 如果标题已经是 YouTube 原始标题，跳过
        if current_title_en == youtube_title:
            logger.info(f"✓ {md_file.name} 已使用 YouTube 原始标题")
            return result
        
        # 需要更新
        result["new_title"] = youtube_title
        result["updated"] = True
        
        if dry_run:
            logger.info(f"[DRY RUN] {md_file.name}")
            logger.info(f"  旧标题: {current_title_en}")
            logger.info(f"  新标题: {youtube_title}")
            return result
        
        # 更新元数据
        metadata["title_en"] = youtube_title
        new_content = update_yaml_metadata(content, metadata)
        
        # 保存文件
        md_file.write_text(new_content, encoding="utf-8")
        logger.success(f"✓ 更新 {md_file.name}")
        logger.info(f"  旧: {current_title_en}")
        logger.info(f"  新: {youtube_title}")
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"处理文件失败 {md_file.name}: {e}")
        return result


def main(dry_run: bool = False):
    """主函数"""
    logger.info("=" * 60)
    logger.info("YouTube 标题修复工具")
    logger.info("=" * 60)
    
    if dry_run:
        logger.warning("🔍 DRY RUN 模式 - 不会实际修改文件")
    
    output_dir = config.OUTPUT_DIR
    if not output_dir.exists():
        logger.error(f"输出目录不存在: {output_dir}")
        return
    
    md_files = list(output_dir.glob("*.md"))
    logger.info(f"找到 {len(md_files)} 个 Markdown 文件")
    
    stats = {
        "total": len(md_files),
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0
    }
    
    for md_file in md_files:
        logger.info(f"\n处理: {md_file.name}")
        result = process_file(md_file, dry_run)
        
        if result["error"]:
            stats["errors"] += 1
        elif result["updated"]:
            stats["updated"] += 1
            stats["processed"] += 1
        elif result["processed"]:
            stats["processed"] += 1
        else:
            stats["skipped"] += 1
    
    # 输出统计
    logger.info("\n" + "=" * 60)
    logger.info("处理完成")
    logger.info("=" * 60)
    logger.info(f"总文件数: {stats['total']}")
    logger.info(f"已处理:   {stats['processed']}")
    logger.info(f"已更新:   {stats['updated']}")
    logger.info(f"跳过:     {stats['skipped']}")
    logger.info(f"错误:     {stats['errors']}")
    
    if dry_run and stats['updated'] > 0:
        logger.warning(f"\n⚠️  实际运行命令: python -m reinvent_insight.tools.fix_youtube_titles")


if __name__ == "__main__":
    import sys
    
    dry_run = "--dry-run" in sys.argv
    main(dry_run)
