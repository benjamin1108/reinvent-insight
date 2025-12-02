#!/usr/bin/env python3
"""计算 XNT312 文章的哈希值"""

import sys
from pathlib import Path
import hashlib

sys.path.insert(0, str(Path(__file__).parent))

from src.reinvent_insight.services.tts_text_preprocessor import TTSTextPreprocessor

# 读取 Markdown 文件
md_file = Path("/home/benjamin/reinvent-insight/downloads/summaries/AWS reInvent 2024 - Use generative AI to optimize cloud operations for Microsoft workloads (XNT312).md")

with open(md_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 提取元数据
preprocessor = TTSTextPreprocessor()
metadata, _ = preprocessor.extract_yaml_metadata(content)

print("=" * 60)
print("XNT312 文章哈希计算")
print("=" * 60)
print(f"视频URL: {metadata.get('video_url', '')}")
print(f"标题: {metadata.get('title_en', '')}")
print(f"上传日期: {metadata.get('upload_date', '')}")
print()

# 计算哈希
article_hash = preprocessor.calculate_article_hash(
    video_url=metadata.get('video_url', ''),
    title=metadata.get('title_en', ''),
    upload_date=metadata.get('upload_date', '')
)

print(f"文章哈希: {article_hash}")
print()

# 检查对应的 TTS 文本文件
tts_text_file = Path(f"/home/benjamin/reinvent-insight/downloads/tts_texts/{article_hash}.txt")
print(f"TTS 文本文件: {tts_text_file}")
print(f"文件存在: {tts_text_file.exists()}")

if tts_text_file.exists():
    with open(tts_text_file, 'r', encoding='utf-8') as f:
        tts_content = f.read()
    print(f"文件大小: {len(tts_content)} 字符")
    print()
    print("前 500 字符:")
    print("-" * 60)
    print(tts_content[:500])
