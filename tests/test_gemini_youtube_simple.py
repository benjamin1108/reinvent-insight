"""
简单测试: Gemini 能否理解 YouTube URL

直接使用 google-genai SDK 测试
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")


async def test_gemini_youtube_direct():
    """直接测试 Gemini 对 YouTube URL 的理解能力"""
    
    print("=" * 60)
    print("测试 Gemini YouTube URL 理解能力")
    print("=" * 60)
    
    try:
        from google import genai
        from google.genai import types
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY 未设置")
            return False
        
        print(f"✅ API Key 已加载: {api_key[:10]}...")
        
        # 创建客户端
        client = genai.Client(api_key=api_key)
        
        # 测试视频 - 使用较短的 AWS 视频
        test_url = "https://www.youtube.com/watch?v=jv-MprP4O8s"  # 短视频
        
        print(f"\n📹 测试视频: {test_url}")
        print("⏳ 调用 Gemini API...")
        
        # 使用简单提示词测试
        prompt = f"""请分析这个 YouTube 视频并告诉我：
1. 这个视频的主题是什么？
2. 视频大约多长？
3. 推荐3个适合截图的时间点（格式 MM:SS）

YouTube 链接: {test_url}

请用 JSON 格式回复，包含 topic, duration, screenshots 字段。
"""
        
        # 同步调用（简化测试）
        def sync_call():
            return client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=2000,
                )
            )
        
        import asyncio
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, sync_call),
            timeout=60
        )
        
        print("\n✅ Gemini 响应成功!")
        print("-" * 40)
        print(response.text)
        print("-" * 40)
        
        return True
        
    except asyncio.TimeoutError:
        print("\n❌ API 调用超时（60秒）")
        return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_gemini_video_file():
    """测试 Gemini File API 上传视频的能力"""
    
    print("\n" + "=" * 60)
    print("测试 Gemini File API (视频上传)")
    print("=" * 60)
    
    try:
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # 检查 File API 是否支持 URL
        print("ℹ️  Gemini File API 支持的文件类型:")
        print("   - 图片 (PNG, JPEG, GIF, WebP)")
        print("   - 视频 (MP4, AVI, MOV 等)")
        print("   - 音频 (MP3, WAV 等)")
        print("   - 文档 (PDF, TXT 等)")
        print("\n⚠️  注意: File API 需要先下载视频文件再上传")
        print("   这意味着需要使用 yt-dlp 下载视频后再分析")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


async def test_alternative_approach():
    """测试替代方案: 使用视频缩略图 + 字幕"""
    
    print("\n" + "=" * 60)
    print("替代方案: 视频缩略图 + 字幕分析")
    print("=" * 60)
    
    try:
        from google import genai
        from google.genai import types
        import urllib.request
        import tempfile
        import os
        
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # 使用 YouTube 缩略图 API
        video_id = "jv-MprP4O8s"
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        print(f"📷 获取视频缩略图: {thumbnail_url}")
        
        # 下载缩略图
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            urllib.request.urlretrieve(thumbnail_url, tmp.name)
            thumbnail_path = tmp.name
        
        print(f"✅ 缩略图已下载: {thumbnail_path}")
        
        # 读取图片数据
        with open(thumbnail_path, 'rb') as f:
            image_data = f.read()
        
        # 使用 Gemini 分析缩略图
        prompt = """这是一个 YouTube 视频的缩略图。
请分析这张图片并告诉我：
1. 这个视频可能是关于什么主题的？
2. 从缩略图中你能看到什么关键元素？

请用中文回答。"""
        
        print("⏳ 使用 Gemini 分析缩略图...")
        
        def sync_call():
            return client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
                ],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                )
            )
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, sync_call),
            timeout=30
        )
        
        print("\n✅ 缩略图分析成功!")
        print("-" * 40)
        print(response.text)
        print("-" * 40)
        
        # 清理临时文件
        os.unlink(thumbnail_path)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行测试"""
    print("\n🔬 开始 Gemini YouTube 功能测试\n")
    
    # 测试1: 直接传入 YouTube URL
    result1 = await test_gemini_youtube_direct()
    
    # 测试2: File API 说明
    result2 = await test_gemini_video_file()
    
    # 测试3: 替代方案 - 缩略图分析
    result3 = await test_alternative_approach()
    
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"  直接 URL 分析: {'✅ 成功' if result1 else '❌ 失败'}")
    print(f"  File API 说明: {'✅ 完成' if result2 else '❌ 失败'}")
    print(f"  缩略图分析:    {'✅ 成功' if result3 else '❌ 失败'}")
    print("=" * 60)
    
    if result1:
        print("\n🎉 好消息! Gemini 可以直接分析 YouTube URL!")
        print("   可以直接使用视频链接让 AI 推荐截图时间点。")
    else:
        print("\n📝 如果直接 URL 分析失败，替代方案：")
        print("   1. 使用 yt-dlp 下载视频")
        print("   2. 上传视频到 Gemini File API")
        print("   3. 让 Gemini 分析视频并推荐截图时间点")


if __name__ == "__main__":
    asyncio.run(main())
