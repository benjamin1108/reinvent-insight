"""
自适应内容长度生成模块的单元测试
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock

from src.reinvent_insight.adaptive_length import (
    VideoAnalyzer, LengthCalculator, LengthConfigManager,
    VideoAnalysisResult, LengthTarget, LengthConfig,
    safe_length_calculation
)
from src.reinvent_insight.downloader import VideoMetadata


class TestVideoAnalyzer:
    """VideoAnalyzer类的单元测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.analyzer = VideoAnalyzer()
        self.mock_metadata = VideoMetadata(
            title="Test Video",
            upload_date="20240101",
            video_url="https://example.com/video"
        )
    
    def test_analyze_short_video(self):
        """测试短视频分析"""
        # 模拟短视频字幕（约10分钟，1500字）
        subtitle_text = " ".join(["word"] * 1500)
        
        result = self.analyzer.analyze(self.mock_metadata, subtitle_text)
        
        assert isinstance(result, VideoAnalysisResult)
        assert result.subtitle_word_count == 1500
        assert result.video_category == "short"
        assert result.density_level in ["low", "medium", "high"]
        assert 0 <= result.complexity_score <= 1
    
    def test_analyze_medium_video(self):
        """测试中等视频分析"""
        # 模拟中等视频字幕（约40分钟，6000字）
        subtitle_text = " ".join(["word"] * 6000)
        
        result = self.analyzer.analyze(self.mock_metadata, subtitle_text)
        
        assert result.subtitle_word_count == 6000
        assert result.video_category == "medium"
        assert result.duration_minutes > 20
    
    def test_analyze_long_video(self):
        """测试长视频分析"""
        # 模拟长视频字幕（约90分钟，15000字）
        subtitle_text = " ".join(["word"] * 15000)
        
        result = self.analyzer.analyze(self.mock_metadata, subtitle_text)
        
        assert result.subtitle_word_count == 15000
        assert result.video_category == "long"
        assert result.duration_minutes > 60
    
    def test_analyze_extra_long_video(self):
        """测试超长视频分析"""
        # 模拟超长视频字幕（约150分钟，25000字）
        subtitle_text = " ".join(["word"] * 25000)
        
        result = self.analyzer.analyze(self.mock_metadata, subtitle_text)
        
        assert result.subtitle_word_count == 25000
        assert result.video_category == "extra_long"
        assert result.duration_minutes > 120
    
    def test_density_categorization(self):
        """测试信息密度分级"""
        # 直接测试密度分类函数，因为通过字幕估算的密度总是接近175字/分钟
        assert self.analyzer._categorize_by_density(80) == "low"
        assert self.analyzer._categorize_by_density(150) == "medium" 
        assert self.analyzer._categorize_by_density(250) == "high"
        
        # 测试边界值
        assert self.analyzer._categorize_by_density(99) == "low"
        assert self.analyzer._categorize_by_density(100) == "medium"
        assert self.analyzer._categorize_by_density(199) == "medium"
        assert self.analyzer._categorize_by_density(200) == "high"
    
    def test_complexity_score_calculation(self):
        """测试复杂度评分计算"""
        # 技术内容
        tech_text = " ".join([
            "aws", "cloud", "api", "database", "architecture", "security",
            "network", "infrastructure", "deployment", "kubernetes"
        ] * 100)
        
        result_tech = self.analyzer.analyze(self.mock_metadata, tech_text)
        
        # 普通内容
        normal_text = " ".join(["hello", "world", "this", "is", "normal", "content"] * 100)
        result_normal = self.analyzer.analyze(self.mock_metadata, normal_text)
        
        # 技术内容的复杂度应该更高
        assert result_tech.complexity_score > result_normal.complexity_score
    
    def test_empty_subtitle_handling(self):
        """测试空字幕处理"""
        result = self.analyzer.analyze(self.mock_metadata, "")
        
        assert result.subtitle_word_count == 0
        assert result.duration_minutes == 1.0  # 最小值
        assert result.words_per_minute == 0
        assert result.complexity_score == 0.5  # 默认值


