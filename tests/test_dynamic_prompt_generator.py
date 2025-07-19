"""
动态提示词生成器测试模块

测试动态提示词生成器的各种功能，包括：
- 基础功能测试
- 不同详细程度的提示词生成
- 参数化模板替换
- 边界情况处理
"""

import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from src.reinvent_insight.adaptive_length import LengthTarget, VideoAnalysisResult, LengthConfig
from src.reinvent_insight.dynamic_prompt_generator import (
    DynamicPromptGenerator, 
    DetailLevel,
    load_base_prompt_template,
    create_dynamic_prompt_generator
)
from src.reinvent_insight.prompts import (
    PromptTemplateManager,
    create_length_parameters,
    create_adaptive_outline_prompt,
    create_adaptive_chapter_prompt,
    create_adaptive_conclusion_prompt
)


class TestDynamicPromptGenerator:
    """动态提示词生成器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        # 创建测试用的长度目标
        self.length_target_short = LengthTarget(
            target_length=12000,
            min_length=9600,
            max_length=14400,
            chapter_count=10,
            avg_chapter_length=1200
        )
        
        self.length_target_medium = LengthTarget(
            target_length=25000,
            min_length=20000,
            max_length=30000,
            chapter_count=15,
            avg_chapter_length=1667
        )
        
        self.length_target_long = LengthTarget(
            target_length=40000,
            min_length=32000,
            max_length=48000,
            chapter_count=20,
            avg_chapter_length=2000
        )
        
        # 基础提示词
        self.base_prompt = "这是一个测试基础提示词模板"
        
        # 测试字幕
        self.test_transcript = "This is a test transcript for testing purposes."
        self.test_outline = "1. Chapter One\n2. Chapter Two\n3. Chapter Three"
        self.test_chapters = "### 1. Chapter One\nContent of chapter one..."
    
    def test_detail_level_determination(self):
        """测试详细程度判断"""
        # 测试简洁级别
        generator_short = DynamicPromptGenerator(self.base_prompt, self.length_target_short)
        assert generator_short.detail_level.name == "简洁"
        
        # 测试适度级别
        generator_medium = DynamicPromptGenerator(self.base_prompt, self.length_target_medium)
        assert generator_medium.detail_level.name == "适度"
        
        # 测试深度级别
        generator_long = DynamicPromptGenerator(self.base_prompt, self.length_target_long)
        assert generator_long.detail_level.name == "深度"
    
    def test_outline_prompt_generation(self):
        """测试大纲提示词生成"""
        generator = DynamicPromptGenerator(self.base_prompt, self.length_target_medium)
        outline_prompt = generator.generate_outline_prompt(self.test_transcript)
        
        # 检查是否包含基础提示词
        assert self.base_prompt in outline_prompt
        
        # 检查是否包含字幕内容
        assert self.test_transcript in outline_prompt
        
        # 检查是否包含章节数量
        assert str(self.length_target_medium.chapter_count) in outline_prompt
        
        # 检查是否包含长度信息（格式化后的）
        assert "25,000" in outline_prompt
    
    def test_chapter_prompt_generation(self):
        """测试章节提示词生成"""
        generator = DynamicPromptGenerator(self.base_prompt, self.length_target_medium)
        chapter_prompt = generator.generate_chapter_prompt(
            1, "Test Chapter", self.test_outline, self.test_transcript
        )
        
        # 检查是否包含基础提示词
        assert self.base_prompt in chapter_prompt
        
        # 检查是否包含章节信息
        assert "Test Chapter" in chapter_prompt
        assert "第 `1` 章" in chapter_prompt
        
        # 检查是否包含长度指导
        assert "目标长度" in chapter_prompt
        
        # 检查是否包含详细程度指导
        assert generator.detail_level.chapter_instruction in chapter_prompt
    
    def test_conclusion_prompt_generation(self):
        """测试结论提示词生成"""
        generator = DynamicPromptGenerator(self.base_prompt, self.length_target_medium)
        conclusion_prompt = generator.generate_conclusion_prompt(
            self.test_transcript, self.test_chapters
        )
        
        # 检查是否包含基础提示词
        assert self.base_prompt in conclusion_prompt
        
        # 检查是否包含字幕和章节内容
        assert self.test_transcript in conclusion_prompt
        assert self.test_chapters in conclusion_prompt
        
        # 检查是否包含深度指导
        assert "洞见延伸" in conclusion_prompt
        assert "金句&原声引用" in conclusion_prompt
    
    def test_chapter_length_calculation(self):
        """测试章节长度计算"""
        generator = DynamicPromptGenerator(self.base_prompt, self.length_target_medium)
        
        # 测试第一章（应该稍长）
        first_chapter_length = generator._calculate_chapter_length_target(1)
        expected_first = int(self.length_target_medium.avg_chapter_length * 1.1)
        assert first_chapter_length == expected_first
        
        # 测试最后一章（应该稍长）
        last_chapter_length = generator._calculate_chapter_length_target(
            self.length_target_medium.chapter_count
        )
        expected_last = int(self.length_target_medium.avg_chapter_length * 1.05)
        assert last_chapter_length == expected_last
        
        # 测试中间章节（标准长度）
        middle_chapter_length = generator._calculate_chapter_length_target(5)
        assert middle_chapter_length == self.length_target_medium.avg_chapter_length
    
    def test_different_detail_levels(self):
        """测试不同详细程度的配置"""
        # 简洁级别
        generator_short = DynamicPromptGenerator(self.base_prompt, self.length_target_short)
        assert "简洁精炼" in generator_short.detail_level.chapter_instruction
        assert "精选要点" in generator_short.detail_level.conclusion_instruction
        
        # 适度级别
        generator_medium = DynamicPromptGenerator(self.base_prompt, self.length_target_medium)
        assert "适度详细" in generator_medium.detail_level.chapter_instruction
        assert "全面总结" in generator_medium.detail_level.conclusion_instruction
        
        # 深度级别
        generator_long = DynamicPromptGenerator(self.base_prompt, self.length_target_long)
        assert "深度详细" in generator_long.detail_level.chapter_instruction
        assert "深度洞察" in generator_long.detail_level.conclusion_instruction


class TestPromptTemplateManager:
    """提示词模板管理器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.test_template = """
这是一个测试模板
目标长度：{TARGET_LENGTH}
章节数量：{CHAPTER_COUNT}
详细程度：{DETAIL_LEVEL}
"""
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_template_loading(self, mock_exists, mock_file):
        """测试模板加载"""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = self.test_template
        
        manager = PromptTemplateManager("test_template.txt")
        assert manager.base_template == self.test_template
    
    def test_parameterized_prompt_creation(self):
        """测试参数化提示词创建"""
        manager = PromptTemplateManager()
        manager.base_template = self.test_template
        
        params = {
            'TARGET_LENGTH': '25,000',
            'CHAPTER_COUNT': '15',
            'DETAIL_LEVEL': '适度'
        }
        
        result = manager.create_parameterized_prompt(params)
        
        assert '25,000' in result
        assert '15' in result
        assert '适度' in result
    
    def test_missing_parameters_handling(self):
        """测试缺少参数的处理"""
        manager = PromptTemplateManager()
        manager.base_template = self.test_template
        
        # 缺少参数的情况
        incomplete_params = {
            'TARGET_LENGTH': '25,000'
            # 缺少 CHAPTER_COUNT 和 DETAIL_LEVEL
        }
        
        result = manager.create_parameterized_prompt(incomplete_params)
        # 应该返回原始模板
        assert result == self.test_template


