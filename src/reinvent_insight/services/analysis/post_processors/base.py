"""后处理器基类和数据模型"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ProcessorPriority(Enum):
    """处理器优先级（数字越小越先执行）"""
    HIGHEST = 0    # 最高优先级：结构调整
    HIGH = 10      # 高优先级：内容重组
    NORMAL = 50    # 正常优先级：内容增强
    LOW = 90       # 低优先级：格式美化
    LOWEST = 100   # 最低优先级：最终清理


@dataclass
class PostProcessorContext:
    """后处理上下文
    
    包含处理过程中需要的所有信息
    """
    # 核心信息
    task_id: str
    report_content: str
    
    # 文档元数据
    title: str = ""
    doc_hash: str = ""
    chapter_count: int = 0
    
    # 模式标记
    is_ultra_mode: bool = False
    is_pdf: bool = False
    content_type: str = "transcript"
    
    # 任务目录（存放中间文件）
    task_dir: str = ""
    
    # 原始素材
    source_content: str = ""
    outline_content: str = ""
    
    # 元数据
    video_url: str = ""
    upload_date: str = ""
    
    # 扩展字段（用于处理器间传递数据）
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取扩展字段"""
        return self.extra.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置扩展字段"""
        self.extra[key] = value


@dataclass
class PostProcessorResult:
    """后处理结果"""
    success: bool
    content: str
    message: str = ""
    changes: List[str] = field(default_factory=list)  # 变更记录
    
    @classmethod
    def ok(cls, content: str, message: str = "", changes: List[str] = None) -> "PostProcessorResult":
        """成功结果"""
        return cls(success=True, content=content, message=message, changes=changes or [])
    
    @classmethod
    def skip(cls, content: str, reason: str = "跳过") -> "PostProcessorResult":
        """跳过处理"""
        return cls(success=True, content=content, message=f"跳过: {reason}")
    
    @classmethod
    def error(cls, content: str, error: str) -> "PostProcessorResult":
        """失败结果（保持原内容）"""
        return cls(success=False, content=content, message=f"错误: {error}")


class PostProcessor(ABC):
    """后处理器抽象基类
    
    所有精加工处理器都应继承此类。
    
    实现示例（同步处理器）：
        class ImageEnhancementProcessor(PostProcessor):
            name = "image_enhancement"
            description = "为文章添加AI生成配图"
            priority = ProcessorPriority.NORMAL
            is_async = False  # 同步执行，结果写入报告
            
            async def should_run(self, context: PostProcessorContext) -> bool:
                return context.is_ultra_mode and context.chapter_count >= 10
            
            async def process(self, context: PostProcessorContext) -> PostProcessorResult:
                enhanced_content = await self._add_images(context.report_content)
                return PostProcessorResult.ok(enhanced_content, "添加了5张配图")
    
    实现示例（异步处理器）：
        class VisualInsightProcessor(PostProcessor):
            name = "visual_insight"
            description = "生成可视化解读HTML"
            priority = ProcessorPriority.LOW
            is_async = True  # 异步执行，只触发不等待
            
            async def should_run(self, context: PostProcessorContext) -> bool:
                return True  # 所有文章都生成Visual
            
            async def process(self, context: PostProcessorContext) -> PostProcessorResult:
                # 只触发任务，不等待完成
                await self._trigger_visual_generation(context)
                return PostProcessorResult.ok(context.report_content, "已触发Visual生成")
    """
    
    # 子类应覆盖这些属性
    name: str = "base_processor"
    description: str = "基础后处理器"
    priority: ProcessorPriority = ProcessorPriority.NORMAL
    is_async: bool = False  # True = 异步执行（只触发不等待），False = 同步执行
    
    @abstractmethod
    async def should_run(self, context: PostProcessorContext) -> bool:
        """判断是否应该运行此处理器
        
        Args:
            context: 后处理上下文
            
        Returns:
            True 表示应该运行，False 表示跳过
        """
        pass
    
    @abstractmethod
    async def process(self, context: PostProcessorContext) -> PostProcessorResult:
        """执行后处理
        
        Args:
            context: 后处理上下文（包含report_content）
            
        Returns:
            处理结果
        """
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, priority={self.priority.value})>"
