#!/usr/bin/env python3
"""
测试输入端分片策略

运行方式:
    python tests/test_input_chunking.py
"""
import asyncio
import os
import sys
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reinvent_insight.model_config import GeminiClient, ModelConfig


def test_text_splitting():
    """测试文本切分功能"""
    # 创建一个简单的配置
    config = ModelConfig(
        task_type="text_to_speech",
        provider="gemini",
        model_name="gemini-2.5-flash-preview-tts",
        api_key="dummy_key",
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        max_output_tokens=8000
    )
    client = GeminiClient(config)
    
    # 测试短文本（不需要切分）
    short_text = "这是一个短文本。"
    chunks = client._split_text_for_streaming(short_text, max_chunk_size=100)
    assert len(chunks) == 1, f"短文本应该只有1个片段，但得到 {len(chunks)}"
    assert chunks[0] == short_text, "短文本内容应该保持不变"
    print(f"✅ 短文本测试通过: {len(chunks)} 个片段")
    
    # 测试长文本（需要切分）
    long_text = """
    这是第一个句子。这是第二个句子！这是第三个句子？
    这是第四个句子。这是第五个句子。这是第六个句子。
    这是第七个句子。这是第八个句子。这是第九个句子。
    这是第十个句子。
    """
    chunks = client._split_text_for_streaming(long_text, max_chunk_size=50)
    assert len(chunks) > 1, f"长文本应该被切分为多个片段，但只得到 {len(chunks)}"
    print(f"✅ 长文本测试通过: {len(chunks)} 个片段")
    
    # 验证每个片段的长度
    for i, chunk in enumerate(chunks):
        print(f"   片段 {i+1}: {len(chunk)} 字符 - {chunk[:30]}...")
        # 大部分片段应该不超过 max_chunk_size（最后一个可能较短）
        if i < len(chunks) - 1:
            assert len(chunk) <= 100, f"片段 {i+1} 过长: {len(chunk)} 字符"
    
    # 测试没有标点符号的文本（强制按字符切分）
    no_punctuation = "这是一段没有任何标点符号的很长的文本" * 10
    chunks = client._split_text_for_streaming(no_punctuation, max_chunk_size=50)
    assert len(chunks) > 1, "没有标点的长文本应该被强制切分"
    print(f"✅ 无标点文本测试通过: {len(chunks)} 个片段")
    
    # 验证切分后的文本拼接回去应该等于原文本
    rejoined = "".join(chunks)
    assert rejoined.strip() == no_punctuation.strip(), "切分后拼接应该等于原文本"
    print("✅ 文本完整性测试通过")
    
    print("\n🎉 所有文本切分测试通过！")


async def test_streaming_with_chunking():
    """测试带输入端分片的流式播放"""
    # 检查 API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  跳过实际 API 测试（需要 GEMINI_API_KEY）")
        return
    
    # 创建客户端
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
    
    # 测试文本（多个句子）
    text = """
    这是第一个句子，用于测试输入端分片策略。
    这是第二个句子，我们期望能快速收到第一个片段的音频。
    这是第三个句子，系统应该持续发送后续片段的音频。
    这样用户就能在几秒钟内开始听到声音，而不是等待所有音频生成完成。
    """
    
    print("=" * 60)
    print("🎬 开始测试输入端分片流式 TTS")
    print("=" * 60)
    print(f"📝 文本长度: {len(text)} 字符")
    print()
    
    # 记录时间
    start_time = time.time()
    first_chunk_time = None
    chunk_count = 0
    total_bytes = 0
    
    try:
        # 迭代流
        async for chunk in client.generate_tts_stream(text, "kore", "zh-CN"):
            current_time = time.time()
            
            if first_chunk_time is None:
                first_chunk_time = current_time
                first_chunk_latency = first_chunk_time - start_time
                print(f"⚡ 首块延迟: {first_chunk_latency:.2f}s")
                print()
                
                if first_chunk_latency < 5.0:
                    print("🎯 太棒了！首块延迟 < 5 秒，输入端分片策略成功！")
                elif first_chunk_latency < 10.0:
                    print("✅ 不错！首块延迟 < 10 秒，比之前的 15 秒有改善")
                else:
                    print(f"⚠️  首块延迟仍然较长: {first_chunk_latency:.2f}s")
                print()
            
            chunk_count += 1
            chunk_size = len(chunk)
            total_bytes += chunk_size
            
            elapsed = current_time - start_time
            print(f"📦 块 {chunk_count}: {chunk_size} bytes, 累计 {total_bytes / 1024:.1f}KB, 耗时 {elapsed:.2f}s")
        
        # 完成
        total_time = time.time() - start_time
        print()
        print("=" * 60)
        print("🎉 输入端分片流式播放测试完成")
        print("=" * 60)
        print(f"📊 统计信息:")
        print(f"   - 总块数: {chunk_count}")
        print(f"   - 总大小: {total_bytes / 1024:.1f}KB")
        print(f"   - 总时长: {total_time:.2f}s")
        print(f"   - 首块延迟: {first_chunk_latency:.2f}s" if first_chunk_time else "   - 首块延迟: N/A")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行文本切分测试（不需要 API key）
    test_text_splitting()
    
    print("\n" + "=" * 60 + "\n")
    
    # 运行实际 API 测试（需要 API key）
    asyncio.run(test_streaming_with_chunking())
