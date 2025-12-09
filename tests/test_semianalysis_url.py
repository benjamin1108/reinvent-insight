"""
测试SemiAnalysis文章URL转换为Markdown

测试URL: https://newsletter.semianalysis.com/p/clustermax-20-the-industry-standard
"""

import asyncio
import logging
from pathlib import Path
from reinvent_insight.infrastructure.html import HTMLToMarkdownConverter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_semianalysis_conversion():
    """测试SemiAnalysis文章转换"""
    
    url = "https://newsletter.semianalysis.com/p/microsofts-ai-strategy-deconstructed"
    output_path = Path("downloads/summaries/microsoft_ai_strategy.md")
    
    logger.info(f"开始测试URL转换: {url}")
    logger.info(f"输出路径: {output_path}")
    logger.info(f"预计处理时间: 5-8分钟（分段处理 + 低思考模式）")
    
    try:
        # 创建转换器（启用调试模式）
        converter = HTMLToMarkdownConverter(debug=True)
        
        # 执行转换
        import time
        start_time = time.time()
        logger.info("正在获取网页并转换（调试模式已启用）...")
        result = await converter.convert_from_url(url, output_path)
        elapsed_time = time.time() - start_time
        
        # 输出结果统计
        logger.info("=" * 60)
        logger.info("转换完成！")
        logger.info("=" * 60)
        logger.info(f"处理时间: {elapsed_time:.1f}秒 ({elapsed_time/60:.1f}分钟)")
        logger.info(f"标题: {result.content.title}")
        logger.info(f"正文长度: {len(result.content.content)} 字符")
        logger.info(f"图片数量: {len(result.content.images)}")
        logger.info(f"Markdown长度: {len(result.markdown)} 字符")
        logger.info(f"输出文件: {output_path}")
        logger.info("=" * 60)
        
        # 显示前500个字符的预览
        logger.info("\n内容预览（前500字符）:")
        logger.info("-" * 60)
        print(result.markdown[:500])
        logger.info("-" * 60)
        
        # 显示图片信息
        if result.content.images:
            logger.info(f"\n提取的图片 ({len(result.content.images)}张):")
            for i, img in enumerate(result.content.images[:5], 1):  # 只显示前5张
                logger.info(f"  {i}. {img.url}")
                if img.alt:
                    logger.info(f"     Alt: {img.alt}")
        
        return result
        
    except Exception as e:
        logger.error(f"转换失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_semianalysis_conversion())
