"""
测试基于字幕的关键帧分析
"""

import asyncio
import os
import sys
import json
import re
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from reinvent_insight.core import config


def parse_vtt_with_timestamps(vtt_content: str) -> str:
    """解析 VTT 字幕，保留时间戳但简化格式"""
    lines = vtt_content.splitlines()
    result = []
    current_time = None
    current_text = []
    seen_texts = set()
    
    for line in lines:
        line = line.strip()
        
        if 'WEBVTT' in line or 'Kind:' in line or 'Language:' in line or not line:
            continue
        
        if '-->' in line:
            if current_time and current_text:
                text = ' '.join(current_text)
                text = re.sub(r'<[^>]+>', '', text)
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    result.append(f"[{current_time}] {text}")
            
            time_match = re.match(r'(\d+):(\d+):(\d+)', line)
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2))
                seconds = int(time_match.group(3))
                total_seconds = hours * 3600 + minutes * 60 + seconds
                current_time = f"{total_seconds}s"
            else:
                time_match = re.match(r'(\d+):(\d+)', line)
                if time_match:
                    minutes = int(time_match.group(1))
                    seconds = int(time_match.group(2))
                    total_seconds = minutes * 60 + seconds
                    current_time = f"{total_seconds}s"
            
            current_text = []
        else:
            if line and not line.isdigit():
                current_text.append(line)
    
    if current_time and current_text:
        text = ' '.join(current_text)
        text = re.sub(r'<[^>]+>', '', text)
        if text and text not in seen_texts:
            result.append(f"[{current_time}] {text}")
    
    return '\n'.join(result)


async def analyze_video_keyframes(video_url: str):
    """分析视频关键帧"""
    
    print("=" * 60)
    print(f"分析视频: {video_url}")
    print("=" * 60)
    
    try:
        from google import genai
        from google.genai import types
        from reinvent_insight.infrastructure.media.youtube_downloader import (
            SubtitleDownloader, normalize_youtube_url
        )
        
        # 1. 获取字幕
        print("\nℹ️  步骤1: 获取字幕...")
        normalized_url, _ = normalize_youtube_url(video_url)
        dl = SubtitleDownloader(normalized_url)
        
        # 获取元数据
        if not dl._fetch_metadata() or not dl.metadata:
            print("❌ 无法获取视频元数据")
            return None
        
        print(f"✅ 视频标题: {dl.metadata.title}")
        
        # 查找字幕文件
        vtt_path = None
        for lang in ['en', 'en-US', 'zh-Hans', 'zh-CN']:
            path = config.SUBTITLE_DIR / f"{dl.metadata.sanitized_title}.{lang}.vtt"
            if path.exists():
                vtt_path = path
                print(f"✅ 找到字幕: {path.name}")
                break
        
        if not vtt_path:
            print("⚠️  字幕不存在，尝试下载...")
            _, _, error = dl.download()
            if error:
                print(f"❌ 下载字幕失败: {error.message}")
                return None
            
            for lang in ['en', 'en-US', 'zh-Hans', 'zh-CN']:
                path = config.SUBTITLE_DIR / f"{dl.metadata.sanitized_title}.{lang}.vtt"
                if path.exists():
                    vtt_path = path
                    break
        
        if not vtt_path:
            print("❌ 找不到字幕文件")
            return None
        
        # 2. 解析带时间戳的字幕
        print("\nℹ️  步骤2: 解析字幕...")
        vtt_content = vtt_path.read_text(encoding='utf-8')
        timed_transcript = parse_vtt_with_timestamps(vtt_content)
        
        print(f"✅ 字幕长度: {len(timed_transcript)} 字符")
        print("\n字幕预览 (前1000字符):")
        print("-" * 40)
        print(timed_transcript[:1000])
        print("-" * 40)
        
        # 3. 调用 Gemini 分析
        print("\nℹ️  步骤3: 调用 Gemini 分析字幕...")
        
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        prompt = f"""你是一个视频内容分析专家。请根据以下带时间轴的字幕，分析视频内容并推荐截图时间点。

## 视频字幕（带时间轴）
{timed_transcript[:15000]}

## 任务
请推荐 6 个最值得截图的关键时间点：

1. 根据字幕内容，识别演讲者可能在展示图表、架构图、代码或演示的时刻
2. 优先选择字幕中提到 "as you can see"、"this diagram"、"here we have"、"let me show you"、"on the screen" 等表达的时间点
3. 避免纯口播片段，选择有视觉内容的时刻
4. 时间点应均匀分布在视频各部分

## 输出格式
请以 JSON 格式返回，描述使用中文：
{{
  "keyframes": [
    {{
      "timestamp": 秒数(整数),
      "time_display": "分:秒格式",
      "description": "为什么这个时间点值得截图，字幕中说了什么"
    }}
  ]
}}
"""
        
        def sync_call():
            return client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4000,
                )
            )
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, sync_call),
            timeout=120
        )
        
        print("✅ Gemini 响应成功!")
        
        # 解析 JSON
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        try:
            data = json.loads(text.strip())
            print("\n" + "=" * 60)
            print("推荐截图点:")
            print("=" * 60)
            for i, kf in enumerate(data.get('keyframes', []), 1):
                print(f"\n{i}. [{kf.get('time_display', '?')}] (第{kf.get('timestamp', 0)}秒)")
                print(f"   描述: {kf.get('description', 'N/A')}")
            
            print("\n" + "=" * 60)
            print("完整 JSON 输出:")
            print("=" * 60)
            print(json.dumps(data, ensure_ascii=False, indent=2))
            
            return data
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            print("原始响应:")
            print(response.text)
            return None
        
    except asyncio.TimeoutError:
        print("\n❌ API 调用超时")
        return None
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    video_url = "https://youtu.be/rrlppOVdGYY"
    
    print("\n🎬 基于字幕的关键帧分析测试\n")
    
    result = await analyze_video_keyframes(video_url)
    
    if result:
        print("\n\n✅ 分析完成!")


if __name__ == "__main__":
    asyncio.run(main())
