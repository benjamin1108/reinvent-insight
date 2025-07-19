"""
自适应内容长度生成模块

该模块实现了基于视频特征的动态内容长度计算功能，包括：
- 视频分析器：分析视频时长、字幕密度等特征
- 长度计算器：基于视频特征计算目标文章长度
- 配置管理器：管理长度计算相关的配置参数
"""

import os
import re
import yaml
import json
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Tuple, List
from pathlib import Path
from datetime import datetime

from loguru import logger

from .downloader import VideoMetadata


class LengthAdaptationError(Exception):
    """长度自适应相关错误基类"""
    pass


class VideoAnalysisError(LengthAdaptationError):
    """视频分析错误"""
    pass


class LengthCalculationError(LengthAdaptationError):
    """长度计算错误"""
    pass


class ConfigurationError(LengthAdaptationError):
    """配置错误"""
    pass


class MonitoringError(LengthAdaptationError):
    """监控错误"""
    pass


@dataclass
class VideoAnalysisResult:
    """视频分析结果数据类"""
    duration_minutes: float
    subtitle_word_count: int
    words_per_minute: float
    video_category: str  # short/medium/long/extra_long
    density_level: str   # low/medium/high
    complexity_score: float


@dataclass
class LengthTarget:
    """长度目标数据类"""
    target_length: int
    min_length: int
    max_length: int
    chapter_count: int
    avg_chapter_length: int


@dataclass
class LengthStatus:
    """长度状态数据类，用于跟踪生成进度"""
    current_length: int
    target_length: int
    progress_ratio: float
    deviation_ratio: float
    adjustment_needed: bool
    adjustment_type: str  # "expand", "compress", "maintain"
    chapter_index: int
    expected_length: int
    remaining_chapters: int
    predicted_final_length: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ChapterLengthRecord:
    """章节长度记录"""
    chapter_index: int
    chapter_title: str
    content_length: int
    target_length: int
    deviation_ratio: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AdjustmentRecord:
    """调整记录数据类"""
    chapter_index: int
    adjustment_type: str  # "expand", "compress", "maintain"
    original_target: int
    adjusted_target: int
    adjustment_amount: int
    reason: str
    effectiveness_score: Optional[float] = None  # 调整效果评分（0-1）
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AdjustmentStrategy:
    """调整策略数据类"""
    strategy_type: str  # "gradual", "aggressive", "conservative"
    target_chapter_length: int
    content_detail_level: str  # "concise", "moderate", "detailed"
    prompt_adjustments: Dict[str, str]
    compensation_factor: float  # 补偿系数
    priority_areas: List[str]  # 优先调整的内容区域


@dataclass
class LengthConfig:
    """长度配置数据类"""
    # 基础长度比例
    base_ratios: Dict[str, float] = field(default_factory=lambda: {
        "short": 0.7,      # 短视频：70%
        "medium": 0.8,     # 中等视频：80%
        "long": 0.9,       # 长视频：90%
        "extra_long": 1.0  # 超长视频：100%
    })
    
    # 密度调整系数
    density_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "low": 1.2,    # 低密度：增加20%
        "medium": 1.0, # 中密度：保持不变
        "high": 0.8    # 高密度：减少20%
    })
    
    # 章节数量范围
    chapter_ranges: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {
        "short": (8, 12),
        "medium": (12, 16),
        "long": (16, 20),
        "extra_long": (20, 25)
    })
    
    # 长度范围限制
    min_article_length: int = 8000
    max_article_length: int = 60000
    
    # 长度容差范围（±百分比）
    length_tolerance: float = 0.2


class VideoAnalyzer:
    """视频分析器，用于分析视频特征"""
    
    def analyze(self, metadata: VideoMetadata, subtitle_text: str) -> VideoAnalysisResult:
        """
        分析视频特征（带错误处理）
        
        Args:
            metadata: 视频元数据
            subtitle_text: 字幕文本
            
        Returns:
            VideoAnalysisResult: 视频分析结果
            
        Raises:
            VideoAnalysisError: 视频分析失败时抛出
        """
        try:
            # 输入验证
            if not subtitle_text or not subtitle_text.strip():
                raise VideoAnalysisError("字幕文本为空或无效")
            
            # 计算视频时长（从字幕估算，因为metadata中可能没有duration）
            duration_minutes = self._safe_estimate_duration(subtitle_text)
            
            # 计算字幕字数
            word_count = self._safe_count_words(subtitle_text)
            
            # 计算每分钟字数
            words_per_minute = self._safe_calculate_wpm(word_count, duration_minutes)
            
            # 视频分类
            video_category = self._categorize_by_duration(duration_minutes)
            
            # 信息密度分级
            density_level = self._categorize_by_density(words_per_minute)
            
            # 计算复杂度评分
            complexity_score = self._safe_calculate_complexity(subtitle_text, words_per_minute)
            
            logger.info(f"视频分析完成: 时长={duration_minutes:.1f}分钟, 字数={word_count}, "
                       f"密度={words_per_minute:.1f}字/分钟, 类别={video_category}, 密度级别={density_level}")
            
            return VideoAnalysisResult(
                duration_minutes=duration_minutes,
                subtitle_word_count=word_count,
                words_per_minute=words_per_minute,
                video_category=video_category,
                density_level=density_level,
                complexity_score=complexity_score
            )
            
        except Exception as e:
            if isinstance(e, VideoAnalysisError):
                raise
            logger.error(f"视频分析过程中发生未预期错误: {e}")
            raise VideoAnalysisError(f"视频分析失败: {str(e)}") from e
    
    def _safe_estimate_duration(self, subtitle_text: str) -> float:
        """
        安全的时长估算
        
        Args:
            subtitle_text: 字幕文本
            
        Returns:
            float: 估算的时长（分钟）
            
        Raises:
            VideoAnalysisError: 时长估算失败时抛出
        """
        try:
            word_count = self._safe_count_words(subtitle_text)
            if word_count == 0:
                logger.warning("字幕字数为0，使用默认时长")
                return 10.0  # 默认10分钟
            
            # 使用保守的语速估算（175字/分钟）
            estimated_minutes = word_count / 175
            result = max(estimated_minutes, 1.0)  # 至少1分钟
            
            # 合理性检查
            if result > 600:  # 超过10小时可能有问题
                logger.warning(f"估算时长过长({result:.1f}分钟)，可能存在问题")
                return min(result, 300)  # 限制在5小时内
            
            return result
            
        except Exception as e:
            logger.error(f"时长估算失败: {e}")
            raise VideoAnalysisError(f"无法估算视频时长: {str(e)}") from e
    
    def _safe_count_words(self, text: str) -> int:
        """
        安全的单词计数
        
        Args:
            text: 文本
            
        Returns:
            int: 单词数量
            
        Raises:
            VideoAnalysisError: 单词计数失败时抛出
        """
        try:
            if not text or not isinstance(text, str):
                return 0
            
            # 简单的单词计数，按空格分割
            words = re.findall(r'\b\w+\b', text.lower())
            word_count = len(words)
            
            # 合理性检查
            if word_count > 1000000:  # 超过100万字可能有问题
                logger.warning(f"字数过多({word_count})，可能存在问题")
            
            return word_count
            
        except Exception as e:
            logger.error(f"单词计数失败: {e}")
            raise VideoAnalysisError(f"无法计算字幕字数: {str(e)}") from e
    
    def _safe_calculate_wpm(self, word_count: int, duration_minutes: float) -> float:
        """
        安全的每分钟字数计算
        
        Args:
            word_count: 字数
            duration_minutes: 时长（分钟）
            
        Returns:
            float: 每分钟字数
        """
        try:
            if duration_minutes <= 0:
                logger.warning("视频时长无效，使用默认语速")
                return 150.0  # 默认语速
            
            wpm = word_count / duration_minutes
            
            # 合理性检查
            if wpm > 500:  # 超过500字/分钟可能有问题
                logger.warning(f"语速过快({wpm:.1f}字/分钟)，可能存在问题")
            elif wpm < 10:  # 低于10字/分钟可能有问题
                logger.warning(f"语速过慢({wpm:.1f}字/分钟)，可能存在问题")
            
            return wpm
            
        except Exception as e:
            logger.error(f"语速计算失败: {e}")
            return 150.0  # 返回默认语速
    
    def _safe_calculate_complexity(self, subtitle_text: str, words_per_minute: float) -> float:
        """
        安全的复杂度计算
        
        Args:
            subtitle_text: 字幕文本
            words_per_minute: 每分钟字数
            
        Returns:
            float: 复杂度评分（0-1）
        """
        try:
            if not subtitle_text:
                return 0.5  # 默认中等复杂度
            
            # 技术词汇检测（简单版本）
            tech_keywords = [
                'aws', 'cloud', 'api', 'database', 'architecture', 'security',
                'network', 'infrastructure', 'deployment', 'kubernetes', 'docker',
                'microservices', 'serverless', 'machine learning', 'ai', 'data'
            ]
            
            text_lower = subtitle_text.lower()
            tech_word_count = sum(1 for keyword in tech_keywords if keyword in text_lower)
            tech_density = tech_word_count / len(tech_keywords)
            
            # 语速复杂度（偏离正常语速越多，复杂度越高）
            normal_wpm = 150
            speed_complexity = min(abs(words_per_minute - normal_wpm) / normal_wpm, 1.0)
            
            # 综合复杂度评分
            complexity = (tech_density * 0.6 + speed_complexity * 0.4)
            result = min(max(complexity, 0.0), 1.0)
            
            return result
            
        except Exception as e:
            logger.error(f"复杂度计算失败: {e}")
            return 0.5  # 返回默认复杂度
    
    def _estimate_duration_from_subtitles(self, subtitle_text: str) -> float:
        """
        从字幕文本估算视频时长
        
        基于经验值：英文演讲平均语速约150-200字/分钟
        """
        word_count = self._count_words(subtitle_text)
        # 使用保守的语速估算（175字/分钟）
        estimated_minutes = word_count / 175
        return max(estimated_minutes, 1.0)  # 至少1分钟
    
    def _count_words(self, text: str) -> int:
        """计算英文文本的单词数"""
        if not text:
            return 0
        # 简单的单词计数，按空格分割
        words = re.findall(r'\b\w+\b', text.lower())
        return len(words)
    
    def _categorize_by_duration(self, duration: float) -> str:
        """根据时长分类视频"""
        if duration < 20:
            return "short"
        elif duration < 60:
            return "medium"
        elif duration < 120:
            return "long"
        else:
            return "extra_long"
    
    def _categorize_by_density(self, words_per_minute: float) -> str:
        """根据信息密度分级"""
        if words_per_minute < 100:
            return "low"
        elif words_per_minute < 200:
            return "medium"
        else:
            return "high"
    
    def _calculate_complexity_score(self, subtitle_text: str, words_per_minute: float) -> float:
        """
        计算内容复杂度评分（0-1之间）
        
        考虑因素：
        - 技术词汇密度
        - 句子长度变化
        - 语速
        """
        if not subtitle_text:
            return 0.5
        
        # 技术词汇检测（简单版本）
        tech_keywords = [
            'aws', 'cloud', 'api', 'database', 'architecture', 'security',
            'network', 'infrastructure', 'deployment', 'kubernetes', 'docker',
            'microservices', 'serverless', 'machine learning', 'ai', 'data'
        ]
        
        text_lower = subtitle_text.lower()
        tech_word_count = sum(1 for keyword in tech_keywords if keyword in text_lower)
        tech_density = tech_word_count / len(tech_keywords)
        
        # 语速复杂度（偏离正常语速越多，复杂度越高）
        normal_wpm = 150
        speed_complexity = min(abs(words_per_minute - normal_wpm) / normal_wpm, 1.0)
        
        # 综合复杂度评分
        complexity = (tech_density * 0.6 + speed_complexity * 0.4)
        return min(max(complexity, 0.0), 1.0)


