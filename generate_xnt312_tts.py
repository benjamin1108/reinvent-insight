#!/usr/bin/env python3
"""为 XNT312 手动生成 TTS 文本"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.reinvent_insight.services.tts_text_preprocessor import TTSTextPreprocessor
from src.reinvent_insight.config import TTS_TEXT_DIR

def generate_xnt312_tts():
    """生成 XNT312 的 TTS 文本"""
    
    # 读取 Markdown 文件
    md_file = Path("/home/benjamin/reinvent-insight/downloads/summaries/AWS reInvent 2024 - Use generative AI to optimize cloud operations for Microsoft workloads (XNT312).md")
    
    with open(md_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    print("=" * 80)
    print("为 XNT312 生成 TTS 文本")
    print("=" * 80)
    print(f"源文件: {md_file.name}")
    print(f"原始大小: {len(markdown_content):,} 字符\n")
    
    # 初始化预处理器
    preprocessor = TTSTextPreprocessor()
    
    # 执行预处理
    print("正在预处理...")
    result = preprocessor.preprocess(markdown_content)
    
    if not result:
        print("❌ 预处理失败！")
        return
    
    print("✅ 预处理成功！")
    print(f"   - 中文标题: {result.title_cn}")
    print(f"   - 文章哈希: {result.article_hash}")
    print(f"   - 原文长度: {result.original_length:,} 字符")
    print(f"   - 处理后长度: {result.processed_length:,} 字符")
    print(f"   - 保留比例: {result.processed_length/result.original_length*100:.1f}%")
    print(f"   - 移除章节: {', '.join(result.sections_removed)}\n")
    
    # 保存到文件
    print(f"保存到: {TTS_TEXT_DIR}")
    output_file = preprocessor.save_to_file(result, TTS_TEXT_DIR)
    
    if output_file:
        print(f"✅ 文件已保存: {output_file}")
        print(f"   文件大小: {output_file.stat().st_size:,} 字节\n")
        
        # 显示预览
        print("=" * 80)
        print("内容预览（前 1000 字符）:")
        print("=" * 80)
        print(result.text[:1000])
        print("...")
        print("=" * 80)
    else:
        print("❌ 保存文件失败！")

if __name__ == "__main__":
    generate_xnt312_tts()
