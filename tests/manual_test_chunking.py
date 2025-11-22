#!/usr/bin/env python3
"""
手动测试输入端分片策略的实际效果

运行方式:
    export GEMINI_API_KEY=your_key
    python tests/manual_test_chunking.py
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reinvent_insight.model_config import GeminiClient, ModelConfig


async def test_short_chunks():
    """测试短片段策略"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 错误: 需要设置 GEMINI_API_KEY 环境变量")
        return
    
    config = ModelConfig(
        task_type="text_to_speech",
        provider="gemini",
        model_name="gemini-2.5-flash-preview-tts",
        api_key=api_key,
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        max_output_tokens=8000
    )
    client = GeminiClient(config)
    
    # 使用多个短句子测试（确保会被切分）
    text = """你好，这是第一句话。这是第二句话。这是第三句话。
    这是第四句话。这是第五句话。这是第六句话。
    这是第七句话。这是第八句话。这是第九句话。
    这是第十句话。这是第十一句话。这是第十二句话。"""
    
    print("=" * 70)
    print("🎬 测试输入端分片策略（短片段）")
    print("=" * 70)
    print(f"📝 测试文本: {text}")
    print(f"📏 文本长度: {len(text)} 字符")
    print()
    
    # 先看看会切分成几个片段
    chunks = client._split_text_for_streaming(text, max_chunk_size=50)
    print(f"✂️  文本将被切分为 {len(chunks)} 个片段:")
    for i, chunk in enumerate(chunks, 1):
        print(f"   片段 {i}: {len(chunk)} 字 - {chunk}")
    print()
    
    start_time = time.time()
    first_chunk_time = None
    chunk_count = 0
    total_bytes = 0
    
    print("🎵 开始生成音频...")
    print()
    
    try:
        async for audio_chunk in client.generate_tts_stream(text, "kore", "zh-CN"):
            current_time = time.time()
            
            if first_chunk_time is None:
                first_chunk_time = current_time
                latency = first_chunk_time - start_time
                print(f"⚡ 首块延迟: {latency:.2f}s")
                
                if latency < 5.0:
                    print("🎯 成功！延迟 < 5 秒")
                elif latency < 8.0:
                    print("✅ 良好！延迟 < 8 秒")
                else:
                    print(f"⚠️  延迟较长: {latency:.2f}s")
                print()
            
            chunk_count += 1
            chunk_size = len(audio_chunk)
            total_bytes += chunk_size
            elapsed = current_time - start_time
            
            print(f"📦 音频块 {chunk_count}: {chunk_size} bytes, 累计 {total_bytes/1024:.1f}KB, {elapsed:.2f}s")
        
        total_time = time.time() - start_time
        print()
        print("=" * 70)
        print("✅ 测试完成")
        print("=" * 70)
        print(f"📊 统计:")
        print(f"   文本片段数: {len(chunks)}")
        print(f"   音频块数: {chunk_count}")
        print(f"   总大小: {total_bytes/1024:.1f}KB")
        print(f"   总时长: {total_time:.2f}s")
        print(f"   首块延迟: {first_chunk_time - start_time:.2f}s" if first_chunk_time else "   N/A")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_short_chunks())
