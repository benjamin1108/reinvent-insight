"""
数据模型定义

定义了HTML到Markdown转换过程中使用的数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class ImageInfo:
    """图片信息数据类
    
    Attributes:
        url: 图片URL（绝对路径）
        alt: alt文本
        caption: 图片说明（可选）
        position: 在文章中的位置（可选）
    """
    url: str
    alt: str
    caption: Optional[str] = None
    position: Optional[int] = None
    
    def to_markdown(self) -> str:
        """转换为Markdown图片语法
        
        Returns:
            Markdown格式的图片字符串
        """
        # 标准Markdown图片语法: ![alt](url)
        markdown = f"![{self.alt}]({self.url})"
        
        # 如果有caption，添加为下一行的斜体文本
        if self.caption:
            markdown += f"\n*{self.caption}*"
        
        return markdown
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            字典表示
        """
        return {
            "url": self.url,
            "alt": self.alt,
            "caption": self.caption,
            "position": self.position,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageInfo':
        """从字典创建ImageInfo对象
        
        Args:
            data: 字典数据
            
        Returns:
            ImageInfo对象
        """
        return cls(
            url=data.get("url", ""),
            alt=data.get("alt", ""),
            caption=data.get("caption"),
            position=data.get("position"),
        )


@dataclass
class ExtractedContent:
    """提取的内容数据类
    
    Attributes:
        title: 文章标题
        content: 正文内容（Markdown格式）
        images: 相关图片列表
        metadata: 元数据（作者、日期等）
    """
    title: str
    content: str
    images: List[ImageInfo] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            字典表示
        """
        return {
            "title": self.title,
            "content": self.content,
            "images": [img.to_dict() for img in self.images],
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractedContent':
        """从字典创建ExtractedContent对象
        
        Args:
            data: 字典数据
            
        Returns:
            ExtractedContent对象
        """
        images_data = data.get("images", [])
        images = [ImageInfo.from_dict(img) for img in images_data]
        
        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
            images=images,
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversionResult:
    """转换结果数据类
    
    Attributes:
        markdown: 生成的Markdown文本
        content: 提取的内容对象
        stats: 统计信息
    """
    markdown: str
    content: ExtractedContent
    stats: Dict[str, Any] = field(default_factory=dict)
    
    def save(self, path: Path) -> None:
        """保存Markdown到文件
        
        Args:
            path: 输出文件路径
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.markdown)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            字典表示
        """
        return {
            "markdown": self.markdown,
            "content": self.content.to_dict(),
            "stats": self.stats,
        }
