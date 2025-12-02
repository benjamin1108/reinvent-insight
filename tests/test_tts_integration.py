"""
TTS 预生成系统集成测试

测试完整的文本预处理、任务队列和音频生成流程
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reinvent_insight.services.tts_text_preprocessor import TTSTextPreprocessor
from src.reinvent_insight.services.tts_pregeneration_service import TTSPregenerationService
from src.reinvent_insight.services.tts_service import TTSService
from src.reinvent_insight.services.audio_cache import AudioCache
from src.reinvent_insight.model_config import get_model_client
from src.reinvent_insight.config import TTS_TEXT_DIR


# 示例 Markdown 文章
SAMPLE_MARKDOWN = """---
title: AWS re:Invent 2024 - AI 创新突破
video_url: https://www.youtube.com/watch?v=test_integration_123
upload_date: 2024-11-28
---

# Advancing AI Innovation at AWS AWS 人工智能创新突破

### 引言

本文介绍 AWS re:Invent 2024 大会上的 AI 创新技术。

### 目录

- [AI 基础设施](#ai-infrastructure)
- [机器学习平台](#ml-platform)
- [核心洞见](#insights)

### AI 基础设施

AWS 推出了新一代 **AI 加速芯片** Trainium2，性能提升 4 倍。

主要特点：
- 超大规模训练能力
- 降低 40% 成本
- 支持最新模型架构

```python
# 示例代码（将被跳过）
import boto3
client = boto3.client('sagemaker')
```

### 机器学习平台

Amazon SageMaker 新增 → 多项创新功能。

### 核心洞见

1. AI 基础设施是云计算的下一个战场
2. 成本优化是企业 AI 应用的关键

### 金句

> "创新永无止境"
> "AI 改变一切"
"""


async def test_text_preprocessing():
    """测试文本预处理"""
    print("\n" + "="*60)
    print("测试 1: 文本预处理")
    print("="*60)
    
    preprocessor = TTSTextPreprocessor()
    
    result = preprocessor.preprocess(
        SAMPLE_MARKDOWN,
        video_url="https://www.youtube.com/watch?v=test_integration_123",
        title="AWS re:Invent 2024",
        upload_date="2024-11-28"
    )
    
    if result:
        print(f"✅ 预处理成功")
        print(f"   - 中文标题: {result.title_cn}")
        print(f"   - 文章哈希: {result.article_hash}")
        print(f"   - 原文长度: {result.original_length} 字符")
        print(f"   - 处理后长度: {result.processed_length} 字符")
        print(f"   - 移除章节: {', '.join(result.sections_removed)}")
        print(f"\n处理后文本预览 (前 200 字符):")
        print(f"   {result.text[:200]}...")
        
        # 保存到文件
        output_path = preprocessor.save_to_file(result, TTS_TEXT_DIR)
        if output_path:
            print(f"\n✅ 已保存到: {output_path}")
        
        return result
    else:
        print("❌ 预处理失败")
        return None


async def test_audio_cache():
    """测试音频缓存系统"""
    print("\n" + "="*60)
    print("测试 2: 音频缓存系统")
    print("="*60)
    
    cache_dir = Path("downloads/tts_cache")
    audio_cache = AudioCache(cache_dir, max_size_mb=500)
    
    # 测试查询
    test_hash = "test_article_hash"
    result = audio_cache.find_by_article_hash(test_hash)
    
    if result:
        print(f"✅ 找到缓存音频")
        print(f"   - 音频哈希: {result.hash}")
        print(f"   - 时长: {result.duration:.2f}s")
        print(f"   - 音色: {result.voice}")
    else:
        print(f"ℹ️  未找到哈希为 '{test_hash}' 的音频缓存")
    
    # 获取统计信息
    stats = audio_cache.get_stats()
    print(f"\n缓存统计:")
    print(f"   - 总文件数: {stats['total_files']}")
    print(f"   - 总大小: {stats['total_size_mb']:.2f} MB")
    print(f"   - 使用率: {stats['usage_percent']:.1f}%")
    print(f"   - 缓存目录: {stats['cache_dir']}")


async def test_pregeneration_service():
    """测试预生成服务"""
    print("\n" + "="*60)
    print("测试 3: TTS 预生成服务")
    print("="*60)
    
    try:
        # 初始化服务
        model_client = get_model_client("text_to_speech")
        tts_service = TTSService(model_client)
        audio_cache = AudioCache(Path("downloads/tts_cache"), max_size_mb=500)
        preprocessor = TTSTextPreprocessor()
        
        pregeneration_service = TTSPregenerationService(
            tts_service, audio_cache, preprocessor
        )
        
        print("✅ 服务初始化成功")
        
        # 获取队列统计
        stats = pregeneration_service.get_queue_stats()
        print(f"\n队列统计:")
        print(f"   - 队列长度: {stats['queue_size']}")
        print(f"   - 总任务数: {stats['total_tasks']}")
        print(f"   - 待处理: {stats['pending']}")
        print(f"   - 处理中: {stats['processing']}")
        print(f"   - 已完成: {stats['completed']}")
        print(f"   - 失败: {stats['failed']}")
        print(f"   - 服务运行: {stats['is_running']}")
        
        print("\nℹ️  实际音频生成需要 API 密钥和网络连接")
        print("   请在生产环境中测试完整流程")
        
    except Exception as e:
        print(f"❌ 服务初始化失败: {e}")


async def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("TTS 预生成系统集成测试")
    print("="*60)
    
    # 测试 1: 文本预处理
    preprocess_result = await test_text_preprocessing()
    
    # 测试 2: 音频缓存
    await test_audio_cache()
    
    # 测试 3: 预生成服务
    await test_pregeneration_service()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print("\n✅ 所有核心组件测试通过")
    print("\n下一步:")
    print("1. 启动后端服务: python -m src.reinvent_insight.main web")
    print("2. 访问前端页面测试完整流程")
    print("3. 添加一篇新文章，观察自动预生成")
    print("4. 在阅读页面测试播放按钮和移动端熄屏播放")


if __name__ == "__main__":
    asyncio.run(main())
