"""
测试长度监控和调整机制
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import json

from src.reinvent_insight.adaptive_length import (
    LengthTarget, LengthStatus, LengthMonitor, 
    LengthAdjustmentEngine, CompensationGenerator,
    AdjustmentStrategy, AdjustmentRecord
)


class TestLengthMonitor:
    """测试LengthMonitor类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.length_target = LengthTarget(
            target_length=20000,
            min_length=16000,
            max_length=24000,
            chapter_count=15,
            avg_chapter_length=1333
        )
        self.monitor = LengthMonitor(self.length_target, "test_task")
    
    def test_monitor_chapter_normal(self):
        """测试正常章节监控"""
        chapter_content = "A" * 1300  # 接近目标长度
        status = self.monitor.monitor_chapter(chapter_content, 0, "第一章")
        
        assert status.current_length == 1300
        assert status.chapter_index == 0
        assert not status.adjustment_needed  # 偏差不大，不需要调整
        assert status.adjustment_type == "maintain"
    
    def test_monitor_chapter_too_long(self):
        """测试章节过长的情况"""
        chapter_content = "A" * 2000  # 明显超过目标长度
        status = self.monitor.monitor_chapter(chapter_content, 0, "第一章")
        
        assert status.current_length == 2000
        assert status.adjustment_needed  # 需要调整
        assert status.adjustment_type == "compress"
    
    def test_monitor_chapter_too_short(self):
        """测试章节过短的情况"""
        chapter_content = "A" * 500  # 明显低于目标长度
        status = self.monitor.monitor_chapter(chapter_content, 0, "第一章")
        
        assert status.current_length == 500
        assert status.adjustment_needed  # 需要调整
        assert status.adjustment_type == "expand"
    
    def test_predict_final_length(self):
        """测试最终长度预测"""
        # 添加几个章节
        self.monitor.monitor_chapter("A" * 1000, 0, "第一章")
        self.monitor.monitor_chapter("A" * 1200, 1, "第二章")
        
        predicted = self.monitor._predict_final_length(2)
        expected = (1000 + 1200) + (15 - 2) * ((1000 + 1200) / 2)
        assert predicted == int(expected)
    
    def test_get_monitoring_summary(self):
        """测试监控摘要"""
        self.monitor.monitor_chapter("A" * 1300, 0, "第一章")
        self.monitor.monitor_chapter("A" * 1400, 1, "第二章")
        
        summary = self.monitor.get_monitoring_summary()
        assert summary["completed_chapters"] == 2
        assert summary["total_chapters"] == 15
        assert summary["current_total_length"] == 2700
        assert summary["progress_percentage"] == (2 / 15) * 100


