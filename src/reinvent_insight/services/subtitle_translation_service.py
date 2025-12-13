"""
字幕翻译服务

将英文字幕分段翻译为中文，同时纠正机器生成字幕的错误。
使用 Gemini low thinking 模式进行高效翻译。
"""

import asyncio
import logging
import re
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from reinvent_insight.infrastructure.ai.model_config import get_model_client
from reinvent_insight.core import config as app_config
from reinvent_insight.domain.prompts.subtitle import build_translation_prompt, build_correction_prompt

logger = logging.getLogger(__name__)


@dataclass
class SubtitleCue:
    """字幕条目"""
    index: int
    start: str  # 原始时间戳格式
    end: str
    text: str
    translated_text: Optional[str] = None


class SubtitleTranslationService:
    """字幕翻译服务"""
    
    TASK_TYPE = "subtitle_translation"
    
    # 分片校验阈值
    CHUNK_QUALITY_THRESHOLD = 90.0  # 质量分低于此值触发修正
    MAX_CORRECTION_RETRIES = 2  # 最大修正重试次数
    
    def __init__(self):
        self._translation_config = self._load_translation_config()
        self._article_content: Optional[str] = None  # 文章上下文
    
    def _load_translation_config(self) -> Dict:
        """从配置文件加载翻译特定配置"""
        try:
            config_path = app_config.PROJECT_ROOT / "config" / "model_config.yaml"
            if not config_path.exists():
                logger.warning("配置文件不存在，使用默认值")
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'tasks' not in config_data:
                return {}
            
            task_config = config_data['tasks'].get(self.TASK_TYPE, {})
            return task_config.get('translation', {})
            
        except Exception as e:
            logger.warning(f"加载翻译配置失败，使用默认值: {e}")
            return {}
    
    @property
    def concurrent_delay(self) -> float:
        """并发调用间隔（秒）"""
        return self._translation_config.get('concurrent_delay', 1.0)
    
    @property
    def chunk_size(self) -> int:
        """每段翻译的最大字幕条数"""
        return self._translation_config.get('chunk_size', 50)
    
    @property
    def target_language(self) -> str:
        """目标语言"""
        return self._translation_config.get('target_language', '中文')
    
    @property
    def source_language(self) -> str:
        """源语言"""
        return self._translation_config.get('source_language', '英文')
    
    def parse_vtt(self, vtt_content: str) -> List[SubtitleCue]:
        """解析 VTT 字幕为结构化列表，自动去重滚动式字幕"""
        raw_cues = []
        lines = vtt_content.split('\n')
        i = 0
        
        # 跳过 WEBVTT 头部
        while i < len(lines) and '-->' not in lines[i]:
            i += 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            if '-->' in line:
                # 解析时间轴: 00:00:01.000 --> 00:00:04.000
                match = re.match(r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})', line)
                if match:
                    start = match.group(1)
                    end = match.group(2)
                    
                    # 收集字幕文本（可能多行）
                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        # 移除 HTML 标签
                        clean_line = re.sub(r'<[^>]+>', '', lines[i]).strip()
                        if clean_line:
                            text_lines.append(clean_line)
                        i += 1
                    
                    if text_lines:
                        raw_cues.append({
                            'start': start,
                            'end': end,
                            'text': ' '.join(text_lines)
                        })
                else:
                    i += 1
            else:
                i += 1
        
        # 去重滚动式字幕
        deduplicated = self._deduplicate_rolling_subtitles(raw_cues)
        
        # 生成最终字幕列表
        cues = []
        for idx, item in enumerate(deduplicated, 1):
            cues.append(SubtitleCue(
                index=idx,
                start=item['start'],
                end=item['end'],
                text=item['text']
            ))
        
        logger.info(f"字幕解析完成: 原始 {len(raw_cues)} 条 -> 去重后 {len(cues)} 条")
        return cues
    
    def _deduplicate_rolling_subtitles(self, raw_cues: List[Dict]) -> List[Dict]:
        """
        去重滚动式字幕
        
        YouTube 自动字幕有两种重叠模式：
        1. 前缀扩展："hello" -> "hello everyone" -> "hello everyone I'm"
        2. 后半段重叠："A and B" -> "B and C" (后一条以前一条的后半部分开头)
        
        策略：检测重叠部分，从后一条中移除重叠内容
        """
        if not raw_cues:
            return []
        
        MIN_OVERLAP = 15  # 最小重叠字符数
        
        result = []
        i = 0
        
        while i < len(raw_cues):
            current = raw_cues[i]
            current_text = current['text']
            
            # 检查是否与下一条有重叠
            if i + 1 < len(raw_cues):
                next_cue = raw_cues[i + 1]
                next_text = next_cue['text']
                
                # 检查前缀扩展：下一条以当前开头
                if next_text.startswith(current_text):
                    # 跳过当前，使用更完整的下一条，但继承当前的开始时间
                    raw_cues[i + 1] = {
                        'start': current['start'],  # 继承当前的开始时间
                        'end': next_cue['end'],
                        'text': next_text
                    }
                    i += 1
                    continue
                
                # 检查后半段重叠：当前的后半部分是下一条的前缀
                overlap = self._find_overlap(current_text, next_text, MIN_OVERLAP)
                if overlap:
                    # 保留当前，修改下一条移除重叠部分
                    result.append(current)
                    # 修改下一条，移除重叠前缀
                    raw_cues[i + 1] = {
                        'start': next_cue['start'],
                        'end': next_cue['end'],
                        'text': next_text[len(overlap):].strip()
                    }
                    i += 1
                    continue
            
            # 无重叠，直接保留
            result.append(current)
            i += 1
        
        # 过滤空字幕
        result = [c for c in result if c['text'].strip()]
        
        # 递归处理，直到没有更多可合并的
        if len(result) < len(raw_cues):
            return self._deduplicate_rolling_subtitles(result)
        
        return result
    
    def _find_overlap(self, text1: str, text2: str, min_overlap: int = 10) -> Optional[str]:
        """
        查找 text1 的后缀和 text2 的前缀的重叠部分
        
        例如：
        text1 = "hello everyone I'm SAA Ramis and I lead product for elastic load balancing and"
        text2 = "product for elastic load balancing and API Gateway"
        返回："product for elastic load balancing and"
        """
        # 从最长可能的重叠开始查找
        max_overlap = min(len(text1), len(text2))
        
        for length in range(max_overlap, min_overlap - 1, -1):
            suffix = text1[-length:]
            if text2.startswith(suffix):
                return suffix
        
        return None
    
    def set_article_context(self, article_content: str) -> None:
        """
        设置文章上下文，用于提供全局理解能力
        
        Args:
            article_content: 解读文章全文
        """
        self._article_content = article_content
        logger.info(f"已设置文章上下文，长度: {len(article_content)} 字符")
    
    def _build_translation_prompt(self, cues: List[SubtitleCue]) -> str:
        """
        构建翻译提示词
        
        输入格式带时间轴，让大模型直接合并并输出合并后的字幕
        """
        # 构建带时间轴的字幕文本
        subtitle_lines = []
        for cue in cues:
            subtitle_lines.append(f"{cue.start} --> {cue.end}")
            subtitle_lines.append(cue.text)
            subtitle_lines.append("")  # 空行分隔
        
        subtitle_text = '\n'.join(subtitle_lines)
        
        # 使用提示词模板
        return build_translation_prompt(
            subtitle_text=subtitle_text,
            source_language=self.source_language,
            target_language=self.target_language,
            article_content=self._article_content
        )
    
    def _parse_translation_response(self, response: str) -> List[SubtitleCue]:
        """解析大模型输出的合并后字幕（VTT格式）"""
        cues = []
        lines = response.strip().split('\n')
        i = 0
        index = 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 匹配时间轴: 00:00:00.480 --> 00:00:08.560
            if '-->' in line:
                match = re.match(r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})', line)
                if match:
                    start = match.group(1)
                    end = match.group(2)
                    
                    # 下一行是翻译内容
                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    if text_lines:
                        cues.append(SubtitleCue(
                            index=index,
                            start=start,
                            end=end,
                            text='',  # 原文不需要了
                            translated_text=' '.join(text_lines)
                        ))
                        index += 1
                else:
                    i += 1
            else:
                i += 1
        
        return cues

    def _diagnose_chunk_issues(
        self, 
        original_cues: List[SubtitleCue], 
        translated_cues: List[SubtitleCue]
    ) -> Tuple[str, float]:
        """
        诊断分片翻译问题，生成诊断报告
        
        校验逻辑：
        1. 检查翻译字幕的时间范围是否覆盖了原始字幕（允许合理合并）
        2. 检查是否有幻觉时间戳
        3. 检查是否有时间空洞
        4. 检查单条字幕时长是否超过10秒
        
        Args:
            original_cues: 原始字幕列表
            translated_cues: 翻译后字幕列表
            
        Returns:
            (诊断报告文本, 质量评分)
        """
        issues = []
        
        if not translated_cues:
            return "翻译结果为空", 0.0
        
        # 排序
        sorted_original = sorted(original_cues, key=lambda c: self._time_to_ms(c.start))
        sorted_translated = sorted(translated_cues, key=lambda c: self._time_to_ms(c.start))
        
        # 1. 检查每条原始字幕是否被翻译字幕覆盖（允许合并）
        uncovered_originals = []
        for orig in sorted_original:
            orig_start_ms = self._time_to_ms(orig.start)
            
            # 检查是否有翻译字幕覆盖这个时间点
            covered = False
            for trans in sorted_translated:
                trans_start_ms = self._time_to_ms(trans.start)
                trans_end_ms = self._time_to_ms(trans.end)
                
                # 如果原始字幕的起始时间在翻译字幕的时间范围内，认为被覆盖
                # 允许500ms的容差
                if trans_start_ms - 500 <= orig_start_ms <= trans_end_ms + 500:
                    covered = True
                    break
            
            if not covered:
                uncovered_originals.append(orig)
        
        if uncovered_originals:
            issues.append(
                f"### 问题1：原始字幕未被覆盖\n"
                f"以下原始字幕的时间段未被任何翻译字幕覆盖（共{len(uncovered_originals)}条）：\n" +
                "\n".join(f"- {c.start}: {c.text[:30]}..." if len(c.text) > 30 else f"- {c.start}: {c.text}" 
                          for c in uncovered_originals[:10]) +
                (f"\n- ...（还有{len(uncovered_originals)-10}条）" if len(uncovered_originals) > 10 else "")
            )
        
        # 2. 检测幻觉时间戳（翻译创造的时间戳不在原始字幕时间范围内）
        original_starts = {cue.start for cue in original_cues}
        hallucinated = []
        for trans in sorted_translated:
            if trans.start not in original_starts:
                # 检查这个时间戳是否接近某个原始时间戳（500ms容差）
                trans_start_ms = self._time_to_ms(trans.start)
                is_close = False
                for orig_start in original_starts:
                    if abs(self._time_to_ms(orig_start) - trans_start_ms) <= 500:
                        is_close = True
                        break
                if not is_close:
                    hallucinated.append(trans.start)
        
        if hallucinated:
            issues.append(
                f"### 问题2：幻觉时间戳\n"
                f"以下时间戳不在原始字幕中存在（共{len(hallucinated)}个）：\n" +
                "\n".join(f"- {t}" for t in hallucinated[:10]) +
                (f"\n- ...（还有{len(hallucinated)-10}个）" if len(hallucinated) > 10 else "")
            )
        
        # 3. 检测时间范围空洞（翻译字幕之间超过10秒的间隙，且原文有内容）
        gaps = []
        for i in range(len(sorted_translated) - 1):
            curr_end_ms = self._time_to_ms(sorted_translated[i].end)
            next_start_ms = self._time_to_ms(sorted_translated[i+1].start)
            gap_seconds = (next_start_ms - curr_end_ms) / 1000
            
            if gap_seconds > 10:
                # 检查原始字幕在这个时间段是否有内容
                has_original_content = False
                for orig in sorted_original:
                    orig_start_ms = self._time_to_ms(orig.start)
                    if curr_end_ms <= orig_start_ms <= next_start_ms:
                        has_original_content = True
                        break
                
                if has_original_content:
                    gaps.append({
                        'start': sorted_translated[i].end,
                        'end': sorted_translated[i+1].start,
                        'duration': gap_seconds
                    })
        
        if gaps:
            issues.append(
                f"### 问题3：时间范围空洞\n"
                f"以下时间段有原始字幕但无翻译覆盖（共{len(gaps)}处）：\n" +
                "\n".join(f"- {g['start']} ~ {g['end']} ({g['duration']:.1f}秒)" for g in gaps[:5]) +
                (f"\n- ...（还有{len(gaps)-5}处）" if len(gaps) > 5 else "")
            )
        
        # 4. 检测单条字幕时长超过10秒
        oversized_cues = []
        for trans in sorted_translated:
            start_ms = self._time_to_ms(trans.start)
            end_ms = self._time_to_ms(trans.end)
            duration_seconds = (end_ms - start_ms) / 1000
            if duration_seconds > 10:
                oversized_cues.append({
                    'start': trans.start,
                    'end': trans.end,
                    'duration': duration_seconds,
                    'text': trans.translated_text or trans.text
                })
        
        if oversized_cues:
            issues.append(
                f"### 问题4：单条字幕时长超过10秒\n"
                f"以下字幕持续时间过长，需要拆分（共{len(oversized_cues)}条）：\n" +
                "\n".join(f"- {c['start']} ~ {c['end']} ({c['duration']:.1f}秒): {c['text'][:20]}..." 
                          for c in oversized_cues[:5]) +
                (f"\n- ...（还有{len(oversized_cues)-5}条）" if len(oversized_cues) > 5 else "")
            )
        
        # 计算质量评分
        total_original = len(original_cues)
        covered_count = total_original - len(uncovered_originals)
        hallucination_penalty = len(hallucinated) * 0.5
        oversized_penalty = len(oversized_cues) * 2  # 超时字幕扣分更重
        
        if total_original > 0:
            quality_score = max(0, (covered_count / total_original * 100) - hallucination_penalty - oversized_penalty)
        else:
            quality_score = 100.0
        
        if not issues:
            return "无问题", quality_score
        
        return "\n\n".join(issues), quality_score
    
    def _time_to_ms(self, time_str: str) -> int:
        """时间戳转毫秒"""
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        h, m = int(parts[0]), int(parts[1])
        s_parts = parts[2].split('.')
        s = int(s_parts[0])
        ms = int(s_parts[1]) if len(s_parts) > 1 else 0
        return ((h * 60 + m) * 60 + s) * 1000 + ms
    
    def _format_cues_as_subtitle(self, cues: List[SubtitleCue], use_translated: bool = False) -> str:
        """将字幕列表格式化为字幕文本"""
        lines = []
        for cue in cues:
            lines.append(f"{cue.start} --> {cue.end}")
            text = cue.translated_text if use_translated and cue.translated_text else cue.text
            lines.append(text)
            lines.append("")
        return "\n".join(lines)
    
    async def _correct_chunk(
        self,
        original_cues: List[SubtitleCue],
        translated_cues: List[SubtitleCue],
        diagnosis_report: str,
        chunk_index: int
    ) -> List[SubtitleCue]:
        """
        修正有问题的分片翻译
        
        Args:
            original_cues: 原始字幕
            translated_cues: 之前的翻译结果
            diagnosis_report: 问题诊断报告
            chunk_index: 分片索引
            
        Returns:
            修正后的字幕列表
        """
        original_text = self._format_cues_as_subtitle(original_cues)
        previous_text = self._format_cues_as_subtitle(translated_cues, use_translated=True)
        
        correction_prompt = build_correction_prompt(
            diagnosis_report=diagnosis_report,
            original_subtitle=original_text,
            previous_translation=previous_text
        )
        
        try:
            client = get_model_client(self.TASK_TYPE)
            response = await client.generate_content(correction_prompt)
            corrected_cues = self._parse_translation_response(response)
            logger.info(f"片段 {chunk_index + 1} 修正完成，输出 {len(corrected_cues)} 条")
            return corrected_cues
        except Exception as e:
            logger.error(f"片段 {chunk_index + 1} 修正失败: {e}")
            return translated_cues  # 修正失败返回原结果

    def _cleanup_old_chunk_dirs(self) -> None:
        """清理老旧的分片目录，保留最新的 MAX_CHUNK_DIRS 个"""
        try:
            if not CHUNK_DEBUG_DIR.exists():
                return
            
            # 获取所有子目录，按修改时间排序
            dirs = [d for d in CHUNK_DEBUG_DIR.iterdir() if d.is_dir()]
            if len(dirs) <= MAX_CHUNK_DIRS:
                return
            
            # 按修改时间排序，最新的在前面
            dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            
            # 删除超出的目录
            for old_dir in dirs[MAX_CHUNK_DIRS:]:
                import shutil
                shutil.rmtree(old_dir)
                logger.info(f"清理老旧分片目录: {old_dir.name}")
        except Exception as e:
            logger.warning(f"清理分片目录失败: {e}")

    def _save_chunk_debug(
        self,
        video_id: str,
        chunk_index: int,
        original_cues: List[SubtitleCue],
        translated_cues: List[SubtitleCue],
        diagnosis_report: str,
        quality_score: float,
        retry_count: int = 0
    ) -> None:
        """
        保存分片调试文件
        
        保存位置: downloads/subtitles/chunks/{video_id}/
        """
        if not video_id:
            return
        
        try:
            # 确保基础目录存在
            CHUNK_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            
            # 清理老旧目录
            self._cleanup_old_chunk_dirs()
            
            chunk_dir = CHUNK_DEBUG_DIR / video_id
            chunk_dir.mkdir(parents=True, exist_ok=True)
            
            suffix = f"_retry{retry_count}" if retry_count > 0 else ""
            
            # 保存原始分片
            original_path = chunk_dir / f"chunk_{chunk_index:03d}_original.txt"
            original_path.write_text(
                self._format_cues_as_subtitle(original_cues),
                encoding="utf-8"
            )
            
            # 保存翻译分片
            translated_path = chunk_dir / f"chunk_{chunk_index:03d}_translated{suffix}.txt"
            translated_path.write_text(
                self._format_cues_as_subtitle(translated_cues, use_translated=True),
                encoding="utf-8"
            )
            
            # 保存诊断报告
            report_path = chunk_dir / f"chunk_{chunk_index:03d}_report{suffix}.txt"
            report_path.write_text(
                f"质量评分: {quality_score:.1f}\n\n{diagnosis_report}",
                encoding="utf-8"
            )
            
            logger.debug(f"分片 {chunk_index + 1} 调试文件已保存: {chunk_dir}")
        except Exception as e:
            logger.warning(f"保存分片调试文件失败: {e}")

    async def translate_chunk(self, cues: List[SubtitleCue], chunk_index: int, total_chunks: int, video_id: str = None) -> List[SubtitleCue]:
        """翻译一个字幕片段，返回合并后的字幕列表（含分片校验和修正）"""
        logger.info(f"翻译字幕片段 {chunk_index + 1}/{total_chunks}，输入 {len(cues)} 条")
        
        prompt = self._build_translation_prompt(cues)
        
        try:
            client = get_model_client(self.TASK_TYPE)
            response = await client.generate_content(prompt)
            
            # 解析大模型输出的合并后字幕
            translated_cues = self._parse_translation_response(response)
            
            logger.info(f"片段 {chunk_index + 1} 初次翻译完成，{len(cues)} 条 -> {len(translated_cues)} 条")
            
            # 分片级别校验
            diagnosis_report, quality_score = self._diagnose_chunk_issues(cues, translated_cues)
            logger.info(f"片段 {chunk_index + 1} 质量评分: {quality_score:.1f}")
            
            # 保存分片调试文件
            self._save_chunk_debug(
                video_id, chunk_index, cues, translated_cues,
                diagnosis_report, quality_score, retry_count=0
            )
            
            # 如果质量不达标，触发修正
            retry_count = 0
            while quality_score < self.CHUNK_QUALITY_THRESHOLD and retry_count < self.MAX_CORRECTION_RETRIES:
                retry_count += 1
                logger.warning(
                    f"片段 {chunk_index + 1} 质量不达标 ({quality_score:.1f} < {self.CHUNK_QUALITY_THRESHOLD})，"
                    f"进行第 {retry_count} 次修正"
                )
                logger.info(f"诊断报告:\n{diagnosis_report}")
                
                # 执行修正
                translated_cues = await self._correct_chunk(
                    cues, translated_cues, diagnosis_report, chunk_index
                )
                
                # 重新校验
                diagnosis_report, quality_score = self._diagnose_chunk_issues(cues, translated_cues)
                logger.info(f"片段 {chunk_index + 1} 修正后质量评分: {quality_score:.1f}")
                
                # 保存修正后的分片
                self._save_chunk_debug(
                    video_id, chunk_index, cues, translated_cues,
                    diagnosis_report, quality_score, retry_count=retry_count
                )
            
            if quality_score < self.CHUNK_QUALITY_THRESHOLD:
                logger.warning(
                    f"片段 {chunk_index + 1} 经过 {self.MAX_CORRECTION_RETRIES} 次修正仍未达标 "
                    f"({quality_score:.1f})，使用当前结果"
                )
            
            return translated_cues
            
        except Exception as e:
            logger.error(f"翻译片段 {chunk_index + 1} 失败: {e}")
            # 失败时保留原文
            for cue in cues:
                cue.translated_text = cue.text
            return cues
    
    async def translate_subtitles(
        self, 
        vtt_content: str,
        article_content: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        video_id: Optional[str] = None
    ) -> Tuple[List[SubtitleCue], str]:
        """
        翻译完整字幕
        
        Args:
            vtt_content: VTT 字幕内容
            article_content: 可选，解读文章全文（提供全局上下文理解）
            progress_callback: 进度回调函数，接收 (current, total) 参数
            video_id: 视频 ID（仅用于日志）
            
        Returns:
            (翻译后的字幕列表, 翻译后的 VTT 内容)
        """
        # 设置文章上下文
        if article_content:
            self.set_article_context(article_content)
        # 解析字幕
        cues = self.parse_vtt(vtt_content)
        
        if not cues:
            logger.warning("没有解析到字幕内容")
            return [], vtt_content
        
        logger.info(f"开始翻译字幕，共 {len(cues)} 条，分段大小: {self.chunk_size}")
        
        # 分段
        chunks = [cues[i:i + self.chunk_size] for i in range(0, len(cues), self.chunk_size)]
        total_chunks = len(chunks)
        
        logger.info(f"字幕分为 {total_chunks} 段进行并发翻译，间隔: {self.concurrent_delay}秒")
        
        # 并发翻译，每个任务间隔启动
        async def translate_with_delay(chunk: List[SubtitleCue], idx: int) -> Tuple[int, List[SubtitleCue]]:
            """带延迟的翻译任务"""
            # 根据索引计算延迟时间
            delay = idx * self.concurrent_delay
            if delay > 0:
                await asyncio.sleep(delay)
            
            result = await self.translate_chunk(chunk, idx, total_chunks, video_id=video_id)
            
            if progress_callback:
                try:
                    await progress_callback(idx + 1, total_chunks)
                except Exception:
                    pass
            
            return idx, result
        
        # 创建所有翻译任务
        tasks = [
            translate_with_delay(chunk, i) 
            for i, chunk in enumerate(chunks)
        ]
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 按索引顺序收集结果
        translated_cues = []
        for result in sorted(results, key=lambda x: x[0] if isinstance(x, tuple) else float('inf')):
            if isinstance(result, tuple):
                _, cue_list = result
                translated_cues.extend(cue_list)
            else:
                # 异常情况，记录错误
                logger.error(f"翻译任务异常: {result}")
        
        # 规范化时间轴，确保无重叠
        translated_cues = self._normalize_timeline(translated_cues)
        
        # 生成翻译后的 VTT
        translated_vtt = self._generate_vtt(translated_cues)
        
        logger.info(f"字幕翻译完成，共翻译 {len(translated_cues)} 条")
        
        return translated_cues, translated_vtt
    
    def _normalize_timeline(self, cues: List[SubtitleCue]) -> List[SubtitleCue]:
        """规范化时间轴，确保无重叠
        
        如果当前字幕的开始时间 < 上一条的结束时间，
        则将当前字幕的开始时间调整为上一条的结束时间
        """
        if not cues or len(cues) < 2:
            return cues
        
        def time_to_ms(time_str: str) -> int:
            """HH:MM:SS.mmm -> 毫秒"""
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            h, m = int(parts[0]), int(parts[1])
            s_parts = parts[2].split('.')
            s = int(s_parts[0])
            ms = int(s_parts[1]) if len(s_parts) > 1 else 0
            return ((h * 60 + m) * 60 + s) * 1000 + ms
        
        def ms_to_time(ms: int) -> str:
            """毫秒 -> HH:MM:SS.mmm"""
            h = ms // 3600000
            ms %= 3600000
            m = ms // 60000
            ms %= 60000
            s = ms // 1000
            ms %= 1000
            return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
        
        normalized = [cues[0]]
        prev_end_ms = time_to_ms(cues[0].end)
        
        for i in range(1, len(cues)):
            cue = cues[i]
            start_ms = time_to_ms(cue.start)
            end_ms = time_to_ms(cue.end)
            
            # 如果开始时间 < 上一条结束时间，调整开始时间
            if start_ms < prev_end_ms:
                start_ms = prev_end_ms
                # 确保结束时间 > 开始时间
                if end_ms <= start_ms:
                    end_ms = start_ms + 100  # 最小100ms
            
            normalized.append(SubtitleCue(
                index=cue.index,
                start=ms_to_time(start_ms),
                end=ms_to_time(end_ms),
                text=cue.text,
                translated_text=cue.translated_text
            ))
            prev_end_ms = end_ms
        
        logger.info(f"时间轴规范化完成，共 {len(normalized)} 条字幕")
        return normalized
    
    def _generate_vtt(self, cues: List[SubtitleCue]) -> str:
        """生成 VTT 格式字幕"""
        lines = ["WEBVTT", ""]
        
        for cue in cues:
            lines.append(f"{cue.start} --> {cue.end}")
            lines.append(cue.translated_text or cue.text)
            lines.append("")
        
        return '\n'.join(lines)
    
    def check_alignment_quality(
        self, 
        original_vtt: str, 
        translated_vtt: str,
        video_id: str = None
    ) -> Dict:
        """
        检查翻译后字幕与原始字幕的时间轴对齐质量
        
        Args:
            original_vtt: 原始字幕VTT内容
            translated_vtt: 翻译后字幕VTT内容
            video_id: 视频ID（用于日志）
            
        Returns:
            包含对齐质量统计的字典
        """
        import re
        
        def time_to_ms(t: str) -> int:
            h, m, rest = t.split(':')
            s, ms = rest.replace(',', '.').split('.')
            return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)
        
        def extract_start_times(vtt_content: str) -> List[str]:
            pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> \d{2}:\d{2}:\d{2}\.\d{3}'
            return re.findall(pattern, vtt_content)
        
        # 提取起始时间
        original_starts = extract_start_times(original_vtt)
        translated_starts = extract_start_times(translated_vtt)
        original_starts_set = set(original_starts)
        original_ms_list = sorted([time_to_ms(t) for t in original_starts])
        
        # 统计
        exact_match = 0
        fuzzy_match_500ms = 0
        fuzzy_match_2s = 0
        no_match = 0
        
        for t_start in translated_starts:
            if t_start in original_starts_set:
                exact_match += 1
            else:
                t_ms = time_to_ms(t_start)
                min_diff = min(abs(t_ms - o_ms) for o_ms in original_ms_list) if original_ms_list else float('inf')
                
                if min_diff <= 500:
                    fuzzy_match_500ms += 1
                elif min_diff <= 2000:
                    fuzzy_match_2s += 1
                else:
                    no_match += 1
        
        total = len(translated_starts)
        exact_rate = (exact_match / total * 100) if total else 0
        fuzzy_500_rate = ((exact_match + fuzzy_match_500ms) / total * 100) if total else 0
        fuzzy_2s_rate = ((exact_match + fuzzy_match_500ms + fuzzy_match_2s) / total * 100) if total else 0
        
        # 计算质量评分（满分100）
        # 精确匹配权重最高，偏移越大扣分越多
        quality_score = (
            exact_match * 1.0 +
            fuzzy_match_500ms * 0.8 +
            fuzzy_match_2s * 0.5 +
            no_match * 0.0
        ) / total * 100 if total else 0
        
        # 评级
        if quality_score >= 95:
            grade = "优秀 ⭐⭐⭐"
        elif quality_score >= 85:
            grade = "良好 ⭐⭐"
        elif quality_score >= 70:
            grade = "一般 ⭐"
        else:
            grade = "较差 ⚠️"
        
        result = {
            'original_count': len(original_starts),
            'translated_count': total,
            'exact_match': exact_match,
            'fuzzy_match_500ms': fuzzy_match_500ms,
            'fuzzy_match_2s': fuzzy_match_2s,
            'no_match': no_match,
            'exact_rate': exact_rate,
            'fuzzy_500_rate': fuzzy_500_rate,
            'fuzzy_2s_rate': fuzzy_2s_rate,
            'quality_score': quality_score,
            'grade': grade
        }
        
        # 输出详细日志报表
        vid_label = f"[{video_id}] " if video_id else ""
        logger.info(f"\n{'='*60}")
        logger.info(f"{vid_label}字幕翻译质量报表")
        logger.info(f"{'='*60}")
        logger.info(f"原始字幕条数: {len(original_starts)}")
        logger.info(f"翻译后条数:   {total}")
        logger.info(f"合并比例:     {len(original_starts)/total:.1f}:1" if total else "N/A")
        logger.info(f"-"*40)
        logger.info(f"精确匹配:     {exact_match} 条 ({exact_rate:.1f}%)")
        logger.info(f"500ms内偏移:  {fuzzy_match_500ms} 条")
        logger.info(f"2秒内偏移:    {fuzzy_match_2s} 条")
        logger.info(f"无法匹配:     {no_match} 条")
        logger.info(f"-"*40)
        logger.info(f"累计匹配率(500ms): {fuzzy_500_rate:.1f}%")
        logger.info(f"累计匹配率(2秒):   {fuzzy_2s_rate:.1f}%")
        logger.info(f"-"*40)
        logger.info(f"质量评分:     {quality_score:.1f}/100")
        logger.info(f"评级:         {grade}")
        logger.info(f"{'='*60}\n")
        
        return result


