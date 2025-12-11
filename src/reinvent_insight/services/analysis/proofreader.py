# -*- coding: utf-8 -*-
"""
文章校对服务 - Ultra DeepInsight 后校验

采用智能分步处理策略：
0. Step 0: 评估是否需要结构重组（mapping）还是仅优化衔接
1. Step 1: 如需重组，输出映射规划表
2. Step 2: 分板块整合或仅润色衔接

原始素材加载：
- 视频类：从 downloads/subtitles 获取字幕
- PDF类：加载原始 PDF 内容
"""

import re
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from reinvent_insight.core import config
from reinvent_insight.infrastructure.ai.model_config import get_model_client
from reinvent_insight.domain.prompts.proofreading import (
    STEP0_EVALUATE_PROMPT,
    STEP1_MAPPING_PROMPT,
    STEP2_MERGE_PROMPT,
    STEP2_POLISH_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass
class ProofreadingResult:
    """校对结果"""
    mapping: str = ""
    new_outline: List[Dict] = field(default_factory=list)
    merged_content: str = ""
    changes: str = ""
    needs_restructure: bool = False  # 是否需要结构重组
    success: bool = False
    error: Optional[str] = None


class ArticleProofreader:
    """文章校对器 - 智能分步策略"""
    
    MIN_CHAPTERS_FOR_PROOFREADING = 15
    
    def __init__(self, task_id: str, task_dir: str, video_url: str = None, source_type: str = "youtube"):
        """
        Args:
            task_id: 任务ID
            task_dir: 临时目录
            video_url: 原始视频URL（用于获取字幕）
            source_type: 来源类型 (youtube/pdf/text)
        """
        self.task_id = task_id
        self.task_dir = Path(task_dir)
        self.video_url = video_url
        self.source_type = source_type
        self.client = get_model_client("proofreading")
        self.chapters: List[Dict] = []
        self.outline: str = ""
        self.original_content: str = ""  # 原始素材（字幕/文档）
    
    async def should_proofread(self) -> bool:
        """判断是否需要校对"""
        chapter_files = list(self.task_dir.glob("chapter_*.md"))
        chapter_count = len(chapter_files)
        should = chapter_count >= self.MIN_CHAPTERS_FOR_PROOFREADING
        
        if should:
            logger.info(f"任务 {self.task_id} - 检测到 {chapter_count} 个章节，将触发校对")
        else:
            logger.info(f"任务 {self.task_id} - {chapter_count} 个章节，无需校对")
        
        return should
    
    async def run(self) -> bool:
        """执行智能校对流程"""
        logger.info(f"任务 {self.task_id} - 开始智能校对...")
        
        # 创建诊断目录
        debug_dir = self.task_dir / "proofreading_debug"
        debug_dir.mkdir(exist_ok=True)
        
        try:
            # 1. 加载所有内容
            self.outline, self.chapters = self._load_all_content()
            if not self.chapters:
                logger.error(f"任务 {self.task_id} - 未找到章节文件")
                return False
            
            logger.info(f"任务 {self.task_id} - 已加载 {len(self.chapters)} 个章节")
            
            # 输出: 章节列表
            chapters_info = "\n".join([f"{ch['index']}. {ch['title']}" for ch in self.chapters])
            (debug_dir / "00_chapters_list.txt").write_text(chapters_info, encoding="utf-8")
            
            # 2. 加载原始素材
            self.original_content = await self._load_original_content()
            if self.original_content:
                logger.info(f"任务 {self.task_id} - 已加载原始素材 ({len(self.original_content)} 字符)")
                (debug_dir / "01_original_content.txt").write_text(self.original_content[:20000], encoding="utf-8")
            else:
                (debug_dir / "01_original_content.txt").write_text("（未获取到原始素材）", encoding="utf-8")
            
            # 3. Step 0: 评估是否需要结构重组
            result = await self._step0_evaluate()
            (debug_dir / "02_step0_evaluate_result.txt").write_text(
                f"需要重组: {result.needs_restructure}", encoding="utf-8"
            )
            
            if result.needs_restructure:
                # 4a. 需要重组：Step 1 + Step 2
                logger.info(f"任务 {self.task_id} - 检测到结构问题，执行结构重组")
                result = await self._step1_get_mapping()
                
                # 输出: 映射规划原始输出
                (debug_dir / "03_step1_mapping_raw.md").write_text(
                    result.mapping or "（映射为空）", encoding="utf-8"
                )
                # 输出: 解析后的映射
                parsed_mapping = "\n".join([
                    f"板块{o['index']}: {o['title']} <- 原章节 {o['source_chapters']}"
                    for o in result.new_outline
                ]) if result.new_outline else "（解析失败）"
                (debug_dir / "04_step1_mapping_parsed.txt").write_text(parsed_mapping, encoding="utf-8")
                
                if not result.new_outline:
                    logger.error(f"任务 {self.task_id} - 映射规划失败: {result.error}")
                    (debug_dir / "99_error.txt").write_text(f"映射规划失败: {result.error}", encoding="utf-8")
                    return False
                
                result = await self._step2_merge_content(result)
                # 输出: 整合后内容
                (debug_dir / "05_step2_merged_content.md").write_text(
                    result.merged_content or "（整合失败）", encoding="utf-8"
                )
            else:
                # 4b. 无需重组：仅优化衔接和流畅度
                logger.info(f"任务 {self.task_id} - 无结构问题，仅优化衔接")
                
                # 输出: 原始拼接内容
                original_combined = "\n\n".join([ch["content"] for ch in self.chapters])
                (debug_dir / "03_original_combined.md").write_text(original_combined, encoding="utf-8")
                
                result = await self._step2_polish_only(result)
                # 输出: 润色后内容
                (debug_dir / "04_step2_polished_content.md").write_text(
                    result.merged_content or "（润色失败）", encoding="utf-8"
                )
            
            if not result.merged_content:
                logger.error(f"任务 {self.task_id} - 内容处理失败: {result.error}")
                (debug_dir / "99_error.txt").write_text(f"内容处理失败: {result.error}", encoding="utf-8")
                return False
            
            # 输出: 变更摘要
            (debug_dir / "06_changes_summary.txt").write_text(result.changes or "（无变更）", encoding="utf-8")
            
            # 5. 写入结果
            self._write_result(result)
            
            logger.info(f"任务 {self.task_id} - 校对完成，诊断文件在 {debug_dir}")
            result.success = True
            return True
            
        except Exception as e:
            logger.error(f"任务 {self.task_id} - 校对过程出错: {e}", exc_info=True)
            (debug_dir / "99_error.txt").write_text(f"校对异常: {e}", encoding="utf-8")
            return False
    
    async def _load_original_content(self) -> str:
        """加载原始素材（字幕/PDF原文）"""
        if not self.video_url:
            return ""
        
        try:
            if self.source_type == "youtube" or "youtube.com" in self.video_url or "youtu.be" in self.video_url:
                return await self._load_subtitle()
            elif self.source_type == "pdf":
                return await self._load_pdf_content()
            else:
                return ""
        except Exception as e:
            logger.warning(f"任务 {self.task_id} - 加载原始素材失败: {e}")
            return ""
    
    async def _load_subtitle(self) -> str:
        """从本地加载字幕文件"""
        from reinvent_insight.infrastructure.media.youtube_downloader import SubtitleDownloader
        
        # 尝试从本地字幕目录查找
        subtitle_dir = config.SUBTITLE_DIR
        if not subtitle_dir.exists():
            return ""
        
        # 尝试下载或从缓存获取
        loop = asyncio.get_running_loop()
        dl = SubtitleDownloader(self.video_url)
        subtitle_text, _, error = await loop.run_in_executor(None, dl.download)
        
        if error or not subtitle_text:
            logger.warning(f"任务 {self.task_id} - 获取字幕失败")
            return ""
        
        return subtitle_text
    
    async def _load_pdf_content(self) -> str:
        """加载 PDF 原文内容"""
        # PDF 路径通常存储在 video_url 中
        pdf_path = Path(self.video_url) if self.video_url else None
        
        if not pdf_path or not pdf_path.exists():
            # 尝试从 downloads/pdfs 目录查找
            return ""
        
        # PDF 内容通过 RAG 方式已在生成时处理，这里返回空
        # 实际校对时依赖章节内容即可
        return ""
    
    async def _step0_evaluate(self) -> ProofreadingResult:
        """Step 0: 评估是否需要结构重组"""
        result = ProofreadingResult()
        
        # 构建章节标题列表
        chapter_list = "\n".join([f"{ch['index']}. {ch['title']}" for ch in self.chapters])
        
        prompt = STEP0_EVALUATE_PROMPT.format(
            chapter_count=len(self.chapters),
            chapter_list=chapter_list,
            original_content=self.original_content[:5000] if self.original_content else "（无原始素材）"
        )
        
        try:
            logger.info(f"任务 {self.task_id} - Step 0: 评估结构质量...")
            raw_output = await self.client.generate_content(prompt)
            
            if not raw_output:
                # 默认进行重组
                result.needs_restructure = True
                return result
            
            # 解析评估结果
            output_lower = raw_output.lower()
            result.needs_restructure = "需要重组" in raw_output or "needs_restructure: true" in output_lower or "是" in raw_output[:50]
            
            logger.info(f"任务 {self.task_id} - 评估结果: {'需要重组' if result.needs_restructure else '仅需优化'}")
            
        except Exception as e:
            logger.warning(f"任务 {self.task_id} - Step 0 失败: {e}，默认进行重组")
            result.needs_restructure = True
        
        return result
    
    def _load_all_content(self) -> Tuple[str, List[Dict]]:
        """加载大纲和所有章节"""
        outline_path = self.task_dir / "outline.md"
        outline = ""
        if outline_path.exists():
            outline = outline_path.read_text(encoding="utf-8")
        
        chapters = []
        chapter_files = sorted(
            self.task_dir.glob("chapter_*.md"),
            key=lambda f: int(re.search(r'chapter_(\d+)', f.name).group(1))
        )
        
        for chapter_file in chapter_files:
            match = re.search(r'chapter_(\d+)', chapter_file.name)
            if match:
                index = int(match.group(1))
                content = chapter_file.read_text(encoding="utf-8")
                # 提取标题
                title_match = re.search(r'^## \d+\.\s*(.+)$', content, re.MULTILINE)
                title = title_match.group(1) if title_match else f"章节 {index}"
                # 提取金句和洞见
                quotes = re.findall(r'^>\s*["「].*?["」].*$', content, re.MULTILINE)
                insights = re.findall(r'^>\s*\*\*.*?\*\*.*$', content, re.MULTILINE)
                
                chapters.append({
                    "index": index,
                    "title": title,
                    "content": content,
                    "quotes": quotes,
                    "insights": insights,
                    "file": chapter_file
                })
        
        return outline, chapters
    
    async def _step1_get_mapping(self) -> ProofreadingResult:
        """Step 1: AI 输出映射规划表（不强制章节数量）"""
        result = ProofreadingResult()
        result.needs_restructure = True
        
        chapter_list = "\n".join([f"{ch['index']}. {ch['title']}" for ch in self.chapters])
        
        prompt = STEP1_MAPPING_PROMPT.format(
            chapter_count=len(self.chapters),
            chapter_list=chapter_list,
            original_content=self.original_content[:8000] if self.original_content else "（无原始素材）"
        )
        
        try:
            logger.info(f"任务 {self.task_id} - Step 1: 请求映射规划...")
            raw_output = await self.client.generate_content(prompt)
            
            if not raw_output:
                result.error = "AI 返回空内容"
                return result
            
            result.mapping = raw_output
            result.new_outline = self._parse_mapping(raw_output)
            
            if not result.new_outline:
                result.error = "未能解析映射规划"
                
        except Exception as e:
            result.error = str(e)
            logger.error(f"任务 {self.task_id} - Step 1 失败: {e}")
        
        return result
    
    def _parse_mapping(self, raw_output: str) -> List[Dict]:
        """解析映射规划输出"""
        new_outline = []
        
        # 匹配格式: 板块N: [标题] <- 原章节 1,2,3
        pattern = r'板块(\d+)[:：]\s*(.+?)\s*<-\s*原章节\s*([\d,，\s]+)'
        matches = re.findall(pattern, raw_output)
        
        for match in matches:
            index = int(match[0])
            title = match[1].strip()
            # 解析源章节编号
            source_str = match[2].replace('，', ',')
            source_chapters = [int(x.strip()) for x in source_str.split(',') if x.strip().isdigit()]
            
            new_outline.append({
                "index": index,
                "title": title,
                "source_chapters": source_chapters
            })
        
        return new_outline
    
    async def _step2_merge_content(self, result: ProofreadingResult) -> ProofreadingResult:
        """Step 2: 分板块整合内容"""
        merged_parts = []
        changes_log = []
        
        for new_section in result.new_outline:
            section_idx = new_section["index"]
            section_title = new_section["title"]
            source_indices = new_section["source_chapters"]
            
            source_contents = []
            source_quotes = []
            source_insights = []
            
            for src_idx in source_indices:
                for ch in self.chapters:
                    if ch["index"] == src_idx:
                        source_contents.append(ch["content"])
                        source_quotes.extend(ch["quotes"])
                        source_insights.extend(ch["insights"])
                        break
            
            if not source_contents:
                logger.warning(f"板块 {section_idx} 未找到源章节内容")
                continue
            
            if len(source_contents) == 1:
                content = source_contents[0]
                content = re.sub(r'^## \d+\.', f'## {section_idx}.', content, count=1)
                merged_parts.append(content)
                changes_log.append(f"板块 {section_idx}: 直接复用原章节 {source_indices[0]}")
            else:
                merged_content = await self._merge_multiple_chapters(
                    section_idx, section_title, source_contents, source_quotes, source_insights
                )
                if merged_content:
                    merged_parts.append(merged_content)
                    changes_log.append(f"板块 {section_idx}: 整合原章节 {source_indices} -> {section_title}")
        
        result.merged_content = "\n\n".join(merged_parts)
        result.changes = "\n".join(changes_log)
        
        return result
    
    async def _step2_polish_only(self, result: ProofreadingResult) -> ProofreadingResult:
        """Step 2 (替代): 仅优化衔接和流畅度，不重组结构"""
        # 直接将所有章节按顺序拼接
        all_content = "\n\n".join([ch["content"] for ch in self.chapters])
        
        # 调用 AI 优化衔接
        prompt = STEP2_POLISH_PROMPT.format(
            chapter_count=len(self.chapters),
            all_content=all_content,
            original_content=self.original_content[:5000] if self.original_content else "（无原始素材）"
        )
        
        try:
            logger.info(f"任务 {self.task_id} - Step 2: 优化衔接...")
            polished = await self.client.generate_content(prompt)
            
            if polished:
                result.merged_content = polished.strip()
                result.changes = "仅优化衔接和流畅度，未重组结构"
            else:
                # 降级：直接使用原内容
                result.merged_content = all_content
                result.changes = "优化失败，保留原内容"
                
        except Exception as e:
            logger.error(f"任务 {self.task_id} - Step 2 优化失败: {e}")
            result.merged_content = all_content
            result.changes = f"优化失败: {e}"
        
        return result
    
    async def _merge_multiple_chapters(
        self, 
        section_idx: int,
        section_title: str,
        source_contents: List[str],
        quotes: List[str],
        insights: List[str]
    ) -> str:
        """整合多个源章节为一个板块"""
        # 拼接源内容
        combined = "\n\n---\n\n".join(source_contents)
        
        # 构建整合提示词
        prompt = STEP2_MERGE_PROMPT.format(
            section_idx=section_idx,
            section_title=section_title,
            source_content=combined,
            quotes_to_keep="\n".join(quotes) if quotes else "（无）",
            insights_to_keep="\n".join(insights) if insights else "（无）"
        )
        
        try:
            merged = await self.client.generate_content(prompt)
            return merged.strip() if merged else ""
        except Exception as e:
            logger.error(f"板块 {section_idx} 整合失败: {e}")
            # 降级：直接拼接
            return f"## {section_idx}. {section_title}\n\n" + combined
    
    def _write_result(self, result: ProofreadingResult):
        """写入校对结果"""
        # 删除旧章节
        old_files = list(self.task_dir.glob("chapter_*.md"))
        for f in old_files:
            f.unlink()
        
        # 按新板块拆分并写入
        parts = re.split(r'\n(?=## \d+\.)', result.merged_content)
        new_chapter_count = 0
        for part in parts:
            part = part.strip()
            if not part:
                continue
            match = re.match(r'## (\d+)\.', part)
            if match:
                idx = int(match.group(1))
                new_path = self.task_dir / f"chapter_{idx}.md"
                new_path.write_text(part, encoding="utf-8")
                new_chapter_count += 1
        
        # 保存变更日志
        changes_path = self.task_dir / "proofreading_changes.md"
        changes_path.write_text(f"# 校对变更记录\n\n## 映射规划\n{result.mapping}\n\n## 变更摘要\n{result.changes}", encoding="utf-8")
        
        logger.info(f"任务 {self.task_id} - 已写入 {new_chapter_count} 个新板块")
    
    def generate_diagnosis_report(self) -> str:
        """生成诊断报告"""
        report_lines = [
            "# 校对诊断报告",
            "",
            f"## 基本信息",
            f"- 任务ID: {self.task_id}",
            f"- 来源类型: {self.source_type}",
            f"- 视频/文档URL: {self.video_url or '无'}",
            f"- 章节数量: {len(self.chapters)}",
            f"- 原始素材长度: {len(self.original_content)} 字符",
            "",
            "## 章节列表",
        ]
        
        for ch in self.chapters:
            quotes_count = len(ch.get('quotes', []))
            insights_count = len(ch.get('insights', []))
            report_lines.append(f"- 第{ch['index']}章: {ch['title']} (金句:{quotes_count}, 洞见:{insights_count})")
        
        report_lines.append("")
        report_lines.append("## 金句与洞见统计")
        total_quotes = sum(len(ch.get('quotes', [])) for ch in self.chapters)
        total_insights = sum(len(ch.get('insights', [])) for ch in self.chapters)
        report_lines.append(f"- 总金句数: {total_quotes}")
        report_lines.append(f"- 总洞见数: {total_insights}")
        
        return "\n".join(report_lines)
