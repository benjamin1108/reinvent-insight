#!/usr/bin/env python3
"""
文档标识符迁移脚本

将老文档中存储在 video_url 字段的文档标识符（如 pdf://xxx, txt://xxx）
迁移到语义正确的 content_identifier 字段。

用法：
    python scripts/migrate_document_identifier.py --dry-run  # 预览模式
    python scripts/migrate_document_identifier.py            # 执行迁移
"""

import re
import sys
import yaml
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reinvent_insight.core import config


def is_document_identifier(value: str) -> bool:
    """判断是否为文档标识符（非 HTTP URL）"""
    if not value:
        return False
    # 文档标识符格式：xxx://... 但不是 http:// 或 https://
    if "://" in value and not value.startswith(("http://", "https://")):
        return True
    return False


def migrate_file(file_path: Path, dry_run: bool = True) -> dict:
    """
    迁移单个文件
    
    Returns:
        {
            'status': 'migrated' | 'skipped' | 'error',
            'reason': str,
            'old_video_url': str,
            'new_content_identifier': str
        }
    """
    result = {
        'status': 'skipped',
        'reason': '',
        'old_video_url': '',
        'new_content_identifier': ''
    }
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # 解析 YAML front matter
        yaml_pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(yaml_pattern, content, re.DOTALL)
        
        if not match:
            result['reason'] = '无 YAML front matter'
            return result
        
        yaml_content = match.group(1)
        metadata = yaml.safe_load(yaml_content)
        
        if not metadata:
            result['reason'] = 'YAML 解析失败'
            return result
        
        video_url = metadata.get('video_url', '')
        content_identifier = metadata.get('content_identifier', '')
        
        # 检查是否需要迁移
        if not is_document_identifier(video_url):
            if video_url.startswith(('http://', 'https://')):
                result['reason'] = 'YouTube 视频，无需迁移'
            elif content_identifier:
                result['reason'] = '已有 content_identifier'
            else:
                result['reason'] = '无标识符'
            return result
        
        # 需要迁移：video_url 是文档标识符
        result['old_video_url'] = video_url
        result['new_content_identifier'] = video_url
        
        if dry_run:
            result['status'] = 'migrated'
            result['reason'] = '将迁移（预览模式）'
            return result
        
        # 执行迁移
        # 更新 metadata
        metadata['content_identifier'] = video_url
        metadata['video_url'] = ''  # 清空 video_url
        
        # 重新生成 YAML
        new_yaml = yaml.dump(metadata, allow_unicode=True, sort_keys=False).rstrip()
        new_front_matter = f"---\n{new_yaml}\n---"
        
        # 替换文件内容
        new_content = re.sub(yaml_pattern, new_front_matter + '\n', content, count=1, flags=re.DOTALL)
        
        # 写回文件
        file_path.write_text(new_content, encoding='utf-8')
        
        result['status'] = 'migrated'
        result['reason'] = '迁移成功'
        return result
        
    except Exception as e:
        result['status'] = 'error'
        result['reason'] = str(e)
        return result


def main():
    parser = argparse.ArgumentParser(description='迁移文档标识符')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际修改文件')
    parser.add_argument('--dir', type=str, default=None, help='指定目录，默认使用 config.OUTPUT_DIR')
    args = parser.parse_args()
    
    # 确定目录
    if args.dir:
        output_dir = Path(args.dir)
    else:
        output_dir = config.OUTPUT_DIR
    
    if not output_dir.exists():
        print(f"错误：目录不存在 {output_dir}")
        sys.exit(1)
    
    print(f"{'[预览模式]' if args.dry_run else '[执行模式]'} 扫描目录: {output_dir}")
    print("-" * 60)
    
    # 统计
    stats = {'migrated': 0, 'skipped': 0, 'error': 0}
    
    # 扫描所有 md 文件
    md_files = sorted(output_dir.glob('*.md'))
    
    for md_file in md_files:
        result = migrate_file(md_file, dry_run=args.dry_run)
        stats[result['status']] += 1
        
        # 输出结果
        if result['status'] == 'migrated':
            print(f"✓ {md_file.name}")
            print(f"  video_url: {result['old_video_url'][:50]}...")
            print(f"  → content_identifier: {result['new_content_identifier'][:50]}...")
        elif result['status'] == 'error':
            print(f"✗ {md_file.name}: {result['reason']}")
        else:
            # skipped - 只在 verbose 模式下显示
            pass
    
    print("-" * 60)
    print(f"总计: {len(md_files)} 个文件")
    print(f"  迁移: {stats['migrated']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {stats['error']}")
    
    if args.dry_run and stats['migrated'] > 0:
        print("\n[提示] 使用不带 --dry-run 参数重新运行以执行实际迁移")


if __name__ == '__main__':
    main()
