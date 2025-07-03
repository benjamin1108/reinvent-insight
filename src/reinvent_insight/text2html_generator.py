"""
Text2HTML生成器模块

将markdown文章转换为符合品牌调性的精美HTML网页的核心生成器。
支持单文件生成、批量处理、增量更新等功能。
"""

import logging
import asyncio
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import re
import yaml

from . import config
from .summarizer import get_summarizer
from .api import clean_content_metadata
from .text2html_prompts import create_html_prompt, get_prompts_manager

logger = logging.getLogger(__name__)

class Text2HtmlConfig:
    """Text2HTML配置管理器"""
    
    DEFAULT_BRAND_CONFIG = {
        "name": "Reinvent Insight",
        "colors": {
            "primary": "#00BFFF",
            "highlight": "#39FF14", 
            "bg": "#121212",
            "surface": "#1E1E1E",
            "text": "#E0E0E0",
            "text_secondary": "#B0B0B0"
        },
        "fonts": {
            "main": "'Noto Sans SC', sans-serif",
            "base_size": "17px",
            "line_height": "1.8"
        },
        "layout": {
            "container_width": "960px",
            "section_padding": "4rem 0"
        }
    }
    
    def __init__(self, custom_config: Optional[Dict] = None):
        self.config = self.DEFAULT_BRAND_CONFIG.copy()
        if custom_config:
            self._merge_config(custom_config)
    
    def _merge_config(self, custom_config: Dict):
        """深度合并自定义配置"""
        for key, value in custom_config.items():
            if isinstance(value, dict) and key in self.config:
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点分割路径"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

class GenerationResult:
    """生成结果数据类"""
    
    def __init__(self, success: bool, input_file: Path, output_file: Optional[Path] = None, 
                 error_message: Optional[str] = None, metadata: Optional[Dict] = None):
        self.success = success
        self.input_file = input_file
        self.output_file = output_file
        self.error_message = error_message
        self.metadata = metadata or {}
        self.generated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "success": self.success,
            "input_file": str(self.input_file),
            "output_file": str(self.output_file) if self.output_file else None,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat()
        }

