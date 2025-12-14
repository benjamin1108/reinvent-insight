"""
Visual To Image Service - Visual Insight 转长图服务

负责协调截图生成、文件管理和元数据更新
"""

import re
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

import logging

import yaml

from reinvent_insight.core import config
from reinvent_insight.services.document.hash_registry import (
    hash_to_filename,
    hash_to_versions,
)
from reinvent_insight.infrastructure.media.screenshot_generator import ScreenshotGenerator


logger = logging.getLogger(__name__)


class VisualToImageService:
    """Visual Insight 转长图服务"""
    
    def __init__(self):
        """初始化服务"""
        self.screenshot_generator = ScreenshotGenerator()
        self.output_dir = config.OUTPUT_DIR
        self.image_dir = config.VISUAL_LONG_IMAGE_DIR
        
        # 确保图片目录存在
        self.image_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"初始化 VisualToImageService - 图片目录: {self.image_dir}")
    
    async def generate_long_image(
        self, 
        doc_hash: str, 
        version: Optional[int] = None,
        viewport_width: Optional[int] = None,
        force_regenerate: bool = False
    ) -> Dict:
        """
        生成长图主流程
        
        Args:
            doc_hash: 文档哈希
            version: 版本号（可选）
            viewport_width: 视口宽度（可选）
            force_regenerate: 是否强制重新生成
            
        Returns:
            包含生成结果的字典
            
        Raises:
            FileNotFoundError: Visual HTML 文件不存在
            Exception: 截图生成失败
        """
        logger.info(f"开始生成长图 - doc_hash: {doc_hash}, version: {version}")
        
        # 1. 定位 Visual HTML 文件
        visual_html_path, article_path = self._locate_visual_html(doc_hash, version)
        logger.info(f"定位到 Visual HTML: {visual_html_path}")
        logger.info(f"对应文章: {article_path}")
        
        # 2. 确定输出路径
        image_path = self._get_image_output_path(visual_html_path)
        logger.info(f"长图输出路径: {image_path}")
        
        # 3. 检查是否需要重新生成
        if not force_regenerate and image_path.exists():
            # 检查 HTML 是否更新
            html_mtime = visual_html_path.stat().st_mtime
            image_mtime = image_path.stat().st_mtime
            
            if image_mtime > html_mtime:
                logger.info("长图已存在且未过期，跳过生成")
                file_size = image_path.stat().st_size
                
                # 读取已有元数据
                metadata = self._read_metadata(article_path)
                existing_info = metadata.get('visual_long_image', {})
                
                return {
                    "status": "success",
                    "message": "长图已存在",
                    "image_path": str(image_path.relative_to(self.output_dir)),
                    "file_size": file_size,
                    "dimensions": existing_info.get('dimensions', {}),
                    "generated_at": existing_info.get('generated_at')
                }
        
        # 4. 执行截图
        logger.info("开始截图生成...")
        screenshot_info = await self.screenshot_generator.capture_full_page(
            html_path=visual_html_path,
            output_path=image_path,
            viewport_width=viewport_width
        )
        
        # 5. 更新文章元数据
        logger.info("更新文章元数据...")
        await self._update_metadata(article_path, image_path, screenshot_info)
        
        logger.info(f"长图生成完成 - {image_path}")
        
        return {
            "status": "success",
            "message": "长图生成成功",
            "image_path": str(image_path.relative_to(self.output_dir)),
            "file_size": screenshot_info['file_size'],
            "dimensions": screenshot_info['dimensions'],
            "generated_at": screenshot_info['generated_at']
        }
    
    def get_long_image_path(
        self, 
        doc_hash: str, 
        version: Optional[int] = None
    ) -> Optional[Path]:
        """
        获取已生成长图路径
        
        Args:
            doc_hash: 文档哈希
            version: 版本号（可选）
            
        Returns:
            长图路径（如果存在）或 None
        """
        try:
            visual_html_path, _ = self._locate_visual_html(doc_hash, version)
            image_path = self._get_image_output_path(visual_html_path)
            
            if image_path.exists():
                return image_path
            return None
            
        except FileNotFoundError:
            return None
    
    def _locate_visual_html(
        self, 
        doc_hash: str, 
        version: Optional[int] = None
    ) -> tuple[Path, Path]:
        """
        定位 Visual HTML 文件
        
        Args:
            doc_hash: 文档哈希
            version: 版本号（可选）
            
        Returns:
            (Visual HTML 路径, 对应文章路径)
            
        Raises:
            FileNotFoundError: 文件未找到
        """
        # 获取文章文件名
        if version is not None:
            # 指定版本
            versions = hash_to_versions.get(doc_hash, [])
            filename = None
            for v_filename in versions:
                if f"_v{version}.md" in v_filename or (version == 0 and "_v" not in v_filename):
                    filename = v_filename
                    break
            if not filename:
                raise FileNotFoundError(f"版本 {version} 未找到")
        else:
            # 默认版本
            filename = hash_to_filename.get(doc_hash)
            if not filename:
                raise FileNotFoundError(f"文章未找到: {doc_hash}")
        
        # 构建 Visual HTML 文件名
        base_name = Path(filename).stem
        visual_filename = f"{base_name}_visual.html"
        visual_path = self.output_dir / visual_filename
        
        if not visual_path.exists():
            raise FileNotFoundError(f"Visual Insight HTML 未生成: {visual_filename}")
        
        article_path = self.output_dir / filename
        
        return visual_path, article_path
    
    def _get_image_output_path(self, visual_html_path: Path) -> Path:
        """
        根据 Visual HTML 路径确定图片输出路径
        
        Args:
            visual_html_path: Visual HTML 文件路径
            
        Returns:
            图片输出路径
        """
        # 从 xxx_visual.html 提取基础名称
        base_name = visual_html_path.stem  # xxx_visual
        
        # 生成图片文件名：xxx_visual.png
        image_filename = f"{base_name}.png"
        
        return self.image_dir / image_filename
    
    def _read_metadata(self, article_path: Path) -> Dict:
        """
        读取文章 YAML front matter
        
        Args:
            article_path: 文章路径
            
        Returns:
            元数据字典
        """
        try:
            content = article_path.read_text(encoding="utf-8")
            
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1])
                    return metadata or {}
            
            return {}
            
        except Exception as e:
            logger.warning(f"读取元数据失败: {e}")
            return {}
    
    async def _update_metadata(
        self, 
        article_path: Path, 
        image_path: Path, 
        screenshot_info: Dict
    ) -> None:
        """
        更新文章元数据，记录长图信息
        
        Args:
            article_path: 文章路径
            image_path: 图片路径
            screenshot_info: 截图信息
        """
        try:
            content = article_path.read_text(encoding="utf-8")
            
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1]) or {}
                    article_body = parts[2]
                    
                    # 更新元数据
                    metadata["visual_long_image"] = {
                        "status": "completed",
                        "file": str(image_path.relative_to(self.output_dir)),
                        "generated_at": screenshot_info['generated_at'],
                        "dimensions": screenshot_info['dimensions'],
                        "file_size": screenshot_info['file_size']
                    }
                    
                    # 重新组装文件
                    new_content = f"---\n{yaml.dump(metadata, allow_unicode=True)}---{article_body}"
                    article_path.write_text(new_content, encoding="utf-8")
                    
                    logger.info(f"元数据已更新: {article_path}")
                else:
                    logger.warning("文章格式异常，无法更新元数据")
            else:
                logger.warning("文章缺少 YAML front matter，无法更新元数据")
                
        except Exception as e:
            logger.error(f"更新元数据失败: {e}", exc_info=True)
            # 不抛出异常，元数据更新失败不影响主流程


# 全局服务实例
_service_instance: Optional[VisualToImageService] = None


def get_visual_to_image_service() -> VisualToImageService:
    """获取服务单例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = VisualToImageService()
    return _service_instance