class TestLengthCalculator:
    """LengthCalculator类的单元测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.config = LengthConfig()
        self.calculator = LengthCalculator(self.config)
    
    def test_calculate_target_length_short_video(self):
        """测试短视频长度计算"""
        analysis = VideoAnalysisResult(
            duration_minutes=15,
            subtitle_word_count=2000,
            words_per_minute=133,
            video_category="short",
            density_level="medium",
            complexity_score=0.5
        )
        
        result = self.calculator.calculate_target_length(analysis)
        
        assert isinstance(result, LengthTarget)
        assert result.target_length > 0
        assert result.min_length < result.target_length < result.max_length
        assert 8 <= result.chapter_count <= 12  # 短视频章节范围
    
    def test_calculate_target_length_medium_video(self):
        """测试中等视频长度计算"""
        analysis = VideoAnalysisResult(
            duration_minutes=40,
            subtitle_word_count=6000,
            words_per_minute=150,
            video_category="medium",
            density_level="medium",
            complexity_score=0.6
        )
        
        result = self.calculator.calculate_target_length(analysis)
        
        assert 12 <= result.chapter_count <= 16  # 中等视频章节范围
        assert result.avg_chapter_length > 0
    
    def test_calculate_target_length_long_video(self):
        """测试长视频长度计算"""
        analysis = VideoAnalysisResult(
            duration_minutes=90,
            subtitle_word_count=15000,
            words_per_minute=167,
            video_category="long",
            density_level="medium",
            complexity_score=0.7
        )
        
        result = self.calculator.calculate_target_length(analysis)
        
        assert 16 <= result.chapter_count <= 20  # 长视频章节范围
    
    def test_calculate_target_length_extra_long_video(self):
        """测试超长视频长度计算"""
        analysis = VideoAnalysisResult(
            duration_minutes=150,
            subtitle_word_count=25000,
            words_per_minute=167,
            video_category="extra_long",
            density_level="medium",
            complexity_score=0.8
        )
        
        result = self.calculator.calculate_target_length(analysis)
        
        assert 20 <= result.chapter_count <= 25  # 超长视频章节范围
    
    def test_density_adjustment(self):
        """测试密度调整"""
        # 使用更大的字幕字数来避免触及最小长度限制
        base_analysis = VideoAnalysisResult(
            duration_minutes=60,
            subtitle_word_count=15000,  # 增加字数
            words_per_minute=250,
            video_category="long",
            density_level="medium",
            complexity_score=0.5
        )
        
        # 创建三个独立的分析结果对象
        low_analysis = VideoAnalysisResult(
            duration_minutes=base_analysis.duration_minutes,
            subtitle_word_count=base_analysis.subtitle_word_count,
            words_per_minute=base_analysis.words_per_minute,
            video_category=base_analysis.video_category,
            density_level="low",
            complexity_score=base_analysis.complexity_score
        )
        
        medium_analysis = VideoAnalysisResult(
            duration_minutes=base_analysis.duration_minutes,
            subtitle_word_count=base_analysis.subtitle_word_count,
            words_per_minute=base_analysis.words_per_minute,
            video_category=base_analysis.video_category,
            density_level="medium",
            complexity_score=base_analysis.complexity_score
        )
        
        high_analysis = VideoAnalysisResult(
            duration_minutes=base_analysis.duration_minutes,
            subtitle_word_count=base_analysis.subtitle_word_count,
            words_per_minute=base_analysis.words_per_minute,
            video_category=base_analysis.video_category,
            density_level="high",
            complexity_score=base_analysis.complexity_score
        )
        
        result_low = self.calculator.calculate_target_length(low_analysis)
        result_medium = self.calculator.calculate_target_length(medium_analysis)
        result_high = self.calculator.calculate_target_length(high_analysis)
        
        # 低密度应该产生更长的文章，高密度应该产生更短的文章
        assert result_low.target_length > result_medium.target_length > result_high.target_length
    
    def test_boundary_limits(self):
        """测试边界限制"""
        # 测试最小长度限制
        tiny_analysis = VideoAnalysisResult(
            duration_minutes=1,
            subtitle_word_count=100,
            words_per_minute=100,
            video_category="short",
            density_level="high",
            complexity_score=0.1
        )
        
        result_tiny = self.calculator.calculate_target_length(tiny_analysis)
        assert result_tiny.target_length >= self.config.min_article_length
        
        # 测试最大长度限制
        huge_analysis = VideoAnalysisResult(
            duration_minutes=300,
            subtitle_word_count=100000,
            words_per_minute=333,
            video_category="extra_long",
            density_level="low",
            complexity_score=1.0
        )
        
        result_huge = self.calculator.calculate_target_length(huge_analysis)
        assert result_huge.target_length <= self.config.max_article_length


class TestLengthConfigManager:
    """LengthConfigManager类的单元测试"""
    
    def test_default_config_loading(self):
        """测试默认配置加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent_config.yaml"
            manager = LengthConfigManager(str(config_path))
            
            assert isinstance(manager.config, LengthConfig)
            assert manager.config.base_ratios["short"] == 0.7
    
    def test_config_file_loading(self):
        """测试配置文件加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            
            # 创建测试配置文件
            test_config = {
                'base_ratios': {'short': 0.6, 'medium': 0.7, 'long': 0.8, 'extra_long': 0.9},
                'density_multipliers': {'low': 1.3, 'medium': 1.1, 'high': 0.9},
                'min_article_length': 10000,
                'max_article_length': 50000
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(test_config, f)
            
            manager = LengthConfigManager(str(config_path))
            
            assert manager.config.base_ratios["short"] == 0.6
            assert manager.config.density_multipliers["low"] == 1.3
            assert manager.config.min_article_length == 10000
    
    def test_config_saving(self):
        """测试配置保存"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "save_test_config.yaml"
            manager = LengthConfigManager(str(config_path))
            
            # 修改配置
            manager.config.min_article_length = 12000
            
            # 保存配置
            success = manager.save_config()
            assert success
            assert config_path.exists()
            
            # 验证保存的内容
            with open(config_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data['min_article_length'] == 12000
    
    def test_config_updating(self):
        """测试配置更新"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "update_test_config.yaml"
            manager = LengthConfigManager(str(config_path))
            
            # 更新配置
            success = manager.update_config(
                min_article_length=15000,
                max_article_length=45000
            )
            
            assert success
            assert manager.config.min_article_length == 15000
            assert manager.config.max_article_length == 45000
    
    def test_config_reloading(self):
        """测试配置重新加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "reload_test_config.yaml"
            
            # 创建初始配置
            initial_config = {'min_article_length': 8000}
            with open(config_path, 'w') as f:
                yaml.dump(initial_config, f)
            
            manager = LengthConfigManager(str(config_path))
            assert manager.config.min_article_length == 8000
            
            # 外部修改配置文件
            updated_config = {'min_article_length': 12000}
            with open(config_path, 'w') as f:
                yaml.dump(updated_config, f)
            
            # 重新加载
            success = manager.reload_config()
            assert success
            assert manager.config.min_article_length == 12000


class TestSafeLengthCalculation:
    """测试安全长度计算函数"""
    
    def test_successful_calculation(self):
        """测试成功的长度计算"""
        analysis = VideoAnalysisResult(
            duration_minutes=30,
            subtitle_word_count=4000,
            words_per_minute=133,
            video_category="medium",
            density_level="medium",
            complexity_score=0.5
        )
        config = LengthConfig()
        
        result = safe_length_calculation(analysis, config)
        
        assert isinstance(result, LengthTarget)
        assert result.target_length > 0
    
    def test_fallback_on_error(self):
        """测试错误时的降级处理"""
        # 创建一个会导致错误的分析结果
        analysis = VideoAnalysisResult(
            duration_minutes=-1,  # 无效值
            subtitle_word_count=-1,  # 无效值
            words_per_minute=-1,
            video_category="invalid",
            density_level="invalid",
            complexity_score=-1
        )
        
        # 创建一个会导致错误的配置 - 使用None来强制触发异常
        config = None
        
        result = safe_length_calculation(analysis, config)
        
        # 应该返回默认值
        assert isinstance(result, LengthTarget)
        assert result.target_length == 20000
        assert result.chapter_count == 15


if __name__ == "__main__":
    pytest.main([__file__])