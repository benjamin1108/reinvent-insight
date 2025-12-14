"""后处理管道实现"""

import logging
from typing import List, Optional, Type

from .base import PostProcessor, PostProcessorContext, PostProcessorResult, ProcessorPriority

logger = logging.getLogger(__name__)


class PostProcessorPipeline:
    """后处理管道
    
    管理和执行一系列后处理器，按优先级顺序执行。
    
    使用示例：
        pipeline = PostProcessorPipeline()
        pipeline.register(ImageEnhancementProcessor())
        pipeline.register(ContentPolishProcessor())
        
        context = PostProcessorContext(
            task_id="xxx",
            report_content=final_report,
            is_ultra_mode=True,
            chapter_count=18
        )
        
        result = await pipeline.run(context)
        final_report = result.content
    """
    
    def __init__(self):
        self._processors: List[PostProcessor] = []
        self._enabled: bool = True
    
    def register(self, processor: PostProcessor) -> "PostProcessorPipeline":
        """注册后处理器
        
        Args:
            processor: 后处理器实例
            
        Returns:
            self（支持链式调用）
        """
        self._processors.append(processor)
        # 按优先级排序
        self._processors.sort(key=lambda p: p.priority.value)
        logger.debug(f"注册后处理器: {processor}")
        return self
    
    def unregister(self, name: str) -> bool:
        """取消注册后处理器
        
        Args:
            name: 处理器名称
            
        Returns:
            是否成功取消
        """
        for i, processor in enumerate(self._processors):
            if processor.name == name:
                self._processors.pop(i)
                logger.debug(f"取消注册后处理器: {name}")
                return True
        return False
    
    def enable(self) -> None:
        """启用管道"""
        self._enabled = True
    
    def disable(self) -> None:
        """禁用管道"""
        self._enabled = False
    
    @property
    def processors(self) -> List[PostProcessor]:
        """获取已注册的处理器列表（按优先级排序）"""
        return self._processors.copy()
    
    async def run(
        self, 
        context: PostProcessorContext,
        stop_on_error: bool = False
    ) -> PostProcessorResult:
        """执行后处理管道
        
        Args:
            context: 后处理上下文
            stop_on_error: 遇到错误是否停止
            
        Returns:
            最终处理结果
        """
        if not self._enabled:
            logger.info("后处理管道已禁用，跳过所有处理")
            return PostProcessorResult.skip(context.report_content, "管道已禁用")
        
        if not self._processors:
            logger.debug("没有注册任何后处理器")
            return PostProcessorResult.ok(context.report_content, "无处理器")
        
        current_content = context.report_content
        all_changes: List[str] = []
        executed_count = 0
        skipped_count = 0
        error_count = 0
        
        logger.info(f"开始执行后处理管道，共 {len(self._processors)} 个处理器")
        
        for processor in self._processors:
            try:
                # 检查是否应该运行
                should_run = await processor.should_run(context)
                if not should_run:
                    logger.debug(f"[{processor.name}] 条件不满足，跳过")
                    skipped_count += 1
                    continue
                
                # 更新上下文中的内容
                context.report_content = current_content
                
                # 根据处理器类型执行
                if processor.is_async:
                    # 异步处理器：只触发不等待
                    logger.info(f"[{processor.name}] 触发异步任务...")
                    try:
                        result = await processor.process(context)
                        executed_count += 1
                        logger.info(f"[{processor.name}] 已触发: {result.message}")
                        # 异步处理器不修改内容，不记录changes
                    except Exception as e:
                        logger.warning(f"[{processor.name}] 触发失败: {e}")
                        # 异步处理器失败不影响主流程
                else:
                    # 同步处理器：执行并等待结果
                    logger.info(f"[{processor.name}] 开始执行...")
                    
                    result = await processor.process(context)
                    
                    if result.success:
                        current_content = result.content
                        executed_count += 1
                        if result.changes:
                            all_changes.extend(result.changes)
                        logger.info(f"[{processor.name}] 完成: {result.message}")
                    else:
                        error_count += 1
                        logger.warning(f"[{processor.name}] 失败: {result.message}")
                        if stop_on_error:
                            return PostProcessorResult.error(
                                current_content, 
                                f"处理器 {processor.name} 失败: {result.message}"
                            )
                        
            except Exception as e:
                error_count += 1
                logger.error(f"[{processor.name}] 异常: {e}", exc_info=True)
                if stop_on_error and not processor.is_async:
                    return PostProcessorResult.error(current_content, str(e))
        
        summary = f"执行 {executed_count} 个，跳过 {skipped_count} 个，失败 {error_count} 个"
        logger.info(f"后处理管道完成: {summary}")
        
        return PostProcessorResult.ok(current_content, summary, all_changes)


# 全局默认管道实例
_default_pipeline: Optional[PostProcessorPipeline] = None


def get_default_pipeline() -> PostProcessorPipeline:
    """获取默认后处理管道
    
    Returns:
        全局默认管道实例
    """
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = PostProcessorPipeline()
        # 在这里注册默认的处理器
        # _default_pipeline.register(SomeDefaultProcessor())
    return _default_pipeline


def register_processor(processor: PostProcessor) -> None:
    """向默认管道注册处理器
    
    Args:
        processor: 后处理器实例
    """
    get_default_pipeline().register(processor)
