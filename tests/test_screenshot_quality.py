#!/usr/bin/env python3
"""
测试长图生成质量（清晰度和宽度）

使用方法：
    python tests/test_screenshot_quality.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from reinvent_insight.infrastructure.media.screenshot_generator import ScreenshotGenerator


async def test_quality():
    """测试不同配置的截图质量"""
    
    # 测试 HTML 文件路径
    test_html = Path("downloads/summaries/test_visual.html")
    
    if not test_html.exists():
        print(f"❌ 测试文件不存在: {test_html}")
        return
    
    print("=" * 80)
    print("长图质量测试")
    print("=" * 80)
    print()
    
    # 配置 1：移动端高清（1080px 宽度，2x 分辨率）
    print("📱 测试配置 1: 移动端高清（1080px 宽度，2x 分辨率）")
    print("-" * 80)
    
    generator1 = ScreenshotGenerator(
        viewport_width=1080,
        wait_time=3,
        browser_timeout=30000
    )
    
    output1 = Path("downloads/summaries/images/test_mobile_hd.png")
    
    try:
        result1 = await generator1.capture_full_page(
            html_path=test_html,
            output_path=output1,
            viewport_width=1080
        )
        
        print(f"✅ 生成成功")
        print(f"   文件路径: {result1['path']}")
        print(f"   图片尺寸: {result1['dimensions']['width']}x{result1['dimensions']['height']}px")
        print(f"   文件大小: {result1['file_size'] / 1024 / 1024:.2f}MB")
        print(f"   生成耗时: {result1['duration']:.2f}s")
        print()
        print(f"   💡 提示: 实际渲染分辨率为 {result1['dimensions']['width']*2}x{result1['dimensions']['height']*2}px（2x）")
        print(f"   💡 在 1:1 查看时，PPI 是标准截图的 2 倍，清晰度显著提升")
        print()
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 配置 2：桌面端标清（1920px 宽度，2x 分辨率）
    print("🖥️  测试配置 2: 桌面端高清（1920px 宽度，2x 分辨率）")
    print("-" * 80)
    
    generator2 = ScreenshotGenerator(
        viewport_width=1920,
        wait_time=3,
        browser_timeout=30000
    )
    
    output2 = Path("downloads/summaries/images/test_desktop_hd.png")
    
    try:
        result2 = await generator2.capture_full_page(
            html_path=test_html,
            output_path=output2,
            viewport_width=1920
        )
        
        print(f"✅ 生成成功")
        print(f"   文件路径: {result2['path']}")
        print(f"   图片尺寸: {result2['dimensions']['width']}x{result2['dimensions']['height']}px")
        print(f"   文件大小: {result2['file_size'] / 1024 / 1024:.2f}MB")
        print(f"   生成耗时: {result2['duration']:.2f}s")
        print()
        print(f"   💡 提示: 实际渲染分辨率为 {result2['dimensions']['width']*2}x{result2['dimensions']['height']*2}px（2x）")
        print()
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 对比总结
    print("=" * 80)
    print("📊 对比总结")
    print("=" * 80)
    print()
    print("移动端版本（1080px）:")
    print(f"  - 优势: 宽度适中，适合手机查看，两侧留白少")
    print(f"  - 文件大小: {result1['file_size'] / 1024 / 1024:.2f}MB")
    print(f"  - 推荐场景: 微信/微博分享、移动端阅读")
    print()
    print("桌面端版本（1920px）:")
    print(f"  - 优势: 宽度更宽，适合大屏展示")
    print(f"  - 文件大小: {result2['file_size'] / 1024 / 1024:.2f}MB")
    print(f"  - 推荐场景: PPT 展示、桌面端查看")
    print()
    print("🎯 两个版本都使用 2x 分辨率，清晰度一致（高清）")
    print()


if __name__ == "__main__":
    asyncio.run(test_quality())
