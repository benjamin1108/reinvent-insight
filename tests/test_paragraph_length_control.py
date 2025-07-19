"""
测试段落长度控制功能

验证动态提示词生成器是否正确添加了段落长度控制指令
"""

import pytest
from src.reinvent_insight.adaptive_length import LengthTarget
from src.reinvent_insight.dynamic_prompt_generator import DynamicPromptGenerator


class TestParagraphLengthControl:
    """测试段落长度控制功能"""
    
    def setup_method(self):
        """设置测试环境"""
        self.base_prompt = "这是一个基础提示词模板"
        
    def test_chapter_prompt_contains_paragraph_control(self):
        """测试章节提示词包含段落长度控制指令"""
        # 创建不同长度目标的测试用例
        test_cases = [
            # 简洁级别
            LengthTarget(target_length=12000, min_length=9600, max_length=14400, 
                        chapter_count=10, avg_chapter_length=1200),
            # 适度级别
            LengthTarget(target_length=20000, min_length=16000, max_length=24000, 
                        chapter_count=15, avg_chapter_length=1333),
            # 深度级别
            LengthTarget(target_length=35000, min_length=28000, max_length=42000, 
                        chapter_count=20, avg_chapter_length=1750)
        ]
        
        for length_target in test_cases:
            generator = DynamicPromptGenerator(self.base_prompt, length_target)
            
            # 生成章节提示词
            chapter_prompt = generator.generate_chapter_prompt(
                chapter_index=1,
                chapter_title="测试章节",
                outline="测试大纲",
                transcript="测试字幕"
            )
            
            # 验证段落长度控制指令存在
            assert "段落长度控制" in chapter_prompt, f"章节提示词缺少段落长度控制指令 (目标长度: {length_target.target_length})"
            assert "100-150字之间" in chapter_prompt, f"章节提示词缺少具体的段落长度要求 (目标长度: {length_target.target_length})"
            assert "段落结构要求" in chapter_prompt, f"章节提示词缺少段落结构要求 (目标长度: {length_target.target_length})"
            assert "3-5个句子" in chapter_prompt, f"章节提示词缺少句子数量要求 (目标长度: {length_target.target_length})"
    
    def test_outline_prompt_contains_paragraph_control(self):
        """测试大纲提示词包含段落长度控制指令"""
        test_cases = [
            # 简洁级别
            LengthTarget(target_length=12000, min_length=9600, max_length=14400, 
                        chapter_count=10, avg_chapter_length=1200),
            # 适度级别  
            LengthTarget(target_length=20000, min_length=16000, max_length=24000, 
                        chapter_count=15, avg_chapter_length=1333),
            # 深度级别
            LengthTarget(target_length=35000, min_length=28000, max_length=42000, 
                        chapter_count=20, avg_chapter_length=1750)
        ]
        
        for length_target in test_cases:
            generator = DynamicPromptGenerator(self.base_prompt, length_target)
            
            # 生成大纲提示词
            outline_prompt = generator.generate_outline_prompt("测试字幕")
            
            # 验证段落长度控制指令存在
            assert "段落长度控制" in outline_prompt, f"大纲提示词缺少段落长度控制指令 (目标长度: {length_target.target_length})"
            assert "100-150字之间" in outline_prompt, f"大纲提示词缺少具体的段落长度要求 (目标长度: {length_target.target_length})"
    
    def test_different_detail_levels_have_paragraph_control(self):
        """测试不同详细程度级别都包含段落长度控制"""
        # 简洁级别 (< 15000字)
        simple_target = LengthTarget(target_length=12000, min_length=9600, max_length=14400, 
                                   chapter_count=10, avg_chapter_length=1200)
        simple_generator = DynamicPromptGenerator(self.base_prompt, simple_target)
        
        # 适度级别 (15000-30000字)
        moderate_target = LengthTarget(target_length=20000, min_length=16000, max_length=24000, 
                                    chapter_count=15, avg_chapter_length=1333)
        moderate_generator = DynamicPromptGenerator(self.base_prompt, moderate_target)
        
        # 深度级别 (> 30000字)
        detailed_target = LengthTarget(target_length=35000, min_length=28000, max_length=42000, 
                                     chapter_count=20, avg_chapter_length=1750)
        detailed_generator = DynamicPromptGenerator(self.base_prompt, detailed_target)
        
        generators = [
            (simple_generator, "简洁"),
            (moderate_generator, "适度"), 
            (detailed_generator, "深度")
        ]
        
        for generator, level_name in generators:
            # 检查详细程度配置
            assert generator.detail_level.name == level_name, f"详细程度级别不正确: 期望{level_name}, 实际{generator.detail_level.name}"
            
            # 检查大纲指导中的段落控制
            outline_instruction = generator.detail_level.outline_instruction
            assert "段落长度控制" in outline_instruction, f"{level_name}级别的大纲指导缺少段落长度控制"
            assert "100-150字之间" in outline_instruction, f"{level_name}级别的大纲指导缺少具体段落长度要求"
    
    def test_paragraph_control_in_adaptive_prompt_template(self):
        """测试自适应提示词模板包含段落长度控制"""
        # 读取自适应提示词模板
        try:
            with open("prompt/youtbe-deep-summary-adaptive.txt", 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 验证模板包含段落长度控制指令
            assert "段落长度控制" in template_content, "自适应提示词模板缺少段落长度控制指令"
            assert "100-150字之间" in template_content, "自适应提示词模板缺少具体的段落长度要求"
            assert "段落结构要求" in template_content, "自适应提示词模板缺少段落结构要求"
            assert "3-5个句子" in template_content, "自适应提示词模板缺少句子数量要求"
            
        except FileNotFoundError:
            pytest.skip("自适应提示词模板文件不存在")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])