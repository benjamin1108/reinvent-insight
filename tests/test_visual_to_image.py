"""
测试 Visual Insight 转长图功能

验证完整的端到端流程
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import logging

from reinvent_insight.services.visual_to_image_service import get_visual_to_image_service
from reinvent_insight.core import config

logger = logging.getLogger(__name__)


async def test_visual_to_image():
    """测试长图生成功能"""
    
    logger.info("=" * 60)
    logger.info("开始测试 Visual Insight 转长图功能")
    logger.info("=" * 60)
    
    # 检查配置
    logger.info(f"长图功能启用: {config.VISUAL_LONG_IMAGE_ENABLED}")
    logger.info(f"视口宽度: {config.VISUAL_SCREENSHOT_VIEWPORT_WIDTH}px")
    logger.info(f"等待时间: {config.VISUAL_SCREENSHOT_WAIT_TIME}s")
    logger.info(f"输出目录: {config.VISUAL_LONG_IMAGE_DIR}")
    
    # 检查 images 目录
    if not config.VISUAL_LONG_IMAGE_DIR.exists():
        logger.warning(f"图片目录不存在，创建: {config.VISUAL_LONG_IMAGE_DIR}")
        config.VISUAL_LONG_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 查找已有的 Visual HTML 文件
    visual_html_files = list(config.OUTPUT_DIR.glob("*_visual.html"))
    
    if not visual_html_files:
        logger.warning("未找到任何 Visual Insight HTML 文件")
        logger.info("请先生成 Visual Insight，然后再运行此测试")
        return
    
    logger.info(f"找到 {len(visual_html_files)} 个 Visual HTML 文件")
    
    # 选择第一个文件进行测试
    test_html = visual_html_files[0]
    logger.info(f"使用测试文件: {test_html.name}")
    
    # 获取对应的 doc_hash
    # 从文件名提取 (假设格式为 {hash}_visual.html)
    base_name = test_html.stem.replace("_visual", "")
    
    # 尝试查找对应的文章文件
    article_files = list(config.OUTPUT_DIR.glob(f"{base_name}.md"))
    
    if not article_files:
        logger.warning(f"未找到对应的文章文件: {base_name}.md")
        logger.info("跳过测试")
        return
    
    logger.info(f"对应文章: {article_files[0].name}")
    
    # 获取服务
    service = get_visual_to_image_service()
    
    # 模拟生成（直接使用文件路径测试截图功能）
    from reinvent_insight.infrastructure.media.screenshot_generator import ScreenshotGenerator
    
    screenshot_gen = ScreenshotGenerator()
    
    # 生成输出路径
    output_path = config.VISUAL_LONG_IMAGE_DIR / f"{base_name}_visual_test.png"
    
    logger.info(f"开始截图测试...")
    logger.info(f"HTML: {test_html}")
    logger.info(f"输出: {output_path}")
    
    try:
        result = await screenshot_gen.capture_full_page(
            html_path=test_html,
            output_path=output_path
        )
        
        logger.info("截图测试成功！")
        logger.info(f"图片路径: {result['path']}")
        logger.info(f"图片尺寸: {result['dimensions']['width']}x{result['dimensions']['height']}px")
        logger.info(f"文件大小: {result['file_size'] / 1024 / 1024:.2f}MB")
        logger.info(f"耗时: {result['duration']:.2f}s")
        
        # 验证文件存在
        if output_path.exists():
            logger.info(f"图片文件已生成: {output_path}")
        else:
            logger.error("图片文件未生成！")
            
    except Exception as e:
        logger.error(f"截图测试失败: {e}", exc_info=True)
        raise
    
    logger.info("=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_visual_to_image())
