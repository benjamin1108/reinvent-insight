"""
自适应深度摘要工作流模块

该模块实现了集成长度自适应功能的深度摘要工作流，包括：
- AdaptiveDeepSummaryWorkflow类：继承现有工作流并集成自适应功能
- 视频分析和长度计算的集成
- 动态提示词生成的集成
- 长度监控和调整的集成
- 详细的日志记录和用户反馈
"""

import os
import asyncio
from typing import Optional, List, Tuple
from pathlib import Path
from datetime import datetime

from loguru import logger

from .workflow import DeepSummaryWorkflow, parse_outline, generate_toc_with_links
from .downloader import VideoMetadata
from .adaptive_length import (
    VideoAnalyzer, LengthCalculator, LengthMonitor, LengthConfigManager,
    VideoAnalysisResult, LengthTarget, LengthStatus
)
from .dynamic_prompt_generator import DynamicPromptGenerator, create_dynamic_prompt_generator
from .task_manager import manager as task_manager
from . import prompts

logger = logger.bind(name=__name__)


class AdaptiveDeepSummaryWorkflow(DeepSummaryWorkflow):
    """
    自适应深度摘要工作流类
    
    继承现有的DeepSummaryWorkflow类，集成长度自适应功能，
    包括视频分析、长度计算、动态提示词生成和长度监控。
    """
    
    def __init__(self, task_id: str, model_name: str, transcript: str, video_metadata: VideoMetadata):
        """
        初始化自适应工作流
        
        Args:
            task_id: 任务ID
            model_name: 模型名称
            transcript: 视频字幕文本
            video_metadata: 视频元数据
        """
        # 调用父类初始化
        super().__init__(task_id, model_name, transcript, video_metadata)
        
        # 初始化自适应组件
        self.video_analyzer = VideoAnalyzer()
        self.length_config_manager = LengthConfigManager()
        self.length_calculator = LengthCalculator(self.length_config_manager.config)
        
        # 分析视频并计算目标长度
        self.analysis_result: Optional[VideoAnalysisResult] = None
        self.length_target: Optional[LengthTarget] = None
        self.length_monitor: Optional[LengthMonitor] = None
        self.prompt_generator: Optional[DynamicPromptGenerator] = None
        
        # 执行初始分析
        self._initialize_adaptive_components()
        
        logger.info(f"自适应工作流初始化完成 - 任务ID: {task_id}")
    
    def _initialize_adaptive_components(self):
        """初始化自适应组件"""
        try:
            # 分析视频特征
            self.analysis_result = self.video_analyzer.analyze(self.metadata, self.transcript)
            
            # 计算目标长度
            self.length_target = self.length_calculator.calculate_target_length(self.analysis_result)
            
            # 初始化长度监控器
            self.length_monitor = LengthMonitor(self.length_target, self.task_id)
            
            # 创建动态提示词生成器
            self.prompt_generator = create_dynamic_prompt_generator(self.length_target)
            
            logger.info(f"自适应组件初始化成功 - 目标长度: {self.length_target.target_length}字, "
                       f"章节数: {self.length_target.chapter_count}")
            
            # 更新任务管理器的自适应状态
            task_manager.set_adaptive_enabled(self.task_id, True)
            task_manager.set_video_analysis(self.task_id, {
                "duration_minutes": self.analysis_result.duration_minutes,
                "video_category": self.analysis_result.video_category,
                "subtitle_word_count": self.analysis_result.subtitle_word_count,
                "words_per_minute": self.analysis_result.words_per_minute,
                "density_level": self.analysis_result.density_level,
                "complexity_score": self.analysis_result.complexity_score
            })
            task_manager.set_length_target(self.task_id, {
                "target_length": self.length_target.target_length,
                "min_length": self.length_target.min_length,
                "max_length": self.length_target.max_length,
                "chapter_count": self.length_target.chapter_count,
                "avg_chapter_length": self.length_target.avg_chapter_length
            })
            
        except Exception as e:
            logger.error(f"自适应组件初始化失败: {e}")
            # 如果初始化失败，设置为None，工作流将回退到标准模式
            self.analysis_result = None
            self.length_target = None
            self.length_monitor = None
            self.prompt_generator = None
            task_manager.set_adaptive_enabled(self.task_id, False)
    
    async def run(self):
        """执行完整的自适应深度摘要工作流"""
        try:
            await self._log("正在启动自适应深度分析流程...")
            task_manager.tasks[self.task_id].status = "running"
            
            # 记录自适应分析结果
            if self.analysis_result and self.length_target:
                await self._log_adaptive_analysis()
            else:
                await self._log("自适应功能未启用，使用标准工作流", error=False)
                # 回退到父类的标准工作流
                return await super().run()
            
            # 步骤 1: 生成大纲（使用自适应提示词）
            outline_content = await self._generate_outline()
            if not outline_content:
                raise Exception("生成大纲失败")

            title, chapters_raw, introduction = parse_outline(outline_content)
            if not title or not chapters_raw:
                raise Exception("解析大纲失败")
            
            # 清理章节标题
            chapters = [chapter.strip() for chapter in chapters_raw]
            
            # 验证章节数量是否符合预期
            expected_chapters = self.length_target.chapter_count
            actual_chapters = len(chapters)
            if actual_chapters != expected_chapters:
                await self._log(f"章节数量不符合预期: 预期{expected_chapters}个，实际{actual_chapters}个", 
                               error=False)
                # 调整长度目标以匹配实际章节数
                self._adjust_length_target_for_chapters(actual_chapters)

            await self._log(f"成功生成标题和 {len(chapters)} 个章节的分析框架")
            
            # 生成带链接的目录
            toc_md = generate_toc_with_links(chapters)

            # 步骤 2: 并行生成章节内容（使用自适应提示词和长度监控）
            success = await self._generate_chapters_parallel_adaptive(chapters, title, outline_content)
            if not success:
                raise Exception("部分或全部章节内容生成失败")
            
            # 步骤 3: 生成洞见和金句（使用自适应提示词）
            conclusion_content = await self._generate_conclusion_adaptive(chapters)
            if not conclusion_content:
                raise Exception("生成收尾内容失败")
            
            # 步骤 4: 组装最终报告
            final_report, final_filename, doc_hash = await self._assemble_final_report(
                title, introduction, toc_md, conclusion_content, len(chapters), self.metadata
            )
            if not final_report:
                raise Exception("组装最终报告失败")

            # 记录最终长度统计
            await self._log_final_length_statistics(final_report)

            await self._log("自适应分析完成！", progress=100)
            await task_manager.send_result(title, final_report, self.task_id, final_filename, doc_hash)

        except Exception as e:
            error_message = f"自适应工作流遇到严重错误: {e}"
            logger.error(f"任务 {self.task_id} - {error_message}", exc_info=True)
            await task_manager.set_task_error(self.task_id, "分析过程中出现错误，请稍后重试")
    
    async def _log_adaptive_analysis(self):
        """记录自适应分析结果"""
        if not self.analysis_result or not self.length_target:
            return
        
        analysis_info = (
            f"视频分析完成:\n"
            f"  - 视频时长: {self.analysis_result.duration_minutes:.1f} 分钟\n"
            f"  - 视频类别: {self.analysis_result.video_category}\n"
            f"  - 字幕字数: {self.analysis_result.subtitle_word_count:,} 字\n"
            f"  - 信息密度: {self.analysis_result.words_per_minute:.1f} 字/分钟 ({self.analysis_result.density_level})\n"
            f"  - 复杂度评分: {self.analysis_result.complexity_score:.2f}"
        )
        
        length_info = (
            f"长度目标设定:\n"
            f"  - 目标长度: {self.length_target.target_length:,} 字\n"
            f"  - 长度范围: {self.length_target.min_length:,} - {self.length_target.max_length:,} 字\n"
            f"  - 章节数量: {self.length_target.chapter_count} 个\n"
            f"  - 平均章节长度: {self.length_target.avg_chapter_length:,} 字"
        )
        
        await self._log(f"{analysis_info}\n\n{length_info}")
    
    def _adjust_length_target_for_chapters(self, actual_chapter_count: int):
        """根据实际章节数调整长度目标"""
        if not self.length_target:
            return
        
        # 重新计算平均章节长度
        new_avg_chapter_length = self.length_target.target_length // actual_chapter_count
        
        # 更新长度目标
        self.length_target.chapter_count = actual_chapter_count
        self.length_target.avg_chapter_length = new_avg_chapter_length
        
        # 重新初始化长度监控器
        self.length_monitor = LengthMonitor(self.length_target, self.task_id)
        
        logger.info(f"长度目标已调整: 章节数={actual_chapter_count}, "
                   f"平均章节长度={new_avg_chapter_length}")
    
    async def _generate_outline(self) -> Optional[str]:
        """生成大纲（使用自适应提示词）"""
        await self._log("步骤 1/4: 正在分析视频内容结构...")
        
        if self.prompt_generator:
            # 使用自适应提示词
            prompt = self.prompt_generator.generate_outline_prompt(self.transcript)
        else:
            # 回退到标准提示词
            prompt = prompts.OUTLINE_PROMPT_TEMPLATE.format(
                base_prompt=self.base_prompt,
                full_transcript=self.transcript
            )
        
        for attempt in range(self.max_retries + 1):
            try:
                outline = await self.summarizer.generate_content(prompt)
                if outline:
                    outline_path = os.path.join(self.task_dir, "outline.md")
                    with open(outline_path, "w", encoding="utf-8") as f:
                        f.write(outline)
                    await self._log("内容结构分析完成", progress=25)
                    return outline
                
                raise ValueError("模型返回了空内容")

            except Exception as e:
                logger.warning(f"任务 {self.task_id} - 生成大纲失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"任务 {self.task_id} - 生成大纲达到最大重试次数，失败。", exc_info=True)
                    raise e
                await self._log(f"正在重新尝试分析... ({attempt + 2}/{self.max_retries + 1})")
                await asyncio.sleep(2)
        return None
    
    async def _generate_chapters_parallel_adaptive(self, chapters: List[str], title: str, 
                                                 outline_content: str) -> bool:
        """并行生成所有章节的内容（使用自适应提示词和长度监控）"""
        await self._log(f"步骤 2/4: 正在深度分析 {len(chapters)} 个核心章节...")

        tasks = []
        for i, chapter_title in enumerate(chapters):
            task = self._generate_single_chapter_adaptive(i, chapter_title, outline_content)
            tasks.append(task)
            # 在启动每个任务后，增加一个固定的延迟
            await asyncio.sleep(0.5)  # 减少延迟，因为我们有长度监控
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_chapters = 0
        for i, result in enumerate(results):
            if isinstance(result, str):
                successful_chapters += 1
                logger.info(f"任务 {self.task_id} - 章节 '{chapters[i]}' 已成功生成。")
            else:
                logger.error(f"任务 {self.task_id} - 生成章节 '{chapters[i]}' 失败: {result}", 
                           exc_info=result)
        
        progress = 25 + int(50 * (successful_chapters / len(chapters)))
        await self._log(f"章节分析完成（{successful_chapters}/{len(chapters)}）", progress=progress)

        return successful_chapters == len(chapters)
    
    async def _generate_single_chapter_adaptive(self, index: int, chapter_title: str, 
                                              outline_content: str) -> str:
        """为单个章节生成内容（使用自适应提示词和长度监控）"""
        if self.prompt_generator:
            # 使用自适应提示词
            prompt = self.prompt_generator.generate_chapter_prompt(
                index + 1, chapter_title, outline_content, self.transcript
            )
        else:
            # 回退到标准提示词
            prompt = prompts.CHAPTER_PROMPT_TEMPLATE.format(
                base_prompt=self.base_prompt,
                full_transcript=self.transcript,
                full_outline=outline_content,
                chapter_number=index + 1,
                current_chapter_title=chapter_title
            )

        for attempt in range(self.max_retries + 1):
            try:
                chapter_content = await self.summarizer.generate_content(prompt)
                
                if not chapter_content or not chapter_content.strip():
                    raise ValueError("模型返回了空内容")

                # 标题校验和修复逻辑（继承自父类）
                chapter_content = self._fix_chapter_title(chapter_content, index, chapter_title)
                
                # 长度监控和调整建议
                if self.length_monitor:
                    status = self.length_monitor.monitor_chapter(chapter_content, index, chapter_title)
                    await self._log_length_monitoring(status, index + 1, chapter_title)
                    
                    # 如果需要调整，记录调整建议
                    if status.adjustment_needed:
                        recommendation = self.length_monitor.get_adjustment_recommendation(status)
                        await self._log(f"章节{index + 1}长度调整建议: {recommendation['strategy']}", 
                                       error=False)
                    
                    # 发送实时长度更新到任务管理器
                    await self._send_length_update(status, index + 1)

                # 保存章节内容
                chapter_path = os.path.join(self.task_dir, f"chapter_{index + 1}.md")
                with open(chapter_path, "w", encoding="utf-8") as f:
                    f.write(chapter_content)
                
                return chapter_content
                
            except Exception as e:
                logger.warning(f"任务 {self.task_id} - 生成章节 '{chapter_title}' 失败 "
                             f"(尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    raise e
                await asyncio.sleep(2 * (attempt + 1))
        
        raise RuntimeError(f"未能为章节 '{chapter_title}' 生成内容。")
    
    def _fix_chapter_title(self, chapter_content: str, index: int, chapter_title: str) -> str:
        """修复章节标题格式（继承自父类逻辑）"""
        import re
        
        # 移除 chapter_title 中可能存在的 Markdown 链接语法
        clean_chapter_title = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', chapter_title).strip()
        
        expected_title_prefix = f"### {index + 1}. {clean_chapter_title}"
        
        # 为了稳健比较，将实际内容的第一行提取出来处理
        content_lines = chapter_content.strip().split('\n')
        first_line = content_lines[0].strip()
        
        # 如果第一行不是以 '###' 开头，或者与预期的标题不符
        if not first_line.startswith("###") or \
           not first_line.lstrip('# ').lstrip(f"{index + 1}.").strip().startswith(clean_chapter_title):
            
            logger.warning(
                f"任务 {self.task_id} - 章节 '{chapter_title}' 的标题格式不正确。 "
                f"预期开头: '{expected_title_prefix}', "
                f"实际开头: '{first_line}'. "
                "正在自动修复..."
            )
            # 移除可能存在的错误标题
            if first_line.startswith("###"):
                chapter_content = '\n'.join(content_lines[1:]).lstrip()

            # 添加正确的标题
            chapter_content = f"{expected_title_prefix}\n\n{chapter_content}"
        
        return chapter_content
    
    async def _log_length_monitoring(self, status: LengthStatus, chapter_num: int, chapter_title: str):
        """记录长度监控信息"""
        # 基础监控信息
        monitoring_info = (
            f"章节{chapter_num}长度监控:\n"
            f"  - 当前章节: {len(chapter_title)} 字符标题\n"
            f"  - 累计长度: {status.current_length:,} 字\n"
            f"  - 进度: {status.progress_ratio:.1%}\n"
            f"  - 预测最终长度: {status.predicted_final_length:,} 字\n"
            f"  - 目标偏差: {status.deviation_ratio:+.1%}"
        )
        
        if status.adjustment_needed:
            monitoring_info += f"\n  - 调整建议: {status.adjustment_type}"
        
        await self._log(monitoring_info, error=False)
    
    async def _send_length_update(self, status: LengthStatus, chapter_num: int):
        """发送长度更新到任务管理器"""
        if not self.length_monitor:
            return
        
        # 获取监控摘要
        monitoring_summary = self.length_monitor.get_monitoring_summary()
        
        # 构建长度更新数据
        length_data = {
            "chapter_completed": chapter_num,
            "current_length": status.current_length,
            "target_length": status.target_length,
            "progress_ratio": status.progress_ratio,
            "deviation_ratio": status.deviation_ratio,
            "predicted_final_length": status.predicted_final_length,
            "adjustment_needed": status.adjustment_needed,
            "adjustment_type": status.adjustment_type,
            "monitoring_summary": monitoring_summary
        }
        
        # 更新任务管理器的长度统计
        task_manager.update_length_statistics(self.task_id, length_data)
        
        # 发送实时更新
        await task_manager.send_length_update(self.task_id, length_data)
    
    async def _generate_conclusion_adaptive(self, chapters: List[str]) -> Optional[str]:
        """生成洞见和金句（使用自适应提示词）"""
        await self._log("步骤 3/4: 正在提炼核心洞见...")

        # 从文件中读取所有章节内容
        all_chapters_content = []
        for i in range(len(chapters)):
            try:
                chapter_path = os.path.join(self.task_dir, f"chapter_{i + 1}.md")
                with open(chapter_path, "r", encoding="utf-8") as f:
                    all_chapters_content.append(f.read())
            except FileNotFoundError:
                logger.error(f"任务 {self.task_id} - 未找到章节文件: chapter_{i + 1}.md")
                return None
        
        full_chapters_text = "\n\n".join(all_chapters_content)

        if self.prompt_generator:
            # 使用自适应提示词
            prompt = self.prompt_generator.generate_conclusion_prompt(self.transcript, full_chapters_text)
        else:
            # 回退到标准提示词
            prompt = prompts.CONCLUSION_PROMPT_TEMPLATE.format(
                base_prompt=self.base_prompt,
                full_transcript=self.transcript,
                all_generated_chapters=full_chapters_text
            )

        for attempt in range(self.max_retries + 1):
            try:
                conclusion_content = await self.summarizer.generate_content(prompt)
                if conclusion_content:
                    conclusion_path = os.path.join(self.task_dir, "conclusion.md")
                    with open(conclusion_path, "w", encoding="utf-8") as f:
                        f.write(conclusion_content)
                    await self._log("核心洞见提炼完成", progress=90)
                    return conclusion_content
                raise ValueError("模型返回了空内容")
            except Exception as e:
                logger.warning(f"任务 {self.task_id} - 生成收尾内容失败 "
                             f"(尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"任务 {self.task_id} - 生成收尾内容达到最大重试次数，失败。", 
                               exc_info=True)
                    await self._log(f"提炼洞见时遇到问题，请稍后重试", error=True)
                    return None
                await asyncio.sleep(2)
        return None
    
    async def _log_final_length_statistics(self, final_report: str):
        """记录最终长度统计信息"""
        if not self.length_target or not self.length_monitor:
            return
        
        final_length = len(final_report)
        target_length = self.length_target.target_length
        deviation = (final_length - target_length) / target_length
        
        # 获取监控摘要
        monitoring_summary = self.length_monitor.get_monitoring_summary()
        
        stats_info = (
            f"最终长度统计:\n"
            f"  - 实际长度: {final_length:,} 字\n"
            f"  - 目标长度: {target_length:,} 字\n"
            f"  - 长度偏差: {deviation:+.1%}\n"
            f"  - 目标达成: {'✓' if abs(deviation) <= 0.2 else '✗'}\n"
            f"  - 章节数量: {monitoring_summary.get('completed_chapters', 0)}/{monitoring_summary.get('total_chapters', 0)}\n"
            f"  - 平均章节长度: {monitoring_summary.get('avg_chapter_length', 0):,} 字"
        )
        
        await self._log(stats_info, error=False)
        
        # 记录成功标准验证
        success_criteria = self._validate_success_criteria(final_length)
        if success_criteria:
            await self._log(f"成功标准验证: {success_criteria}", error=False)
    
    def _validate_success_criteria(self, final_length: int) -> str:
        """验证成功标准"""
        if not self.analysis_result:
            return ""
        
        video_category = self.analysis_result.video_category
        duration = self.analysis_result.duration_minutes
        
        # 根据视频类别验证长度范围
        if video_category == "short" and duration < 20:
            expected_range = "12k-18k"
            is_valid = 12000 <= final_length <= 18000
        elif video_category == "medium" and 20 <= duration < 60:
            expected_range = "20k-30k"
            is_valid = 20000 <= final_length <= 30000
        elif video_category == "long" and 60 <= duration < 120:
            expected_range = "30k-45k"
            is_valid = 30000 <= final_length <= 45000
        elif video_category == "extra_long" and duration >= 120:
            expected_range = "40k-60k"
            is_valid = 40000 <= final_length <= 60000
        else:
            return "视频类别未知，无法验证标准"
        
        status = "✓ 符合" if is_valid else "✗ 不符合"
        return f"{status}预期范围 {expected_range} 字"
    
    def get_adaptive_status(self) -> dict:
        """获取自适应工作流状态"""
        status = {
            "adaptive_enabled": self.analysis_result is not None,
            "analysis_result": None,
            "length_target": None,
            "monitoring_summary": None
        }
        
        if self.analysis_result:
            status["analysis_result"] = {
                "duration_minutes": self.analysis_result.duration_minutes,
                "video_category": self.analysis_result.video_category,
                "subtitle_word_count": self.analysis_result.subtitle_word_count,
                "words_per_minute": self.analysis_result.words_per_minute,
                "density_level": self.analysis_result.density_level,
                "complexity_score": self.analysis_result.complexity_score
            }
        
        if self.length_target:
            status["length_target"] = {
                "target_length": self.length_target.target_length,
                "min_length": self.length_target.min_length,
                "max_length": self.length_target.max_length,
                "chapter_count": self.length_target.chapter_count,
                "avg_chapter_length": self.length_target.avg_chapter_length
            }
        
        if self.length_monitor:
            status["monitoring_summary"] = self.length_monitor.get_monitoring_summary()
        
        return status


async def run_adaptive_deep_summary_workflow(task_id: str, model_name: str, 
                                           transcript: str, video_metadata: VideoMetadata):
    """
    自适应工作流的入口函数
    
    Args:
        task_id: 任务ID
        model_name: 模型名称
        transcript: 视频字幕文本
        video_metadata: 视频元数据
    """
    workflow = AdaptiveDeepSummaryWorkflow(task_id, model_name, transcript, video_metadata)
    await workflow.run()