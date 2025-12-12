"""
测试 Playwright 对 YouTube 视频的截图能力
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reinvent_insight.core import config


async def test_youtube_screenshot():
    """测试 Playwright 截取 YouTube 视频"""
    
    print("=" * 60)
    print("测试 Playwright YouTube 视频截图")
    print("=" * 60)
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright 未安装")
        return False
    
    # 输出目录
    output_dir = config.OUTPUT_DIR / "test_screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 测试视频和时间点
    video_id = "dQw4w9WgXcQ"  # 经典测试视频
    timestamps = [30, 60, 120]  # 测试多个时间点
    
    results = []
    
    async with async_playwright() as p:
        print("\n🚀 启动 Chromium 浏览器...")
        
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--autoplay-policy=no-user-gesture-required',
            ]
        )
        
        for timestamp in timestamps:
            print(f"\n📹 截取时间点: {timestamp} 秒")
            
            try:
                # 创建新页面
                page = await browser.new_page(
                    viewport={'width': 1920, 'height': 1080},
                    device_scale_factor=2
                )
                
                # 构建 embed URL (嵌入式播放器更可控)
                embed_url = f"https://www.youtube.com/embed/{video_id}?start={timestamp}&autoplay=1&controls=0&modestbranding=1&rel=0"
                
                print(f"   URL: {embed_url}")
                
                await page.goto(embed_url, wait_until='domcontentloaded', timeout=30000)
                
                # 等待视频加载和播放
                print("   ⏳ 等待视频加载...")
                await asyncio.sleep(5)
                
                # 尝试点击播放（如果需要）
                try:
                    # 检查是否有播放按钮覆盖层
                    play_overlay = page.locator('.ytp-large-play-button')
                    if await play_overlay.is_visible():
                        print("   ▶️  点击播放按钮...")
                        await play_overlay.click()
                        await asyncio.sleep(3)
                except Exception:
                    pass
                
                # 截图
                output_path = output_dir / f"youtube_{video_id}_{timestamp}s.png"
                
                print(f"   📸 截图中...")
                await page.screenshot(path=str(output_path), full_page=False)
                
                if output_path.exists():
                    file_size = output_path.stat().st_size / 1024
                    print(f"   ✅ 成功! 大小: {file_size:.1f} KB")
                    print(f"   📁 路径: {output_path}")
                    results.append({
                        "timestamp": timestamp,
                        "path": str(output_path),
                        "size_kb": file_size,
                        "success": True
                    })
                else:
                    print(f"   ❌ 截图文件未生成")
                    results.append({"timestamp": timestamp, "success": False})
                
                await page.close()
                
            except Exception as e:
                print(f"   ❌ 错误: {e}")
                results.append({"timestamp": timestamp, "success": False, "error": str(e)})
        
        await browser.close()
    
    # 总结
    print("\n" + "=" * 60)
    print("截图结果总结")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r.get("success"))
    print(f"成功: {success_count}/{len(timestamps)}")
    
    for r in results:
        if r.get("success"):
            print(f"  ✅ {r['timestamp']}秒 - {r['size_kb']:.1f} KB")
        else:
            print(f"  ❌ {r['timestamp']}秒 - {r.get('error', '失败')}")
    
    return success_count > 0


async def test_youtube_embed_screenshot():
    """测试使用 embed 播放器的截图方式"""
    
    print("\n" + "=" * 60)
    print("测试 YouTube Embed 播放器截图")
    print("=" * 60)
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright 未安装")
        return False
    
    output_dir = config.OUTPUT_DIR / "test_screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    video_id = "jv-MprP4O8s"  # 另一个测试视频
    timestamp = 45
    
    async with async_playwright() as p:
        print("\n🚀 启动浏览器...")
        
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # 使用 embed 格式，设置自动播放和隐藏控件
        page = await browser.new_page(
            viewport={'width': 1280, 'height': 720},
            device_scale_factor=2
        )
        
        # 创建一个 HTML 页面来嵌入视频
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; background: black; }}
                iframe {{ 
                    width: 100vw; 
                    height: 100vh; 
                    border: none;
                }}
            </style>
        </head>
        <body>
            <iframe 
                src="https://www.youtube.com/embed/{video_id}?start={timestamp}&autoplay=1&mute=1&controls=0&modestbranding=1&showinfo=0&rel=0&iv_load_policy=3&enablejsapi=1"
                allow="autoplay; encrypted-media"
                allowfullscreen>
            </iframe>
        </body>
        </html>
        """
        
        # 使用 data URL 加载 HTML
        await page.set_content(html_content)
        
        print(f"📹 视频ID: {video_id}, 时间点: {timestamp}秒")
        print("⏳ 等待视频加载和播放...")
        
        # 等待视频加载
        await asyncio.sleep(8)
        
        # 截图
        output_path = output_dir / f"youtube_embed_{video_id}_{timestamp}s.png"
        
        print("📸 执行截图...")
        await page.screenshot(path=str(output_path), full_page=False)
        
        await browser.close()
        
        if output_path.exists():
            file_size = output_path.stat().st_size / 1024
            print(f"\n✅ 截图成功!")
            print(f"   路径: {output_path}")
            print(f"   大小: {file_size:.1f} KB")
            return True
        else:
            print("\n❌ 截图失败")
            return False


async def main():
    """运行测试"""
    print("\n🔬 Playwright YouTube 截图测试\n")
    
    # 测试1: 直接截图
    result1 = await test_youtube_screenshot()
    
    # 测试2: Embed 方式
    result2 = await test_youtube_embed_screenshot()
    
    print("\n" + "=" * 60)
    print("最终结果")
    print("=" * 60)
    print(f"  直接截图: {'✅ 成功' if result1 else '❌ 失败'}")
    print(f"  Embed截图: {'✅ 成功' if result2 else '❌ 失败'}")
    
    if result1 or result2:
        print("\n🎉 Playwright 可以截取 YouTube 视频!")
        print("   推荐使用 embed 模式，可以更好地控制播放器。")
    else:
        print("\n⚠️  截图测试失败，可能需要调整策略")
        print("   替代方案: 使用 yt-dlp 下载视频后用 ffmpeg 截图")


if __name__ == "__main__":
    asyncio.run(main())