# 全局服务实例
_subtitle_translation_service: Optional[SubtitleTranslationService] = None

# 正在翻译中的任务跟踪
_translating_videos: set = set()

# 翻译缓存目录
TRANSLATED_SUBTITLE_DIR = app_config.SUBTITLE_DIR / "translated"
TRANSLATED_SUBTITLE_DIR.mkdir(exist_ok=True)

# 分片调试目录
CHUNK_DEBUG_DIR = app_config.SUBTITLE_DIR / "chunks"
CHUNK_DEBUG_DIR.mkdir(exist_ok=True)

# 最大保留分片目录数
MAX_CHUNK_DIRS = 10


def get_subtitle_translation_service() -> SubtitleTranslationService:
    """获取字幕翻译服务单例"""
    global _subtitle_translation_service
    if _subtitle_translation_service is None:
        _subtitle_translation_service = SubtitleTranslationService()
    return _subtitle_translation_service


def is_translating(video_id: str) -> bool:
    """检查是否正在翻译中"""
    return video_id in _translating_videos


def get_cached_translation(video_id: str) -> Optional[str]:
    """获取缓存的翻译字幕
    
    Returns:
        VTT 内容，如果不存在返回 None
    """
    cache_path = TRANSLATED_SUBTITLE_DIR / f"{video_id}.zh.vtt"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    return None


