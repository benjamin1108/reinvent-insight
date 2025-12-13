#!/usr/bin/env python3
"""
字幕翻译功能测试脚本

测试分段翻译英文字幕为中文的完整流程。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reinvent_insight.services.subtitle_translation_service import get_subtitle_translation_service


# 测试用的简短 VTT 字幕
TEST_VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
Hello everyone, welcome to AWS re:Invent 2024.

00:00:04.500 --> 00:00:08.000
Today we're going to talk about serverless architecture.

00:00:08.500 --> 00:00:12.000
First, let me introduce myself. I'm a solutions architect at AWS.

00:00:12.500 --> 00:00:16.000
We'll cover three main topics in this session.

00:00:16.500 --> 00:00:20.000
Lambda, API Gateway, and DynamoDB.
"""


async def test_vtt_parsing():
    """测试 VTT 解析"""
    print("=" * 60)
    print("测试 1: VTT 解析")
    print("=" * 60)
    
    service = get_subtitle_translation_service()
    cues = service.parse_vtt(TEST_VTT)
    
    print(f"解析到 {len(cues)} 条字幕:")
    for cue in cues:
        print(f"  [{cue.index}] {cue.start} --> {cue.end}")
        print(f"      {cue.text}")
    
    assert len(cues) == 5, f"期望 5 条字幕，实际 {len(cues)} 条"
    print("\n✅ VTT 解析测试通过")
    return cues


async def test_translation():
    """测试翻译功能"""
    print("\n" + "=" * 60)
    print("测试 2: 字幕翻译")
    print("=" * 60)
    
    service = get_subtitle_translation_service()
    
    print(f"配置信息:")
    print(f"  chunk_size: {service.chunk_size}")
    print(f"  target_language: {service.target_language}")
    print(f"  source_language: {service.source_language}")
    
    async def progress_callback(current, total):
        print(f"  翻译进度: {current}/{total}")
    
    print("\n开始翻译...")
    translated_cues, translated_vtt = await service.translate_subtitles(
        TEST_VTT, 
        progress_callback=progress_callback
    )
    
    print(f"\n翻译完成，共 {len(translated_cues)} 条:")
    for cue in translated_cues:
        print(f"  [{cue.index}] 原文: {cue.text}")
        print(f"       译文: {cue.translated_text}")
    
    print("\n生成的 VTT:")
    print("-" * 40)
    print(translated_vtt[:500])
    print("-" * 40)
    
    # 验证翻译结果
    success_count = sum(1 for c in translated_cues if c.translated_text and c.translated_text != c.text)
    print(f"\n成功翻译: {success_count}/{len(translated_cues)} 条")
    
    if success_count > 0:
        print("\n✅ 翻译测试通过")
    else:
        print("\n⚠️ 翻译结果可能有问题，请检查")
    
    return translated_vtt


async def main():
    """运行所有测试"""
    print("\n🚀 开始字幕翻译功能测试\n")
    
    try:
        # 测试解析
        await test_vtt_parsing()
        
        # 测试翻译
        await test_translation()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
