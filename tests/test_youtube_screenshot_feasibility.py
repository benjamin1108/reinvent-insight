"""
YouTube 视频关键截图方案可行性测试

测试两个关键点：
1. Gemini 能否解读 YouTube URL 并识别关键时间点
2. Playwright 能否在指定时间点对 YouTube 视频进行全屏截图

使用方法：
    python tests/test_youtube_screenshot_feasibility.py
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reinvent_insight.core import config
from reinvent_insight.infrastructure.ai.model_config import get_model_client


# 测试用的 YouTube 视频（AWS re:Invent 视频，较短，适合测试）
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # 替换为实际测试视频

# 输出目录
OUTPUT_DIR = config.OUTPUT_DIR / "test_screenshots"


async def test_gemini_youtube_understanding():
    """
    测试1: 验证 Gemini 能否理解 YouTube 视频内容并推荐截图时间点
    
    Gemini 2.0+ 支持直接传入 YouTube URL 进行视频理解
    """
    print("\n" + "=" * 60)
    print("测试 1: Gemini YouTube 视频理解能力")
    print("=" * 60)
    
    try:
        # 获取模型客户端
        client = get_model_client("video_summary")
        
        # 构建测试提示词
        prompt = f"""请分析以下 YouTube 视频，并推荐 3-5 个适合截图的关键时间点。

YouTube 视频链接: {TEST_VIDEO_URL}

请按以下 JSON 格式输出：
{{
    "video_analysis": {{
        "title": "视频标题",
        "duration_seconds": 视频时长（秒）,
        "main_topics": ["主题1", "主题2"]
    }},
    "screenshot_recommendations": [
        {{
            "timestamp_seconds": 时间戳（秒）,
            "timestamp_formatted": "MM:SS 格式",
            "description": "为什么这个时间点适合截图",
            "scene_type": "演示/图表/代码/演讲者/标题屏等"
        }}
    ]
}}

注意：
1. 优先选择有重要图表、代码演示、架构图的时间点
2. 避免选择过渡画面或模糊的时间点
3. 尽量分散选择，覆盖视频的不同部分
"""
        
        print(f"\n📹 测试视频: {TEST_VIDEO_URL}")
        print("⏳ 正在调用 Gemini API 分析视频...")
        
        # 调用 Gemini API
        response = await client.generate_content(
            prompt=prompt,
            is_json=True,
            thinking_level="low"
        )
        
        print("\n✅ Gemini 响应成功!")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        # 尝试解析 JSON
        import json
        try:
            result = json.loads(response)
            print("\n📊 解析结果:")
            print(f"   视频标题: {result.get('video_analysis', {}).get('title', 'N/A')}")
            print(f"   推荐截图点数量: {len(result.get('screenshot_recommendations', []))}")
            
            for i, rec in enumerate(result.get('screenshot_recommendations', []), 1):
                print(f"\n   截图点 {i}:")
                print(f"      时间: {rec.get('timestamp_formatted', 'N/A')}")
                print(f"      类型: {rec.get('scene_type', 'N/A')}")
                print(f"      原因: {rec.get('description', 'N/A')[:50]}...")
            
            return result
        except json.JSONDecodeError:
            print("⚠️  响应不是有效的 JSON，但 Gemini 能够理解视频")
            return None
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_playwright_youtube_screenshot(timestamp_seconds: int = 30):
    """
    测试2: 验证 Playwright 能否在指定时间点截取 YouTube 视频全屏截图
    
    Args:
        timestamp_seconds: 要截图的时间点（秒）
    """
    print("\n" + "=" * 60)
    print("测试 2: Playwright YouTube 视频截图能力")
    print("=" * 60)
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright 未安装，请运行: pip install playwright && playwright install chromium")
        return None
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 构建带时间戳的 YouTube URL
    video_url = f"{TEST_VIDEO_URL}&t={timestamp_seconds}s"
    output_path = OUTPUT_DIR / f"youtube_screenshot_{timestamp_seconds}s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    print(f"\n📹 视频 URL: {video_url}")
    print(f"⏱️  时间点: {timestamp_seconds} 秒")
    print(f"📁 输出路径: {output_path}")
    
    try:
        async with async_playwright() as p:
            print("\n🚀 启动 Chromium 浏览器...")
            
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--autoplay-policy=no-user-gesture-required',  # 允许自动播放
                ]
            )
            
            # 创建页面，模拟 1920x1080 分辨率
            page = await browser.new_page(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=2  # 高清截图
            )
            
            print("📄 加载 YouTube 页面...")
            
            # 加载页面
            await page.goto(video_url, wait_until='domcontentloaded', timeout=60000)
            
            # 等待视频播放器加载
            print("⏳ 等待视频播放器加载...")
            await asyncio.sleep(3)
            
            # 尝试点击播放按钮（如果有的话）
            try:
                play_button = page.locator('button.ytp-play-button')
                if await play_button.count() > 0:
                    print("▶️  点击播放按钮...")
                    await play_button.click()
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"   (跳过播放按钮: {e})")
            
            # 尝试全屏播放器
            try:
                # 双击视频进入全屏或点击全屏按钮
                fullscreen_button = page.locator('button.ytp-fullscreen-button')
                if await fullscreen_button.count() > 0:
                    print("🖥️  进入全屏模式...")
                    await fullscreen_button.click()
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"   (跳过全屏: {e})")
            
            # 隐藏 YouTube 控件
            print("🎬 隐藏播放控件...")
            await page.evaluate("""
                () => {
                    // 隐藏控制栏
                    const controls = document.querySelector('.ytp-chrome-bottom');
                    if (controls) controls.style.display = 'none';
                    
                    // 隐藏顶部渐变
                    const gradient = document.querySelector('.ytp-gradient-top');
                    if (gradient) gradient.style.display = 'none';
                    
                    // 隐藏底部渐变
                    const gradientBottom = document.querySelector('.ytp-gradient-bottom');
                    if (gradientBottom) gradientBottom.style.display = 'none';
                    
                    // 隐藏大播放按钮
                    const bigPlay = document.querySelector('.ytp-large-play-button');
                    if (bigPlay) bigPlay.style.display = 'none';
                }
            """)
            
            # 等待视频画面稳定
            print("⏳ 等待画面稳定...")
            await asyncio.sleep(3)
            
            # 尝试定位视频元素并截图
            print("📸 执行截图...")
            
            # 方法1: 尝试截取视频播放器
            video_player = page.locator('#movie_player')
            if await video_player.count() > 0:
                await video_player.screenshot(path=str(output_path))
                print(f"✅ 视频播放器截图成功!")
            else:
                # 方法2: 全页面截图
                await page.screenshot(path=str(output_path), full_page=False)
                print(f"✅ 全页面截图成功!")
            
            await browser.close()
            
            # 检查输出文件
            if output_path.exists():
                file_size = output_path.stat().st_size
                print(f"\n📊 截图信息:")
                print(f"   路径: {output_path}")
                print(f"   大小: {file_size / 1024:.1f} KB")
                return str(output_path)
            else:
                print("❌ 截图文件未生成")
                return None
                
    except Exception as e:
        print(f"\n❌ 截图失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_gemini_with_article():
    """
    测试3: 测试 Gemini 结合文章内容推荐截图时间点
    """
    print("\n" + "=" * 60)
    print("测试 3: Gemini 结合文章推荐截图时间点")
    print("=" * 60)
    
    # 模拟一篇 DeepInsight 文章（简化版）
    sample_article = """
