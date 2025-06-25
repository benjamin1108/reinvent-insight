#!/usr/bin/env python3
"""
批量更新markdown文档的metadata
将原有的title字段改为title_en，并从文档H1标题提取title_cn
"""

import os
import re
from pathlib import Path
import yaml
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_markdown_with_yaml(content: str) -> tuple[dict, str, str]:
    """
    解析包含YAML front matter的markdown文档
    返回: (metadata_dict, yaml_content, markdown_content)
    """
    # 匹配YAML front matter
    yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    
    if yaml_match:
        yaml_content = yaml_match.group(1)
        markdown_content = content[yaml_match.end():]
        try:
            metadata = yaml.safe_load(yaml_content)
            return metadata, yaml_content, markdown_content
        except yaml.YAMLError as e:
            logger.error(f"YAML解析错误: {e}")
            return {}, "", content
    else:
        return {}, "", content

def extract_h1_title(markdown_content: str) -> str:
    """
    从markdown内容中提取第一个H1标题
    """
    for line in markdown_content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('# ') and not stripped.startswith('## '):
            return stripped[2:].strip()
    return ""

def update_metadata_structure(metadata: dict, h1_title: str) -> dict:
    """
    更新metadata结构：
    - 将title改为title_en
    - 添加title_cn (使用H1标题)
    """
    new_metadata = metadata.copy()
    
    # 如果已经有title_en和title_cn，说明已经更新过
    if 'title_en' in new_metadata and 'title_cn' in new_metadata:
        logger.info("  metadata已经是新格式，跳过")
        return None
    
    # 将原有的title改为title_en
    if 'title' in new_metadata:
        new_metadata['title_en'] = new_metadata.pop('title')
    
    # 添加title_cn
    new_metadata['title_cn'] = h1_title if h1_title else new_metadata.get('title_en', 'Untitled')
    
    return new_metadata

def save_updated_markdown(file_path: Path, metadata: dict, markdown_content: str):
    """
    保存更新后的markdown文件
    """
    # 生成新的YAML front matter
    yaml_content = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    
    # 组合完整内容
    full_content = f"---\n{yaml_content}---\n{markdown_content}"
    
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_content)

def process_directory(directory: Path):
    """
    处理指定目录下的所有markdown文件
    """
    md_files = list(directory.glob("*.md"))
    logger.info(f"找到 {len(md_files)} 个markdown文件")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for md_file in md_files:
        logger.info(f"\n处理文件: {md_file.name}")
        
        try:
            # 读取文件
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析内容
            metadata, yaml_content, markdown_content = parse_markdown_with_yaml(content)
            
            if not metadata:
                logger.warning(f"  无法解析YAML metadata，跳过")
                skipped_count += 1
                continue
            
            # 提取H1标题
            h1_title = extract_h1_title(markdown_content)
            if not h1_title:
                logger.warning(f"  未找到H1标题，跳过")
                skipped_count += 1
                continue
            
            logger.info(f"  找到H1标题: {h1_title[:50]}...")
            
            # 更新metadata结构
            new_metadata = update_metadata_structure(metadata, h1_title)
            
            if new_metadata is None:
                skipped_count += 1
                continue
            
            # 保存更新后的文件
            save_updated_markdown(md_file, new_metadata, markdown_content)
            logger.info(f"  ✓ 更新成功")
            updated_count += 1
            
        except Exception as e:
            logger.error(f"  处理文件时出错: {e}")
            error_count += 1
    
    # 统计结果
    logger.info(f"\n处理完成:")
    logger.info(f"  - 成功更新: {updated_count} 个文件")
    logger.info(f"  - 跳过: {skipped_count} 个文件")
    logger.info(f"  - 错误: {error_count} 个文件")

def main():
    """
    主函数
    """
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent  # 脚本在tools目录下，向上一级是项目根目录
    
    # 设置要处理的目录
    summaries_dir = project_root / "downloads" / "summaries"
    
    if not summaries_dir.exists():
        logger.error(f"目录不存在: {summaries_dir}")
        return
    
    logger.info(f"开始处理目录: {summaries_dir}")
    process_directory(summaries_dir)

if __name__ == "__main__":
    main() 