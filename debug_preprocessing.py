#!/usr/bin/env python3
"""诊断 TTS 文本预处理问题"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.reinvent_insight.services.tts_text_preprocessor import TTSTextPreprocessor

def debug_preprocessing():
    """逐步诊断预处理过程"""
    
    # 读取原始文件
    md_file = Path("/home/benjamin/reinvent-insight/downloads/summaries/AWS reInvent 2024 - Use generative AI to optimize cloud operations for Microsoft workloads (XNT312).md")
    
    with open(md_file, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    print("=" * 80)
    print("TTS 文本预处理诊断")
    print("=" * 80)
    print(f"\n📄 原始文件: {md_file.name}")
    print(f"📊 原始大小: {len(original_content):,} 字符\n")
    
    preprocessor = TTSTextPreprocessor()
    
    # 步骤 1: 提取 YAML 元数据
    metadata, content = preprocessor.extract_yaml_metadata(original_content)
    print(f"步骤 1️⃣ - 提取 YAML 元数据")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)")
    print(f"   元数据: {metadata}\n")
    
    # 步骤 2: 提取中文标题
    title_cn, content = preprocessor.extract_chinese_title(content)
    print(f"步骤 2️⃣ - 提取中文标题")
    print(f"   标题: {title_cn}")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)\n")
    
    # 步骤 3: 移除目录
    content, toc_removed = preprocessor.remove_toc_section(content)
    print(f"步骤 3️⃣ - 移除目录")
    print(f"   是否移除: {toc_removed}")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)\n")
    
    # 步骤 4: 移除洞见和金句
    before_remove = len(content)
    content, removed = preprocessor.remove_insights_and_quotes(content)
    print(f"步骤 4️⃣ - 移除洞见和金句")
    print(f"   移除的章节: {removed}")
    print(f"   删除字符: {before_remove - len(content):,}")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)\n")
    
    # 步骤 5: 清理 Markdown 语法
    before_clean = len(content)
    content = preprocessor.clean_markdown_syntax(content)
    print(f"步骤 5️⃣ - 清理 Markdown 语法")
    print(f"   删除字符: {before_clean - len(content):,}")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)\n")
    
    # 步骤 6: 优化标题格式
    before_heading = len(content)
    content = preprocessor.optimize_headings(content)
    print(f"步骤 6️⃣ - 优化标题格式")
    print(f"   字符变化: {len(content) - before_heading:+,}")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)\n")
    
    # 步骤 7: 优化列表格式
    before_list = len(content)
    content = preprocessor.optimize_lists(content)
    print(f"步骤 7️⃣ - 优化列表格式")
    print(f"   字符变化: {len(content) - before_list:+,}")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)\n")
    
    # 步骤 8: 替换特殊符号
    before_symbol = len(content)
    content = preprocessor.replace_special_symbols(content)
    print(f"步骤 8️⃣ - 替换特殊符号")
    print(f"   字符变化: {len(content) - before_symbol:+,}")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)\n")
    
    # 步骤 9: 规范化空白字符
    before_whitespace = len(content)
    content = preprocessor.normalize_whitespace(content)
    print(f"步骤 9️⃣ - 规范化空白字符")
    print(f"   字符变化: {len(content) - before_whitespace:+,}")
    print(f"   剩余字符: {len(content):,} ({len(content)/len(original_content)*100:.1f}%)\n")
    
    # 最终结果
    print("=" * 80)
    print(f"🎯 最终结果: {len(content):,} 字符 (保留 {len(content)/len(original_content)*100:.2f}%)")
    print("=" * 80)
    
    # 显示前 500 字符
    print(f"\n📝 处理后内容预览（前 500 字符）:")
    print("-" * 80)
    print(content[:500])
    print("-" * 80)

if __name__ == "__main__":
    debug_preprocessing()