class Text2HtmlGenerator:
    """Text2HTML主生成器类"""
    
    def __init__(self, brand_config: Optional[Dict] = None, model_name: str = "Gemini", debug: bool = False):
        """
        初始化生成器
        
        Args:
            brand_config: 自定义品牌配置
            model_name: AI模型名称，默认使用Gemini
            debug: 是否启用调试模式，会保存提示词到文件
        """
        self.config = Text2HtmlConfig(brand_config)
        self.model_name = model_name
        self.summarizer = get_summarizer(model_name)
        self.debug = debug
        
        # 目录配置
        self.input_dir = config.OUTPUT_DIR  # downloads/summaries
        self.output_dir = config.PROJECT_ROOT / "downloads" / "insights"
        self.output_dir.mkdir(exist_ok=True)
        
        # 调试目录配置
        if self.debug:
            self.debug_dir = config.PROJECT_ROOT / "downloads" / "debug"
            self.debug_dir.mkdir(exist_ok=True)
        
        # 模板文件路径
        self.template_file = config.PROJECT_ROOT / "prompt" / "text2html.txt"
        self.template_content = self._load_template()
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
        
        logger.info(f"Text2HtmlGenerator初始化完成，模型: {model_name}，调试模式: {debug}")
    
    def _load_template(self) -> str:
        """加载text2html模板"""
        try:
            if self.template_file.exists():
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info("成功加载text2html模板")
                return content
            else:
                logger.warning(f"模板文件不存在: {self.template_file}")
                return ""
        except Exception as e:
            logger.error(f"加载模板文件失败: {e}")
            return ""
    
    def _extract_article_metadata(self, content: str) -> Tuple[str, Dict]:
        """
        提取文章元数据和清理内容
        
        Returns:
            Tuple[清理后的内容, 元数据字典]
        """
        metadata = {}
        
        # 提取YAML front matter
        if content.startswith('---'):
            try:
                match = re.match(r'^---\s*\n(.*?)\n\s*---\s*\n', content, re.DOTALL)
                if match:
                    yaml_content = match.group(1)
                    metadata = yaml.safe_load(yaml_content)
                    content = content[match.end():]
            except yaml.YAMLError as e:
                logger.warning(f"解析YAML front matter失败: {e}")
        
        # 使用现有的内容清理函数
        title = metadata.get('title', '')
        cleaned_content = clean_content_metadata(content, title)
        
        # 计算统计信息
        metadata.update({
            'word_count': len(cleaned_content),
            'char_count': len(cleaned_content),
            'estimated_reading_time': max(1, len(cleaned_content) // 500)  # 估算阅读时间（分钟）
        })
        
        return cleaned_content, metadata
    
    def _build_generation_prompt(self, content: str, metadata: Dict, template_name: str = None) -> str:
        """构建AI生成提示词"""
        # 使用新的提示词系统
        return create_html_prompt(
            content=content,
            metadata=metadata,
            brand_config=self.config.config,
            template_name=template_name
        )
    
    def _validate_html_output(self, html_content: str) -> bool:
        """验证HTML输出质量"""
        if not html_content or not isinstance(html_content, str):
            return False
        
        # 基础HTML结构检查
        required_elements = [
            '<!DOCTYPE html>',
            '<html',
            '</html>',
            '<head>',
            '</head>',
            '<body>',
            '</body>',
            '<style>',
            '</style>'
        ]
        
        for element in required_elements:
            if element not in html_content:
                logger.warning(f"HTML验证失败：缺少 {element}")
                return False
        
        # 品牌变量检查
        brand_variables = ['var(--primary-color)', 'var(--bg-color)', 'var(--text-color)']
        has_brand_vars = any(var in html_content for var in brand_variables)
        
        if not has_brand_vars:
            logger.warning("HTML验证失败：缺少品牌CSS变量")
            return False
        
        # 内容长度检查
        if len(html_content) < 1000:
            logger.warning("HTML验证失败：内容过短")
            return False
        
        return True
    
    def _inject_mobile_optimizations(self, html_content: str) -> str:
        """注入移动端优化CSS"""
        mobile_css = """
        
        /* 移动端优化 */
        @media (max-width: 768px) {
            .container { 
                max-width: 100%; 
                padding: 1rem; 
                margin: 0 auto;
            }
            h1 { font-size: 2rem !important; }
            h2 { font-size: 1.75rem !important; }
            h3 { font-size: 1.5rem !important; }
            .card { 
                padding: 1.5rem !important; 
                margin: 1rem 0 !important;
            }
            .data-highlight { 
                padding: 1rem !important;
                margin: 1rem 0 !important;
            }
            .analogy-box {
                padding: 1rem !important;
                margin: 1rem 0 !important;
            }
            blockquote {
                padding: 1rem !important;
                margin: 1rem 0 !important;
                font-size: 0.9rem !important;
            }
        }
        
        @media (max-width: 480px) {
            .container { padding: 0.75rem; }
            h1 { font-size: 1.75rem !important; }
            h2 { font-size: 1.5rem !important; }
            h3 { font-size: 1.25rem !important; }
            .card, .data-highlight, .analogy-box { 
                padding: 1rem !important;
                border-radius: 0.5rem !important;
            }
        }
        """
        
        # 在</style>标签前插入移动端CSS
        if '</style>' in html_content:
            html_content = html_content.replace('</style>', mobile_css + '\n</style>')
        
        return html_content
    
    def check_needs_update(self, md_file: Path, html_file: Path) -> bool:
        """检查是否需要重新生成"""
        if not html_file.exists():
            return True
        
        # 检查源文件是否更新
        md_mtime = md_file.stat().st_mtime
        html_mtime = html_file.stat().st_mtime
        
        if md_mtime > html_mtime:
            logger.info(f"源文件已更新: {md_file.name}")
            return True
        
        # 检查模板是否更新
        if self.template_file.exists():
            template_mtime = self.template_file.stat().st_mtime
            if template_mtime > html_mtime:
                logger.info(f"模板文件已更新，需要重新生成: {md_file.name}")
                return True
        
        return False
    
    def _save_metadata(self, html_file: Path, metadata: Dict, generation_time: float):
        """保存生成元数据"""
        metadata_file = html_file.with_suffix('.json')
        
        full_metadata = {
            **metadata,
            "generated_at": datetime.now().isoformat(),
            "generation_time_seconds": round(generation_time, 2),
            "ai_model": self.model_name,
            "template_version": "1.0",
            "brand_config": self.config.config
        }
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(full_metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"元数据已保存: {metadata_file}")
        except Exception as e:
            logger.warning(f"保存元数据失败: {e}")
    
    async def generate_single(self, md_file: Path, force_regenerate: bool = False) -> GenerationResult:
        """
        生成单个文章的HTML版本
        
        Args:
            md_file: markdown文件路径
            force_regenerate: 是否强制重新生成
            
        Returns:
            GenerationResult: 生成结果
        """
        start_time = datetime.now()
        self.stats["total_processed"] += 1
        
        try:
            # 验证输入文件
            if not md_file.exists():
                raise FileNotFoundError(f"文件不存在: {md_file}")
            
            if not md_file.suffix.lower() == '.md':
                raise ValueError(f"不是markdown文件: {md_file}")
            
            # 确定输出文件路径
            html_file = self.output_dir / (md_file.stem + '.html')
            
            # 检查是否需要更新
            if not force_regenerate and not self.check_needs_update(md_file, html_file):
                logger.info(f"文件无需更新，跳过: {md_file.name}")
                self.stats["skipped"] += 1
                return GenerationResult(
                    success=True,
                    input_file=md_file,
                    output_file=html_file,
                    metadata={"skipped": True, "reason": "文件未变更"}
                )
            
            # 读取markdown内容
            with open(md_file, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # 提取元数据和清理内容
            cleaned_content, metadata = self._extract_article_metadata(raw_content)
            
            if not cleaned_content.strip():
                raise ValueError("文章内容为空")
            
            # 自动选择最合适的模板
            prompts_mgr = get_prompts_manager()
            template_name = prompts_mgr.auto_select_template(cleaned_content, metadata)
            logger.info(f"自动选择模板: {template_name} (字数: {metadata.get('word_count', 0)})")
            
            # 构建AI提示词
            prompt = self._build_generation_prompt(cleaned_content, metadata, template_name)
            
            # 调用AI生成HTML
            logger.info(f"开始生成HTML: {md_file.name}")
            debug_filename = md_file.stem if self.debug else None
            html_content = await self._generate_with_retry(prompt, max_retries=3, debug_filename=debug_filename)
            
            if not html_content:
                raise Exception("AI生成返回空内容")
            
            # 验证HTML质量
            if not self._validate_html_output(html_content):
                raise Exception("生成的HTML未通过质量验证")
            
            # 注入移动端优化
            html_content = self._inject_mobile_optimizations(html_content)
            
            # 保存HTML文件
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 计算生成时间
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # 保存元数据
            self._save_metadata(html_file, metadata, generation_time)
            
            logger.info(f"✅ 生成成功: {html_file.name} (耗时: {generation_time:.1f}s)")
            self.stats["successful"] += 1
            
            return GenerationResult(
                success=True,
                input_file=md_file,
                output_file=html_file,
                metadata={
                    **metadata,
                    "generation_time": generation_time,
                    "file_size": html_file.stat().st_size
                }
            )
            
        except Exception as e:
            error_msg = f"生成失败: {str(e)}"
            logger.error(f"❌ {md_file.name}: {error_msg}")
            self.stats["failed"] += 1
            
            return GenerationResult(
                success=False,
                input_file=md_file,
                error_message=error_msg
            )
    
    async def _generate_with_retry(self, prompt: str, max_retries: int = 3, debug_filename: str = None) -> Optional[str]:
        """带重试机制的AI生成"""
        # 如果启用调试模式，保存提示词到文件
        if self.debug and debug_filename:
            debug_file = self.debug_dir / f"{debug_filename}_prompt.txt"
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== 调试信息 ===\n")
                    f.write(f"时间: {datetime.now().isoformat()}\n")
                    f.write(f"模型: {self.model_name}\n")
                    f.write(f"提示词长度: {len(prompt)} 字符\n")
                    f.write(f"提示词MD5: {hashlib.md5(prompt.encode()).hexdigest()}\n")
                    f.write(f"\n{'='*50}\n")
                    f.write(f"=== 完整提示词 ===\n")
                    f.write(f"{'='*50}\n\n")
                    f.write(prompt)
                    f.write(f"\n\n{'='*50}\n")
                    f.write(f"=== 提示词结束 ===\n")
                    f.write(f"{'='*50}\n")
                logger.info(f"🔍 调试提示词已保存到: {debug_file}")
                print(f"🔍 调试提示词已保存到: {debug_file}")
            except Exception as e:
                logger.warning(f"保存调试提示词失败: {e}")
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.summarizer.generate_content(prompt)
                
                # 如果启用调试模式，保存AI返回的原始内容
                if self.debug and debug_filename and result:
                    response_file = self.debug_dir / f"{debug_filename}_response_{attempt + 1}.html"
                    try:
                        with open(response_file, 'w', encoding='utf-8') as f:
                            f.write(f"<!-- 调试信息 -->\n")
                            f.write(f"<!-- 时间: {datetime.now().isoformat()} -->\n")
                            f.write(f"<!-- 第{attempt + 1}次尝试 -->\n")
                            f.write(f"<!-- 内容长度: {len(result)} 字符 -->\n")
                            f.write(f"<!-- 内容MD5: {hashlib.md5(result.encode()).hexdigest()} -->\n")
                            f.write(f"<!-- ============================================ -->\n\n")
                            f.write(result)
                        logger.info(f"🔍 AI返回内容已保存到: {response_file}")
                    except Exception as e:
                        logger.warning(f"保存AI返回内容失败: {e}")
                
                if result and self._validate_html_output(result):
                    if self.debug and debug_filename:
                        logger.info(f"✅ 第{attempt + 1}次生成成功并通过验证")
                    return result
                
                if attempt < max_retries:
                    logger.warning(f"第{attempt + 1}次生成质量不符合要求，正在重试...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"第{attempt + 1}次生成失败: {e}，正在重试...")
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"生成失败，已达最大重试次数: {e}")
                    raise e
        
        return None
    
    async def generate_batch(self, file_patterns: List[str] = None, 
                           max_concurrent: int = 3, force_regenerate: bool = False) -> List[GenerationResult]:
        """
        批量生成多个文章的HTML版本
        
        Args:
            file_patterns: 文件模式列表，默认处理所有.md文件
            max_concurrent: 最大并发数
            force_regenerate: 是否强制重新生成
            
        Returns:
            List[GenerationResult]: 生成结果列表
        """
        # 查找待处理文件
        if not file_patterns:
            md_files = list(self.input_dir.glob("*.md"))
        else:
            md_files = []
            for pattern in file_patterns:
                md_files.extend(self.input_dir.glob(pattern))
        
        if not md_files:
            logger.warning("未找到待处理的markdown文件")
            return []
        
        logger.info(f"开始批量处理 {len(md_files)} 个文件，最大并发数: {max_concurrent}")
        
        # 并发控制
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(md_file: Path) -> GenerationResult:
            async with semaphore:
                return await self.generate_single(md_file, force_regenerate)
        
        # 执行批量处理
        tasks = [process_with_semaphore(f) for f in md_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(GenerationResult(
                    success=False,
                    input_file=md_files[i],
                    error_message=f"处理异常: {str(result)}"
                ))
            else:
                final_results.append(result)
        
        # 输出统计信息
        self._print_batch_summary(final_results)
        
        return final_results
    
    def _print_batch_summary(self, results: List[GenerationResult]):
        """打印批量处理统计信息"""
        successful = sum(1 for r in results if r.success and not r.metadata.get('skipped'))
        failed = sum(1 for r in results if not r.success)
        skipped = sum(1 for r in results if r.success and r.metadata.get('skipped'))
        
        logger.info("=" * 50)
        logger.info("批量处理完成统计:")
        logger.info(f"  总计: {len(results)} 个文件")
        logger.info(f"  成功: {successful} 个")
        logger.info(f"  失败: {failed} 个")
        logger.info(f"  跳过: {skipped} 个")
        logger.info("=" * 50)
        
        # 显示失败的文件
        if failed > 0:
            logger.info("失败的文件:")
            for result in results:
                if not result.success:
                    logger.info(f"  ❌ {result.input_file.name}: {result.error_message}")
    
    def get_stats(self) -> Dict:
        """获取生成器统计信息"""
        return {
            **self.stats,
            "output_directory": str(self.output_dir),
            "template_loaded": bool(self.template_content),
            "ai_model": self.model_name,
            "brand_name": self.config.get('name')
        } 