"""可视化解读生成工作器

该模块负责将深度解读文章转换为高度可视化的 HTML 网页。
采用分阶段生成模式：
1. AI 设计 Header（样式 + 标题）
2. AI 分章节生成内容（灵活设计）
3. AI 生成 Footer（脚本 + 结尾）
"""

import os
import re
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from reinvent_insight.core import config
from reinvent_insight.core.logger import get_logger
from reinvent_insight.infrastructure.ai.model_config import get_model_client
from .task_manager import manager as task_manager

logger = get_logger(__name__)

# 提示词文件路径
PROMPT_DIR = Path("./prompt/visual")
HEADER_PROMPT_PATH = PROMPT_DIR / "header_prompt.txt"
CHAPTER_PROMPT_PATH = PROMPT_DIR / "chapter_prompt.txt"
FOOTER_PROMPT_PATH = PROMPT_DIR / "footer_prompt.txt"
TEXT2HTML_PROMPT_PATH = Path("./prompt/text2html.txt")


class VisualInterpretationWorker:
    """可视化解读生成工作器
    
    采用分阶段生成：AI 设计 Header → 分章节生成内容 → AI 生成 Footer
    每个阶段都由 AI 灵活设计，保持每篇文章的独特性。
    
    样式传递机制：Header 阶段确定样式规范，传递给章节和 Footer，确保整篇文章风格一致。
    """
    
    # 默认样式规范（当 AI 未输出时使用）
    DEFAULT_STYLE_SPEC = {
        "brand_color": "#3B82F6",
        "brand_color_name": "blue-500",
        "chapter_title_template": '<div class="mb-8"><div class="flex items-center mb-4"><span class="text-[#3B82F6] font-mono text-xl mr-3">{{INDEX}}</span><h2 class="text-3xl md:text-4xl font-bold text-white">{{TITLE}}</h2></div></div>',
        "card_style": "bg-zinc-900 rounded-2xl p-6 border border-zinc-800"
    }
    
    def __init__(
        self, 
        task_id: str, 
        article_path: str, 
        model_name: str = None, 
        version: int = 0,
        task_dir: str = None
    ):
        """初始化可视化解读工作器"""
        self.task_id = task_id
        self.article_path = Path(article_path)
        self.version = version
        self.task_dir = Path(task_dir) if task_dir else None
        
        # 使用任务类型获取模型客户端
        self.client = get_model_client("visual_generation")
        self.max_retries = 3
        
        # 样式规范（由 Header 阶段确定，传递给章节和 Footer）
        self.style_spec = None
        
        # 加载提示词
        self.header_prompt = self._load_prompt(HEADER_PROMPT_PATH)
        self.chapter_prompt = self._load_prompt(CHAPTER_PROMPT_PATH)
        self.footer_prompt = self._load_prompt(FOOTER_PROMPT_PATH)
        self.text2html_prompt = self._load_prompt(TEXT2HTML_PROMPT_PATH)
        
        # 判断模式：有 task_dir 和章节文件则用分章节模式
        self.use_chunked_mode = self._check_chunked_mode()
        
        logger.info(
            f"初始化可视化工作器 - 任务: {task_id}, 分章节模式: {self.use_chunked_mode}"
        )
    
    def _load_prompt(self, path: Path) -> str:
        """加载提示词文件"""
        if not path.exists():
            logger.warning(f"提示词文件不存在: {path}")
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"读取提示词失败 {path}: {e}")
            return ""
    
    def _check_chunked_mode(self) -> bool:
        """检查是否可以使用分章节模式
        
        优先级：
        1. task_dir 存在且有章节文件 → True
        2. 文章内容可以精准还原章节 → True（回退模式）
        3. 其他情况 → False（使用一次性模式）
        """
        # 方式1：task_dir 中有章节文件
        if self.task_dir and self.task_dir.exists():
            chapter_files = list(self.task_dir.glob("chapter_*.md"))
            if chapter_files:
                self._chapter_source = 'task_dir'
                return True
        
        # 方式2：从文章内容中还原章节
        if self._can_extract_chapters_from_article():
            self._chapter_source = 'article'
            logger.info("task_dir 不存在，将从文章内容中还原章节")
            return True
        
        return False
    
    def _can_extract_chapters_from_article(self) -> bool:
        """检查文章内容是否可以精准还原章节"""
        if not self.article_path.exists():
            return False
        
        try:
            content = self.article_path.read_text(encoding="utf-8")
            # 检查是否有目录结构
            if "### 主要目录" not in content:
                return False
            # 检查是否有章节标题格式
            chapter_pattern = re.compile(r'^###? \d+\.', re.MULTILINE)
            matches = chapter_pattern.findall(content)
            return len(matches) >= 2  # 至少2个章节才值得分段
        except Exception as e:
            logger.debug(f"检查文章格式失败: {e}")
            return False
    
    async def run(self) -> Optional[str]:
        """执行可视化解读生成"""
        try:
            if self.task_id in task_manager.tasks:
                task_manager.tasks[self.task_id].status = "running"
            
            logger.info(f"[可视化生成] 开始, task_id={self.task_id}, 分章节模式={self.use_chunked_mode}")
            await self._log("正在生成可视化解读...", progress=5)
            
            # 根据模式选择生成方式
            if self.use_chunked_mode:
                html_content = await self._run_chunked_mode()
            else:
                html_content = await self._run_oneshot_mode()
            
            if not html_content:
                raise ValueError("生成的 HTML 内容为空")
            
            # 保存 HTML 文件
            html_path = await self._save_html(html_content)
            await self._log(f"HTML 文件已保存: {html_path.name}", progress=95)
            
            # 更新文章元数据
            await self._update_article_metadata(html_path)
            await self._log("可视化解读生成完成！", progress=100)
            
            await task_manager.set_task_completed(self.task_id, str(html_path))
            logger.success(f"[可视化生成] 成功, task_id={self.task_id}, html={html_path}")
            return str(html_path)
            
        except Exception as e:
            logger.error(f"任务 {self.task_id} - 可视化解读生成失败: {e}", exc_info=True)
            await self._log(f"生成失败: {str(e)}", progress=0)
            await task_manager.set_task_error(self.task_id, f"可视化解读生成失败: {str(e)}")
            return None
    
    # ==================== 分章节生成模式 ====================
    
    async def _run_chunked_mode(self) -> str:
        """分章节生成模式：AI 灵活设计，分阶段生成"""
        source = getattr(self, '_chapter_source', 'task_dir')
        logger.info(f"使用分章节生成模式，章节来源: {source}")
        
        # 1. 读取章节文件
        await self._log("正在读取章节内容...", progress=10)
        
        if source == 'task_dir':
            chapters = self._load_chapter_files()
        else:
            chapters = self._extract_chapters_from_article()
        
        if not chapters:
            raise ValueError("未找到章节内容")
        
        logger.info(f"成功加载 {len(chapters)} 个章节")
        
        # 2. 提取文章元数据
        metadata = self._extract_article_metadata()
        
        # 3. AI 生成 Header（样式 + 标题区域）
        await self._log("正在设计页面样式...", progress=15)
        header_html = await self._generate_header(metadata, chapters)
        
        # 4. 并发生成各章节的 HTML 片段
        await self._log(f"正在生成 {len(chapters)} 个章节的可视化内容...", progress=20)
        chapter_htmls = await self._generate_chapters_parallel(chapters)
        
        # 5. AI 生成 Footer（结尾 + 脚本）
        await self._log("正在生成页面结尾...", progress=85)
        footer_html = await self._generate_footer(metadata)
        
        # 6. 组装完整 HTML
        await self._log("HTML 组装完成，验证中...", progress=90)
        html_content = header_html + '\n'.join(chapter_htmls) + footer_html
        
        if not self._validate_html(html_content):
            raise ValueError("组装的 HTML 格式无效")
        
        return html_content
    
    async def _generate_header(self, metadata: Dict, chapters: List[Dict]) -> str:
        """让 AI 生成 HTML 头部（样式 + 标题），并提取样式规范"""
        # 构建文章概要
        article_summary = self._build_article_summary(chapters)
        
        prompt = self.header_prompt.replace(
            "{{TITLE_CN}}", metadata.get('title_cn', '深度解读')
        ).replace(
            "{{TITLE_EN}}", metadata.get('title_en', 'Deep Insight')
        ).replace(
            "{{CHAPTER_COUNT}}", str(len(chapters))
        ).replace(
            "{{DATE}}", metadata.get('date', '')
        ).replace(
            "{{ARTICLE_SUMMARY}}", article_summary
        )
        
        for attempt in range(self.max_retries + 1):
            try:
                header = await self.client.generate_content(prompt)
                if header and header.strip():
                    # 提取样式规范
                    self.style_spec = self._extract_style_spec(header)
                    logger.info(f"提取到样式规范: {self.style_spec}")
                    
                    # 清理 HTML（移除样式规范块）
                    return self._clean_header_html(header)
            except Exception as e:
                logger.warning(f"Header 生成失败 (尝试 {attempt+1}): {e}")
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return ""
    
    def _extract_style_spec(self, header_output: str) -> Dict:
        """从 Header 输出中提取样式规范
        
        格式：
        <!-- STYLE_SPEC_START
        { "brand_color": "#XXXXXX", ... }
        STYLE_SPEC_END -->
        """
        try:
            # 匹配样式规范块
            pattern = r'<!--\s*STYLE_SPEC_START\s*([\s\S]*?)STYLE_SPEC_END\s*-->'
            match = re.search(pattern, header_output)
            
            if match:
                json_str = match.group(1).strip()
                spec = json.loads(json_str)
                logger.info(f"成功提取样式规范: 品牌色={spec.get('brand_color')}")
                return spec
            else:
                logger.warning("未找到样式规范块，使用默认值")
                return self.DEFAULT_STYLE_SPEC.copy()
                
        except json.JSONDecodeError as e:
            logger.warning(f"样式规范 JSON 解析失败: {e}，使用默认值")
            return self.DEFAULT_STYLE_SPEC.copy()
        except Exception as e:
            logger.warning(f"提取样式规范失败: {e}，使用默认值")
            return self.DEFAULT_STYLE_SPEC.copy()
    
    async def _generate_footer(self, metadata: Dict) -> str:
        """让 AI 生成 HTML 尾部（结尾 + 脚本），注入样式规范"""
        # 构建样式规范文本
        style_spec_text = self._format_style_spec_for_prompt()
        
        prompt = self.footer_prompt.replace(
            "{{TITLE_CN}}", metadata.get('title_cn', '')
        ).replace(
            "{{GENERATION_DATE}}", datetime.now().strftime("%Y-%m-%d")
        ).replace(
            "{{STYLE_SPEC}}", style_spec_text
        )
        
        for attempt in range(self.max_retries + 1):
            try:
                footer = await self.client.generate_content(prompt)
                if footer and footer.strip():
                    # 确保包含 iframe 通信脚本
                    footer = self._ensure_iframe_script(footer)
                    return self._clean_footer_html(footer)
            except Exception as e:
                logger.warning(f"Footer 生成失败 (尝试 {attempt+1}): {e}")
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return ""
    
    def _build_article_summary(self, chapters: List[Dict]) -> str:
        """构建文章概要（供 AI 设计 Header 时参考）"""
        summary_parts = []
        for ch in chapters[:5]:  # 取前 5 章
            title = ch.get('title', '')
            content = ch.get('content', '')[:200]
            summary_parts.append(f"- {title}: {content}...")
        return '\n'.join(summary_parts)
    
    def _clean_header_html(self, html: str) -> str:
        """清理 Header HTML，移除样式规范块"""
        # 移除样式规范块
        html = re.sub(r'<!--\s*STYLE_SPEC_START[\s\S]*?STYLE_SPEC_END\s*-->', '', html)
        
        # 移除 markdown 代码块标记
        html = re.sub(r'^```html\s*\n', '', html, flags=re.MULTILINE)
        html = re.sub(r'\n```\s*$', '', html, flags=re.MULTILINE)
        html = re.sub(r'```', '', html)
        return html.strip()
    
    def _clean_footer_html(self, html: str) -> str:
        """清理 Footer HTML"""
        html = re.sub(r'^```html\s*\n', '', html, flags=re.MULTILINE)
        html = re.sub(r'\n```\s*$', '', html, flags=re.MULTILINE)
        html = re.sub(r'```', '', html)
        return html.strip()
    
    def _format_style_spec_for_prompt(self) -> str:
        """将样式规范格式化为提示词文本"""
        spec = self.style_spec or self.DEFAULT_STYLE_SPEC
        
        # 章节标题模板
        chapter_title_template = spec.get(
            'chapter_title_template',
            '<div class="mb-8"><div class="flex items-center mb-4"><span class="text-[#3B82F6] font-mono text-xl mr-3">{{INDEX}}</span><h2 class="text-3xl md:text-4xl font-bold text-white">{{TITLE}}</h2></div></div>'
        )
        
        return f"""
- **品牌色**: {spec.get('brand_color', '#3B82F6')} ({spec.get('brand_color_name', 'blue-500')})
- **章节标题模板** (`chapter_title_template`): 
  ```html
  {chapter_title_template}
  ```
  - `{{{{INDEX}}}}` → 章节序号（如 "01"）
  - `{{{{TITLE}}}}` → 章节标题文字
- **卡片样式**: `{spec.get('card_style', 'bg-zinc-900 rounded-2xl p-6 border border-zinc-800')}`
"""
    
    def _ensure_iframe_script(self, footer: str) -> str:
        """确保 footer 包含 iframe 通信脚本"""
        if 'iframe-height' not in footer:
            iframe_script = '''
<script>
(function() {
  function sendHeight() {
    const height = Math.max(
      document.body.scrollHeight,
      document.body.offsetHeight,
      document.documentElement.clientHeight,
      document.documentElement.scrollHeight,
      document.documentElement.offsetHeight
    );
    window.parent.postMessage({type: 'iframe-height', height: height}, '*');
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', sendHeight);
  } else {
    sendHeight();
  }
  window.addEventListener('load', sendHeight);
  window.addEventListener('resize', sendHeight);
  const observer = new MutationObserver(sendHeight);
  observer.observe(document.body, {childList: true, subtree: true, attributes: true});
})();
</script>
'''
            # 在 </body> 前插入
            if '</body>' in footer.lower():
                pos = footer.lower().rfind('</body>')
                footer = footer[:pos] + iframe_script + footer[pos:]
        return footer
    
    # ==================== 一次性生成模式 ====================
    
    async def _run_oneshot_mode(self) -> str:
        """一次性生成模式（无章节文件时使用）"""
        logger.info("使用一次性生成模式")
        
        # 读取文章内容
        article_content = await self._read_article_content()
        await self._log("已读取文章内容", progress=20)
        
        # 构建提示词
        prompt = self._build_oneshot_prompt(article_content)
        await self._log("正在调用 AI 生成 HTML...", progress=30)
        
        # 调用 AI 生成
        for attempt in range(self.max_retries + 1):
            try:
                html = await self.client.generate_content(prompt)
                if html and html.strip():
                    html = self._clean_full_html(html)
                    html = self._inject_iframe_script(html)
                    await self._log("AI 生成完成", progress=80)
                    return html
            except Exception as e:
                logger.warning(f"HTML 生成失败 (尝试 {attempt+1}): {e}")
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return ""
    
    async def _read_article_content(self) -> str:
        """读取文章内容，移除 YAML front matter"""
        if not self.article_path.exists():
            raise FileNotFoundError(f"文章文件不存在: {self.article_path}")
        
        content = self.article_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        return content
    
    def _build_oneshot_prompt(self, article_content: str) -> str:
        """构建一次性生成提示词"""
        output_instruction = """

# 重要输出要求

**你必须直接输出完整的 HTML 代码，不要添加任何解释。**

- 直接从 `<!DOCTYPE html>` 开始输出
- 以 `</html>` 结束输出
- 不要输出 markdown 代码块标记

现在，请直接输出 HTML 代码：

"""
        return f"{self.text2html_prompt}{output_instruction}\n---\n{article_content}\n---"
    
    def _clean_full_html(self, html: str) -> str:
        """清理完整 HTML"""
        html = re.sub(r'^```html\s*\n', '', html, flags=re.MULTILINE)
        html = re.sub(r'\n```\s*$', '', html, flags=re.MULTILINE)
        html = re.sub(r'```', '', html)
        
        # 从 DOCTYPE 开始
        doctype_match = re.search(r'<!DOCTYPE\s+html>', html, re.IGNORECASE)
        if doctype_match:
            html = html[doctype_match.start():]
        
        # 到 </html> 结束
        html_end = list(re.finditer(r'</html>', html, re.IGNORECASE))
        if html_end:
            html = html[:html_end[-1].end()]
        
        return html.strip()
    
    def _load_chapter_files(self) -> List[Dict]:
        """加载 task_dir 下的章节文件"""
        chapters = []
        chapter_files = sorted(
            self.task_dir.glob("chapter_*.md"),
            key=lambda p: int(re.search(r'chapter_(\d+)', p.name).group(1))
        )
        
        for i, chapter_file in enumerate(chapter_files, 1):
            try:
                content = chapter_file.read_text(encoding="utf-8")
                # 提取章节标题（第一个 ## 标题）
                title_match = re.search(r'^##\s*\d*\.?\s*(.+)$', content, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else f"章节 {i}"
                
                chapters.append({
                    'index': i,
                    'title': title,
                    'content': content,
                    'file': chapter_file
                })
                logger.debug(f"加载章节 {i}: {title}")
            except Exception as e:
                logger.error(f"读取章节文件失败 {chapter_file}: {e}")
        
        return chapters
    
    def _extract_chapters_from_article(self) -> List[Dict]:
        """从文章内容中精准还原章节
        
        根据文章标准格式进行切分：
        - 章节标题格式：`## N. 标题` 或 `### N. 标题`
        - 跳过引言和目录部分
        
        Returns:
            章节列表，每个章节包含 index, title, content
        """
        chapters = []
        
        try:
            content = self.article_path.read_text(encoding="utf-8")
            
            # 移除 YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2].strip()
            
            # 找到第一个章节标题的位置（跳过引言和目录）
            # 章节标题格式：## 1. xxx 或 ### 1. xxx
            chapter_pattern = re.compile(
                r'^(###?) (\d+)\.\s*(.+?)$',
                re.MULTILINE
            )
            
            matches = list(chapter_pattern.finditer(content))
            
            if not matches:
                logger.warning("未在文章中找到章节标题")
                return []
            
            logger.info(f"找到 {len(matches)} 个章节标题")
            
            for i, match in enumerate(matches):
                chapter_num = int(match.group(2))
                title = match.group(3).strip()
                
                # 计算章节内容范围
                start_pos = match.start()
                if i + 1 < len(matches):
                    end_pos = matches[i + 1].start()
                else:
                    end_pos = len(content)
                
                chapter_content = content[start_pos:end_pos].strip()
                
                # 移除章节分隔符 ---
                chapter_content = re.sub(r'\n---\s*$', '', chapter_content)
                
                chapters.append({
                    'index': chapter_num,
                    'title': title,
                    'content': chapter_content,
                    'file': None  # 从文章提取的没有文件
                })
                
                logger.debug(f"提取章节 {chapter_num}: {title[:30]}... ({len(chapter_content)} 字符)")
            
            logger.info(f"从文章中成功提取 {len(chapters)} 个章节")
            
        except Exception as e:
            logger.error(f"从文章提取章节失败: {e}", exc_info=True)
        
        return chapters
    
    def _extract_article_metadata(self) -> Dict:
        """从文章中提取元数据（让 AI 自己决定配色）"""
        import yaml
        
        today = datetime.now().strftime("%Y-%m-%d")
        metadata = {
            'title_cn': '',
            'title_en': '',
            'date': today,
        }
        
        try:
            content = self.article_path.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_data = yaml.safe_load(parts[1])
                    metadata['title_cn'] = yaml_data.get('title_cn', '')
                    metadata['title_en'] = yaml_data.get('title_en', '')
                    
                    # 处理日期：优先使用 upload_date，如果无效则使用 created_at 或当天日期
                    raw_date = yaml_data.get('upload_date', '')
                    if raw_date:
                        # 格式化日期：YYYYMMDD -> YYYY-MM-DD
                        date_str = str(raw_date).replace('-', '')
                        if len(date_str) == 8:
                            formatted = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
                            # 检查日期是否有效（不是 1970-01-01）
                            if formatted != '1970-01-01':
                                metadata['date'] = formatted
                            else:
                                # upload_date 无效，尝试使用 created_at
                                created_at = yaml_data.get('created_at', '')
                                if created_at:
                                    # created_at 格式：2025-12-14T15:36:57.920029
                                    try:
                                        metadata['date'] = str(created_at)[:10]
                                    except:
                                        pass
        except Exception as e:
            logger.warning(f"提取文章元数据失败: {e}")
        
        return metadata
    
    async def _generate_chapters_parallel(self, chapters: List[Dict]) -> List[str]:
        """并发生成各章节的 HTML 片段"""
        total = len(chapters)
        results = [''] * total
        
        # 获取并发延迟配置
        concurrent_delay = getattr(self.client.config, 'concurrent_delay', 1.0)
        logger.info(f"并发生成 {total} 个章节，间隔: {concurrent_delay}秒")
        
        # 创建并发任务
        tasks = []
        for i, chapter in enumerate(chapters):
            delay = i * concurrent_delay
            task = self._generate_single_chapter_html(chapter, delay, i, total)
            tasks.append(task)
        
        # 执行并发任务
        chapter_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        success_count = 0
        for i, result in enumerate(chapter_results):
            if isinstance(result, Exception):
                logger.error(f"生成章节 {i+1} 失败: {result}")
                # 使用简单的回退内容
                results[i] = self._generate_fallback_chapter_html(chapters[i])
            else:
                results[i] = result
                success_count += 1
        
        logger.info(f"章节生成完成: {success_count}/{total}")
        return results
    
    async def _generate_single_chapter_html(
        self, 
        chapter: Dict, 
        delay: float,
        current_index: int,
        total: int
    ) -> str:
        """生成单个章节的 HTML 片段，注入样式规范"""
        if delay > 0:
            await asyncio.sleep(delay)
        
        index = chapter['index']
        title = chapter['title']
        content = chapter['content']
        
        logger.info(f"开始生成章节 {index}/{total}: {title[:30]}...")
        
        # 构建样式规范文本
        style_spec_text = self._format_style_spec_for_prompt()
        
        # 构建提示词，注入样式规范
        prompt = self.chapter_prompt.replace(
            "{{CHAPTER_INDEX}}", str(index)
        ).replace(
            "{{CHAPTER_TITLE}}", title
        ).replace(
            "{{CHAPTER_CONTENT}}", content
        ).replace(
            "{{STYLE_SPEC}}", style_spec_text
        )
        
        # 重试逻辑
        for attempt in range(self.max_retries + 1):
            try:
                html_fragment = await self.client.generate_content(prompt)
                
                if html_fragment and html_fragment.strip():
                    # 清理 HTML 片段
                    html_fragment = self._clean_chapter_html(html_fragment)
                    
                    # 更新进度
                    progress = 20 + int((current_index + 1) / total * 55)
                    await self._log(f"章节 {index} 生成完成", progress=progress)
                    
                    logger.info(f"章节 {index} 生成成功，片段长度: {len(html_fragment)}")
                    return html_fragment
                
                raise ValueError("AI 返回空内容")
                
            except Exception as e:
                logger.warning(f"生成章节 {index} 失败 (尝试 {attempt+1}): {e}")
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return ""
    
    def _clean_chapter_html(self, html: str) -> str:
        """清理章节 HTML 片段"""
        # 移除 markdown 代码块标记
        html = re.sub(r'^```html\s*\n', '', html, flags=re.MULTILINE)
        html = re.sub(r'\n```\s*$', '', html, flags=re.MULTILINE)
        html = re.sub(r'```', '', html)
        
        # 确保从 <section 开始
        section_match = re.search(r'<section[^>]*>', html, re.IGNORECASE)
        if section_match:
            html = html[section_match.start():]
        
        # 确保到 </section> 结束
        section_end_matches = list(re.finditer(r'</section>', html, re.IGNORECASE))
        if section_end_matches:
            last_match = section_end_matches[-1]
            html = html[:last_match.end()]
        
        return html.strip()
    
    def _generate_fallback_chapter_html(self, chapter: Dict) -> str:
        """生成回退用的简单章节 HTML"""
        index = chapter['index']
        title = chapter['title']
        content = chapter['content']
        
        # 简单的 Markdown 转 HTML
        content_html = content.replace('\n\n', '</p><p class="text-gray-300 mb-4">').replace('\n', '<br>')
        
        return f'''
<section id="chapter-{index}" class="chapter-section fade-in-up">
    <h2 class="chapter-title">
        <span class="text-brand mr-2">{index}.</span>
        {title}
    </h2>
    <div class="main-card p-8">
        <div class="text-gray-300 space-y-4">
            <p>{content_html}</p>
        </div>
    </div>
</section>
'''
    
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
        try:
            # 注入 iframe 高度通信脚本
            logger.info("注入 iframe 通信脚本")
            html_content = self._inject_iframe_script(html_content)
            
            # 生成文件名：{原文件名}_visual.html 或 {原文件名}_v2_visual.html
            base_name = self.article_path.stem
            logger.info(f"原始文件名: {base_name}")
            
            # 如果原文件名包含版本号（如 article_v2），提取基础名称
            version_match = re.match(r'^(.+)_v(\d+)$', base_name)
            if version_match:
                base_name = version_match.group(1)
                self.version = int(version_match.group(2))
                logger.info(f"检测到版本号: v{self.version}, 基础名称: {base_name}")
            
            # 构建 HTML 文件名
            if self.version > 0:
                html_filename = f"{base_name}_v{self.version}_visual.html"
            else:
                html_filename = f"{base_name}_visual.html"
            
            html_path = self.article_path.parent / html_filename
            logger.info(f"目标 HTML 路径: {html_path}")
            
            # 确保目录存在
            html_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用原子写入机制：先写入临时文件，完成后再重命名
            temp_path = html_path.with_suffix('.html.tmp')
            
            try:
                # 1. 写入临时文件
                logger.info(f"写入临时文件，内容长度: {len(html_content)} 字符")
                temp_path.write_text(html_content, encoding="utf-8")
                
                # 2. 验证临时文件完整性
                if not temp_path.exists():
                    raise IOError(f"临时文件写入失败: {temp_path}")
                
                temp_size = temp_path.stat().st_size
                if temp_size == 0:
                    raise IOError(f"临时文件为空: {temp_path}")
                
                logger.info(f"临时文件写入成功，大小: {temp_size} 字节")
                
                # 3. 原子重命名（如果目标文件存在会被覆盖）
                temp_path.replace(html_path)
                logger.info(f"原子重命名完成: {temp_path.name} -> {html_path.name}")
                
                # 4. 最终验证
                if not html_path.exists():
                    raise IOError(f"HTML 文件保存失败，文件不存在: {html_path}")
                
                file_size = html_path.stat().st_size
                logger.success(f"可视化 HTML 已保存: {html_path} (版本: {self.version}, 大小: {file_size} 字节)")
                
                return html_path
                
            except Exception as e:
                # 清理临时文件
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                        logger.info(f"已清理临时文件: {temp_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"清理临时文件失败: {cleanup_error}")
                raise
            
        except Exception as e:
            logger.error(f"保存 HTML 文件失败: {e}", exc_info=True)
            raise
    
    def _inject_iframe_script(self, html_content: str) -> str:
        """
        在 HTML 的 </body> 标签前注入 iframe 高度通信脚本
        
        Args:
            html_content: 原始 HTML 内容
            
        Returns:
            注入脚本后的 HTML 内容
        """
        # iframe 高度通信脚本
        iframe_script = """
<script>
(function() {
  function sendHeight() {
    const height = Math.max(
      document.body.scrollHeight,
      document.body.offsetHeight,
      document.documentElement.clientHeight,
      document.documentElement.scrollHeight,
      document.documentElement.offsetHeight
    );
    
    window.parent.postMessage({
      type: 'iframe-height',
      height: height
    }, '*');
  }
  
  // 初始发送
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', sendHeight);
  } else {
    sendHeight();
  }
  
  // 监听内容变化
  window.addEventListener('load', sendHeight);
  window.addEventListener('resize', sendHeight);
  
  // 使用 MutationObserver 监听 DOM 变化
  const observer = new MutationObserver(sendHeight);
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: true
  });
})();
</script>
"""
        
        # 在 </body> 标签前注入脚本
        if '</body>' in html_content.lower():
            # 找到最后一个 </body> 标签的位置
            body_end_pos = html_content.lower().rfind('</body>')
            html_content = (
                html_content[:body_end_pos] +
                iframe_script +
                html_content[body_end_pos:]
            )
            logger.info("已注入 iframe 高度通信脚本")
        else:
            logger.warning("未找到 </body> 标签，无法注入脚本")
        
        return html_content
    
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
