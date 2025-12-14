"""
HTML到Markdown转换器主接口

提供统一的转换接口，协调各组件完成HTML到Markdown的转换。
"""

import logging
from pathlib import Path
from typing import Union, Optional

from reinvent_insight.infrastructure.ai.model_config import get_model_client
from .preprocessor import HTMLPreprocessor
from .extractor import LLMContentExtractor
from .url_processor import URLProcessor
from .generator import MarkdownGenerator
from .models import ConversionResult
from .exceptions import HTMLToMarkdownError

logger = logging.getLogger(__name__)


class HTMLToMarkdownConverter:
    """HTML到Markdown转换器（主接口）
    
    协调各组件完成HTML到Markdown的转换流程。
    
    使用示例:
        >>> converter = HTMLToMarkdownConverter()
        >>> markdown = await converter.convert_from_file("article.html")
    """
    
    def __init__(self, task_type: str = "html_to_markdown", debug: bool = False):
        """初始化转换器
        
        Args:
            task_type: 任务类型（用于获取模型配置）
            debug: 是否启用调试模式（保存中间文件）
        """
        self.task_type = task_type
        self.debug = debug
        
        # 初始化各组件
        logger.info(f"Initializing HTMLToMarkdownConverter with task_type={task_type}, debug={debug}")
        
        self.preprocessor = HTMLPreprocessor()
        self.model_client = get_model_client(task_type)
        self.extractor = LLMContentExtractor(self.model_client)
        self.url_processor = None  # 将在转换时根据base_url初始化
        self.generator = MarkdownGenerator()
        
        logger.info("HTMLToMarkdownConverter initialized successfully")
    
    async def convert_from_file(
        self,
        html_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        base_url: Optional[str] = None
    ) -> ConversionResult:
        """从HTML文件转换为Markdown
        
        Args:
            html_path: HTML文件路径
            output_path: 输出Markdown文件路径（可选）
            base_url: 网页的基础URL（用于图片路径转换）
            
        Returns:
            ConversionResult对象
            
        Raises:
            HTMLToMarkdownError: 转换失败
        """
        logger.info(f"Converting from file: {html_path}")
        
        # 读取HTML文件
        html_path = Path(html_path)
        if not html_path.exists():
            raise HTMLToMarkdownError(f"HTML file not found: {html_path}")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # 转换
        result = await self.convert_from_string(html, output_path, base_url)
        
        logger.info(f"Conversion from file completed: {html_path}")
        return result
    
    async def convert_from_url(
        self,
        url: str,
        output_path: Optional[Union[str, Path]] = None
    ) -> ConversionResult:
        """从URL获取HTML并转换为Markdown
        
        Args:
            url: 网页URL
            output_path: 输出Markdown文件路径（可选）
            
        Returns:
            ConversionResult对象
            
        Raises:
            HTMLToMarkdownError: 转换失败
        """
        logger.info(f"Converting from URL: {url}")
        
        try:
            import httpx
        except ImportError:
            raise HTMLToMarkdownError(
                "httpx is required for URL fetching. Install it with: pip install httpx"
            )
        
        # 获取HTML
        try:
            logger.info("正在获取网页...")
            # 增加超时时间，SemiAnalysis网页较大
            timeout_config = httpx.Timeout(60.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout_config, follow_redirects=True) as client:
                logger.debug("发送HTTP请求...")
                response = await client.get(url)
                response.raise_for_status()
                html = response.text
                html_size_mb = len(html) / (1024 * 1024)
                logger.info(f"获取成功，HTML大小: {html_size_mb:.2f} MB ({len(html):,} 字符)")
        except Exception as e:
            logger.error(f"获取失败: {e}")
            raise HTMLToMarkdownError(f"Failed to fetch URL: {e}") from e
        
        # 使用URL作为base_url
        result = await self.convert_from_string(html, output_path, base_url=url)
        
        logger.info(f"Conversion from URL completed: {url}")
        return result
    
    async def convert_from_string(
        self,
        html: str,
        output_path: Optional[Union[str, Path]] = None,
        base_url: Optional[str] = None
    ) -> ConversionResult:
        """从HTML字符串转换为Markdown
        
        Args:
            html: HTML字符串
            output_path: 输出Markdown文件路径（可选）
            base_url: 网页的基础URL（用于图片路径转换）
            
        Returns:
            ConversionResult对象
            
        Raises:
            HTMLToMarkdownError: 转换失败
        """
        logger.info("Converting from HTML string")
        logger.info(f"HTML length: {len(html)} chars, base_url: {base_url}")
        
        try:
            # 如果启用调试模式，保存原始HTML
            if self.debug and output_path:
                debug_dir = Path(output_path).parent / "debug"
                debug_dir.mkdir(exist_ok=True)
                
                original_html_path = debug_dir / f"{Path(output_path).stem}_01_original.html"
                with open(original_html_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info(f"Debug: Saved original HTML to {original_html_path}")
            
            # 步骤1: 预处理HTML
            logger.info("步骤1: 预处理HTML（去除JS/CSS/广告等）...")
            cleaned_html = self.preprocessor.preprocess(html)
            cleaned_size_mb = len(cleaned_html) / (1024 * 1024)
            reduction = (1 - len(cleaned_html) / len(html)) * 100
            logger.info(f"预处理完成: {cleaned_size_mb:.2f} MB ({len(cleaned_html):,} 字符)，压缩率: {reduction:.1f}%")
            
            # 如果启用调试模式，保存预处理后的HTML
            if self.debug and output_path:
                cleaned_html_path = debug_dir / f"{Path(output_path).stem}_02_cleaned.html"
                with open(cleaned_html_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_html)
                logger.info(f"Debug: Saved cleaned HTML to {cleaned_html_path}")
            
            # 步骤2: LLM提取内容
            logger.info("步骤2: 使用 Gemini 提取正文内容...")
            
            # 如果启用调试模式，传递调试目录给extractor
            if self.debug and output_path:
                self.extractor.debug_dir = debug_dir
                self.extractor.output_stem = Path(output_path).stem
            
            extracted_content = await self.extractor.extract(cleaned_html, base_url)
            logger.info(f"Content extracted: title='{extracted_content.title}', "
                       f"content_length={len(extracted_content.content)}, "
                       f"images={len(extracted_content.images)}")
            
            # 如果启用调试模式，保存提取的内容（JSON格式）
            if self.debug and output_path:
                import json
                extracted_json_path = debug_dir / f"{Path(output_path).stem}_03_extracted.json"
                with open(extracted_json_path, 'w', encoding='utf-8') as f:
                    json.dump(extracted_content.to_dict(), f, ensure_ascii=False, indent=2)
                logger.info(f"Debug: Saved extracted content to {extracted_json_path}")
            
            # 步骤3: 处理图片URL
            if base_url and extracted_content.images:
                logger.info("Step 3: Processing image URLs...")
                url_processor = URLProcessor(base_url)
                
                for image in extracted_content.images:
                    try:
                        original_url = image.url
                        processed_url = url_processor.process_image_url(original_url)
                        image.url = processed_url
                        
                        if original_url != processed_url:
                            logger.debug(f"URL processed: {original_url} -> {processed_url}")
                    except Exception as e:
                        logger.warning(f"Failed to process image URL {image.url}: {e}")
                        # 继续处理其他图片
                
                logger.info(f"Processed {len(extracted_content.images)} image URLs")
            else:
                logger.info("Step 3: Skipping URL processing (no base_url or no images)")
            
            # 步骤4: 生成Markdown
            logger.info("Step 4: Generating Markdown...")
            output_path_obj = Path(output_path) if output_path else None
            result = self.generator.generate(extracted_content, output_path_obj)
            logger.info(f"Markdown generated: {len(result.markdown)} chars")
            
            logger.info("Conversion completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}", exc_info=True)
            raise