class TestLengthParameters:
    """长度参数测试类"""
    
    def test_create_length_parameters(self):
        """测试长度参数创建"""
        params = create_length_parameters(
            target_length=25000,
            min_length=20000,
            max_length=30000,
            chapter_count=15,
            avg_chapter_length=1667,
            detail_level="适度",
            detail_description="平衡深度与可读性"
        )
        
        # 检查基础参数
        assert params['TARGET_LENGTH'] == '25,000'
        assert params['MIN_LENGTH'] == '20,000'
        assert params['MAX_LENGTH'] == '30,000'
        assert params['CHAPTER_COUNT'] == '15'
        assert params['AVG_CHAPTER_LENGTH'] == '1,667'
        assert params['DETAIL_LEVEL'] == '适度'
        assert params['DETAIL_DESCRIPTION'] == '平衡深度与可读性'
        
        # 检查生成的指导语句
        assert 'CONTENT_DENSITY_INSTRUCTION' in params
        assert 'CHAPTER_LENGTH_INSTRUCTION' in params
        assert 'CONTENT_DEPTH_INSTRUCTION' in params
        assert 'LENGTH_CONTROL_INSTRUCTION' in params
        assert 'INSIGHT_COUNT' in params
        assert 'QUOTE_COUNT' in params
        assert 'INSIGHT_LENGTH' in params
    
    def test_different_detail_levels_parameters(self):
        """测试不同详细程度的参数"""
        # 简洁级别
        params_short = create_length_parameters(
            12000, 9600, 14400, 10, 1200, "简洁", "重点突出核心观点"
        )
        assert params_short['INSIGHT_COUNT'] == '5-7'
        assert params_short['QUOTE_COUNT'] == '5-7'
        assert params_short['INSIGHT_LENGTH'] == '150-200'
        
        # 适度级别
        params_medium = create_length_parameters(
            25000, 20000, 30000, 15, 1667, "适度", "平衡深度与可读性"
        )
        assert params_medium['INSIGHT_COUNT'] == '8-10'
        assert params_medium['QUOTE_COUNT'] == '8-10'
        assert params_medium['INSIGHT_LENGTH'] == '180-250'
        
        # 深度级别
        params_long = create_length_parameters(
            40000, 32000, 48000, 20, 2000, "深度", "全面展开论述和分析"
        )
        assert params_long['INSIGHT_COUNT'] == '10'
        assert params_long['QUOTE_COUNT'] == '10'
        assert params_long['INSIGHT_LENGTH'] == '250-300'


