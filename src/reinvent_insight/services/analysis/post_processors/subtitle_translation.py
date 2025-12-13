"""字幕翻译后处理器

在文章生成完成后，异步触发字幕翻译。
"""

import re
import asyncio
from typing import Optional
from loguru import logger

from reinvent_insight.core import config
from reinvent_insight.services.subtitle_translation_service import (
    get_cached_translation,
    trigger_subtitle_translation
)
from .base import PostProcessor, PostProcessorContext, PostProcessorResult, ProcessorPriority


class SubtitleTranslationProcessor(PostProcessor):
    """字幕翻译后处理器
    
    异步处理器：在文章生成完成后，触发字幕翻译任务。
    不阻塞主流程，翻译在后台异步完成。
    
    仅对 YouTube 视频类型的文章有效。
    """
    
    name = "subtitle_translation"
    description = "翻译字幕为中文"
    priority = ProcessorPriority.LOW
    is_async = True
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    async def should_run(self, context: PostProcessorContext) -> bool:
        """判断是否应该触发字幕翻译"""
        if not self.enabled:
            return False
        
        if not getattr(config, 'SUBTITLE_AUTO_TRANSLATE', True):
            logger.debug("字幕自动翻译已禁用（配置）")
            return False
        
        # 只处理 YouTube 视频
        video_url = context.video_url
        if not video_url or ('youtube' not in video_url.lower() and 'youtu.be' not in video_url.lower()):
            logger.debug("非 YouTube 视频，跳过字幕翻译")
            return False
        
        video_id = self._extract_video_id(video_url)
        if not video_id:
            logger.debug(f"无法从 URL 提取 video_id: {video_url}")
            return False
        
        # 检查翻译缓存是否已存在
        if get_cached_translation(video_id):
            logger.debug(f"中文字幕已存在，跳过翻译: video_id={video_id}")
            return False
        
        return True
    
    async def process(self, context: PostProcessorContext) -> PostProcessorResult:
        """触发字幕翻译任务（异步）"""
        try:
            video_id = self._extract_video_id(context.video_url)
            
            if not video_id:
                return PostProcessorResult.skip(
                    context.report_content,
                    "无法提取 video_id"
                )
            
            logger.info(f"触发字幕翻译任务: video_id={video_id}")
            
            # 获取文章内容作为上下文
            article_content = context.report_content
            
            # 触发后台翻译任务（统一入口）
            asyncio.create_task(
                trigger_subtitle_translation(video_id, article_content)
            )
            
            return PostProcessorResult.ok(
                context.report_content,
                f"已触发字幕翻译 (video_id: {video_id})"
            )
            
        except Exception as e:
            logger.error(f"触发字幕翻译失败: {e}", exc_info=True)
            return PostProcessorResult.skip(
                context.report_content,
                f"触发失败: {e}"
            )
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """从 YouTube URL 提取 video_id"""
        if not url:
            return None
        
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'[?&]v=([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
