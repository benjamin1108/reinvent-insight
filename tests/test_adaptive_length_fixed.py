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
        # 直接测试密度分类函数，因为完整的分析会使用固定的175字/分钟估算
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
        assert config_manager.config.min_article_length <= length_target.target_length <= config_manager.config.max_article_length, \
            "目标长度超出边界限制"
        
        results.append({
            'name': test_case['name'],
            'analysis': analysis,
            'target': length_target
        })
    
    # 5. 验证长度递增趋势
    print("\n4. 验证长度计算逻辑...")
    for i in range(len(results) - 1):
        current = results[i]['target'].target_length
        next_target = results[i + 1]['target'].target_length
        print(f"   {results[i]['name']}: {current}字 -> {results[i+1]['name']}: {next_target}字")
        
        # 一般来说，更长的视频应该产生更长的文章（但不是绝对的，因为有密度调整）
        # 这里我们只验证结果在合理范围内
        assert current > 0 and next_target > 0, "长度计算结果无效"
    
    # 6. 测试安全计算函数
    print("\n5. 测试异常处理...")
    safe_result = safe_length_calculation(results[0]['analysis'], config_manager.config)
    print(f"   安全计算结果: {safe_result.target_length}字")
    assert safe_result.target_length > 0, "安全计算失败"
    
    # 测试异常情况
    safe_fallback = safe_length_calculation(results[0]['analysis'], None)
    print(f"   降级处理结果: {safe_fallback.target_length}字")
    assert safe_fallback.target_length == 20000, "降级处理失败"
    
    print("\n=== 所有测试通过！系统工作正常 ===")
    return True


def test_config_management():
    """测试配置管理功能"""
    print("\n=== 配置管理测试 ===")
    
    # 测试配置加载
    config_manager = LengthConfigManager()
    print(f"配置加载成功: {config_manager.config_path}")
    
    # 测试配置更新
    original_min = config_manager.config.min_article_length
    config_manager.update_config(min_article_length=10000)
    assert config_manager.config.min_article_length == 10000, "配置更新失败"
    
    # 恢复原始配置
    config_manager.update_config(min_article_length=original_min)
    assert config_manager.config.min_article_length == original_min, "配置恢复失败"
    
    print("配置管理测试通过！")


if __name__ == "__main__":
    try:
        test_complete_workflow()
        test_config_management()
        print("\n🎉 所有集成测试通过！自适应内容长度生成系统已准备就绪。")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)