class TestLengthAdjustmentEngine:
    """测试LengthAdjustmentEngine类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.length_target = LengthTarget(
            target_length=20000,
            min_length=16000,
            max_length=24000,
            chapter_count=15,
            avg_chapter_length=1333
        )
        self.engine = LengthAdjustmentEngine(self.length_target, "test_adj")
    
    def test_detect_deviation_basic(self):
        """测试基础偏差检测"""
        # 创建一个偏差较大的状态
        status = LengthStatus(
            current_length=5000,
            target_length=20000,
            progress_ratio=0.2,
            deviation_ratio=0.5,  # 50%偏差
            adjustment_needed=True,
            adjustment_type="compress",
            chapter_index=2,
            expected_length=4000,
            remaining_chapters=13,
            predicted_final_length=25000
        )
        
        assert self.engine.detect_deviation(status) == True
    
    def test_generate_adjustment_strategy_compress(self):
        """测试压缩调整策略生成"""
        status = LengthStatus(
            current_length=8000,
            target_length=20000,
            progress_ratio=0.3,
            deviation_ratio=0.4,  # 内容过长
            adjustment_needed=True,
            adjustment_type="compress",
            chapter_index=4,
            expected_length=6000,
            remaining_chapters=10,
            predicted_final_length=26000
        )
        
        strategy = self.engine.generate_adjustment_strategy(status)
        assert strategy.strategy_type in ["gradual", "aggressive", "conservative"]
        assert strategy.content_detail_level == "concise"
        assert strategy.target_chapter_length < self.length_target.avg_chapter_length
    
    def test_generate_adjustment_strategy_expand(self):
        """测试扩展调整策略生成"""
        status = LengthStatus(
            current_length=1000,  # 更短的当前长度
            target_length=20000,
            progress_ratio=0.3,
            deviation_ratio=-0.6,  # 更大的负偏差
            adjustment_needed=True,
            adjustment_type="expand",
            chapter_index=4,
            expected_length=6000,
            remaining_chapters=10,
            predicted_final_length=10000  # 更低的预测长度
        )
        
        strategy = self.engine.generate_adjustment_strategy(status)
        # 由于需要大幅扩展，目标章节长度应该显著增加
        assert strategy.target_chapter_length > self.length_target.avg_chapter_length
        # 内容详细程度应该是详细或适度
        assert strategy.content_detail_level in ["detailed", "moderate"]
    
    def test_apply_adjustment(self):
        """测试应用调整"""
        strategy = AdjustmentStrategy(
            strategy_type="gradual",
            target_chapter_length=1500,
            content_detail_level="moderate",
            prompt_adjustments={},
            compensation_factor=1.0,
            priority_areas=[]
        )
        
        record = self.engine.apply_adjustment(5, 1333, strategy, "测试调整")
        
        assert record.chapter_index == 5
        assert record.original_target == 1333
        assert record.adjusted_target == 1500
        assert record.adjustment_amount == 167
        assert len(self.engine.adjustment_records) == 1
    
    def test_evaluate_adjustment_effectiveness(self):
        """测试调整效果评估"""
        record = AdjustmentRecord(
            chapter_index=0,
            adjustment_type="gradual",
            original_target=1333,
            adjusted_target=1500,
            adjustment_amount=167,
            reason="测试"
        )
        
        # 测试完全命中目标的情况
        effectiveness = self.engine.evaluate_adjustment_effectiveness(record, 1500)
        assert effectiveness == 1.0
        
        # 测试偏差较大的情况
        effectiveness = self.engine.evaluate_adjustment_effectiveness(record, 1000)
        assert effectiveness < 0.5


class TestCompensationGenerator:
    """测试CompensationGenerator类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.length_target = LengthTarget(
            target_length=20000,
            min_length=16000,
            max_length=24000,
            chapter_count=15,
            avg_chapter_length=1333
        )
        self.generator = CompensationGenerator(self.length_target, "test_comp")
    
    def test_assess_compensation_need_no_compensation(self):
        """测试无需补偿的情况"""
        assessment = self.generator.assess_compensation_need(19500)  # 接近目标
        
        assert not assessment["needs_compensation"]
        assert assessment["final_length"] == 19500
        assert assessment["target_length"] == 20000
        assert abs(assessment["gap_ratio"]) < 0.15
    
    def test_assess_compensation_need_expand(self):
        """测试需要扩展补偿的情况"""
        assessment = self.generator.assess_compensation_need(16000)  # 明显偏短
        
        assert assessment["needs_compensation"]
        assert assessment["compensation_type"] == "expand"
        assert assessment["length_gap"] == -4000
        assert assessment["gap_ratio"] < 0
    
    def test_assess_compensation_need_compress(self):
        """测试需要压缩补偿的情况"""
        assessment = self.generator.assess_compensation_need(25000)  # 明显偏长
        
        assert assessment["needs_compensation"]
        assert assessment["compensation_type"] == "compress"
        assert assessment["length_gap"] == 5000
        assert assessment["gap_ratio"] > 0
    
    def test_generate_compensation_strategy_expand(self):
        """测试扩展补偿策略"""
        assessment = {
            "needs_compensation": True,
            "compensation_type": "expand",
            "length_gap": -3000,
            "severity": "中等"
        }
        
        strategy = self.generator.generate_compensation_strategy(assessment)
        
        assert strategy["compensation_type"] == "expand"
        assert strategy["target_compensation"] == 3000
        assert strategy["method"] == "章节扩展"
        assert "深化技术分析" in strategy["content_areas"]
    
    def test_generate_compensation_strategy_compress(self):
        """测试压缩补偿策略"""
        assessment = {
            "needs_compensation": True,
            "compensation_type": "compress",
            "length_gap": 4000,
            "severity": "严重"
        }
        
        strategy = self.generator.generate_compensation_strategy(assessment)
        
        assert strategy["compensation_type"] == "compress"
        assert strategy["target_compensation"] == 4000
        assert strategy["method"] == "章节合并"
        assert "合并重复内容" in strategy["content_areas"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])