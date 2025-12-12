"""
优化版 YouTube 截图测试

解决问题：
1. 等待视频实际加载完成
2. 确保捕捉到视频帧而非加载画面
3. 验证截图质量
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reinvent_insight.core import config


async def test_youtube_screenshot_optimized():
    """优化版 YouTube 截图"""
    
    print("=" * 60)
    print("优化版 YouTube 视频截图测试")
    print("=" * 60)
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright 未安装")
        return False
    
    output_dir = config.OUTPUT_DIR / "test_screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    video_id = "dQw4w9WgXcQ"  # 经典测试视频
    timestamp = 60  # 1分钟位置
    
    async with async_playwright() as p:
        print("\n🚀 启动浏览器 (headless)...")
        
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--autoplay-policy=no-user-gesture-required',
                '--disable-web-security',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=2,
            # 模拟真实浏览器
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # 使用 watch 页面而非 embed（更真实）
        url = f"https://www.youtube.com/watch?v={video_id}&t={timestamp}s"
        
        print(f"\n📹 视频: {video_id}")
        print(f"⏱️  时间点: {timestamp}秒")
        print(f"🔗 URL: {url}")
        
        print("\n📄 加载页面...")
        await page.goto(url, wait_until='networkidle', timeout=60000)
        
        # 等待视频播放器
        print("⏳ 等待视频播放器加载...")
        try:
            await page.wait_for_selector('#movie_player', timeout=15000)
            print("   ✅ 播放器已加载")
        except Exception:
            print("   ⚠️  播放器选择器未找到")
        
        # 同意 Cookie（如果有弹窗）
        try:
            consent_button = page.locator('button:has-text("Accept all")')
            if await consent_button.count() > 0:
                print("🍪 处理 Cookie 同意弹窗...")
                await consent_button.click()
                await asyncio.sleep(1)
        except Exception:
            pass
        
        # 等待视频元素
        await asyncio.sleep(3)
        
        # 尝试点击播放
        try:
            # 先检查视频状态
            is_playing = await page.evaluate("""
                () => {
                    const video = document.querySelector('video');
                    return video && !video.paused;
                }
            """)
            
            if not is_playing:
                print("▶️  尝试播放视频...")
                # 点击视频区域
                video_container = page.locator('#movie_player')
                if await video_container.count() > 0:
                    await video_container.click()
                    await asyncio.sleep(2)
        except Exception as e:
            print(f"   (播放尝试: {e})")
        
        # 跳转到指定时间
        print(f"⏩ 跳转到 {timestamp} 秒...")
        try:
            await page.evaluate(f"""
                () => {{
                    const video = document.querySelector('video');
                    if (video) {{
                        video.currentTime = {timestamp};
                        video.play();
                    }}
                }}
            """)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"   (跳转: {e})")
        
        # 进入全屏并隐藏控件
        print("🎬 优化截图画面...")
        await page.evaluate("""
            () => {
                // 隐藏所有 YouTube 覆盖层
                const elementsToHide = [
                    '.ytp-chrome-top',
                    '.ytp-chrome-bottom', 
                    '.ytp-gradient-top',
                    '.ytp-gradient-bottom',
                    '.ytp-large-play-button',
                    '.ytp-spinner',
                    '.ytp-pause-overlay',
                    '.ytp-cued-thumbnail-overlay',
                    'ytd-masthead',
                    '#secondary',
                    '#below',
                    '#related',
                    '#comments',
                ];
                
                elementsToHide.forEach(selector => {
                    const el = document.querySelector(selector);
                    if (el) el.style.display = 'none';
                });
                
                // 最大化视频播放器
                const player = document.querySelector('#movie_player');
                if (player) {
                    player.style.position = 'fixed';
                    player.style.top = '0';
                    player.style.left = '0';
                    player.style.width = '100vw';
                    player.style.height = '100vh';
                    player.style.zIndex = '9999';
                }
            }
        """)
        
        # 等待渲染
        await asyncio.sleep(3)
        
        # 检查视频是否有内容
        has_video_content = await page.evaluate("""
            () => {
                const video = document.querySelector('video');
                if (!video) return false;
                // 检查视频是否已加载帧
                return video.readyState >= 2;
            }
        """)
        
        print(f"   视频状态: {'已加载' if has_video_content else '未加载'}")
        
        # 截图
        output_path = output_dir / f"youtube_optimized_{video_id}_{timestamp}s.png"
        
        print("\n📸 执行高清截图...")
        
        # 尝试只截取视频播放器
        try:
            player = page.locator('#movie_player')
            if await player.count() > 0:
                await player.screenshot(path=str(output_path))
            else:
                await page.screenshot(path=str(output_path), full_page=False)
        except Exception:
            await page.screenshot(path=str(output_path), full_page=False)
        
        await browser.close()
        
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"\n✅ 截图成功!")
            print(f"   📁 路径: {output_path}")
            print(f"   📊 大小: {file_size / 1024:.1f} KB ({file_size / 1024 / 1024:.2f} MB)")
            
            # 判断截图质量
            if file_size > 500 * 1024:  # 大于 500KB
                print("   🎉 高质量截图（视频帧）")
                return True
            elif file_size > 100 * 1024:
                print("   ⚠️  中等质量（可能是视频帧）")
                return True
            else:
                print("   ⚠️  低质量（可能是加载画面或黑屏）")
                return False
        else:
            print("❌ 截图失败")
            return False


async def test_yt_dlp_ffmpeg_approach():
    """
    替代方案：使用 yt-dlp + ffmpeg 截图
    
    这种方法更可靠，因为直接操作视频文件
    """
    
    print("\n" + "=" * 60)
    print("替代方案: yt-dlp + ffmpeg 截图")
    print("=" * 60)
    
    import subprocess
    import tempfile
    import os
    
    video_id = "dQw4w9WgXcQ"
    timestamp = 60
    
    output_dir = config.OUTPUT_DIR / "test_screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"ytdlp_ffmpeg_{video_id}_{timestamp}s.jpg"
    
    print(f"\n📹 视频ID: {video_id}")
    print(f"⏱️  时间点: {timestamp}秒")
    
    try:
        # 方法: 使用 yt-dlp 获取直接视频流 URL，然后用 ffmpeg 截图
        print("\n1️⃣  获取视频流 URL...")
        
        result = subprocess.run(
            ['yt-dlp', '-g', '-f', 'best[height<=720]', f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"   ❌ 获取 URL 失败: {result.stderr}")
            return False
        
        video_url = result.stdout.strip().split('\n')[0]
        print(f"   ✅ 获取成功")
        
        print("\n2️⃣  使用 ffmpeg 截图...")
        
        # 使用 ffmpeg 截取特定时间点
        ffmpeg_cmd = [
            'ffmpeg',
            '-ss', str(timestamp),  # 跳转到指定时间
            '-i', video_url,  # 输入流
            '-vframes', '1',  # 只截取1帧
            '-q:v', '2',  # 高质量
            '-y',  # 覆盖输出
            str(output_path)
        ]
        
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"\n✅ 截图成功!")
            print(f"   📁 路径: {output_path}")
            print(f"   📊 大小: {file_size / 1024:.1f} KB")
            return True
        else:
            print(f"   ❌ 截图失败: {result.stderr[:200]}")
            return False
            
    except FileNotFoundError as e:
        print(f"\n❌ 命令未找到: {e}")
        print("   需要安装: yt-dlp 和 ffmpeg")
        return False
    except subprocess.TimeoutExpired:
        print("\n❌ 命令超时")
        return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


async def main():
    """运行测试"""
    print("\n🔬 YouTube 视频截图方案对比测试\n")
    
    # 方案1: Playwright 优化版
    result1 = await test_youtube_screenshot_optimized()
    
    # 方案2: yt-dlp + ffmpeg
    result2 = await test_yt_dlp_ffmpeg_approach()
    
    print("\n" + "=" * 60)
    print("方案对比结果")
    print("=" * 60)
    print(f"  Playwright 方案: {'✅ 成功' if result1 else '❌ 失败'}")
    print(f"  yt-dlp+ffmpeg:  {'✅ 成功' if result2 else '❌ 失败'}")
    
    print("\n📝 方案建议:")
    if result1 and result2:
        print("   两种方案都可行！")
        print("   - Playwright: 更灵活，但可能受 YouTube 限制")
        print("   - yt-dlp+ffmpeg: 更可靠，适合批量处理")
    elif result2:
        print("   推荐使用 yt-dlp + ffmpeg 方案（更可靠）")
    elif result1:
        print("   Playwright 方案可用")
    else:
        print("   两种方案都失败，需要进一步调查")


if __name__ == "__main__":
    asyncio.run(main())
