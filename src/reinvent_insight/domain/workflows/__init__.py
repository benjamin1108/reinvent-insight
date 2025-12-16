"""工作流定义模块"""

from reinvent_insight.core.config import GenerationMode
from .base import AnalysisWorkflow, TaskNotifier
from .youtube_workflow import YouTubeAnalysisWorkflow


async def run_deep_summary_workflow(
    task_id: str,
    model_name: str,
    content,
    video_metadata,
    task_notifier: TaskNotifier,
    is_ultra_mode: bool = False,
    target_version: int = None,
    doc_hash: str = None,
    generation_mode: GenerationMode = GenerationMode.CONCURRENT
):
    """运行深度摘要工作流
    
    Args:
        task_id: 任务ID
        model_name: 模型名称
        content: 内容（字符串或DocumentContent）
        video_metadata: 视频元数据
        task_notifier: 任务通知器（用于进度报告）
        is_ultra_mode: 是否为Ultra模式
        target_version: 目标版本号（仅Ultra模式）
        doc_hash: 文档哈希（仅Ultra模式）
        generation_mode: 章节生成模式 (concurrent/sequential)
    """
    # 创建工作流实例
    workflow = YouTubeAnalysisWorkflow(
        task_id=task_id,
        model_name=model_name,
        content=content,
        video_metadata=video_metadata,
        task_notifier=task_notifier,
        is_ultra_mode=is_ultra_mode,
        target_version=target_version,
        doc_hash=doc_hash,
        generation_mode=generation_mode
    )
    
    # 执行工作流
    await workflow.run()


__all__ = [
    'AnalysisWorkflow',
    'TaskNotifier',
    'YouTubeAnalysisWorkflow',
    'run_deep_summary_workflow',
]