class LengthCalculator:
    """长度计算器，基于视频特征计算目标长度"""
    
    def __init__(self, config: LengthConfig):
        self.config = config
    
    def calculate_target_length(self, analysis: VideoAnalysisResult) -> LengthTarget:
        """
        计算目标长度（带错误处理）
        
        Args:
            analysis: 视频分析结果
            
        Returns:
            LengthTarget: 长度目标
            
        Raises:
            LengthCalculationError: 长度计算失败时抛出
        """
        try:
            # 输入验证
            if not analysis:
                raise LengthCalculationError("视频分析结果为空")
            
            if analysis.subtitle_word_count <= 0:
                raise LengthCalculationError("字幕字数无效")
            
            # 基础长度计算
            base_ratio = self._safe_get_base_ratio(analysis.video_category)
            base_length = self._safe_calculate_base_length(analysis.subtitle_word_count, base_ratio)
            
            # 密度调整
            density_multiplier = self._safe_get_density_multiplier(analysis.density_level)
            adjusted_length = self._safe_apply_density_adjustment(base_length, density_multiplier)
            
            # 复杂度调整
            final_length = self._safe_apply_complexity_adjustment(adjusted_length, analysis.complexity_score)
            
            # 应用边界限制
            final_length = self._safe_apply_boundaries(final_length)
            
            # 计算章节数量
            chapter_count = self._safe_calculate_chapter_count(final_length, analysis.video_category)
            
            # 计算长度范围
            min_length, max_length = self._safe_calculate_length_range(final_length)
            
            avg_chapter_length = final_length // chapter_count if chapter_count > 0 else 1000
            
            logger.info(f"长度计算完成: 目标={final_length}字, 章节数={chapter_count}, "
                       f"范围=[{min_length}-{max_length}]字")
            
            return LengthTarget(
                target_length=final_length,
                min_length=min_length,
                max_length=max_length,
                chapter_count=chapter_count,
                avg_chapter_length=avg_chapter_length
            )
            
        except Exception as e:
            if isinstance(e, LengthCalculationError):
                raise
            logger.error(f"长度计算过程中发生未预期错误: {e}")
            raise LengthCalculationError(f"长度计算失败: {str(e)}") from e
    
    def _safe_get_base_ratio(self, video_category: str) -> float:
        """
        安全获取基础比例
        
        Args:
            video_category: 视频类别
            
        Returns:
            float: 基础比例
        """
        try:
            ratio = self.config.base_ratios.get(video_category, 0.8)
            if not isinstance(ratio, (int, float)) or ratio <= 0 or ratio > 2.0:
                logger.warning(f"基础比例异常({ratio})，使用默认值")
                return 0.8
            return ratio
        except Exception as e:
            logger.error(f"获取基础比例失败: {e}")
            return 0.8
    
    def _safe_calculate_base_length(self, word_count: int, base_ratio: float) -> int:
        """
        安全计算基础长度
        
        Args:
            word_count: 字数
            base_ratio: 基础比例
            
        Returns:
            int: 基础长度
            
        Raises:
            LengthCalculationError: 计算失败时抛出
        """
        try:
            if word_count <= 0:
                raise LengthCalculationError("字数必须大于0")
            
            base_length = int(word_count * base_ratio)
            
            # 合理性检查
            if base_length < 1000:
                logger.warning(f"基础长度过短({base_length})，调整为最小值")
                return 1000
            elif base_length > 100000:
                logger.warning(f"基础长度过长({base_length})，可能存在问题")
                return min(base_length, 80000)
            
            return base_length
            
        except Exception as e:
            logger.error(f"基础长度计算失败: {e}")
            raise LengthCalculationError(f"无法计算基础长度: {str(e)}") from e
    
    def _safe_get_density_multiplier(self, density_level: str) -> float:
        """
        安全获取密度调整系数
        
        Args:
            density_level: 密度级别
            
        Returns:
            float: 密度调整系数
        """
        try:
            multiplier = self.config.density_multipliers.get(density_level, 1.0)
            if not isinstance(multiplier, (int, float)) or multiplier <= 0 or multiplier > 3.0:
                logger.warning(f"密度调整系数异常({multiplier})，使用默认值")
                return 1.0
            return multiplier
        except Exception as e:
            logger.error(f"获取密度调整系数失败: {e}")
            return 1.0
    
    def _safe_apply_density_adjustment(self, base_length: int, density_multiplier: float) -> int:
        """
        安全应用密度调整
        
        Args:
            base_length: 基础长度
            density_multiplier: 密度调整系数
            
        Returns:
            int: 调整后长度
        """
        try:
            adjusted_length = int(base_length * density_multiplier)
            
            # 合理性检查
            if adjusted_length < base_length * 0.5:
                logger.warning("密度调整导致长度过度减少，限制调整幅度")
                return int(base_length * 0.5)
            elif adjusted_length > base_length * 2.0:
                logger.warning("密度调整导致长度过度增加，限制调整幅度")
                return int(base_length * 2.0)
            
            return adjusted_length
            
        except Exception as e:
            logger.error(f"密度调整失败: {e}")
            return base_length  # 返回原始长度
    
    def _safe_apply_complexity_adjustment(self, adjusted_length: int, complexity_score: float) -> int:
        """
        安全应用复杂度调整
        
        Args:
            adjusted_length: 调整后长度
            complexity_score: 复杂度评分
            
        Returns:
            int: 最终长度
        """
        try:
            # 验证复杂度评分
            if not isinstance(complexity_score, (int, float)) or complexity_score < 0 or complexity_score > 1:
                logger.warning(f"复杂度评分异常({complexity_score})，使用默认值")
                complexity_score = 0.5
            
            # 复杂度调整
            complexity_adjustment = 1.0 + (complexity_score - 0.5) * 0.3
            final_length = int(adjusted_length * complexity_adjustment)
            
            # 合理性检查
            if final_length < adjusted_length * 0.7:
                logger.warning("复杂度调整导致长度过度减少，限制调整幅度")
                return int(adjusted_length * 0.7)
            elif final_length > adjusted_length * 1.3:
                logger.warning("复杂度调整导致长度过度增加，限制调整幅度")
                return int(adjusted_length * 1.3)
            
            return final_length
            
        except Exception as e:
            logger.error(f"复杂度调整失败: {e}")
            return adjusted_length  # 返回调整前长度
    
    def _safe_apply_boundaries(self, final_length: int) -> int:
        """
        安全应用边界限制
        
        Args:
            final_length: 最终长度
            
        Returns:
            int: 边界限制后的长度
        """
        try:
            min_length = getattr(self.config, 'min_article_length', 8000)
            max_length = getattr(self.config, 'max_article_length', 60000)
            
            # 验证边界值
            if min_length <= 0 or max_length <= min_length:
                logger.warning("边界配置异常，使用默认值")
                min_length, max_length = 8000, 60000
            
            bounded_length = max(min_length, min(final_length, max_length))
            
            if bounded_length != final_length:
                logger.info(f"长度被边界限制调整: {final_length} -> {bounded_length}")
            
            return bounded_length
            
        except Exception as e:
            logger.error(f"应用边界限制失败: {e}")
            return max(8000, min(final_length, 60000))  # 使用默认边界
    
    def _safe_calculate_chapter_count(self, target_length: int, video_category: str) -> int:
        """
        安全计算章节数量
        
        Args:
            target_length: 目标长度
            video_category: 视频类别
            
        Returns:
            int: 章节数量
        """
        try:
            # 获取章节范围
            chapter_range = self.config.chapter_ranges.get(video_category, (12, 16))
            
            # 验证章节范围
            if not isinstance(chapter_range, (tuple, list)) or len(chapter_range) != 2:
                logger.warning(f"章节范围配置异常({chapter_range})，使用默认值")
                chapter_range = (12, 16)
            
            min_chapters, max_chapters = chapter_range
            if min_chapters <= 0 or max_chapters <= min_chapters or max_chapters > 50:
                logger.warning(f"章节范围值异常({chapter_range})，使用默认值")
                min_chapters, max_chapters = 12, 16
            
            # 根据目标长度进行微调
            if target_length < 15000:
                chapter_range = (8, 12)
            elif target_length < 25000:
                chapter_range = (12, 16)
            elif target_length < 35000:
                chapter_range = (16, 20)
            else:
                chapter_range = (20, 25)
            
            # 在范围内随机选择
            return random.randint(chapter_range[0], chapter_range[1])
            
        except Exception as e:
            logger.error(f"章节数量计算失败: {e}")
            return 15  # 返回默认章节数
    
    def _safe_calculate_length_range(self, target_length: int) -> Tuple[int, int]:
        """
        安全计算长度范围
        
        Args:
            target_length: 目标长度
            
        Returns:
            Tuple[int, int]: 最小长度和最大长度
        """
        try:
            tolerance = getattr(self.config, 'length_tolerance', 0.2)
            
            # 验证容差值
            if not isinstance(tolerance, (int, float)) or tolerance < 0 or tolerance > 0.5:
                logger.warning(f"长度容差异常({tolerance})，使用默认值")
                tolerance = 0.2
            
            min_length = int(target_length * (1 - tolerance))
            max_length = int(target_length * (1 + tolerance))
            
            # 确保最小长度不小于绝对最小值
            min_length = max(min_length, 5000)
            
            return min_length, max_length
            
        except Exception as e:
            logger.error(f"长度范围计算失败: {e}")
            return int(target_length * 0.8), int(target_length * 1.2)  # 使用默认范围
    
    def _calculate_chapter_count(self, target_length: int, video_category: str) -> int:
        """计算合适的章节数量"""
        # 首先根据视频类别获取基础范围
        chapter_range = self.config.chapter_ranges.get(video_category, (12, 16))
        
        # 根据目标长度进行微调，优先使用视频类别的范围
        if video_category == "short":
            chapter_range = (8, 12)
        elif video_category == "medium":
            chapter_range = (12, 16)
        elif video_category == "long":
            chapter_range = (16, 20)
        elif video_category == "extra_long":
            chapter_range = (20, 25)
        else:
            # 如果类别未知，根据目标长度决定
            if target_length < 15000:
                chapter_range = (8, 12)
            elif target_length < 25000:
                chapter_range = (12, 16)
            elif target_length < 35000:
                chapter_range = (16, 20)
            else:
                chapter_range = (20, 25)
        
        # 在范围内随机选择
        return random.randint(chapter_range[0], chapter_range[1])