class TestAdaptivePromptFunctions:
    """自适应提示词函数测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.base_prompt = "测试基础提示词"
        self.transcript = "测试字幕内容"
        self.outline = "1. 章节一\n2. 章节二"
        self.chapters = "### 1. 章节一\n内容..."
        self.length_params = {
            'TARGET_LENGTH': '25,000',
            'CHAPTER_COUNT': '15',
            'AVG_CHAPTER_LENGTH': '1,667',
            'DETAIL_LEVEL': '适度',
            'CONTENT_DENSITY_INSTRUCTION': '平衡深度与可读性',
            'CONTENT_DEPTH_INSTRUCTION': '在深度和可读性之间找到平衡',
            'INSIGHT_COUNT': '8-10',
            'QUOTE_COUNT': '8-10',
            'INSIGHT_LENGTH': '180-250'
        }
    
    def test_adaptive_outline_prompt(self):
        """测试自适应大纲提示词"""
        prompt = create_adaptive_outline_prompt(
            self.base_prompt, self.transcript, self.length_params
        )
        
        assert self.base_prompt in prompt
        assert self.transcript in prompt
        assert '15 个主要章节' in prompt
        assert '15 个章节' in prompt
    
    def test_adaptive_chapter_prompt(self):
        """测试自适应章节提示词"""
        prompt = create_adaptive_chapter_prompt(
            self.base_prompt, 1, "测试章节", self.outline, 
            self.transcript, self.length_params
        )
        
        assert self.base_prompt in prompt
        assert "测试章节" in prompt
        assert "第 `1` 章" in prompt
        assert self.transcript in prompt
        assert self.outline in prompt
        assert "1,667" in prompt  # 平均长度
    
    def test_adaptive_conclusion_prompt(self):
        """测试自适应结论提示词"""
        prompt = create_adaptive_conclusion_prompt(
            self.base_prompt, self.transcript, self.chapters, self.length_params
        )
        
        assert self.base_prompt in prompt
        assert self.transcript in prompt
        assert self.chapters in prompt
        assert "8-10 条" in prompt  # 洞见数量
        assert "180-250 字" in prompt  # 洞见长度


class TestIntegration:
    """集成测试类"""
    
    @patch("src.reinvent_insight.dynamic_prompt_generator.load_base_prompt_template")
    def test_create_dynamic_prompt_generator(self, mock_load):
        """测试创建动态提示词生成器的便捷函数"""
        mock_load.return_value = "测试基础提示词"
        
        length_target = LengthTarget(
            target_length=25000,
            min_length=20000,
            max_length=30000,
            chapter_count=15,
            avg_chapter_length=1667
        )
        
        generator = create_dynamic_prompt_generator(length_target)
        
        assert generator.base_prompt == "测试基础提示词"
        assert generator.length_target == length_target
        assert generator.detail_level.name == "适度"
    
    def test_end_to_end_prompt_generation(self):
        """测试端到端的提示词生成流程"""
        # 创建长度目标
        length_target = LengthTarget(
            target_length=25000,
            min_length=20000,
            max_length=30000,
            chapter_count=15,
            avg_chapter_length=1667
        )
        
        # 创建动态提示词生成器
        base_prompt = "测试基础提示词模板"
        generator = DynamicPromptGenerator(base_prompt, length_target)
        
        # 生成各种提示词
        transcript = "This is a test transcript."
        outline = "1. Introduction\n2. Main Content\n3. Conclusion"
        chapters = "### 1. Introduction\nTest content..."
        
        outline_prompt = generator.generate_outline_prompt(transcript)
        chapter_prompt = generator.generate_chapter_prompt(1, "Introduction", outline, transcript)
        conclusion_prompt = generator.generate_conclusion_prompt(transcript, chapters)
        
        # 验证所有提示词都包含基础内容
        assert base_prompt in outline_prompt
        assert base_prompt in chapter_prompt
        assert base_prompt in conclusion_prompt
        
        # 验证长度信息被正确包含
        assert "25,000" in outline_prompt
        assert "目标长度" in chapter_prompt
        assert "洞见延伸" in conclusion_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])