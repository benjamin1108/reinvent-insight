"""应用启动服务 - 管理应用启动时的初始化逻辑"""

import os
import asyncio
import logging

from reinvent_insight.core import config

logger = logging.getLogger(__name__)


def init_post_processors():
    """初始化后处理管道，注册处理器"""
    try:
        from reinvent_insight.services.analysis.post_processors import (
            register_processor,
            VisualInsightProcessor
        )
        from reinvent_insight.services.analysis.post_processors.keyframe_screenshot import KeyframeScreenshotProcessor
        
        # 注册 Visual Insight 后处理器（异步，文章生成后自动触发）
        register_processor(VisualInsightProcessor())
        
        # 注册关键帧截图处理器（异步，文章生成后自动触发）
        if config.ENABLE_KEYFRAME_SCREENSHOT:
            register_processor(KeyframeScreenshotProcessor())
            logger.info("关键帧截图处理器已注册")
        
        logger.info("后处理管道已初始化")
        
    except Exception as e:
        logger.error(f"初始化后处理管道失败: {e}", exc_info=True)


async def start_visual_watcher():
    """启动可视化解读文件监测器"""
    # 检查配置开关
    visual_enabled = os.getenv("VISUAL_INTERPRETATION_ENABLED", "true").lower() == "true"
    
    if not visual_enabled:
        logger.info("可视化解读功能已禁用（VISUAL_INTERPRETATION_ENABLED=false）")
        return
    
    try:
        from reinvent_insight.services.analysis.visual_watcher import VisualInterpretationWatcher
        
        watcher = VisualInterpretationWatcher(
            watch_dir=config.OUTPUT_DIR,
            model_name=config.PREFERRED_MODEL
        )
        
        # 在后台运行监测器
        asyncio.create_task(watcher.start_watching())
        logger.info("可视化解读文件监测器已启动")
        
    except Exception as e:
        logger.error(f"启动可视化解读监测器失败: {e}", exc_info=True)


async def start_tts_pregeneration():
    """启动 TTS 预生成服务"""
    # 检查配置开关
    if not config.TTS_PREGENERATE_ENABLED:
        logger.info("TTS 预生成服务已禁用（TTS_PREGENERATE_ENABLED=false）")
        return
    
    try:
        # 获取预生成服务
        from reinvent_insight.services.tts_pregeneration_service import get_tts_pregeneration_service
        pregeneration_service = get_tts_pregeneration_service()
        
        # 启动服务
        await pregeneration_service.start()
        logger.info("TTS 预生成服务已启动")
        
        # 启动文件监控
        from reinvent_insight.infrastructure.file_system.watcher import start_tts_watching
        
        # 获取当前事件循环，以便在回调中使用
        loop = asyncio.get_running_loop()
        
        def tts_callback(file_path, article_hash, source_file):
            """TTS 预生成回调函数"""
            # 在事件循环中调度异步任务
            asyncio.run_coroutine_threadsafe(
                pregeneration_service.add_task(article_hash, source_file),
                loop
            )
        
        start_tts_watching(config.OUTPUT_DIR, tts_callback)
        logger.info("TTS 预生成文件监控器已启动")
        
    except Exception as e:
        logger.error(f"启动 TTS 预生成服务失败: {e}", exc_info=True)
