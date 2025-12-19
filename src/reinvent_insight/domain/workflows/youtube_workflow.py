"""YouTube 视频分析工作流实现"""

import os
import re
import logging
import asyncio
import json
from typing import List, Optional, Tuple, Dict
from pathlib import Path

from reinvent_insight.core import config
from reinvent_insight.core.utils import (
    parse_outline, 
    generate_toc_with_links,
    remove_parenthetical_english,
    extract_titles_from_outline,
    extract_content_type_info
)
from reinvent_insight.domain.workflows.base import AnalysisWorkflow
from reinvent_insight.infrastructure.media.youtube_downloader import VideoMetadata
# v2 prompt 模块
from prompt.v2 import (
    build_outline_prompt,
    build_chapter_prompt,
    build_conclusion_prompt,
    get_mode_config
)
from prompt.v2.deep_ultra import (
    DEDUPLICATION_INSTRUCTION_SEQUENTIAL,
    build_previous_context
)

logger = logging.getLogger(__name__)


class YouTubeAnalysisWorkflow(AnalysisWorkflow):
    """YouTube 视频分析工作流
    
    实现YouTube视频字幕的深度分析流程：
    1. 生成大纲（标题、引言、章节列表）
    2. 并发生成所有章节内容
    3. 生成结论（洞见和金句）
    4. 组装最终Markdown报告
    """
    
    async def _parse_outline_result(self, outline_content: str) -> Tuple[Optional[str], Optional[List[str]], Optional[str]]:
        """解析大纲生成结果
        
        Args:
            outline_content: 大纲内容
            
        Returns:
            (title, chapters, introduction)
        """
        title, chapters, introduction = parse_outline(outline_content)
        
        # 提取章节元数据（复用父类方法）
        self._extract_chapter_metadata(outline_content)
        
        return title, chapters, introduction
    
    async def _validate_chapter_count(self, chapters: List[str], outline_content: str):
        """验证章节数量（Ultra模式特殊处理）"""
        if self.is_ultra_mode and len(chapters) > 20:
            logger.warning(f"任务 {self.task_id} - Ultra模式章节数超出限制（{len(chapters)}章），重新生成大纲")
            await self._log(f"章节数过多（{len(chapters)}章），正在重新分析内容结构...")
            
            # 重新生成大纲
            outline_content = await self._generate_outline()
            if not outline_content:
                raise Exception("重新生成大纲失败")
            
            title, chapters_raw, introduction = await self._parse_outline_result(outline_content)
            if not title or not chapters_raw:
                raise Exception("解析大纲失败")
            
            chapters = [re.sub(r'[\[\]]', '', c).strip() for c in chapters_raw]
            
            # 如果还是超过20章，报错
            if len(chapters) > 20:
                raise Exception(f"Ultra模式章节数仍超过20（{len(chapters)}章），请检查内容结构")
    
    async def _generate_outline(self) -> str:
        """生成大纲（包含标题、引言、章节列表）"""
        await self._log("步骤 1/4: 正在分析内容结构...")
        
        # 确定内容
        if self.is_pdf:
            full_content = "[PDF文档内容请参见附件]"
        else:
            full_content = self.transcript
        
        # 使用 v2 prompt 构建函数
        mode = "ultra" if self.is_ultra_mode else "deep"
        prompt = build_outline_prompt(full_content, mode=mode)
        
        # 重试逻辑
        for attempt in range(self.max_retries + 1):
            try:
                # 根据内容类型选择调用方式
                if self.is_pdf and self.file_info:
                    # PDF 多模态：使用 generate_content_with_file
                    outline = await self.client.generate_content_with_file(prompt, self.file_info)
                else:
                    # 文本内容：使用普通的 generate_content
                    outline = await self.client.generate_content(prompt)
                
                if outline:
                    # 后处理：清理不必要的英文注释
                    outline = remove_parenthetical_english(outline)
                    
                    # 保存到任务目录
                    outline_path = os.path.join(self.task_dir, "outline.md")
                    with open(outline_path, "w", encoding="utf-8") as f:
                        f.write(outline)
                    
                    # 提取标题并发送到前端
                    try:
                        title_en, title_cn = extract_titles_from_outline(outline)
                        if title_en:
                            self.generated_title_en = title_en
                            logger.info(f"任务 {self.task_id} - 成功提取英文标题: {title_en}")
                        # 发送标题到前端进度窗口
                        if title_cn:
                            await self._log(f"标题: {title_cn}")
                    except Exception as e:
                        logger.warning(f"任务 {self.task_id} - 提取标题时出错: {e}")
                    
                    # 提取内容类型信息并发送到前端（v2 prompt 新功能）
                    try:
                        content_type, content_type_rationale = extract_content_type_info(outline)
                        if content_type:
                            await self._log(f"类型: {content_type}")
                            if content_type_rationale:
                                # 截取判断理由，简洁展示
                                rationale = content_type_rationale[:80] + ('...' if len(content_type_rationale) > 80 else '')
                                await self._log(f"理由: {rationale}")
                    except Exception as e:
                        logger.debug(f"任务 {self.task_id} - 提取内容类型失败: {e}")
                    
                    # 提取章节目录并发送到前端
                    try:
                        _, chapters_list, _ = parse_outline(outline)
                        if chapters_list and len(chapters_list) > 0:
                            await self._log(f"目录: 共 {len(chapters_list)} 章")
                            # 每章单独一行，最多展示8章
                            for i, ch in enumerate(chapters_list[:8], 1):
                                ch_title = ch[:35] + ('...' if len(ch) > 35 else '')
                                await self._log(f"  {i}. {ch_title}")
                            if len(chapters_list) > 8:
                                await self._log(f"  ... 等共 {len(chapters_list)} 章")
                    except Exception as e:
                        logger.debug(f"任务 {self.task_id} - 提取章节目录失败: {e}")
                    
                    await self._log("内容结构分析完成", progress=25)
                    return outline
                
                raise ValueError("模型返回了空内容")
            
            except Exception as e:
                logger.warning(f"任务 {self.task_id} - 生成大纲失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"任务 {self.task_id} - 生成大纲达到最大重试次数", exc_info=True)
                    raise e
                await self._log(f"正在重新尝试分析... ({attempt + 2}/{self.max_retries + 1})")
                await asyncio.sleep(2)
        
        return None
    
    async def _generate_single_chapter(
        self, 
        index: int, 
        chapter_title: str, 
        outline_content: str, 
        previous_chapters: List[Dict] = None,
        rationale: str = ""
    ) -> str:
        """生成单个章节内容
        
        Args:
            index: 章节索引（0-based）
            chapter_title: 章节标题
            outline_content: 完整大纲内容
            previous_chapters: 已生成的章节列表（顺序模式下使用，并发模式下为None）
            rationale: 该章节的详细生成指导
            
        Returns:
            章节内容（Markdown格式）
        """
        # 确定内容
        if self.is_pdf:
            full_content = "[PDF文档内容请参见附件]"
        else:
            full_content = self.transcript
        
        # 构建章节元数据
        chapter_meta = self._get_chapter_metadata(index + 1)
        subsections = chapter_meta.get('subsections', [])
        must_include = chapter_meta.get('must_include', [])
        must_exclude = chapter_meta.get('must_exclude', [])
        content_guidance = chapter_meta.get('content_guidance', f"本章节聚焦于'{chapter_title}'主题，请基于原文内容充分展开。")
        
        # 构建前序章节上下文
        previous_chapter = None
        previous_summaries = None
        
        if previous_chapters and len(previous_chapters) > 0:
            # 构建摘要列表
            previous_summaries = []
            for prev in previous_chapters:
                content_preview = prev.get('content', '')[:500]
                if len(prev.get('content', '')) > 500:
                    content_preview += '...'
                previous_summaries.append({
                    'index': prev.get('index', 0),
                    'title': prev.get('title', ''),
                    'summary': content_preview
                })
            
            # 最后一章完整内容
            last = previous_chapters[-1]
            previous_chapter = {
                'index': last.get('index', 0),
                'title': last.get('title', ''),
                'content': last.get('content', '')
            }
        
        # 使用 v2 prompt 构建函数
        prompt = build_chapter_prompt(
            full_content=full_content,
            full_outline=outline_content,
            chapter_number=index + 1,
            chapter_title=chapter_title,
            subsections=subsections,
            must_include=must_include,
            must_exclude=must_exclude,
            content_guidance=content_guidance,
            previous_chapter=previous_chapter,
            previous_summaries=previous_summaries
        )
        
        # 重试逻辑
        for attempt in range(self.max_retries + 1):
            try:
                # 根据内容类型选择调用方式
                # 章节生成使用 low thinking 模式以加快速度
                if self.is_pdf and self.file_info:
                    chapter_content = await self.client.generate_content_with_file(
                        prompt, self.file_info, thinking_level="low"
                    )
                else:
                    chapter_content = await self.client.generate_content(
                        prompt, thinking_level="low"
                    )
                
                if chapter_content:
                    # 后处理
                    chapter_content = remove_parenthetical_english(chapter_content)
                    
                    # 标题校验和修复
                    chapter_content = self._fix_chapter_title(
                        chapter_content, 
                        index + 1, 
                        chapter_title
                    )
                    
                    # 保存到任务目录
                    chapter_path = os.path.join(self.task_dir, f"chapter_{index + 1}.md")
                    with open(chapter_path, "w", encoding="utf-8") as f:
                        f.write(chapter_content)
                    
                    return chapter_content
                
                raise ValueError("模型返回了空内容")
            
            except Exception as e:
                logger.warning(
                    f"任务 {self.task_id} - 生成章节 '{chapter_title}' 失败 "
                    f"(尝试 {attempt + 1}/{self.max_retries + 1}): {e}"
                )
                if attempt == self.max_retries:
                    logger.error(f"任务 {self.task_id} - 生成章节达到最大重试次数", exc_info=True)
                    raise e
                await asyncio.sleep(2)
        
        return None
    
    def _fix_chapter_title(self, chapter_content: str, chapter_num: int, expected_title: str) -> str:
        """修复章节标题格式
        
        确保章节标题格式为: ### {chapter_num}. {title} (H3)
        """
        lines = chapter_content.split('\n')
        if not lines:
            return chapter_content
        
        first_line = lines[0].strip()
        expected_pattern = f"### {chapter_num}. {expected_title}"
        
        # 检查第一行是否符合预期
        if first_line != expected_pattern:
            # 尝试修复
            if first_line.startswith('#'):
                # 替换第一行
                lines[0] = expected_pattern
                logger.info(f"修复章节标题: {first_line} -> {expected_pattern}")
            else:
                # 插入正确的标题
                lines.insert(0, expected_pattern)
                logger.info(f"插入章节标题: {expected_pattern}")
            
            return '\n'.join(lines)
        
        return chapter_content
    
    async def _generate_conclusion(self, chapters: List[str]) -> str:
        """生成结论（洞见和金句）
        
        Args:
            chapters: 章节标题列表
            
        Returns:
            结论内容（包含洞见延伸和金句）
        """
        await self._log("步骤 3/4: 正在提炼核心洞见...")
        
        # 读取所有章节内容
        all_chapters_content = []
        for i in range(len(chapters)):
            try:
                chapter_path = os.path.join(self.task_dir, f"chapter_{i + 1}.md")
                with open(chapter_path, "r", encoding="utf-8") as f:
                    all_chapters_content.append(f.read())
            except FileNotFoundError:
                logger.error(f"任务 {self.task_id} - 未找到章节文件: chapter_{i + 1}.md")
                raise
        
        full_chapters_text = "\n\n".join(all_chapters_content)
        
        # 确定内容
        if self.is_pdf:
            full_content = "[PDF文档内容请参见附件]"
        else:
            full_content = self.transcript
        
        # 使用 v2 prompt 构建函数
        prompt = build_conclusion_prompt(
            full_content=full_content,
            all_generated_chapters=full_chapters_text
        )
        
        # 重试逻辑
        for attempt in range(self.max_retries + 1):
            try:
                # 根据内容类型选择调用方式
                if self.is_pdf and self.file_info:
                    conclusion_content = await self.client.generate_content_with_file(prompt, self.file_info)
                else:
                    conclusion_content = await self.client.generate_content(prompt)
                
                if conclusion_content:
                    # 后处理
                    conclusion_content = remove_parenthetical_english(conclusion_content)
                    
                    # 保存到任务目录
                    conclusion_path = os.path.join(self.task_dir, "conclusion.md")
                    with open(conclusion_path, "w", encoding="utf-8") as f:
                        f.write(conclusion_content)
                    
                    await self._log("核心洞见提炼完成", progress=90)
                    return conclusion_content
                
                raise ValueError("模型返回了空内容")
            
            except Exception as e:
                logger.warning(
                    f"任务 {self.task_id} - 生成结论失败 "
                    f"(尝试 {attempt + 1}/{self.max_retries + 1}): {e}"
                )
                if attempt == self.max_retries:
                    logger.error(f"任务 {self.task_id} - 生成结论达到最大重试次数", exc_info=True)
                    raise e
                await asyncio.sleep(2)
        
        return None
    
    async def _assemble_final_report(
        self, 
        title: str, 
        introduction: str, 
        toc_md: str, 
        conclusion_content: str, 
        chapter_count: int, 
        metadata: VideoMetadata
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """组装最终报告
        
        Args:
            title: 文章标题
            introduction: 引言
            toc_md: 目录（Markdown格式，带链接）
            conclusion_content: 结论内容
            chapter_count: 章节数量
            metadata: 视频元数据
            
        Returns:
            (final_report, final_filename, doc_hash)
        """
        await self._log("步骤 4/4: 正在整理最终报告...")
        
        try:
            import yaml
            import shutil
            from datetime import datetime
            from reinvent_insight.infrastructure.media.youtube_downloader import sanitize_filename
            from reinvent_insight.core.utils.file_utils import generate_doc_hash
            
            # 读取所有章节内容
            chapter_contents = []
            for i in range(chapter_count):
                chapter_path = os.path.join(self.task_dir, f"chapter_{i + 1}.md")
                with open(chapter_path, 'r', encoding='utf-8') as f:
                    chapter_contents.append(f.read().strip())
            
            # 解析 conclusion_content，提取洞见延伸和金句部分
            insights = ""
            quotes = ""
            
            if conclusion_content:
                conclusion_parts = re.split(r'\n###\s+', '\n' + conclusion_content)
                for part in conclusion_parts:
                    part = part.strip()
                    if not part:
                        continue
                    full_part = "### " + part
                    part_lower = part.lower()
                    if '洞见' in part_lower and '延伸' in part_lower:
                        insights = full_part
                    elif '金句' in part_lower or ('原声' in part_lower and '引用' in part_lower):
                        quotes = full_part
            
            # 生成 YAML front matter
            # 根据内容类型选择标识符字段
            source_id = getattr(metadata, 'content_identifier', None) or metadata.video_url
            is_document = bool(getattr(metadata, 'content_identifier', None))
            
            yaml_data = {
                'title_cn': title,
                'upload_date': metadata.upload_date,
                'created_at': datetime.now().isoformat(),
                'chapter_count': chapter_count,
            }
            
            # 根据类型设置不同的标识符字段
            if is_document:
                yaml_data['content_identifier'] = source_id  # 文档类型
            else:
                yaml_data['video_url'] = source_id  # 视频类型
            
            # 添加可选字段
            # 标题优先级逻辑：
            # - 文档类型：AI 生成的英文标题优先（因为 metadata.title 只是文件名）
            # - 视频类型：原始标题优先（YouTube 视频有真实标题）
            if is_document:
                # 文档类型：AI 生成的英文标题优先
                if self.generated_title_en:
                    yaml_data['title_en'] = self.generated_title_en
                elif hasattr(metadata, 'title') and metadata.title:
                    yaml_data['title_en'] = metadata.title  # 降级使用文件名
            else:
                # 视频类型：原始标题优先
                if hasattr(metadata, 'title') and metadata.title:
                    yaml_data['title_en'] = metadata.title
                elif self.generated_title_en:
                    yaml_data['title_en'] = self.generated_title_en
            if hasattr(metadata, 'is_reinvent'):
                yaml_data['is_reinvent'] = metadata.is_reinvent
            if hasattr(metadata, 'course_code') and metadata.course_code:
                yaml_data['course_code'] = metadata.course_code
            if hasattr(metadata, 'level') and metadata.level:
                yaml_data['level'] = metadata.level
            
            # Ultra模式特殊处理
            new_version = 0
            if self.is_ultra_mode and self.target_version is not None:
                new_version = self.target_version
                yaml_data['version'] = new_version
                yaml_data['is_ultra_deep'] = True
                yaml_data['base_version'] = new_version - 1
            else:
                # 标准模式：检查是否已存在
                existing_version = 0
                if config.OUTPUT_DIR.exists():
                    for md_file in config.OUTPUT_DIR.glob("*.md"):
                        try:
                            content = md_file.read_text(encoding="utf-8")
                            match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                            if match:
                                file_metadata = yaml.safe_load(match.group(1))
                                # 检查 content_identifier 或 video_url
                                file_source_id = file_metadata.get('content_identifier') or file_metadata.get('video_url')
                                if file_source_id == source_id:
                                    file_version = file_metadata.get('version', 0)
                                    existing_version = max(existing_version, file_version)
                        except:
                            pass
                new_version = existing_version + 1
                yaml_data['version'] = new_version
            
            # 生成文档哈希
            doc_hash = generate_doc_hash(source_id)
            yaml_data['hash'] = doc_hash
            
            # 组装 YAML front matter
            metadata_yaml = "---\n" + yaml.dump(yaml_data, allow_unicode=True, sort_keys=False).rstrip() + "\n---"
            
            # 组装最终报告
            final_report_parts = [
                metadata_yaml,
                f"# {title}",
                f"### 引言\n{introduction}" if introduction else "",
                toc_md,
                "\n\n---\n\n".join(chapter_contents),
                insights,
                quotes
            ]
            
            final_report = "\n\n".join(part for part in final_report_parts if part and part.strip())
            
            # 生成文件名
            # 文档类型：AI 生成标题优先；视频类型：原始标题优先
            if is_document:
                if self.generated_title_en:
                    base_name = sanitize_filename(self.generated_title_en)
                elif hasattr(metadata, 'title') and metadata.title:
                    base_name = sanitize_filename(metadata.title)
                else:
                    base_name = sanitize_filename(title)
            else:
                if hasattr(metadata, 'title') and metadata.title:
                    base_name = sanitize_filename(metadata.title)
                elif self.generated_title_en:
                    base_name = sanitize_filename(self.generated_title_en)
                else:
                    base_name = sanitize_filename(title)
            
            final_filename = f"{base_name}_v{new_version}.md"
            
            # 保存到任务目录
            temp_report_path = os.path.join(self.task_dir, "final_report.md")
            with open(temp_report_path, "w", encoding="utf-8") as f:
                f.write(final_report)
            
            # 移动到最终目录
            final_path = config.OUTPUT_DIR / final_filename
            config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(temp_report_path, final_path)
            
            logger.info(f"报告已保存到: {final_path}")
            
            return final_report, final_filename, doc_hash
        
        except Exception as e:
            logger.error(f"任务 {self.task_id} - 组装最终报告失败: {e}", exc_info=True)
            raise