class LengthMonitor:
    """长度监控器，实时跟踪生成进度并提供调整建议"""
    
    def __init__(self, length_target: LengthTarget, task_id: str = None):
        """
        初始化长度监控器
        
        Args:
            length_target: 长度目标
            task_id: 任务ID，用于数据持久化
        """
        self.length_target = length_target
        self.task_id = task_id or f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.chapter_records: List[ChapterLengthRecord] = []
        self.monitoring_data_path = Path(f"logs/length_monitoring/{self.task_id}.json")
        
        # 监控配置
        self.deviation_threshold = 0.3  # 偏差阈值30%
        self.adjustment_sensitivity = 0.2  # 调整敏感度20%
        
        # 确保监控数据目录存在
        self.monitoring_data_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"长度监控器已初始化: 目标长度={length_target.target_length}字, "
                   f"章节数={length_target.chapter_count}, 任务ID={self.task_id}")
    
    def monitor_chapter(self, chapter_content: str, chapter_index: int, 
                       chapter_title: str = "") -> LengthStatus:
        """
        监控单个章节长度（带错误处理）
        
        Args:
            chapter_content: 章节内容
            chapter_index: 章节索引（从0开始）
            chapter_title: 章节标题
            
        Returns:
            LengthStatus: 长度状态
            
        Raises:
            MonitoringError: 监控失败时抛出
        """
        try:
            # 输入验证
            if not isinstance(chapter_content, str):
                raise MonitoringError("章节内容必须是字符串")
            
            if chapter_index < 0 or chapter_index >= self.length_target.chapter_count:
                raise MonitoringError(f"章节索引无效: {chapter_index}")
            
            chapter_length = self._safe_calculate_chapter_length(chapter_content)
            
            # 记录章节数据
            chapter_record = self._safe_create_chapter_record(
                chapter_index, chapter_title, chapter_length
            )
            self.chapter_records.append(chapter_record)
            
            # 计算当前总长度
            current_total = self._safe_calculate_total_length()
            
            # 计算进度比例
            progress_ratio = self._safe_calculate_progress_ratio(chapter_index)
            
            # 计算期望长度
            expected_length = self._safe_calculate_expected_length(progress_ratio)
            
            # 计算偏差比例
            deviation_ratio = self._safe_calculate_deviation_ratio(current_total, expected_length)
            
            # 预测最终长度
            predicted_final_length = self._safe_predict_final_length(chapter_index + 1)
            
            # 确定是否需要调整
            adjustment_needed = abs(deviation_ratio) > self.deviation_threshold
            adjustment_type = self._get_adjustment_type(deviation_ratio)
            
            # 创建状态对象
            status = LengthStatus(
                current_length=current_total,
                target_length=self.length_target.target_length,
                progress_ratio=progress_ratio,
                deviation_ratio=deviation_ratio,
                adjustment_needed=adjustment_needed,
                adjustment_type=adjustment_type,
                chapter_index=chapter_index,
                expected_length=expected_length,
                remaining_chapters=self.length_target.chapter_count - (chapter_index + 1),
                predicted_final_length=predicted_final_length
            )
            
            # 持久化监控数据
            self._safe_save_monitoring_data(status)
            
            # 记录监控日志
            self._safe_log_monitoring_status(status, chapter_record)
            
            return status
            
        except Exception as e:
            if isinstance(e, MonitoringError):
                raise
            logger.error(f"章节监控过程中发生未预期错误: {e}")
            raise MonitoringError(f"章节监控失败: {str(e)}") from e
    
    def _safe_calculate_chapter_length(self, chapter_content: str) -> int:
        """
        安全计算章节长度
        
        Args:
            chapter_content: 章节内容
            
        Returns:
            int: 章节长度
            
        Raises:
            MonitoringError: 计算失败时抛出
        """
        try:
            if not chapter_content:
                return 0
            
            length = len(chapter_content)
            
            # 合理性检查
            if length > 50000:  # 单章节超过5万字可能有问题
                logger.warning(f"章节长度异常({length}字)，可能存在问题")
            
            return length
            
        except Exception as e:
            logger.error(f"章节长度计算失败: {e}")
            raise MonitoringError(f"无法计算章节长度: {str(e)}") from e
    
    def _safe_create_chapter_record(self, chapter_index: int, chapter_title: str, 
                                   chapter_length: int) -> ChapterLengthRecord:
        """
        安全创建章节记录
        
        Args:
            chapter_index: 章节索引
            chapter_title: 章节标题
            chapter_length: 章节长度
            
        Returns:
            ChapterLengthRecord: 章节记录
        """
        try:
            target_length = self.length_target.avg_chapter_length
            deviation_ratio = (chapter_length - target_length) / target_length if target_length > 0 else 0
            
            return ChapterLengthRecord(
                chapter_index=chapter_index,
                chapter_title=chapter_title or f"第{chapter_index + 1}章",
                content_length=chapter_length,
                target_length=target_length,
                deviation_ratio=deviation_ratio
            )
            
        except Exception as e:
            logger.error(f"创建章节记录失败: {e}")
            # 返回默认记录
            return ChapterLengthRecord(
                chapter_index=chapter_index,
                chapter_title=chapter_title or f"第{chapter_index + 1}章",
                content_length=chapter_length,
                target_length=1000,
                deviation_ratio=0.0
            )
    
    def _safe_calculate_total_length(self) -> int:
        """
        安全计算总长度
        
        Returns:
            int: 总长度
        """
        try:
            return sum(record.content_length for record in self.chapter_records)
        except Exception as e:
            logger.error(f"总长度计算失败: {e}")
            return 0
    
    def _safe_calculate_progress_ratio(self, chapter_index: int) -> float:
        """
        安全计算进度比例
        
        Args:
            chapter_index: 章节索引
            
        Returns:
            float: 进度比例
        """
        try:
            if self.length_target.chapter_count <= 0:
                return 0.0
            
            ratio = (chapter_index + 1) / self.length_target.chapter_count
            return min(max(ratio, 0.0), 1.0)  # 限制在0-1之间
            
        except Exception as e:
            logger.error(f"进度比例计算失败: {e}")
            return 0.0
    
    def _safe_calculate_expected_length(self, progress_ratio: float) -> int:
        """
        安全计算期望长度
        
        Args:
            progress_ratio: 进度比例
            
        Returns:
            int: 期望长度
        """
        try:
            if progress_ratio < 0 or progress_ratio > 1:
                logger.warning(f"进度比例异常({progress_ratio})，限制范围")
                progress_ratio = min(max(progress_ratio, 0.0), 1.0)
            
            return int(self.length_target.target_length * progress_ratio)
            
        except Exception as e:
            logger.error(f"期望长度计算失败: {e}")
            return 0
    
    def _safe_calculate_deviation_ratio(self, current_total: int, expected_length: int) -> float:
        """
        安全计算偏差比例
        
        Args:
            current_total: 当前总长度
            expected_length: 期望长度
            
        Returns:
            float: 偏差比例
        """
        try:
            if expected_length <= 0:
                return 0.0
            
            deviation = (current_total - expected_length) / expected_length
            
            # 限制偏差范围，避免极端值
            return min(max(deviation, -2.0), 2.0)
            
        except Exception as e:
            logger.error(f"偏差比例计算失败: {e}")
            return 0.0
    
    def _safe_predict_final_length(self, completed_chapters: int) -> int:
        """
        安全预测最终长度
        
        Args:
            completed_chapters: 已完成章节数
            
        Returns:
            int: 预测的最终长度
        """
        try:
            if completed_chapters <= 0:
                return self.length_target.target_length
            
            # 计算已完成章节的平均长度
            total_completed_length = self._safe_calculate_total_length()
            avg_chapter_length = total_completed_length / completed_chapters
            
            # 预测剩余章节长度
            remaining_chapters = self.length_target.chapter_count - completed_chapters
            if remaining_chapters <= 0:
                return total_completed_length
            
            predicted_remaining_length = remaining_chapters * avg_chapter_length
            predicted_total = int(total_completed_length + predicted_remaining_length)
            
            # 合理性检查
            if predicted_total > self.length_target.target_length * 3:
                logger.warning(f"预测长度异常({predicted_total})，可能存在问题")
                return min(predicted_total, self.length_target.target_length * 2)
            
            return predicted_total
            
        except Exception as e:
            logger.error(f"最终长度预测失败: {e}")
            return self.length_target.target_length
    
    def get_adjustment_recommendation(self, status: LengthStatus) -> Dict[str, any]:
        """
        获取调整建议
        
        Args:
            status: 当前长度状态
            
        Returns:
            Dict: 调整建议
        """
        recommendation = {
            "adjustment_needed": status.adjustment_needed,
            "adjustment_type": status.adjustment_type,
            "severity": self._calculate_adjustment_severity(status.deviation_ratio),
            "target_adjustment": 0,
            "strategy": "",
            "remaining_chapters_target": 0
        }
        
        if not status.adjustment_needed:
            recommendation["strategy"] = "继续按当前策略生成"
            recommendation["remaining_chapters_target"] = self.length_target.avg_chapter_length
            return recommendation
        
        # 计算需要调整的长度
        length_gap = status.predicted_final_length - self.length_target.target_length
        remaining_chapters = status.remaining_chapters
        
        if remaining_chapters > 0:
            adjustment_per_chapter = length_gap / remaining_chapters
            recommendation["target_adjustment"] = int(adjustment_per_chapter)
            recommendation["remaining_chapters_target"] = max(
                500,  # 最小章节长度
                self.length_target.avg_chapter_length - adjustment_per_chapter
            )
        
        # 生成策略建议
        if status.adjustment_type == "compress":
            recommendation["strategy"] = f"后续章节需要压缩内容，建议每章节减少约{abs(recommendation['target_adjustment'])}字"
        elif status.adjustment_type == "expand":
            recommendation["strategy"] = f"后续章节需要扩展内容，建议每章节增加约{recommendation['target_adjustment']}字"
        
        return recommendation
    
    def _calculate_adjustment_severity(self, deviation_ratio: float) -> str:
        """
        计算调整严重程度
        
        Args:
            deviation_ratio: 偏差比例
            
        Returns:
            str: 严重程度
        """
        abs_deviation = abs(deviation_ratio)
        if abs_deviation < 0.1:
            return "轻微"
        elif abs_deviation < 0.3:
            return "中等"
        elif abs_deviation < 0.5:
            return "严重"
        else:
            return "极严重"
    
    def _get_adjustment_type(self, deviation_ratio: float) -> str:
        """
        确定调整类型
        
        Args:
            deviation_ratio: 偏差比例
            
        Returns:
            str: 调整类型
        """
        if deviation_ratio > self.deviation_threshold:
            return "compress"  # 内容过长，需要压缩
        elif deviation_ratio < -self.deviation_threshold:
            return "expand"    # 内容过短，需要扩展
        else:
            return "maintain"  # 保持当前策略
    
    def load_monitoring_data(self) -> Optional[Dict]:
        """
        加载监控数据
        
        Returns:
            Optional[Dict]: 监控数据，如果文件不存在返回None
        """
        try:
            if self.monitoring_data_path.exists():
                with open(self.monitoring_data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载监控数据失败: {e}")
        return None
    
    def get_monitoring_summary(self) -> Dict[str, any]:
        """
        获取监控摘要
        
        Returns:
            Dict: 监控摘要信息
        """
        if not self.chapter_records:
            return {"status": "未开始监控"}
        
        total_length = sum(record.content_length for record in self.chapter_records)
        completed_chapters = len(self.chapter_records)
        avg_chapter_length = total_length / completed_chapters if completed_chapters > 0 else 0
        
        return {
            "task_id": self.task_id,
            "completed_chapters": completed_chapters,
            "total_chapters": self.length_target.chapter_count,
            "current_total_length": total_length,
            "target_length": self.length_target.target_length,
            "avg_chapter_length": int(avg_chapter_length),
            "target_avg_chapter_length": self.length_target.avg_chapter_length,
            "progress_percentage": (completed_chapters / self.length_target.chapter_count) * 100,
            "predicted_final_length": self._safe_predict_final_length(completed_chapters),
            "on_track": abs(total_length - (self.length_target.target_length * completed_chapters / self.length_target.chapter_count)) < (self.length_target.target_length * self.deviation_threshold)
        }
    
    def _safe_save_monitoring_data(self, status: LengthStatus):
        """
        安全保存监控数据
        
        Args:
            status: 长度状态
        """
        try:
            monitoring_data = {
                "task_id": self.task_id,
                "length_target": asdict(self.length_target),
                "current_status": asdict(status),
                "chapter_records": [asdict(record) for record in self.chapter_records],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.monitoring_data_path, 'w', encoding='utf-8') as f:
                json.dump(monitoring_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"保存监控数据失败: {e}")
    
    def _safe_log_monitoring_status(self, status: LengthStatus, chapter_record: ChapterLengthRecord):
        """
        安全记录监控状态日志
        
        Args:
            status: 长度状态
            chapter_record: 章节记录
        """
        try:
            logger.info(f"章节{chapter_record.chapter_index + 1}监控: "
                       f"长度={chapter_record.content_length}字, "
                       f"目标={chapter_record.target_length}字, "
                       f"偏差={chapter_record.deviation_ratio:.1%}")
            
            logger.info(f"总体进度: {status.progress_ratio:.1%}, "
                       f"当前总长度={status.current_length}字, "
                       f"预测最终长度={status.predicted_final_length}字, "
                       f"总偏差={status.deviation_ratio:.1%}")
            
            if status.adjustment_needed:
                recommendation = self.get_adjustment_recommendation(status)
                logger.warning(f"需要调整: {recommendation['strategy']}")
                
        except Exception as e:
            logger.error(f"记录监控日志失败: {e}")


def safe_video_analysis(metadata: VideoMetadata, subtitle_text: str, 
                       fallback_duration: float = 30.0) -> VideoAnalysisResult:
    """
    安全的视频分析函数，包含降级处理
    
    Args:
        metadata: 视频元数据
        subtitle_text: 字幕文本
        fallback_duration: 降级时使用的默认时长（分钟）
        
    Returns:
        VideoAnalysisResult: 视频分析结果
    """
    try:
        analyzer = VideoAnalyzer()
        return analyzer.analyze(metadata, subtitle_text)
    except VideoAnalysisError as e:
        logger.warning(f"视频分析失败，使用降级策略: {e}")
        
        # 降级策略：使用基本估算
        try:
            word_count = len(subtitle_text.split()) if subtitle_text else 1000
            duration = max(word_count / 175, fallback_duration)  # 基于语速估算
            
            return VideoAnalysisResult(
                duration_minutes=duration,
                subtitle_word_count=word_count,
                words_per_minute=word_count / duration,
                video_category="medium",  # 默认中等视频
                density_level="medium",   # 默认中等密度
                complexity_score=0.5      # 默认中等复杂度
            )
        except Exception as fallback_error:
            logger.error(f"降级策略也失败: {fallback_error}")
            # 最终降级：返回完全默认的结果
            return VideoAnalysisResult(
                duration_minutes=fallback_duration,
                subtitle_word_count=5000,
                words_per_minute=150.0,
                video_category="medium",
                density_level="medium",
                complexity_score=0.5
            )


def safe_length_calculation(analysis: VideoAnalysisResult, config: LengthConfig = None) -> LengthTarget:
    """
    安全的长度计算函数，包含异常处理和降级策略
    
    Args:
        analysis: 视频分析结果
        config: 长度配置，如果为None则使用默认配置
        
    Returns:
        LengthTarget: 长度目标
    """
    try:
        # 使用默认配置如果没有提供
        if config is None:
            config = LengthConfig()
        
        calculator = LengthCalculator(config)
        return calculator.calculate_target_length(analysis)
        
    except LengthCalculationError as e:
        logger.warning(f"长度计算失败，使用降级策略: {e}")
        
        # 降级策略：基于视频类别使用预设值
        try:
            category = getattr(analysis, 'video_category', 'medium')
            word_count = getattr(analysis, 'subtitle_word_count', 5000)
            
            # 基于类别的默认长度映射
            default_lengths = {
                "short": 15000,
                "medium": 20000,
                "long": 30000,
                "extra_long": 40000
            }
            
            target_length = default_lengths.get(category, 20000)
            
            # 根据字数进行简单调整
            if word_count > 0:
                ratio = min(max(word_count / 10000, 0.5), 2.0)  # 限制调整范围
                target_length = int(target_length * ratio)
            
            # 确保在合理范围内
            target_length = max(8000, min(target_length, 60000))
            
            # 计算章节数
            chapter_count = max(8, min(target_length // 1500, 25))
            
            return LengthTarget(
                target_length=target_length,
                min_length=int(target_length * 0.8),
                max_length=int(target_length * 1.2),
                chapter_count=chapter_count,
                avg_chapter_length=target_length // chapter_count
            )
            
        except Exception as fallback_error:
            logger.error(f"降级策略也失败: {fallback_error}")
            # 最终降级：返回固定的默认值
            return LengthTarget(
                target_length=20000,
                min_length=16000,
                max_length=24000,
                chapter_count=15,
                avg_chapter_length=1333
            )


def safe_config_loading(config_path: str = "config/length_config.yaml") -> LengthConfig:
    """
    安全的配置加载函数，包含错误处理和默认策略
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        LengthConfig: 长度配置
    """
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            # 验证配置数据
            if not isinstance(data, dict):
                raise ConfigurationError("配置文件格式无效")
            
            # 创建配置对象，使用默认值填充缺失项
            config = LengthConfig()
            
            # 安全更新配置
            if 'base_ratios' in data and isinstance(data['base_ratios'], dict):
                config.base_ratios.update(data['base_ratios'])
            
            if 'density_multipliers' in data and isinstance(data['density_multipliers'], dict):
                config.density_multipliers.update(data['density_multipliers'])
            
            if 'chapter_ranges' in data and isinstance(data['chapter_ranges'], dict):
                config.chapter_ranges.update(data['chapter_ranges'])
            
            # 更新其他配置项
            for key in ['min_article_length', 'max_article_length', 'length_tolerance']:
                if key in data and isinstance(data[key], (int, float)):
                    setattr(config, key, data[key])
            
            logger.info(f"配置文件加载成功: {config_path}")
            return config
            
        else:
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return LengthConfig()
            
    except Exception as e:
        logger.error(f"配置加载失败: {e}，使用默认配置")
        return LengthConfig()


def create_default_config_file(config_path: str = "config/length_config.yaml"):
    """
    创建默认配置文件
    
    Args:
        config_path: 配置文件路径
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 创建默认配置
        default_config = LengthConfig()
        
        # 转换为字典格式
        config_dict = {
            'base_ratios': default_config.base_ratios,
            'density_multipliers': default_config.density_multipliers,
            'chapter_ranges': default_config.chapter_ranges,
            'min_article_length': default_config.min_article_length,
            'max_article_length': default_config.max_article_length,
            'length_tolerance': default_config.length_tolerance
        }
        
        # 写入文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        logger.info(f"默认配置文件已创建: {config_path}")
        
    except Exception as e:
        logger.error(f"创建默认配置文件失败: {e}")


def validate_length_target(target: LengthTarget) -> bool:
    """
    验证长度目标的有效性
    
    Args:
        target: 长度目标
        
    Returns:
        bool: 是否有效
    """
    try:
        if not isinstance(target, LengthTarget):
            return False
        
        # 检查基本字段
        if target.target_length <= 0 or target.chapter_count <= 0:
            return False
        
        # 检查长度范围
        if target.min_length >= target.max_length:
            return False
        
        if target.target_length < target.min_length or target.target_length > target.max_length:
            return False
        
        # 检查章节长度
        if target.avg_chapter_length <= 0:
            return False
        
        # 检查合理性
        if target.target_length > 100000 or target.chapter_count > 50:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"长度目标验证失败: {e}")
        return False


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation_name: str
    start_time: float
    end_time: float
    duration_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LengthAccuracyMetrics:
    """长度准确性指标数据类"""
    task_id: str
    target_length: int
    actual_length: int
    deviation_ratio: float
    accuracy_score: float  # 0-1之间，1表示完全准确
    chapter_count_target: int
    chapter_count_actual: int
    avg_chapter_length_target: int
    avg_chapter_length_actual: int
    completion_time: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SystemHealthMetrics:
    """系统健康指标数据类"""
    total_tasks_processed: int
    successful_tasks: int
    failed_tasks: int
    success_rate: float
    avg_processing_time: float
    avg_accuracy_score: float
    error_rate: float
    last_error_time: Optional[str] = None
    last_error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LengthMetricsCollector:
    """长度指标收集器"""
    
    def __init__(self, metrics_dir: str = "logs/length_metrics"):
        """
        初始化指标收集器
        
        Args:
            metrics_dir: 指标存储目录
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # 指标文件路径
        self.performance_log = self.metrics_dir / "performance.jsonl"
        self.accuracy_log = self.metrics_dir / "accuracy.jsonl"
        self.health_log = self.metrics_dir / "health.json"
        
        # 内存中的指标缓存
        self.performance_metrics: List[PerformanceMetrics] = []
        self.accuracy_metrics: List[LengthAccuracyMetrics] = []
        
        logger.info(f"长度指标收集器已初始化: {metrics_dir}")
    
    def record_performance(self, operation_name: str, start_time: float, 
                          end_time: float, memory_usage: float = 0.0, 
                          cpu_usage: float = 0.0, success: bool = True, 
                          error_message: str = None):
        """
        记录性能指标
        
        Args:
            operation_name: 操作名称
            start_time: 开始时间
            end_time: 结束时间
            memory_usage: 内存使用量(MB)
            cpu_usage: CPU使用率(%)
            success: 是否成功
            error_message: 错误信息
        """
        try:
            duration = end_time - start_time
            
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                success=success,
                error_message=error_message
            )
            
            self.performance_metrics.append(metrics)
            self._append_to_jsonl(self.performance_log, asdict(metrics))
            
            # 记录日志
            if success:
                logger.info(f"性能记录: {operation_name} 耗时 {duration:.2f}s")
            else:
                logger.warning(f"性能记录: {operation_name} 失败，耗时 {duration:.2f}s，错误: {error_message}")
                
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
    
    def record_accuracy(self, task_id: str, target_length: int, actual_length: int,
                       chapter_count_target: int, chapter_count_actual: int,
                       completion_time: float):
        """
        记录长度准确性指标
        
        Args:
            task_id: 任务ID
            target_length: 目标长度
            actual_length: 实际长度
            chapter_count_target: 目标章节数
            chapter_count_actual: 实际章节数
            completion_time: 完成时间
        """
        try:
            # 计算偏差比例
            deviation_ratio = (actual_length - target_length) / target_length if target_length > 0 else 0
            
            # 计算准确性评分（基于偏差程度）
            abs_deviation = abs(deviation_ratio)
            if abs_deviation <= 0.1:
                accuracy_score = 1.0
            elif abs_deviation <= 0.2:
                accuracy_score = 0.8
            elif abs_deviation <= 0.3:
                accuracy_score = 0.6
            elif abs_deviation <= 0.5:
                accuracy_score = 0.4
            else:
                accuracy_score = 0.2
            
            # 计算平均章节长度
            avg_chapter_target = target_length // chapter_count_target if chapter_count_target > 0 else 0
            avg_chapter_actual = actual_length // chapter_count_actual if chapter_count_actual > 0 else 0
            
            metrics = LengthAccuracyMetrics(
                task_id=task_id,
                target_length=target_length,
                actual_length=actual_length,
                deviation_ratio=deviation_ratio,
                accuracy_score=accuracy_score,
                chapter_count_target=chapter_count_target,
                chapter_count_actual=chapter_count_actual,
                avg_chapter_length_target=avg_chapter_target,
                avg_chapter_length_actual=avg_chapter_actual,
                completion_time=completion_time
            )
            
            self.accuracy_metrics.append(metrics)
            self._append_to_jsonl(self.accuracy_log, asdict(metrics))
            
            logger.info(f"准确性记录: 任务{task_id} 目标{target_length}字 实际{actual_length}字 "
                       f"偏差{deviation_ratio:.1%} 评分{accuracy_score:.1f}")
                       
        except Exception as e:
            logger.error(f"记录准确性指标失败: {e}")
    
    def _append_to_jsonl(self, file_path: Path, data: Dict):
        """
        追加数据到JSONL文件
        
        Args:
            file_path: 文件路径
            data: 数据字典
        """
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            logger.error(f"写入JSONL文件失败: {e}")


# 全局指标收集器实例
_global_metrics_collector = None


def get_metrics_collector() -> LengthMetricsCollector:
    """
    获取全局指标收集器实例
    
    Returns:
        LengthMetricsCollector: 指标收集器
    """
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = LengthMetricsCollector()
    return _global_metrics_collector


def performance_monitor(operation_name: str):
    """
    性能监控装饰器
    
    Args:
        operation_name: 操作名称
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            import os
            
            # 记录开始时间和资源使用
            start_time = time.time()
            start_memory = 0.0
            start_cpu = 0.0
            
            # 尝试获取系统资源信息
            try:
                import psutil
                process = psutil.Process(os.getpid())
                start_memory = process.memory_info().rss / 1024 / 1024  # MB
                start_cpu = process.cpu_percent()
            except ImportError:
                logger.debug("psutil未安装，跳过资源监控")
            except Exception as e:
                logger.debug(f"获取系统资源信息失败: {e}")
            
            success = True
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # 记录结束时间和资源使用
                end_time = time.time()
                memory_usage = 0.0
                cpu_usage = 0.0
                
                try:
                    import psutil
                    process = psutil.Process(os.getpid())
                    end_memory = process.memory_info().rss / 1024 / 1024  # MB
                    end_cpu = process.cpu_percent()
                    memory_usage = end_memory - start_memory
                    cpu_usage = (start_cpu + end_cpu) / 2  # 平均CPU使用率
                except ImportError:
                    pass  # psutil未安装，使用默认值0
                except Exception as e:
                    logger.debug(f"获取结束资源信息失败: {e}")
                
                # 记录性能指标
                try:
                    collector = get_metrics_collector()
                    collector.record_performance(
                        operation_name=operation_name,
                        start_time=start_time,
                        end_time=end_time,
                        memory_usage=memory_usage,
                        cpu_usage=cpu_usage,
                        success=success,
                        error_message=error_message
                    )
                except Exception as monitor_error:
                    logger.error(f"性能监控记录失败: {monitor_error}")
        
        return wrapper
    return decorator


class LengthConfigManager:
    """长度配置管理器"""
    
    def __init__(self, config_path: str = "config/length_config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        logger.info(f"长度配置管理器已初始化: {config_path}")
    
    def _load_config(self) -> LengthConfig:
        """
        加载配置文件
        
        Returns:
            LengthConfig: 长度配置对象
        """
        return safe_config_loading(self.config_path)
    
    def reload_config(self) -> bool:
        """
        重新加载配置文件
        
        Returns:
            bool: 是否成功重新加载
        """
        try:
            new_config = safe_config_loading(self.config_path)
            self.config = new_config
            logger.info("配置文件重新加载成功")
            return True
        except Exception as e:
            logger.error(f"配置文件重新加载失败: {e}")
            return False
    
    def update_config(self, **kwargs) -> bool:
        """
        更新配置参数
        
        Args:
            **kwargs: 配置参数
            
        Returns:
            bool: 是否成功更新
        """
        try:
            # 更新内存中的配置
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.info(f"配置参数已更新: {key} = {value}")
                else:
                    logger.warning(f"未知的配置参数: {key}")
            
            return True
        except Exception as e:
            logger.error(f"配置更新失败: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        保存当前配置到文件
        
        Returns:
            bool: 是否成功保存
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # 转换为字典格式
            config_dict = {
                'base_ratios': self.config.base_ratios,
                'density_multipliers': self.config.density_multipliers,
                'chapter_ranges': self.config.chapter_ranges,
                'min_article_length': self.config.min_article_length,
                'max_article_length': self.config.max_article_length,
                'length_tolerance': self.config.length_tolerance
            }
            
            # 写入文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logger.info(f"配置已保存到: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, any]:
        """
        获取配置摘要
        
        Returns:
            Dict: 配置摘要信息
        """
        return {
            "config_path": self.config_path,
            "base_ratios": self.config.base_ratios,
            "density_multipliers": self.config.density_multipliers,
            "chapter_ranges": self.config.chapter_ranges,
            "min_article_length": self.config.min_article_length,
            "max_article_length": self.config.max_article_length,
            "length_tolerance": self.config.length_tolerance
        }
    
    def _safe_save_monitoring_data(self, status: LengthStatus):
        """
        安全保存监控数据
        
        Args:
            status: 长度状态
        """
        try:
            monitoring_data = {
                "task_id": self.task_id,
                "length_target": asdict(self.length_target),
                "current_status": asdict(status),
                "chapter_records": [asdict(record) for record in self.chapter_records],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.monitoring_data_path, 'w', encoding='utf-8') as f:
                json.dump(monitoring_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"保存监控数据失败: {e}")
    
    def _safe_log_monitoring_status(self, status: LengthStatus, chapter_record: ChapterLengthRecord):
        """
        安全记录监控状态日志
        
        Args:
            status: 长度状态
            chapter_record: 章节记录
        """
        try:
            logger.info(f"章节{chapter_record.chapter_index + 1}监控: "
                       f"长度={chapter_record.content_length}字, "
                       f"目标={chapter_record.target_length}字, "
                       f"偏差={chapter_record.deviation_ratio:.1%}")
            
            logger.info(f"总体进度: {status.progress_ratio:.1%}, "
                       f"当前总长度={status.current_length}字, "
                       f"预测最终长度={status.predicted_final_length}字, "
                       f"总偏差={status.deviation_ratio:.1%}")
            
            if status.adjustment_needed:
                recommendation = self.get_adjustment_recommendation(status)
                logger.warning(f"需要调整: {recommendation['strategy']}")
                
        except Exception as e:
            logger.error(f"记录监控日志失败: {e}")
    
    def _predict_final_length(self, completed_chapters: int) -> int:
        """
        预测最终文章长度
        
        Args:
            completed_chapters: 已完成章节数
            
        Returns:
            int: 预测的最终长度
        """
        if completed_chapters == 0:
            return self.length_target.target_length
        
        # 计算已完成章节的平均长度
        total_completed_length = sum(record.content_length for record in self.chapter_records)
        avg_chapter_length = total_completed_length / completed_chapters
        
        # 预测剩余章节长度
        remaining_chapters = self.length_target.chapter_count - completed_chapters
        predicted_remaining_length = remaining_chapters * avg_chapter_length
        
        return int(total_completed_length + predicted_remaining_length)
    
    def _get_adjustment_type(self, deviation_ratio: float) -> str:
        """
        确定调整类型
        
        Args:
            deviation_ratio: 偏差比例
            
        Returns:
            str: 调整类型
        """
        if deviation_ratio > self.deviation_threshold:
            return "compress"  # 内容过长，需要压缩
        elif deviation_ratio < -self.deviation_threshold:
            return "expand"    # 内容过短，需要扩展
        else:
            return "maintain"  # 保持当前策略
    
    def get_adjustment_recommendation(self, status: LengthStatus) -> Dict[str, any]:
        """
        获取调整建议
        
        Args:
            status: 当前长度状态
            
        Returns:
            Dict: 调整建议
        """
        recommendation = {
            "adjustment_needed": status.adjustment_needed,
            "adjustment_type": status.adjustment_type,
            "severity": self._calculate_adjustment_severity(status.deviation_ratio),
            "target_adjustment": 0,
            "strategy": "",
            "remaining_chapters_target": 0
        }
        
        if not status.adjustment_needed:
            recommendation["strategy"] = "继续按当前策略生成"
            recommendation["remaining_chapters_target"] = self.length_target.avg_chapter_length
            return recommendation
        
        # 计算需要调整的长度
        length_gap = status.predicted_final_length - self.length_target.target_length
        remaining_chapters = status.remaining_chapters
        
        if remaining_chapters > 0:
            adjustment_per_chapter = length_gap / remaining_chapters
            recommendation["target_adjustment"] = int(adjustment_per_chapter)
            recommendation["remaining_chapters_target"] = max(
                500,  # 最小章节长度
                self.length_target.avg_chapter_length - adjustment_per_chapter
            )
        
        # 生成策略建议
        if status.adjustment_type == "compress":
            recommendation["strategy"] = f"后续章节需要压缩内容，建议每章节减少约{abs(recommendation['target_adjustment'])}字"
        elif status.adjustment_type == "expand":
            recommendation["strategy"] = f"后续章节需要扩展内容，建议每章节增加约{recommendation['target_adjustment']}字"
        
        return recommendation
    
    def _calculate_adjustment_severity(self, deviation_ratio: float) -> str:
        """
        计算调整严重程度
        
        Args:
            deviation_ratio: 偏差比例
            
        Returns:
            str: 严重程度
        """
        abs_deviation = abs(deviation_ratio)
        if abs_deviation < 0.1:
            return "轻微"
        elif abs_deviation < 0.3:
            return "中等"
        elif abs_deviation < 0.5:
            return "严重"
        else:
            return "极严重"
    
    def _save_monitoring_data(self, status: LengthStatus):
        """
        持久化监控数据
        
        Args:
            status: 长度状态
        """
        try:
            monitoring_data = {
                "task_id": self.task_id,
                "length_target": asdict(self.length_target),
                "current_status": asdict(status),
                "chapter_records": [asdict(record) for record in self.chapter_records],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.monitoring_data_path, 'w', encoding='utf-8') as f:
                json.dump(monitoring_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"保存监控数据失败: {e}")
    
    def _log_monitoring_status(self, status: LengthStatus, chapter_record: ChapterLengthRecord):
        """
        记录监控状态日志
        
        Args:
            status: 长度状态
            chapter_record: 章节记录
        """
        logger.info(f"章节{chapter_record.chapter_index + 1}监控: "
                   f"长度={chapter_record.content_length}字, "
                   f"目标={chapter_record.target_length}字, "
                   f"偏差={chapter_record.deviation_ratio:.1%}")
        
        logger.info(f"总体进度: {status.progress_ratio:.1%}, "
                   f"当前总长度={status.current_length}字, "
                   f"预测最终长度={status.predicted_final_length}字, "
                   f"总偏差={status.deviation_ratio:.1%}")
        
        if status.adjustment_needed:
            recommendation = self.get_adjustment_recommendation(status)
            logger.warning(f"需要调整: {recommendation['strategy']}")
    
    def load_monitoring_data(self) -> Optional[Dict]:
        """
        加载监控数据
        
        Returns:
            Optional[Dict]: 监控数据，如果文件不存在返回None
        """
        try:
            if self.monitoring_data_path.exists():
                with open(self.monitoring_data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载监控数据失败: {e}")
        return None
    
    def get_monitoring_summary(self) -> Dict[str, any]:
        """
        获取监控摘要
        
        Returns:
            Dict: 监控摘要信息
        """
        if not self.chapter_records:
            return {"status": "未开始监控"}
        
        total_length = sum(record.content_length for record in self.chapter_records)
        completed_chapters = len(self.chapter_records)
        avg_chapter_length = total_length / completed_chapters if completed_chapters > 0 else 0
        
        return {
            "task_id": self.task_id,
            "completed_chapters": completed_chapters,
            "total_chapters": self.length_target.chapter_count,
            "current_total_length": total_length,
            "target_length": self.length_target.target_length,
            "avg_chapter_length": int(avg_chapter_length),
            "target_avg_chapter_length": self.length_target.avg_chapter_length,
            "progress_percentage": (completed_chapters / self.length_target.chapter_count) * 100,
            "predicted_final_length": self._safe_predict_final_length(completed_chapters),
            "on_track": abs(total_length - (self.length_target.target_length * completed_chapters / self.length_target.chapter_count)) < (self.length_target.target_length * self.deviation_threshold)
        }


class LengthAdjustmentEngine:
    """长度调整引擎，实现动态调整策略"""
    
    def __init__(self, length_target: LengthTarget, task_id: str = None):
        """
        初始化调整引擎
        
        Args:
            length_target: 长度目标
            task_id: 任务ID
        """
        self.length_target = length_target
        self.task_id = task_id or f"adj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.adjustment_records: List[AdjustmentRecord] = []
        self.adjustment_history_path = Path(f"logs/length_adjustments/{self.task_id}.json")
        
        # 调整策略配置
        self.strategy_configs = {
            "gradual": {
                "max_adjustment_per_chapter": 0.3,  # 最大调整30%
                "compensation_factor": 0.8,         # 补偿系数
                "priority_threshold": 0.2           # 优先级阈值
            },
            "aggressive": {
                "max_adjustment_per_chapter": 0.5,  # 最大调整50%
                "compensation_factor": 1.2,         # 补偿系数
                "priority_threshold": 0.1           # 优先级阈值
            },
            "conservative": {
                "max_adjustment_per_chapter": 0.15, # 最大调整15%
                "compensation_factor": 0.6,         # 补偿系数
                "priority_threshold": 0.3           # 优先级阈值
            }
        }
        
        # 确保调整历史目录存在
        self.adjustment_history_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"长度调整引擎已初始化: 任务ID={self.task_id}")
    
    def detect_deviation(self, status: LengthStatus) -> bool:
        """
        检测长度偏差
        
        Args:
            status: 长度状态
            
        Returns:
            bool: 是否需要调整
        """
        # 基础偏差检测
        basic_deviation = abs(status.deviation_ratio) > 0.3
        
        # 趋势偏差检测（连续3个章节都偏离）
        trend_deviation = self._detect_trend_deviation()
        
        # 预测偏差检测（预测最终长度严重偏离目标）
        prediction_deviation = abs(status.predicted_final_length - status.target_length) > (status.target_length * 0.4)
        
        return basic_deviation or trend_deviation or prediction_deviation
    
    def _detect_trend_deviation(self) -> bool:
        """
        检测趋势偏差
        
        Returns:
            bool: 是否存在趋势偏差
        """
        if len(self.adjustment_records) < 3:
            return False
        
        # 检查最近3次调整是否都是同一方向
        recent_adjustments = self.adjustment_records[-3:]
        adjustment_types = [record.adjustment_type for record in recent_adjustments]
        
        # 如果连续3次都是扩展或压缩，说明存在趋势偏差
        return (all(adj_type == "expand" for adj_type in adjustment_types) or 
                all(adj_type == "compress" for adj_type in adjustment_types))
    
    def generate_adjustment_strategy(self, status: LengthStatus) -> AdjustmentStrategy:
        """
        生成调整策略
        
        Args:
            status: 长度状态
            
        Returns:
            AdjustmentStrategy: 调整策略
        """
        # 确定策略类型
        strategy_type = self._determine_strategy_type(status)
        
        # 计算目标章节长度
        target_chapter_length = self._calculate_adjusted_chapter_length(status, strategy_type)
        
        # 确定内容详细程度
        content_detail_level = self._determine_content_detail_level(status, target_chapter_length)
        
        # 生成提示词调整
        prompt_adjustments = self._generate_prompt_adjustments(status, content_detail_level)
        
        # 计算补偿系数
        compensation_factor = self._calculate_compensation_factor(status, strategy_type)
        
        # 确定优先调整区域
        priority_areas = self._identify_priority_areas(status)
        
        strategy = AdjustmentStrategy(
            strategy_type=strategy_type,
            target_chapter_length=target_chapter_length,
            content_detail_level=content_detail_level,
            prompt_adjustments=prompt_adjustments,
            compensation_factor=compensation_factor,
            priority_areas=priority_areas
        )
        
        logger.info(f"生成调整策略: {strategy_type}, 目标章节长度={target_chapter_length}, "
                   f"详细程度={content_detail_level}")
        
        return strategy
    
    def _determine_strategy_type(self, status: LengthStatus) -> str:
        """
        确定策略类型
        
        Args:
            status: 长度状态
            
        Returns:
            str: 策略类型
        """
        abs_deviation = abs(status.deviation_ratio)
        remaining_ratio = status.remaining_chapters / self.length_target.chapter_count
        
        # 如果偏差很大且剩余章节较少，使用激进策略
        if abs_deviation > 0.5 and remaining_ratio < 0.3:
            return "aggressive"
        # 如果偏差较小，使用保守策略
        elif abs_deviation < 0.2:
            return "conservative"
        # 其他情况使用渐进策略
        else:
            return "gradual"
    
    def _calculate_adjusted_chapter_length(self, status: LengthStatus, strategy_type: str) -> int:
        """
        计算调整后的章节长度
        
        Args:
            status: 长度状态
            strategy_type: 策略类型
            
        Returns:
            int: 调整后的章节长度
        """
        config = self.strategy_configs[strategy_type]
        max_adjustment = config["max_adjustment_per_chapter"]
        
        # 计算需要的总调整量
        length_gap = status.predicted_final_length - status.target_length
        
        if status.remaining_chapters > 0:
            # 计算每章节需要调整的量
            adjustment_per_chapter = length_gap / status.remaining_chapters
            
            # 限制调整幅度
            max_adjustment_amount = self.length_target.avg_chapter_length * max_adjustment
            adjustment_per_chapter = max(-max_adjustment_amount, 
                                       min(adjustment_per_chapter, max_adjustment_amount))
            
            # 计算调整后的目标长度
            adjusted_length = self.length_target.avg_chapter_length - adjustment_per_chapter
            
            # 确保不低于最小长度
            return max(500, int(adjusted_length))
        
        return self.length_target.avg_chapter_length
    
    def _determine_content_detail_level(self, status: LengthStatus, target_length: int) -> str:
        """
        确定内容详细程度
        
        Args:
            status: 长度状态
            target_length: 目标长度
            
        Returns:
            str: 详细程度
        """
        avg_length = self.length_target.avg_chapter_length
        
        if target_length < avg_length * 0.7:
            return "concise"    # 简洁
        elif target_length > avg_length * 1.3:
            return "detailed"   # 详细
        else:
            return "moderate"   # 适度
    
    def _generate_prompt_adjustments(self, status: LengthStatus, detail_level: str) -> Dict[str, str]:
        """
        生成提示词调整
        
        Args:
            status: 长度状态
            detail_level: 详细程度
            
        Returns:
            Dict[str, str]: 提示词调整
        """
        adjustments = {}
        
        if detail_level == "concise":
            adjustments.update({
                "length_instruction": "请保持内容简洁精炼，重点突出核心观点",
                "detail_instruction": "避免过多的细节描述和举例说明",
                "structure_instruction": "使用简洁的段落结构，每个要点直接明了"
            })
        elif detail_level == "detailed":
            adjustments.update({
                "length_instruction": "请提供详细深入的分析，充分展开论述",
                "detail_instruction": "包含具体的案例分析和详细的技术说明",
                "structure_instruction": "使用丰富的段落结构，提供充分的背景信息"
            })
        else:  # moderate
            adjustments.update({
                "length_instruction": "请保持适度的详细程度，平衡深度和简洁性",
                "detail_instruction": "包含必要的解释和适当的举例",
                "structure_instruction": "使用清晰的段落结构，保持逻辑性"
            })
        
        # 添加长度指导
        target_length = self._calculate_adjusted_chapter_length(status, "gradual")
        adjustments["target_length"] = f"目标章节长度约{target_length}字"
        
        return adjustments
    
    def _calculate_compensation_factor(self, status: LengthStatus, strategy_type: str) -> float:
        """
        计算补偿系数
        
        Args:
            status: 长度状态
            strategy_type: 策略类型
            
        Returns:
            float: 补偿系数
        """
        base_factor = self.strategy_configs[strategy_type]["compensation_factor"]
        
        # 根据偏差程度调整补偿系数
        deviation_multiplier = 1.0 + abs(status.deviation_ratio)
        
        # 根据剩余章节比例调整
        remaining_ratio = status.remaining_chapters / self.length_target.chapter_count
        remaining_multiplier = 1.0 + (1.0 - remaining_ratio) * 0.5
        
        return base_factor * deviation_multiplier * remaining_multiplier
    
    def _identify_priority_areas(self, status: LengthStatus) -> List[str]:
        """
        识别优先调整区域
        
        Args:
            status: 长度状态
            
        Returns:
            List[str]: 优先区域列表
        """
        priority_areas = []
        
        if status.adjustment_type == "compress":
            priority_areas.extend([
                "减少重复性描述",
                "精简案例说明",
                "压缩背景介绍",
                "合并相似观点"
            ])
        elif status.adjustment_type == "expand":
            priority_areas.extend([
                "增加技术细节",
                "补充案例分析",
                "扩展实践建议",
                "深化理论阐述"
            ])
        
        return priority_areas
    
    def apply_adjustment(self, chapter_index: int, original_target: int, 
                        strategy: AdjustmentStrategy, reason: str) -> AdjustmentRecord:
        """
        应用调整策略
        
        Args:
            chapter_index: 章节索引
            original_target: 原始目标长度
            strategy: 调整策略
            reason: 调整原因
            
        Returns:
            AdjustmentRecord: 调整记录
        """
        adjustment_amount = strategy.target_chapter_length - original_target
        
        record = AdjustmentRecord(
            chapter_index=chapter_index,
            adjustment_type=strategy.strategy_type,
            original_target=original_target,
            adjusted_target=strategy.target_chapter_length,
            adjustment_amount=adjustment_amount,
            reason=reason
        )
        
        self.adjustment_records.append(record)
        self._save_adjustment_history()
        
        logger.info(f"应用调整: 章节{chapter_index + 1}, "
                   f"原目标={original_target}字, 新目标={strategy.target_chapter_length}字, "
                   f"调整量={adjustment_amount}字")
        
        return record
    
    def evaluate_adjustment_effectiveness(self, record: AdjustmentRecord, 
                                        actual_length: int) -> float:
        """
        评估调整效果
        
        Args:
            record: 调整记录
            actual_length: 实际生成长度
            
        Returns:
            float: 效果评分（0-1）
        """
        target_length = record.adjusted_target
        deviation = abs(actual_length - target_length) / target_length
        
        # 计算效果评分（偏差越小，评分越高）
        effectiveness = max(0.0, 1.0 - deviation * 2)
        
        # 更新记录
        record.effectiveness_score = effectiveness
        self._save_adjustment_history()
        
        logger.info(f"调整效果评估: 章节{record.chapter_index + 1}, "
                   f"目标={target_length}字, 实际={actual_length}字, "
                   f"效果评分={effectiveness:.2f}")
        
        return effectiveness
    
    def _save_adjustment_history(self):
        """保存调整历史"""
        try:
            history_data = {
                "task_id": self.task_id,
                "length_target": asdict(self.length_target),
                "adjustment_records": [asdict(record) for record in self.adjustment_records],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.adjustment_history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"保存调整历史失败: {e}")
    
    def get_adjustment_analytics(self) -> Dict[str, any]:
        """
        获取调整分析数据
        
        Returns:
            Dict: 调整分析数据
        """
        if not self.adjustment_records:
            return {"status": "无调整记录"}
        
        # 统计调整类型分布
        adjustment_types = [record.adjustment_type for record in self.adjustment_records]
        type_distribution = {
            "expand": adjustment_types.count("expand"),
            "compress": adjustment_types.count("compress"),
            "maintain": adjustment_types.count("maintain")
        }
        
        # 计算平均效果评分
        effectiveness_scores = [record.effectiveness_score for record in self.adjustment_records 
                              if record.effectiveness_score is not None]
        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores) if effectiveness_scores else 0
        
        # 计算总调整量
        total_adjustment = sum(abs(record.adjustment_amount) for record in self.adjustment_records)
        
        return {
            "task_id": self.task_id,
            "total_adjustments": len(self.adjustment_records),
            "adjustment_type_distribution": type_distribution,
            "average_effectiveness": avg_effectiveness,
            "total_adjustment_amount": total_adjustment,
            "most_recent_adjustment": asdict(self.adjustment_records[-1]) if self.adjustment_records else None
        }


class CompensationGenerator:
    """补偿生成器，确保目标长度达成"""
    
    def __init__(self, length_target: LengthTarget, task_id: str = None):
        """
        初始化补偿生成器
        
        Args:
            length_target: 长度目标
            task_id: 任务ID
        """
        self.length_target = length_target
        self.task_id = task_id or f"comp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.compensation_threshold = 0.15  # 补偿阈值15%
        
        logger.info(f"补偿生成器已初始化: 任务ID={self.task_id}")
    
    def assess_compensation_need(self, final_length: int) -> Dict[str, any]:
        """
        评估补偿需求
        
        Args:
            final_length: 最终文章长度
            
        Returns:
            Dict: 补偿需求评估
        """
        target_length = self.length_target.target_length
        length_gap = final_length - target_length
        gap_ratio = length_gap / target_length
        
        needs_compensation = abs(gap_ratio) > self.compensation_threshold
        
        assessment = {
            "needs_compensation": needs_compensation,
            "final_length": final_length,
            "target_length": target_length,
            "length_gap": length_gap,
            "gap_ratio": gap_ratio,
            "compensation_type": "expand" if length_gap < 0 else "compress",
            "severity": self._assess_severity(abs(gap_ratio))
        }
        
        if needs_compensation:
            logger.warning(f"需要补偿生成: 最终长度={final_length}字, "
                         f"目标长度={target_length}字, 缺口={length_gap}字")
        else:
            logger.info(f"无需补偿: 最终长度={final_length}字在可接受范围内")
        
        return assessment
    
    def _assess_severity(self, gap_ratio: float) -> str:
        """评估缺口严重程度"""
        if gap_ratio < 0.1:
            return "轻微"
        elif gap_ratio < 0.2:
            return "中等"
        elif gap_ratio < 0.3:
            return "严重"
        else:
            return "极严重"
    
    def generate_compensation_strategy(self, assessment: Dict[str, any]) -> Dict[str, any]:
        """
        生成补偿策略
        
        Args:
            assessment: 补偿需求评估
            
        Returns:
            Dict: 补偿策略
        """
        if not assessment["needs_compensation"]:
            return {"strategy": "无需补偿"}
        
        compensation_type = assessment["compensation_type"]
        length_gap = abs(assessment["length_gap"])
        severity = assessment["severity"]
        
        strategy = {
            "compensation_type": compensation_type,
            "target_compensation": length_gap,
            "method": self._determine_compensation_method(compensation_type, severity),
            "content_areas": self._identify_compensation_areas(compensation_type),
            "prompt_template": self._generate_compensation_prompt(compensation_type, length_gap)
        }
        
        logger.info(f"生成补偿策略: {compensation_type}, 目标补偿={length_gap}字, "
                   f"方法={strategy['method']}")
        
        return strategy
    
    def _determine_compensation_method(self, compensation_type: str, severity: str) -> str:
        """确定补偿方法"""
        if compensation_type == "expand":
            if severity in ["轻微", "中等"]:
                return "章节扩展"  # 在现有章节中添加内容
            else:
                return "新增章节"  # 添加新的章节
        else:  # compress
            if severity in ["轻微", "中等"]:
                return "内容精简"  # 精简现有内容
            else:
                return "章节合并"  # 合并相似章节
    
    def _identify_compensation_areas(self, compensation_type: str) -> List[str]:
        """识别补偿区域"""
        if compensation_type == "expand":
            return [
                "深化技术分析",
                "增加实践案例",
                "扩展应用场景",
                "补充最佳实践",
                "添加故障排除指南"
            ]
        else:  # compress
            return [
                "合并重复内容",
                "精简冗余描述",
                "压缩背景信息",
                "简化技术细节",
                "删除次要案例"
            ]
    
    def _generate_compensation_prompt(self, compensation_type: str, target_length: int) -> str:
        """生成补偿提示词"""
        if compensation_type == "expand":
            return f"""
请为文章生成补充内容，目标增加约{target_length}字。

补充要求：
1. 深化现有章节的技术分析
2. 增加具体的实践案例和应用场景
3. 补充最佳实践建议和故障排除指南
4. 确保补充内容与原文风格一致
5. 保持逻辑连贯性和可读性

请生成高质量的补充内容。
"""
        else:  # compress
            return f"""
请对文章进行精简，目标减少约{target_length}字。

精简要求：
1. 删除重复和冗余的描述
2. 合并相似的观点和案例
3. 精简过于详细的技术细节
4. 保留核心观点和关键信息
5. 确保精简后逻辑仍然完整

请保持文章的核心价值和可读性。
"""
    
    def evaluate_adjustment_effectiveness(self, record: AdjustmentRecord, 
                                        actual_length: int) -> float:
        """
        评估调整效果
        
        Args:
            record: 调整记录
            actual_length: 实际生成长度
            
        Returns:
            float: 效果评分（0-1）
        """
        target_length = record.adjusted_target
        deviation = abs(actual_length - target_length) / target_length
        
        # 计算效果评分（偏差越小，评分越高）
        effectiveness = max(0.0, 1.0 - deviation * 2)
        
        # 更新记录
        record.effectiveness_score = effectiveness
        self._save_adjustment_history()
        
        logger.info(f"调整效果评估: 章节{record.chapter_index + 1}, "
                   f"目标={target_length}字, 实际={actual_length}字, "
                   f"效果评分={effectiveness:.2f}")
        
        return effectiveness
    
    def _save_adjustment_history(self):
        """保存调整历史"""
        try:
            history_data = {
                "task_id": self.task_id,
                "length_target": asdict(self.length_target),
                "adjustment_records": [asdict(record) for record in self.adjustment_records],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.adjustment_history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"保存调整历史失败: {e}")
    
    def get_adjustment_analytics(self) -> Dict[str, any]:
        """
        获取调整分析数据
        
        Returns:
            Dict: 调整分析数据
        """
        if not self.adjustment_records:
            return {"status": "无调整记录"}
        
        # 统计调整类型分布
        adjustment_types = [record.adjustment_type for record in self.adjustment_records]
        type_distribution = {
            "expand": adjustment_types.count("expand"),
            "compress": adjustment_types.count("compress"),
            "maintain": adjustment_types.count("maintain")
        }
        
        # 计算平均效果评分
        effectiveness_scores = [record.effectiveness_score for record in self.adjustment_records 
                              if record.effectiveness_score is not None]
        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores) if effectiveness_scores else 0
        
        # 计算总调整量
        total_adjustment = sum(abs(record.adjustment_amount) for record in self.adjustment_records)
        
        return {
            "task_id": self.task_id,
            "total_adjustments": len(self.adjustment_records),
            "adjustment_type_distribution": type_distribution,
            "average_effectiveness": avg_effectiveness,
            "total_adjustment_amount": total_adjustment,
            "most_recent_adjustment": asdict(self.adjustment_records[-1]) if self.adjustment_records else None
        }


class LengthConfigManager:
    """长度配置管理器"""
    
    def __init__(self, config_path: str = "config/length_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> LengthConfig:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        logger.info(f"成功加载长度配置: {self.config_path}")
                        return LengthConfig(**data)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        
        # 使用默认配置
        logger.info("使用默认长度配置")
        return LengthConfig()
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 将配置转换为字典
            config_dict = {
                'base_ratios': self.config.base_ratios,
                'density_multipliers': self.config.density_multipliers,
                'chapter_ranges': {k: list(v) for k, v in self.config.chapter_ranges.items()},
                'min_article_length': self.config.min_article_length,
                'max_article_length': self.config.max_article_length,
                'length_tolerance': self.config.length_tolerance
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"配置已保存到: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def update_config(self, **kwargs) -> bool:
        """更新配置参数"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.info(f"配置参数已更新: {key} = {value}")
                else:
                    logger.warning(f"未知的配置参数: {key}")
            
            return self.save_config()
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    def reload_config(self) -> bool:
        """重新加载配置"""
        try:
            self.config = self._load_config()
            logger.info("配置已重新加载")
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, any]:
        """获取配置摘要"""
        return {
            "config_path": str(self.config_path),
            "base_ratios": self.config.base_ratios,
            "density_multipliers": self.config.density_multipliers,
            "chapter_ranges": self.config.chapter_ranges,
            "min_article_length": self.config.min_article_length,
            "max_article_length": self.config.max_article_length,
            "length_tolerance": self.config.length_tolerance
        }

