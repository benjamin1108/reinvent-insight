"""
可视化解读生成工作器

该模块负责将深度解读文章转换为高度可视化的 HTML 网页。
使用 text2html.txt 中定义的提示词指导 AI 生成符合设计规范的可视化内容。
"""

import os
import re
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger

from . import config
from .summarizer import get_summarizer
from .task_manager import manager as task_manager

logger = logger.bind(name=__name__)


class VisualInterpretationWorker:
    """可视化解读生成工作器"""
    
    def __init__(self, task_id: str, article_path: str, model_name: str, version: int = 0):
        """
        初始化可视化解读工作器
        
        Args:
            task_id: 任务ID（用于进度推送）
            article_path: 深度解读文章的文件路径
            model_name: AI模型名称（复用现有配置）
            version: 文章版本号（默认0表示无版本）
        """
        self.task_id = task_id
        self.article_path = Path(article_path)
        self.model_name = model_name
        self.version = version
        self.summarizer = get_summarizer(model_name)
        self.text2html_prompt = self._load_text2html_prompt()
        self.max_retries = 3
        
        logger.info(f"初始化可视化工作器 - 任务: {task_id}, 文章: {article_path}, 版本: {version}")
    
    def _load_text2html_prompt(self) -> str:
        """
        加载 text2html.txt 提示词
        
        Returns:
            提示词内容
            
        Raises:
            FileNotFoundError: 如果提示词文件不存在
        """
        prompt_path = Path("./prompt/text2html.txt")
        
        if not prompt_path.exists():
            logger.error(f"text2html 提示词文件未找到: {prompt_path}")
            raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")
        
        try:
            content = prompt_path.read_text(encoding="utf-8")
            logger.info(f"成功加载 text2html 提示词，长度: {len(content)} 字符")
            return content
        except Exception as e:
            logger.error(f"读取 text2html 提示词失败: {e}")
            raise
    
    async def run(self) -> Optional[str]:
        """
        执行可视化解读生成
        
        Returns:
            生成的 HTML 文件路径，失败返回 None
        """
        try:
            logger.info(f"开始生成可视化解读 - 任务: {self.task_id}")
            await self._log("正在生成可视化解读...", progress=10)
            
            # 1. 读取深度解读内容
            article_content = await self._read_article_content()
            await self._log("已读取文章内容", progress=20)
            
            # 2. 构建完整提示词
            full_prompt = self._build_prompt(article_content)
            await self._log("已构建提示词", progress=30)
            
            # 3. 调用 AI 生成 HTML
            html_content = await self._generate_html(full_prompt)
            await self._log("AI 生成完成", progress=60)
            
            # 4. 清理 HTML 内容
            html_content = self._clean_html(html_content)
            await self._log("HTML 清理完成", progress=70)
            
            # 5. 验证 HTML 格式
            if not self._validate_html(html_content):
                raise ValueError("生成的 HTML 格式无效")
            await self._log("HTML 验证通过", progress=80)
            
            # 5. 保存 HTML 文件
            html_path = await self._save_html(html_content)
            await self._log("HTML 文件已保存", progress=90)
            
            # 6. 更新文章元数据
            await self._update_article_metadata(html_path)
            await self._log("可视化解读生成完成！", progress=100)
            
            logger.success(f"可视化解读生成成功: {html_path}")
            return str(html_path)
            
        except Exception as e:
            error_msg = f"可视化解读生成失败: {e}"
            logger.error(f"任务 {self.task_id} - {error_msg}", exc_info=True)
            await task_manager.set_task_error(self.task_id, "可视化解读生成失败")
            return None
    
    async def _read_article_content(self) -> str:
        """
        读取深度解读文章内容，移除 YAML front matter
        
        Returns:
            纯文本内容（不含元数据）
            
        Raises:
            FileNotFoundError: 如果文章文件不存在
        """
        if not self.article_path.exists():
            raise FileNotFoundError(f"文章文件不存在: {self.article_path}")
        
        content = self.article_path.read_text(encoding="utf-8")
        
        # 移除 YAML front matter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
                logger.info(f"已移除 YAML front matter，剩余内容长度: {len(content)} 字符")
        
        return content
    
    def _build_prompt(self, article_content: str) -> str:
        """
        构建完整的提示词
        
        Args:
            article_content: 文章内容
            
        Returns:
            完整的提示词
        """
        # 添加明确的输出格式要求
        output_instruction = """

# 重要输出要求

**你必须直接输出完整的 HTML 代码，不要添加任何解释、前缀或后缀。**

- ❌ 不要输出 "好的，我来生成..." 这样的开场白
- ❌ 不要输出 "```html" 代码块标记
- ❌ 不要在 HTML 前后添加任何说明文字
- ✅ 直接从 `<!DOCTYPE html>` 开始输出
- ✅ 以 `</html>` 结束输出

现在，请直接输出 HTML 代码：

"""
        
        prompt = f"{self.text2html_prompt}{output_instruction}\n---\n{article_content}\n---"
        logger.info(f"构建提示词完成，总长度: {len(prompt)} 字符")
        return prompt
    
    async def _generate_html(self, prompt: str) -> str:
        """
        调用 AI 生成 HTML，包含重试逻辑
        
        Args:
            prompt: 完整提示词
            
        Returns:
            生成的 HTML 内容
            
        Raises:
            RuntimeError: 达到最大重试次数仍失败
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"调用 AI 生成 HTML (尝试 {attempt + 1}/{self.max_retries})")
                
                html = await self.summarizer.generate_content(prompt)
                
                if html and html.strip():
                    logger.success(f"AI 生成成功，HTML 长度: {len(html)} 字符")
                    return html
                
                raise ValueError("AI 返回空内容")
                
            except Exception as e:
                logger.warning(
                    f"生成 HTML 失败 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )
                
                if attempt == self.max_retries - 1:
                    raise
                
                # 指数退避
                wait_time = 2 ** attempt
                logger.info(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
        
        raise RuntimeError("达到最大重试次数")
    
    def _clean_html(self, html: str) -> str:
        """
        清理 AI 生成的 HTML，移除多余的解释文字和代码块标记
        
        Args:
            html: 原始 HTML 内容
            
        Returns:
            清理后的 HTML
        """
        import re
        
        # 1. 尝试提取 ```html 代码块中的内容
        html_block_match = re.search(r'```html\s*(.*?)\s*```', html, re.DOTALL | re.IGNORECASE)
        if html_block_match:
            html = html_block_match.group(1)
            logger.info("从 markdown 代码块中提取 HTML")
        
        # 2. 如果没有代码块，尝试找到 <!DOCTYPE html> 或 <html 的位置
        if '<!DOCTYPE html>' in html:
            start_idx = html.find('<!DOCTYPE html>')
            html = html[start_idx:]
            logger.info("从 <!DOCTYPE html> 开始提取")
        elif '<html' in html.lower():
            start_idx = html.lower().find('<html')
            html = html[start_idx:]
            logger.info("从 <html 标签开始提取")
        
        # 3. 移除 HTML 结束后的多余内容
        if '</html>' in html.lower():
            end_idx = html.lower().rfind('</html>') + len('</html>')
            html = html[:end_idx]
            logger.info("移除 </html> 之后的内容")
        
        # 4. 移除可能的 markdown 代码块结束标记
        html = re.sub(r'```\s*$', '', html, flags=re.MULTILINE)
        
        return html.strip()
    
    def _clean_html(self, html: str) -> str:
        """
        清理 HTML 内容，移除多余的前缀和后缀
        
        Args:
            html: 原始 HTML 内容
            
        Returns:
            清理后的 HTML
        """
        import re
        
        original_length = len(html)
        
        # 1. 移除 markdown 代码块标记
        html = re.sub(r'^```html\s*\n', '', html, flags=re.MULTILINE)
        html = re.sub(r'\n```\s*$', '', html, flags=re.MULTILINE)
        html = re.sub(r'```', '', html)  # 移除所有剩余的 ``` 标记
        
        # 2. 查找 <!DOCTYPE html> 的位置
        doctype_match = re.search(r'<!DOCTYPE\s+html>', html, re.IGNORECASE)
        if doctype_match:
            # 从 DOCTYPE 开始截取
            html = html[doctype_match.start():]
            logger.info(f"已移除 DOCTYPE 之前的 {doctype_match.start()} 个字符")
        else:
            # 如果没有 DOCTYPE，尝试查找 <html
            html_match = re.search(r'<html[^>]*>', html, re.IGNORECASE)
            if html_match:
                html = html[html_match.start():]
                logger.info(f"未找到 DOCTYPE，从 <html> 标签开始截取")
        
        # 3. 查找最后一个 </html> 的位置
        html_end_matches = list(re.finditer(r'</html>', html, re.IGNORECASE))
        if html_end_matches:
            # 从最后一个 </html> 之后截断
            last_match = html_end_matches[-1]
            removed_chars = len(html) - last_match.end()
            html = html[:last_match.end()]
            if removed_chars > 0:
                logger.info(f"已移除 </html> 之后的 {removed_chars} 个字符")
        
        # 4. 移除首尾空白
        html = html.strip()
        
        cleaned_length = len(html)
        logger.info(f"HTML 清理完成: {original_length} → {cleaned_length} 字符")
        
        return html
    
    def _validate_html(self, html: str) -> bool:
        """
        验证 HTML 格式
        
        Args:
            html: HTML 内容
            
        Returns:
            是否有效
        """
        # 基本验证：检查必要的标签
        required_tags = ["<html", "<head", "<style", "<body"]
        
        html_lower = html.lower()
        missing_tags = [tag for tag in required_tags if tag not in html_lower]
        
        if missing_tags:
            logger.error(f"HTML 验证失败，缺少标签: {missing_tags}")
            return False
        
        logger.info("HTML 验证通过，包含所有必要标签")
        return True
    
    async def _save_html(self, html_content: str) -> Path:
        """
        保存 HTML 文件，保持与深度解读相同的版本号
        
        Args:
            html_content: HTML 内容
            
        Returns:
            保存的文件路径
        """
        # 生成文件名：{原文件名}_visual.html 或 {原文件名}_v2_visual.html
        base_name = self.article_path.stem
        
        # 如果原文件名包含版本号（如 article_v2），提取基础名称
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            base_name = version_match.group(1)
            self.version = int(version_match.group(2))
        
        # 构建 HTML 文件名
        if self.version > 0:
            html_filename = f"{base_name}_v{self.version}_visual.html"
        else:
            html_filename = f"{base_name}_visual.html"
        
        html_path = self.article_path.parent / html_filename
        
        # 保存文件
        html_path.write_text(html_content, encoding="utf-8")
        logger.info(f"可视化 HTML 已保存: {html_path} (版本: {self.version})")
        
        return html_path
    
    async def _update_article_metadata(self, html_path: Path):
        """
        更新文章元数据，记录可视化解读状态
        
        Args:
            html_path: HTML 文件路径
        """
        try:
            import yaml
            
            content = self.article_path.read_text(encoding="utf-8")
            
            # 解析 YAML front matter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1])
                    article_body = parts[2]
                    
                    # 更新元数据
                    metadata["visual_interpretation"] = {
                        "status": "completed",
                        "file": html_path.name,
                        "generated_at": datetime.now().isoformat()
                    }
                    
                    # 重新组装文件
                    new_yaml = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
                    new_content = f"---\n{new_yaml}---\n{article_body}"
                    
                    # 保存更新后的文件
                    self.article_path.write_text(new_content, encoding="utf-8")
                    logger.info(f"文章元数据已更新: {self.article_path}")
                else:
                    logger.warning("文章格式不正确，无法更新元数据")
            else:
                logger.warning("文章没有 YAML front matter，无法更新元数据")
                
        except Exception as e:
            logger.error(f"更新文章元数据失败: {e}", exc_info=True)
            # 不抛出异常，因为这不是关键错误
    
    async def _log(self, message: str, progress: int = None):
        """
        向 TaskManager 发送日志和进度更新
        
        Args:
            message: 日志消息
            progress: 进度百分比 (0-100)
        """
        logger.info(f"任务 {self.task_id}: {message}")
        
        if progress is not None:
            await task_manager.update_progress(self.task_id, progress, message)
        else:
            await task_manager.send_message(message, self.task_id)
