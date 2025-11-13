"""
Summarizer 模块 - 已迁移到统一模型配置系统

该模块已被 model_config.py 替代。
所有模型调用现在通过统一的配置系统管理。

迁移指南：
-----------
旧代码：
    from .summarizer import get_summarizer
    summarizer = get_summarizer("Gemini")
    result = await summarizer.generate_content(prompt)

新代码：
    from .model_config import get_model_client
    client = get_model_client("video_summary")  # 或其他任务类型
    result = await client.generate_content(prompt)

支持的任务类型：
- video_summary: 视频摘要
- pdf_processing: PDF处理
- visual_generation: 可视化生成
- document_analysis: 文档分析

配置文件位置：
- config/model_config.yaml

更多信息请参考：
- src/reinvent_insight/model_config.py
- .kiro/specs/unified-model-config/design.md
"""

import logging

logger = logging.getLogger(__name__)

# 为了向后兼容，保留一个简单的重定向
def get_summarizer(model_name: str = None):
    """
    已废弃：请使用 get_model_client() 替代
    
    该函数保留用于向后兼容，但建议迁移到新的 API。
    """
    logger.warning(
        "get_summarizer() 已废弃，请使用 model_config.get_model_client() 替代。"
        "详见 src/reinvent_insight/model_config.py"
    )
    
    from .model_config import get_default_client
    return get_default_client()
