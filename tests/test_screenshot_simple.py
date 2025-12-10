"""
简单的截图功能测试

直接测试 ScreenshotGenerator 是否能正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reinvent_insight.infrastructure.media.screenshot_generator import ScreenshotGenerator
from reinvent_insight.core import config


async def test_screenshot():
    """测试截图功能"""
    
    print("=" * 60)
    print("测试 Playwright 截图功能")
    print("=" * 60)
    
    # 测试文件
    test_html = config.OUTPUT_DIR / "test_visual.html"
    output_image = config.VISUAL_LONG_IMAGE_DIR / "test_screenshot.png"
    
    if not test_html.exists():
        print(f"❌ 测试文件不存在: {test_html}")
        return
    
    print(f"HTML 文件: {test_html}")
    print(f"输出图片: {output_image}")
    print()
    
    # 创建截图生成器
    generator = ScreenshotGenerator()
    
    try:
        print("🚀 开始截图...")
        result = await generator.capture_full_page(
            html_path=test_html,
            output_path=output_image
        )
        
        print()
        print("✅ 截图成功！")
        print(f"   路径: {result['path']}")
        print(f"   尺寸: {result['dimensions']['width']}x{result['dimensions']['height']}px")
        print(f"   大小: {result['file_size'] / 1024 / 1024:.2f}MB")
        print(f"   耗时: {result['duration']:.2f}s")
        
        if output_image.exists():
            print(f"\n✅ 图片文件已生成: {output_image}")
        else:
            print(f"\n❌ 图片文件未生成")
            
    except Exception as e:
        print(f"\n❌ 截图失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_screenshot())