async def trigger_subtitle_translation(
    video_id: str,
    article_content: Optional[str] = None,
    force: bool = False
) -> bool:
    """触发字幕翻译（统一入口）
    
    逻辑：
    1. 查找已下载的字幕（任何语言）
    2. 如果是中文字幕，直接使用，跳过翻译
    3. 如果是英文字幕，进行翻译
    
    Args:
        video_id: YouTube 视频 ID
        article_content: 解读文章内容（作为翻译上下文）
        force: 是否强制重新翻译
        
    Returns:
        True 表示已触发或已完成，False 表示失败
    """
    if video_id in _translating_videos:
        logger.info(f"字幕正在翻译中: video_id={video_id}")
        return True
    
    # 检查缓存
    cache_path = TRANSLATED_SUBTITLE_DIR / f"{video_id}.zh.vtt"
    if not force and cache_path.exists():
        logger.info(f"翻译缓存已存在: video_id={video_id}")
        return True
    
    _translating_videos.add(video_id)
    logger.info(f"开始字幕翻译: video_id={video_id}")
    
    try:
        from reinvent_insight.infrastructure.media.youtube_downloader import SubtitleDownloader
        
        # 获取视频元数据
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()
        dl = SubtitleDownloader(video_url)
        
        success = await loop.run_in_executor(None, dl._fetch_metadata)
        if not success or not dl.metadata:
            logger.error(f"无法获取视频元数据: video_id={video_id}")
            return False
        
        sanitized_title = dl.metadata.sanitized_title
        
        # 查找字幕文件：优先中文，其次英文
        chinese_langs = ['zh-Hans', 'zh-CN', 'zh', 'zh-Hant', 'zh-TW']
        english_langs = ['en', 'en-US', 'en-GB']
        all_langs = chinese_langs + english_langs
        
        vtt_path = None
        found_lang = None
        
        for search_lang in all_langs:
            path = app_config.SUBTITLE_DIR / f"{sanitized_title}.{search_lang}.vtt"
            if path.exists():
                vtt_path = path
                found_lang = search_lang
                break
        
        if not vtt_path:
            # 尝试下载
            _, _, error = await loop.run_in_executor(None, dl.download)
            if error:
                logger.error(f"字幕下载失败: video_id={video_id}, error={error.message}")
                return False
            
            for search_lang in all_langs:
                path = app_config.SUBTITLE_DIR / f"{sanitized_title}.{search_lang}.vtt"
                if path.exists():
                    vtt_path = path
                    found_lang = search_lang
                    break
        
        if not vtt_path or not vtt_path.exists():
            logger.error(f"未找到字幕文件: video_id={video_id}")
            return False
        
        # 读取原始字幕
        original_vtt = vtt_path.read_text(encoding="utf-8")
        
        # 如果是中文字幕，直接使用，跳过翻译
        if found_lang in chinese_langs:
            logger.info(f"原始字幕已是中文 ({found_lang})，跳过翻译: video_id={video_id}")
            cache_path.write_text(original_vtt, encoding="utf-8")
            logger.info(f"已缓存中文字幕: video_id={video_id}")
            return True
        
        # 英文字幕，进行翻译
        logger.info(f"开始翻译 {found_lang} 字幕: video_id={video_id}")
        
        translation_service = get_subtitle_translation_service()
        _, translated_vtt = await translation_service.translate_subtitles(
            original_vtt,
            article_content=article_content,
            video_id=video_id
        )
        
        # 检查翻译质量并输出报表
        translation_service.check_alignment_quality(
            original_vtt, 
            translated_vtt,
            video_id=video_id
        )
        
        # 保存翻译缓存
        cache_path.write_text(translated_vtt, encoding="utf-8")
        logger.info(f"字幕翻译完成并缓存: video_id={video_id}")
        return True
        
    except Exception as e:
        logger.error(f"字幕翻译失败 video_id={video_id}: {e}", exc_info=True)
        return False
    finally:
        _translating_videos.discard(video_id)