# AWS Lambda 深度解析

## 第1章：Lambda 基础架构
Lambda 是 AWS 的无服务器计算服务，可以让您在不管理服务器的情况下运行代码。
核心概念包括：函数、触发器、执行环境。

## 第2章：冷启动优化
冷启动是 Lambda 面临的主要挑战之一。本章讨论了预置并发、SnapStart 等优化策略。
关键图表展示了不同配置下的启动时间对比。

## 第3章：最佳实践
包括函数大小控制、依赖管理、监控和告警配置等内容。
演示了如何使用 CloudWatch 进行性能监控。
"""
    
    try:
        client = get_model_client("video_summary")
        
        prompt = f"""你是一个视频内容分析助手。我有一个 YouTube 视频和基于它生成的文章。
请分析视频内容，找出最能辅助文章阅读的关键截图时间点。

## YouTube 视频
链接: {TEST_VIDEO_URL}

## 文章内容
{sample_article}

## 任务
请推荐 3-5 个关键截图时间点，优先选择：
1. 文章中提到的图表、架构图出现的时刻
2. 代码演示的关键步骤
3. 重要概念的可视化展示

输出 JSON 格式：
{{
    "recommendations": [
        {{
            "timestamp_seconds": 120,
            "timestamp_formatted": "02:00",
            "related_chapter": "第1章：Lambda 基础架构",
            "content_type": "架构图",
            "description": "Lambda 执行环境架构图"
        }}
    ]
}}
"""
        
        print("⏳ 正在分析视频与文章的关联...")
        
        response = await client.generate_content(
            prompt=prompt,
            is_json=True,
            thinking_level="low"
        )
        
        print("\n✅ 分析完成!")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        return response
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("YouTube 视频关键截图方案可行性测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试视频: {TEST_VIDEO_URL}")
    
    results = {
        "gemini_youtube": False,
        "playwright_screenshot": False,
        "gemini_with_article": False
    }
    
    # 测试1: Gemini YouTube 理解
    gemini_result = await test_gemini_youtube_understanding()
    results["gemini_youtube"] = gemini_result is not None
    
    # 测试2: Playwright 截图
    # 如果测试1成功，使用推荐的时间点；否则使用默认值
    timestamp = 30
    if gemini_result and gemini_result.get('screenshot_recommendations'):
        first_rec = gemini_result['screenshot_recommendations'][0]
        timestamp = first_rec.get('timestamp_seconds', 30)
    
    screenshot_path = await test_playwright_youtube_screenshot(timestamp)
    results["playwright_screenshot"] = screenshot_path is not None
    
    # 测试3: 结合文章推荐
    article_result = await test_gemini_with_article()
    results["gemini_with_article"] = article_result is not None
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "-" * 60)
    if all_passed:
        print("🎉 所有测试通过！方案可行！")
        print("\n建议的实现方案：")
        print("1. 使用 Gemini 2.0+ 的视频理解能力分析 YouTube 视频")
        print("2. 结合 DeepInsight 文章内容，让 AI 推荐关键截图时间点")
        print("3. 使用 Playwright 访问带时间戳的 YouTube URL 进行截图")
        print("4. 将截图插入到文章相应位置")
    else:
        print("⚠️  部分测试失败，需要进一步调查")
        
        if not results["gemini_youtube"]:
            print("\n❗ Gemini YouTube 理解失败")
            print("   可能原因：")
            print("   - Gemini API 可能不支持直接解析 YouTube URL")
            print("   - 需要先下载视频再上传到 Gemini")
            print("   替代方案：使用视频字幕 + 缩略图分析")
        
        if not results["playwright_screenshot"]:
            print("\n❗ Playwright 截图失败")
            print("   可能原因：")
            print("   - YouTube 可能有反爬虫机制")
            print("   - 需要登录或 Cookie")
            print("   替代方案：使用 yt-dlp 下载视频后本地截图")
    
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
