"""后处理管道模块

提供文章生成后的精加工能力，如添加配图、内容润色、格式优化等。

使用方式：
    from reinvent_insight.services.analysis.post_processors import PostProcessorPipeline
    
    pipeline = PostProcessorPipeline()
    pipeline.register(ImageEnhancementProcessor())
    
    result = await pipeline.run(report, context)
"""

from .base import PostProcessor, PostProcessorContext, PostProcessorResult, ProcessorPriority
from .pipeline import PostProcessorPipeline, get_default_pipeline, register_processor
from .image_enhancement import ImageEnhancementProcessor, DiagramGeneratorProcessor
from .visual_insight import VisualInsightProcessor
from .keyframe_screenshot import KeyframeScreenshotProcessor

__all__ = [
    # 基类
    'PostProcessor',
    'PostProcessorContext', 
    'PostProcessorResult',
    'ProcessorPriority',
    # 管道
    'PostProcessorPipeline',
    'get_default_pipeline',
    'register_processor',
    # 内置处理器
    'ImageEnhancementProcessor',
    'DiagramGeneratorProcessor',
    'VisualInsightProcessor',
    'KeyframeScreenshotProcessor',
]
