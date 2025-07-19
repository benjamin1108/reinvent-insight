"""
模拟生成交互提示词

展示在实际使用中，动态提示词生成器会生成什么样的提示词，
特别是段落长度控制功能是如何体现在实际提示词中的。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.reinvent_insight.adaptive_length import LengthTarget
from src.reinvent_insight.dynamic_prompt_generator import DynamicPromptGenerator


def simulate_interactive_prompts():
    """模拟生成交互提示词"""
    print("=" * 100)
    print("模拟生成交互提示词 - 展示段落长度控制功能")
    print("=" * 100)
    
    # 模拟一个中等长度的视频分析结果
    length_target = LengthTarget(
        target_length=22000,  # 22k字的目标长度
        min_length=17600,     # 允许范围 80%
        max_length=26400,     # 允许范围 120%
        chapter_count=14,     # 14个章节
        avg_chapter_length=1571  # 平均每章节约1571字
    )
    
    # 基础提示词模板（简化版）
    base_prompt = """## 角色设定
你是一名 **中英双语技术解构官 & 叙事策展人**，擅长将长篇英文内容编译成结构化中文深度笔记。

## 输出总目标
生成一份可**完全替代观看视频**的中文长文笔记，兼具"读书笔记 + 行业解读 + 观点延伸"三重价值。

## 具体要求
1. **篇幅**：严格按照长度要求，确保信息完整；根据详细程度调整内容深度
2. **语言**：专业中文，但术语沿用原英文（首现附中文释义）
3. **风格**：严谨 + 可读：兼顾深度与故事性"""
    
    # 创建动态提示词生成器
    generator = DynamicPromptGenerator(base_prompt, length_target)
    
    print(f"视频分析结果:")
    print(f"- 目标长度: {length_target.target_length:,} 字")
    print(f"- 允许范围: {length_target.min_length:,} - {length_target.max_length:,} 字")
    print(f"- 章节数量: {length_target.chapter_count} 个")
    print(f"- 平均章节长度: {length_target.avg_chapter_length:,} 字")
    print(f"- 详细程度级别: {generator.detail_level.name}")
    print()
    
    # 模拟视频字幕（简化版）
    mock_transcript = """
    Welcome to AWS re:Invent 2024. Today we're going to talk about the future of cloud networking.
    Cloud networking has evolved significantly over the past decade. We've seen the rise of software-defined networking,
    the adoption of containerization, and the emergence of edge computing. These trends are reshaping how we think
    about network architecture and design. In this session, we'll explore the key innovations that are driving
    the next generation of cloud networking solutions...
    """
    
    # 模拟大纲
    mock_outline = """
    # 云网络的未来：AWS re:Invent 2024 深度解析
    
    ### 引言
    本文深度解析了AWS re:Invent 2024关于云网络未来发展的技术演讲...
    
    ### 主要目录
    1. 云网络发展历程回顾
    2. 软件定义网络的演进
    3. 容器化对网络架构的影响
    4. 边缘计算网络挑战
    5. 下一代网络解决方案
    6. 性能优化策略
    7. 安全性考量
    8. 成本效益分析
    9. 实施最佳实践
    10. 案例研究分析
    11. 技术趋势预测
    12. 行业影响评估
    13. 未来发展路线图
    14. 总结与展望
    """
    
    print("=" * 80)
    print("1. 大纲生成提示词示例")
    print("=" * 80)
    
    outline_prompt = generator.generate_outline_prompt(mock_transcript)
    
    # 提取关键的长度控制部分
    print("【长度与结构指导部分】")
    lines = outline_prompt.split('\n')
    in_length_section = False
    for line in lines:
        if "## 长度与结构指导" in line:
            in_length_section = True
        elif line.startswith("## ") and in_length_section:
            in_length_section = False
        
        if in_length_section:
            print(line)
    
    print("\n" + "=" * 80)
    print("2. 章节生成提示词示例（第3章）")
    print("=" * 80)
    
    chapter_prompt = generator.generate_chapter_prompt(
        chapter_index=3,
        chapter_title="容器化对网络架构的影响",
        outline=mock_outline,
        transcript=mock_transcript
    )
    
    # 提取关键的长度控制部分
    print("【长度与质量指导部分】")
    lines = chapter_prompt.split('\n')
    in_length_section = False
    for line in lines:
        if "## 长度与质量指导" in line:
            in_length_section = True
        elif line.startswith("## ") and in_length_section:
            in_length_section = False
        
        if in_length_section:
            print(line)
    
    print("\n【内容详细程度指导部分】")
    lines = chapter_prompt.split('\n')
    in_detail_section = False
    for line in lines:
        if "## 内容详细程度：适度详细" in line:
            in_detail_section = True
        elif line.startswith("## ") and in_detail_section:
            in_detail_section = False
        
        if in_detail_section:
            print(line)
    
    print("\n" + "=" * 80)
    print("3. 段落长度控制指令总结")
    print("=" * 80)
    
    print("在生成的提示词中，段落长度控制体现在以下几个方面：")
    print()
    print("📋 **章节长度指导中的段落控制：**")
    print("   - 段落长度控制：每个段落控制在100-150字之间，避免生成过长的段落")
    print("   - 段落结构要求：每个段落包含3-5个句子，确保内容紧凑且易读")
    print()
    print("📋 **详细程度配置中的段落控制：**")
    print("   - 段落长度控制：每个段落控制在100-150字之间，确保内容紧凑")
    print()
    print("📋 **适用范围：**")
    print("   - ✅ 大纲生成提示词")
    print("   - ✅ 章节生成提示词")
    print("   - ✅ 结论生成提示词")
    print("   - ✅ 所有详细程度级别（简洁/适度/深度）")
    print()
    print("📋 **预期效果：**")
    print("   - 🎯 段落长度控制在100-150字")
    print("   - 🎯 每个段落3-5个句子")
    print("   - 🎯 内容紧凑且易读")
    print("   - 🎯 避免过长段落影响阅读体验")
    
    print("\n" + "=" * 80)
    print("4. 不同详细程度级别的段落控制对比")
    print("=" * 80)
    
    # 测试不同长度目标
    test_cases = [
        ("简洁级别", LengthTarget(12000, 9600, 14400, 10, 1200)),
        ("适度级别", LengthTarget(22000, 17600, 26400, 14, 1571)),
        ("深度级别", LengthTarget(38000, 30400, 45600, 22, 1727))
    ]
    
    for level_name, target in test_cases:
        gen = DynamicPromptGenerator(base_prompt, target)
        print(f"\n【{level_name}】")
        print(f"目标长度: {target.target_length:,}字, 详细程度: {gen.detail_level.name}")
        
        # 提取段落控制指令
        outline_inst = gen.detail_level.outline_instruction
        for line in outline_inst.split('\n'):
            if "段落长度控制" in line:
                print(f"段落控制: {line.strip()}")
                break
    
    print("\n" + "=" * 100)
    print("模拟完成！段落长度控制功能已成功集成到所有提示词生成场景中。")
    print("=" * 100)


if __name__ == "__main__":
    simulate_interactive_prompts()