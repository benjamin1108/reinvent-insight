"""
段落长度控制功能演示脚本

展示动态提示词生成器如何在不同长度目标下生成包含段落长度控制指令的提示词
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.reinvent_insight.adaptive_length import LengthTarget
from src.reinvent_insight.dynamic_prompt_generator import DynamicPromptGenerator


def demo_paragraph_control():
    """演示段落长度控制功能"""
    print("=" * 80)
    print("段落长度控制功能演示")
    print("=" * 80)
    
    # 基础提示词模板
    base_prompt = "这是一个基础提示词模板，用于演示段落长度控制功能。"
    
    # 测试不同长度目标
    test_cases = [
        ("简洁级别", LengthTarget(target_length=12000, min_length=9600, max_length=14400, 
                                chapter_count=10, avg_chapter_length=1200)),
        ("适度级别", LengthTarget(target_length=20000, min_length=16000, max_length=24000, 
                                chapter_count=15, avg_chapter_length=1333)),
        ("深度级别", LengthTarget(target_length=35000, min_length=28000, max_length=42000, 
                                chapter_count=20, avg_chapter_length=1750))
    ]
    
    for level_name, length_target in test_cases:
        print(f"\n{'-' * 60}")
        print(f"测试级别: {level_name}")
        print(f"目标长度: {length_target.target_length:,} 字")
        print(f"章节数量: {length_target.chapter_count} 个")
        print(f"平均章节长度: {length_target.avg_chapter_length:,} 字")
        print(f"{'-' * 60}")
        
        # 创建动态提示词生成器
        generator = DynamicPromptGenerator(base_prompt, length_target)
        
        print(f"详细程度: {generator.detail_level.name}")
        print(f"描述: {generator.detail_level.description}")
        
        # 生成章节提示词示例
        chapter_prompt = generator.generate_chapter_prompt(
            chapter_index=1,
            chapter_title="AWS网络基础设施深度解析",
            outline="1. 网络架构概述\n2. 核心技术分析\n3. 性能优化策略",
            transcript="这是一个关于AWS网络基础设施的技术演讲字幕..."
        )
        
        # 提取段落长度控制相关的指令
        lines = chapter_prompt.split('\n')
        paragraph_control_lines = []
        
        for i, line in enumerate(lines):
            if "段落长度控制" in line or "段落结构要求" in line:
                # 包含前后几行以提供上下文
                start = max(0, i-1)
                end = min(len(lines), i+3)
                paragraph_control_lines.extend(lines[start:end])
                paragraph_control_lines.append("")  # 添加空行分隔
        
        if paragraph_control_lines:
            print("\n提取的段落长度控制指令:")
            print("```")
            for line in paragraph_control_lines:
                print(line)
            print("```")
        
        # 显示详细程度配置中的段落控制
        print(f"\n详细程度配置中的段落控制指令:")
        print("```")
        outline_instruction = generator.detail_level.outline_instruction
        for line in outline_instruction.split('\n'):
            if "段落长度控制" in line:
                print(line)
        print("```")
    
    print(f"\n{'=' * 80}")
    print("演示完成！")
    print("总结:")
    print("- 所有详细程度级别都包含段落长度控制指令")
    print("- 每个段落控制在100-150字之间")
    print("- 每个段落包含3-5个句子")
    print("- 确保内容紧凑且易读")
    print("=" * 80)


if __name__ == "__main__":
    demo_paragraph_control()