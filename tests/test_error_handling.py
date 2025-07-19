"""
测试错误处理和监控功能
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from pathlib import Path

from src.reinvent_insight.adaptive_length import (
    LengthAdaptationError,
    VideoAnalysisError,
    LengthCalculationError,
    ConfigurationError,
    MonitoringError,
    VideoAnalyzer,
    LengthCalculator,
    LengthMonitor,
    LengthConfig,
    VideoAnalysisResult,
    LengthTarget,
    safe_video_analysis,
    safe_length_calculation,
    safe_config_loading,
    validate_length_target,
    get_metrics_collector,
    performance_monitor
)
from src.reinvent_insight.downloader import VideoMetadata


class TestErrorHandling:
    """测试错误处理机制"""
    
    def test_video_analysis_error_empty_subtitle(self):
        """测试空字幕的错误处理"""
        analyzer = VideoAnalyzer()
        metadata = Mock()
        
        with pytest.raises(VideoAnalysisError, match="字幕文本为空或无效"):
            analyzer.analyze(metadata, "")
    
    def test_video_analysis_error_none_subtitle(self):
        """测试None字幕的错误处理"""
        analyzer = VideoAnalyzer()
        metadata = Mock()
        
        with pytest.raises(VideoAnalysisError, match="字幕文本为空或无效"):
            analyzer.analyze(metadata, None)
    
    def test_safe_video_analysis_fallback(self):
        """测试安全视频分析的降级处理"""
        metadata = Mock()
        
        # 测试正常情况
        result = safe_video_analysis(metadata, "This is a test subtitle with some words")
        assert isinstance(result, VideoAnalysisResult)
        assert result.subtitle_word_count > 0
        
        # 测试降级情况
        result = safe_video_analysis(metadata, "", fallback_duration=15.0)
        assert isinstance(result, VideoAnalysisResult)
        assert result.duration_minutes == 15.0
        assert result.video_category == "medium"
    
    def test_length_calculation_error_empty_analysis(self):
        """测试空分析结果的错误处理"""
        config = LengthConfig()
        calculator = LengthCalculator(config)
        
        with pytest.raises(LengthCalculationError, match="视频分析结果为空"):
            calculator.calculate_target_length(None)
    
    def test_length_calculation_error_invalid_word_count(self):
        """测试无效字数的错误处理"""
        config = LengthConfig()
        calculator = LengthCalculator(config)
        
        analysis = VideoAnalysisResult(
            duration_minutes=30.0,
            subtitle_word_count=0,  # 无效字数
            words_per_minute=150.0,
            video_category="medium",
            density_level="medium",
            complexity_score=0.5
        )
        
        with pytest.raises(LengthCalculationError, match="字幕字数无效"):
            calculator.calculate_target_length(analysis)
    
    def test_safe_length_calculation_fallback(self):
        """测试安全长度计算的降级处理"""
        # 测试正常情况
        analysis = VideoAnalysisResult(
            duration_minutes=30.0,
            subtitle_word_count=5000,
            words_per_minute=150.0,
            video_category="medium",
            density_level="medium",
            complexity_score=0.5
        )
        
        result = safe_length_calculation(analysis)
        assert isinstance(result, LengthTarget)
        assert result.target_length > 0
        
        # 测试降级情况（无效分析结果）
        invalid_analysis = VideoAnalysisResult(
            duration_minutes=30.0,
            subtitle_word_count=0,  # 无效字数
            words_per_minute=150.0,
            video_category="medium",
            density_level="medium",
            complexity_score=0.5
        )
        
        result = safe_length_calculation(invalid_analysis)
        assert isinstance(result, LengthTarget)
        assert result.target_length == 20000  # 默认值
    
    def test_monitoring_error_invalid_chapter_index(self):
        """测试无效章节索引的错误处理"""
        target = LengthTarget(
            target_length=20000,
            min_length=16000,
            max_length=24000,
            chapter_count=15,
            avg_chapter_length=1333
        )
        
        monitor = LengthMonitor(target)
        
        with pytest.raises(MonitoringError, match="章节索引无效"):
            monitor.monitor_chapter("test content", -1)  # 负索引
        
        with pytest.raises(MonitoringError, match="章节索引无效"):
            monitor.monitor_chapter("test content", 20)  # 超出范围
    
    def test_monitoring_error_invalid_content_type(self):
        """测试无效内容类型的错误处理"""
        target = LengthTarget(
            target_length=20000,
            min_length=16000,
            max_length=24000,
            chapter_count=15,
            avg_chapter_length=1333
        )
        
        monitor = LengthMonitor(target)
        
        with pytest.raises(MonitoringError, match="章节内容必须是字符串"):
            monitor.monitor_chapter(123, 0)  # 非字符串内容
    
    def test_safe_config_loading_missing_file(self):
        """测试配置文件不存在的处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "nonexistent.yaml")
            config = safe_config_loading(config_path)
            
            assert isinstance(config, LengthConfig)
            assert config.base_ratios["medium"] == 0.8  # 默认值
    
    def test_safe_config_loading_invalid_file(self):
        """测试无效配置文件的处理"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")  # 无效YAML
            f.flush()
            
            try:
                config = safe_config_loading(f.name)
                assert isinstance(config, LengthConfig)
                assert config.base_ratios["medium"] == 0.8  # 默认值
            finally:
                os.unlink(f.name)
    
    def test_validate_length_target_valid(self):
        """测试有效长度目标的验证"""
        target = LengthTarget(
            target_length=20000,
            min_length=16000,
            max_length=24000,
            chapter_count=15,
            avg_chapter_length=1333
        )
        
        assert validate_length_target(target) is True
    
    def test_validate_length_target_invalid(self):
        """测试无效长度目标的验证"""
        # 测试None
        assert validate_length_target(None) is False
        
        # 测试无效长度
        invalid_target = LengthTarget(
            target_length=0,  # 无效长度
            min_length=16000,
            max_length=24000,
            chapter_count=15,
            avg_chapter_length=1333
        )
        assert validate_length_target(invalid_target) is False
        
        # 测试无效范围
        invalid_range_target = LengthTarget(
            target_length=20000,
            min_length=25000,  # 最小值大于最大值
            max_length=24000,
            chapter_count=15,
            avg_chapter_length=1333
        )
        assert validate_length_target(invalid_range_target) is False


class TestMonitoringSystem:
    """测试监控系统"""
    
    def test_metrics_collector_initialization(self):
        """测试指标收集器初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = get_metrics_collector()
            assert collector is not None
    
    def test_performance_monitor_decorator(self):
        """测试性能监控装饰器"""
        @performance_monitor("test_operation")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    def test_performance_monitor_decorator_with_error(self):
        """测试性能监控装饰器处理错误"""
        @performance_monitor("test_operation_error")
        def test_function_with_error():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            test_function_with_error()
    
    def test_safe_calculation_functions_integration(self):
        """测试安全计算函数的集成"""
        # 创建测试数据
        metadata = Mock()
        subtitle_text = "This is a test subtitle with multiple words for testing purposes"
        
        # 测试完整流程
        analysis = safe_video_analysis(metadata, subtitle_text)
        assert isinstance(analysis, VideoAnalysisResult)
        
        target = safe_length_calculation(analysis)
        assert isinstance(target, LengthTarget)
        
        # 验证结果有效性
        assert validate_length_target(target) is True


if __name__ == "__main__":
    pytest.main([__file__])