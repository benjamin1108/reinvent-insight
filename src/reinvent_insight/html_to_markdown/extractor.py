"""
LLM内容提取器

使用大语言模型智能提取HTML中的核心内容。
"""

import json
import logging
from pathlib import Path
from typing import Optional, List

from bs4 import BeautifulSoup

from ..model_config import BaseModelClient
from .models import ExtractedContent, ImageInfo
from .exceptions import LLMProcessingError, ContentExtractionError

logger = logging.getLogger(__name__)


class LLMContentExtractor:
    """LLM内容提取器
    
    使用大语言模型智能提取HTML中的：
    - 文章标题
    - 正文内容
    - 相关图片
    - 元数据（作者、日期等）
    
    同时过滤掉广告、导航等无关内容。
    
    使用示例:
        >>> from reinvent_insight.model_config import get_model_client
        >>> client = get_model_client("html_to_markdown")
        >>> extractor = LLMContentExtractor(client)
        >>> content = await extractor.extract(html, base_url="https://example.com")
    """
    
    def __init__(self, model_client: BaseModelClient):
        """初始化提取器
        
        Args:
            model_client: 模型客户端（来自统一配置系统）
        """
        self.model_client = model_client
        self.prompt_template = self._load_prompt_template()
        self.debug_dir = None  # 调试目录
        self.output_stem = None  # 输出文件名（不含扩展名）
        logger.info("LLMContentExtractor initialized")
    
    def _load_prompt_template(self) -> str:
        """加载提示词模板
        
        Returns:
            提示词模板字符串
        """
        # 获取项目根目录
        from .. import config as app_config
        prompt_path = app_config.PROJECT_ROOT / "prompt" / "html_to_markdown.txt"
        
        if not prompt_path.exists():
            logger.error(f"Prompt template not found: {prompt_path}")
            raise LLMProcessingError(f"Prompt template not found: {prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        logger.info(f"Loaded prompt template from {prompt_path}")
        return template
    
    async def extract(
        self, 
        html: str,
        base_url: Optional[str] = None
    ) -> ExtractedContent:
        """从HTML中提取内容
        
        Args:
            html: 预处理后的HTML
            base_url: 网页的基础URL（用于图片路径转换）
            
        Returns:
            提取的内容对象
            
        Raises:
            LLMProcessingError: LLM处理失败
            ContentExtractionError: 内容提取失败
        """
        logger.info("Starting content extraction with LLM")
        
        # 检查HTML长度，决定是否需要分段处理
        # 目标：每段约5000汉字的内容
        # 20000字符的HTML ≈ 5000汉字的内容（考虑HTML标签开销）
        max_chunk_size = 20000  # 每段最大20KB
        
        if len(html) <= max_chunk_size:
            # 单次处理
            logger.info(f"HTML size ({len(html)} chars) within limit, processing in single pass")
            return await self._extract_single(html, base_url)
        else:
            # 分段处理
            logger.info(f"HTML size ({len(html)} chars) exceeds limit, using chunked processing")
            return await self._extract_chunked(html, base_url, max_chunk_size)
    
    async def _extract_single(
        self,
        html: str,
        base_url: Optional[str] = None
    ) -> ExtractedContent:
        """单次提取（不分段）
        
        Args:
            html: HTML内容
            base_url: 基础URL
            
        Returns:
            提取的内容对象
        """
        # 构建提示词
        prompt = self._build_prompt(html)
        
        try:
            # 调用LLM API（使用JSON模式和低思考级别以提高速度）
            logger.info("Calling LLM API with low thinking level...")
            response = await self.model_client.generate_content(
                prompt=prompt,
                is_json=True,
                thinking_level="low"
            )
            
            logger.info("LLM API call successful")
            
            # 解析响应
            content = self._parse_llm_response(response)
            
            # 验证提取的内容
            self._validate_content(content)
            
            logger.info(f"Content extraction completed: title='{content.title}', "
                       f"images={len(content.images)}")
            
            return content
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {response[:500]}...")
            raise LLMProcessingError(f"LLM returned invalid JSON: {e}") from e
        
        except Exception as e:
            logger.error(f"Content extraction failed: {e}", exc_info=True)
            raise LLMProcessingError(f"Content extraction failed: {e}") from e
    
    async def _extract_chunked(
        self,
        html: str,
        base_url: Optional[str] = None,
        max_chunk_size: int = 150000
    ) -> ExtractedContent:
        """分段提取并合并
        
        Args:
            html: HTML内容
            base_url: 基础URL
            max_chunk_size: 每段最大大小
            
        Returns:
            合并后的内容对象
        """
        from bs4 import BeautifulSoup
        
        # 解析HTML
        soup = BeautifulSoup(html, 'lxml')
        
        # 提取所有段落级元素
        chunks = self._split_html_semantically(soup, max_chunk_size)
        
        logger.info(f"Split HTML into {len(chunks)} chunks")
        
        # 处理每个分段
        all_contents = []
        all_images = []
        title = ""
        metadata = {}
        
        for i, chunk_html in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk_html)} chars)")
            
            # 如果启用调试模式，保存分段HTML
            if self.debug_dir and self.output_stem:
                chunk_html_path = self.debug_dir / f"{self.output_stem}_chunk_{i+1:02d}_html.html"
                with open(chunk_html_path, 'w', encoding='utf-8') as f:
                    f.write(chunk_html)
                logger.info(f"Debug: Saved chunk {i+1} HTML to {chunk_html_path}")
            
            try:
                # 为分段创建特殊提示词
                chunk_prompt = self._build_chunk_prompt(chunk_html, i, len(chunks))
                
                # 使用低思考级别以提高翻译速度
                response = await self.model_client.generate_content(
                    prompt=chunk_prompt,
                    is_json=True,
                    thinking_level="low"
                )
                
                chunk_content = self._parse_llm_response(response)
                
                # 如果启用调试模式，保存分段提取结果
                if self.debug_dir and self.output_stem:
                    chunk_json_path = self.debug_dir / f"{self.output_stem}_chunk_{i+1:02d}_extracted.json"
                    with open(chunk_json_path, 'w', encoding='utf-8') as f:
                        json.dump(chunk_content.to_dict(), f, ensure_ascii=False, indent=2)
                    logger.info(f"Debug: Saved chunk {i+1} extraction to {chunk_json_path}")
                    
                    # 保存分段的Markdown
                    chunk_md_path = self.debug_dir / f"{self.output_stem}_chunk_{i+1:02d}_content.md"
                    with open(chunk_md_path, 'w', encoding='utf-8') as f:
                        f.write(f"# Chunk {i+1}/{len(chunks)}\n\n")
                        if i == 0 and chunk_content.title:
                            f.write(f"## Title: {chunk_content.title}\n\n")
                        f.write(chunk_content.content)
                    logger.info(f"Debug: Saved chunk {i+1} markdown to {chunk_md_path}")
                
                # 第一段提取标题和元数据
                if i == 0:
                    title = chunk_content.title
                    metadata = chunk_content.metadata
                
                # 收集内容和图片
                all_contents.append(chunk_content.content)
                all_images.extend(chunk_content.images)
                
                logger.info(f"Chunk {i+1} processed: {len(chunk_content.content)} chars, "
                           f"{len(chunk_content.images)} images")
                
            except Exception as e:
                logger.error(f"Failed to process chunk {i+1}: {e}")
                # 继续处理其他分段
                continue
        
        # 合并所有内容
        merged_content = self._merge_contents(all_contents)
        
        # 如果启用调试模式，保存合并后的内容
        if self.debug_dir and self.output_stem:
            merged_md_path = self.debug_dir / f"{self.output_stem}_merged_content.md"
            with open(merged_md_path, 'w', encoding='utf-8') as f:
                f.write(f"# Merged Content from {len(chunks)} chunks\n\n")
                f.write(merged_content)
            logger.info(f"Debug: Saved merged content to {merged_md_path}")
        
        # 去重图片
        unique_images = self._deduplicate_images(all_images)
        
        # 创建最终的ExtractedContent对象
        final_content = ExtractedContent(
            title=title,
            content=merged_content,
            images=unique_images,
            metadata=metadata
        )
        
        logger.info(f"Chunked extraction completed: {len(merged_content)} chars total, "
                   f"{len(unique_images)} unique images")
        
        return final_content
    
    def _split_html_semantically(
        self,
        soup: 'BeautifulSoup',
        max_size: int
    ) -> List[str]:
        """按语义分割HTML
        
        Args:
            soup: BeautifulSoup对象
            max_size: 每段最大大小
            
        Returns:
            HTML分段列表
        """
        chunks = []
        current_chunk = []
        current_size = 0
        overlap_size = 1000  # 重叠1KB用于上下文（约200-300汉字）
        
        # 获取body中的所有顶级元素
        body = soup.find('body')
        if not body:
            return [str(soup)]
        
        # 获取所有段落级元素（p, h1-h6, ul, ol, blockquote等）
        elements = body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                                  'ul', 'ol', 'blockquote', 'pre', 'img', 
                                  'table', 'div'], recursive=False)
        
        # 如果没有找到段落级元素，尝试递归查找
        if not elements:
            elements = body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        if not elements:
            # 如果还是没有，返回整个body
            return [str(body)]
        
        logger.info(f"Found {len(elements)} elements to split")
        
        for i, elem in enumerate(elements):
            elem_str = str(elem)
            elem_size = len(elem_str)
            
            # 如果单个元素就超过限制，需要进一步分割
            if elem_size > max_size:
                logger.warning(f"Element {i} is too large ({elem_size} chars), will be split")
                
                # 保存当前chunk
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # 对大元素进行文本级分割
                sub_chunks = self._split_large_element(elem_str, max_size)
                chunks.extend(sub_chunks)
                continue
            
            # 如果加上当前元素会超过限制
            if current_size + elem_size > max_size and current_chunk:
                # 保存当前分段
                chunk_content = ''.join(current_chunk)
                chunks.append(chunk_content)
                logger.debug(f"Created chunk {len(chunks)} with {len(chunk_content)} chars")
                
                # 开始新分段，包含重叠内容（最后几个元素）
                overlap_elements = []
                overlap_len = 0
                for prev_elem in reversed(current_chunk[-5:]):  # 最多保留最后5个元素
                    if overlap_len + len(prev_elem) < overlap_size:
                        overlap_elements.insert(0, prev_elem)
                        overlap_len += len(prev_elem)
                    else:
                        break
                
                current_chunk = overlap_elements
                current_size = overlap_len
            
            current_chunk.append(elem_str)
            current_size += elem_size
        
        # 添加最后一段
        if current_chunk:
            chunk_content = ''.join(current_chunk)
            chunks.append(chunk_content)
            logger.debug(f"Created final chunk {len(chunks)} with {len(chunk_content)} chars")
        
        return chunks
    
    def _split_large_element(self, elem_str: str, max_size: int) -> List[str]:
        """分割过大的单个元素
        
        Args:
            elem_str: 元素字符串
            max_size: 最大大小
            
        Returns:
            分割后的字符串列表
        """
        # 简单按字符数分割，保留一些重叠
        chunks = []
        overlap = 500  # 减小重叠大小
        start = 0
        
        while start < len(elem_str):
            end = start + max_size
            chunk = elem_str[start:end]
            chunks.append(chunk)
            start = end - overlap  # 重叠部分
        
        return chunks
    
    def _build_chunk_prompt(self, html: str, chunk_index: int, total_chunks: int) -> str:
        """为分段构建提示词
        
        Args:
            html: HTML分段
            chunk_index: 当前分段索引
            total_chunks: 总分段数
            
        Returns:
            提示词
        """
        if chunk_index == 0:
            # 第一段：提取标题、元数据和内容
            prefix = f"这是文章的第 {chunk_index + 1}/{total_chunks} 部分（开头部分）。请提取标题、元数据和这部分的完整内容。\n\n"
        elif chunk_index == total_chunks - 1:
            # 最后一段：只提取内容
            prefix = f"这是文章的第 {chunk_index + 1}/{total_chunks} 部分（结尾部分）。请提取这部分的完整内容。标题和元数据可以留空。\n\n"
        else:
            # 中间段：只提取内容
            prefix = f"这是文章的第 {chunk_index + 1}/{total_chunks} 部分（中间部分）。请提取这部分的完整内容。标题和元数据可以留空。\n\n"
        
        return prefix + self.prompt_template.replace("{html}", html)
    
    def _merge_contents(self, contents: List[str]) -> str:
        """合并多个内容段，去除重复
        
        Args:
            contents: 内容列表
            
        Returns:
            合并后的内容
        """
        if not contents:
            return ""
        
        if len(contents) == 1:
            return contents[0]
        
        merged = contents[0]
        
        for i in range(1, len(contents)):
            next_content = contents[i]
            
            # 查找重叠部分（最后几段和开头几段）
            merged_lines = merged.split('\n')
            next_lines = next_content.split('\n')
            
            # 尝试找到重叠的行
            overlap_found = False
            for overlap_len in range(min(20, len(merged_lines), len(next_lines)), 0, -1):
                merged_tail = '\n'.join(merged_lines[-overlap_len:])
                next_head = '\n'.join(next_lines[:overlap_len])
                
                # 使用模糊匹配（允许轻微差异）
                if self._similar_text(merged_tail, next_head, threshold=0.8):
                    # 找到重叠，跳过重复部分
                    merged += '\n' + '\n'.join(next_lines[overlap_len:])
                    overlap_found = True
                    logger.debug(f"Found overlap of {overlap_len} lines between chunks")
                    break
            
            if not overlap_found:
                # 没找到重叠，直接拼接
                merged += '\n\n' + next_content
        
        return merged
    
    def _similar_text(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """判断两段文本是否相似
        
        Args:
            text1: 文本1
            text2: 文本2
            threshold: 相似度阈值
            
        Returns:
            是否相似
        """
        # 简单的相似度计算：基于字符匹配
        if not text1 or not text2:
            return False
        
        # 移除空白字符后比较
        clean1 = ''.join(text1.split())
        clean2 = ''.join(text2.split())
        
        if not clean1 or not clean2:
            return False
        
        # 计算最长公共子序列长度
        shorter = min(len(clean1), len(clean2))
        longer = max(len(clean1), len(clean2))
        
        if shorter == 0:
            return False
        
        # 简单匹配：如果较短文本的大部分出现在较长文本中
        if clean1 in clean2 or clean2 in clean1:
            return True
        
        # 计算相似度
        common = sum(1 for c1, c2 in zip(clean1, clean2) if c1 == c2)
        similarity = common / shorter
        
        return similarity >= threshold
    
    def _deduplicate_images(self, images: List[ImageInfo]) -> List[ImageInfo]:
        """去除重复的图片
        
        Args:
            images: 图片列表
            
        Returns:
            去重后的图片列表
        """
        seen_urls = set()
        unique_images = []
        
        for img in images:
            if img.url not in seen_urls:
                seen_urls.add(img.url)
                unique_images.append(img)
        
        return unique_images
    
    def _build_prompt(self, html: str) -> str:
        """构建LLM提示词
        
        Args:
            html: HTML内容
            
        Returns:
            完整的提示词
        """
        # 限制HTML长度以避免超出token限制
        max_html_length = 2000000  # 约200KB，预处理后的HTML应该很简洁
        if len(html) > max_html_length:
            logger.warning(f"HTML too long ({len(html)} chars), truncating to {max_html_length}")
            html = html[:max_html_length] + "\n... (truncated)"
        
        # 替换模板中的占位符
        prompt = self.prompt_template.replace("{html}", html)
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> ExtractedContent:
        """解析LLM返回的JSON响应
        
        Args:
            response: LLM返回的JSON字符串
            
        Returns:
            ExtractedContent对象
            
        Raises:
            json.JSONDecodeError: JSON解析失败
        """
        # 解析JSON
        data = json.loads(response)
        
        # 提取字段
        title = data.get("title", "")
        content = data.get("content", "")
        images_data = data.get("images", [])
        metadata = data.get("metadata", {})
        
        # 创建ImageInfo对象列表
        images = []
        for i, img_data in enumerate(images_data):
            try:
                image = ImageInfo(
                    url=img_data.get("url", ""),
                    alt=img_data.get("alt", ""),
                    caption=img_data.get("caption"),
                    position=i
                )
                images.append(image)
            except Exception as e:
                logger.warning(f"Failed to parse image data: {img_data}, error: {e}")
                continue
        
        # 创建ExtractedContent对象
        extracted_content = ExtractedContent(
            title=title,
            content=content,
            images=images,
            metadata=metadata
        )
        
        return extracted_content
    
    def _validate_content(self, content: ExtractedContent) -> None:
        """验证提取的内容
        
        Args:
            content: 提取的内容对象
            
        Raises:
            ContentExtractionError: 内容无效
        """
        # 检查标题
        if not content.title or not content.title.strip():
            logger.warning("Extracted title is empty")
            # 不抛出异常，因为有些页面可能没有明确的标题
        
        # 检查正文
        if not content.content or not content.content.strip():
            logger.error("Extracted content is empty")
            raise ContentExtractionError(
                "Failed to extract content from HTML. "
                "The page may not contain article content, or it may be behind a paywall/login."
            )
        
        # 检查正文长度
        if len(content.content.strip()) < 50:
            logger.warning(f"Extracted content is very short: {len(content.content)} chars")
            raise ContentExtractionError(
                f"Extracted content is too short ({len(content.content)} chars). "
                "The page may not contain substantial article content."
            )
        
        logger.debug("Content validation passed")
