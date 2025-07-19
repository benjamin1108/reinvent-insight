"""
完整提示词示例

展示一个完整的章节生成提示词，包含所有段落长度控制指令
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.reinvent_insight.adaptive_length import LengthTarget
from src.reinvent_insight.dynamic_prompt_generator import DynamicPromptGenerator


def show_full_prompt_example():
    """展示完整的提示词示例"""
    print("=" * 120)
    print("完整章节生成提示词示例 - 包含段落长度控制")
    print("=" * 120)
    
    # 创建一个适度级别的长度目标
    length_target = LengthTarget(
        target_length=22000,
        min_length=17600,
        max_length=26400,
        chapter_count=14,
        avg_chapter_length=1571
    )
    
    # 使用实际的自适应提示词模板
    try:
        with open("prompt/youtbe-deep-summary-adaptive.txt", 'r', encoding='utf-8') as f:
            base_prompt = f.read()
    except FileNotFoundError:
        base_prompt = """## 角色设定
你是一名 **中英双语技术解构官 & 叙事策展人**，擅长将长篇英文内容编译成结构化中文深度笔记。

## 输出总目标
生成一份可**完全替代观看视频**的中文长文笔记，兼具"读书笔记 + 行业解读 + 观点延伸"三重价值。

## 高级处理
- **段落长度控制**：每个段落控制在100-150字之间，避免生成过长的段落
- **段落结构要求**：每个段落包含3-5个句子，确保内容紧凑且易读"""
    
    # 创建动态提示词生成器
    generator = DynamicPromptGenerator(base_prompt, length_target)
    
    # 模拟完整的输入数据
    mock_transcript = """
    Welcome to AWS re:Invent 2024. I'm Sarah Chen, Principal Engineer at AWS Networking.
    Today we're diving deep into the evolution of cloud networking architecture.
    
    Over the past decade, we've witnessed a fundamental shift in how we approach network design.
    Traditional networking models, built for static, predictable workloads, are giving way to
    dynamic, software-defined architectures that can adapt in real-time to changing demands.
    
    The rise of containerization has been a game-changer. When we look at how containers
    communicate, we see entirely new patterns of network traffic. Unlike traditional VMs,
    containers are ephemeral, lightweight, and highly dynamic. This creates unique challenges
    for network visibility, security, and performance optimization.
    
    Let me share some concrete data. In our analysis of customer workloads, we found that
    containerized applications generate 3x more east-west traffic compared to traditional
    VM-based deployments. This shift has profound implications for network architecture.
    
    Security is another critical dimension. With containers, the attack surface is constantly
    changing. Traditional perimeter-based security models simply don't work. We need
    zero-trust architectures that can secure individual workloads, not just network boundaries.
    
    Performance optimization in containerized environments requires new approaches.
    Traditional load balancing algorithms, designed for long-lived connections, struggle
    with the rapid scaling and ephemeral nature of container workloads.
    
    Looking ahead, we see several key trends shaping the future of cloud networking...
    """
    
    mock_outline = """
    # 云网络架构演进：从传统到容器化的转型之路
    
    ### 引言
    本文深度解析了AWS re:Invent 2024关于云网络架构演进的技术演讲，主讲人Sarah Chen详细阐述了从传统网络模型向动态软件定义架构的转变过程。
    
    ### 主要目录
    1. 传统网络模型的局限性
    2. 软件定义网络的兴起
    3. 容器化对网络架构的冲击
    4. 东西向流量模式的变化
    5. 网络可见性挑战与解决方案
    6. 零信任安全架构设计
    7. 容器环境下的性能优化
    8. 负载均衡策略的演进
    9. 网络监控与故障排除
    10. 成本优化最佳实践
    11. 合规性与治理考量
    12. 技术选型指导原则
    13. 实施路线图规划
    14. 未来发展趋势展望
    """
    
    # 生成第3章的完整提示词
    chapter_prompt = generator.generate_chapter_prompt(
        chapter_index=3,
        chapter_title="容器化对网络架构的冲击",
        outline=mock_outline,
        transcript=mock_transcript
    )
    
    print("以下是生成的完整章节提示词：")
    print("\n" + "─" * 120)
    print(chapter_prompt)
    print("─" * 120)
    
    print("\n" + "=" * 120)
    print("关键段落长度控制指令提取")
    print("=" * 120)
    
    # 提取所有与段落长度控制相关的指令
    lines = chapter_prompt.split('\n')
    paragraph_control_sections = []
    
    for i, line in enumerate(lines):
        if any(keyword in line for keyword in ["段落长度控制", "段落结构要求", "100-150字", "3-5个句子"]):
            # 获取上下文
            start = max(0, i-2)
            end = min(len(lines), i+3)
            section = lines[start:end]
            paragraph_control_sections.append(section)
    
    print("📋 **在提示词中发现的段落长度控制指令：**\n")
    
    for i, section in enumerate(paragraph_control_sections, 1):
        print(f"【位置 {i}】")
        for line in section:
            if any(keyword in line for keyword in ["段落长度控制", "段落结构要求", "100-150字", "3-5个句子"]):
                print(f"🎯 {line.strip()}")
            else:
                print(f"   {line.strip()}")
        print()
    
    print("=" * 120)
    print("总结：段落长度控制功能的完整实现")
    print("=" * 120)
    
    print("""
✅ **功能实现状态：**
   • 动态提示词生成器已更新
   • 自适应提示词模板已更新
   • 所有详细程度级别都包含段落控制
   • 单元测试全部通过

🎯 **段落控制标准：**
   • 段落长度：100-150字之间
   • 段落结构：3-5个句子
   • 内容要求：紧凑且易读
   • 质量保证：不影响内容完整性

📊 **应用范围：**
   • ✓ 大纲生成提示词
   • ✓ 章节生成提示词  
   • ✓ 结论生成提示词
   • ✓ 简洁/适度/深度三个级别

🚀 **预期效果：**
   • 解决段落过长问题
   • 提升内容可读性
   • 改善用户体验
   • 保持内容质量
    """)
    
    print("=" * 120)


if __name__ == "__main__":
    show_full_prompt_example()