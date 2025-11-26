"""
Low Thinking 模式使用示例

演示如何在不同场景下使用 low_thinking 模式来优化性能。
"""

import asyncio
import time
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reinvent_insight.model_config import get_model_client


async def example_1_use_config_default():
    """示例1：使用配置文件中的默认设置"""
    print("\n" + "=" * 80)
    print("示例 1: 使用配置文件中的默认设置")
    print("=" * 80)
    
    # HTML转Markdown任务默认使用 low_thinking
    client = get_model_client("html_to_markdown")
    
    print(f"\n任务类型: html_to_markdown")
    print(f"配置的 low_thinking: {client.config.low_thinking}")
    print(f"实际使用的 thinking_level: {'low' if client.config.low_thinking else 'high'}")
    
    # 模拟调用（不实际调用API）
    print("\n调用示例:")
    print("  response = await client.generate_content(")
    print("      prompt='转换HTML...',")
    print("      is_json=True")
    print("  )")
    print("\n说明: 由于配置中 low_thinking=true，将自动使用 thinking_level='low'")


async def example_2_override_thinking_level():
    """示例2：运行时覆盖思考级别"""
    print("\n" + "=" * 80)
    print("示例 2: 运行时覆盖思考级别")
    print("=" * 80)
    
    # 获取视频摘要客户端（默认使用 high_thinking）
    client = get_model_client("video_summary")
    
    print(f"\n任务类型: video_summary")
    print(f"配置的 low_thinking: {client.config.low_thinking}")
    print(f"默认 thinking_level: {'low' if client.config.low_thinking else 'high'}")
    
    # 场景1：使用配置默认值（high thinking）
    print("\n场景 1 - 使用配置默认值:")
    print("  response = await client.generate_content(")
    print("      prompt='分析视频内容...'")
    print("  )")
    print("  # 使用 thinking_level='high'（来自配置）")
    
    # 场景2：显式指定为 low thinking（用于快速预览）
    print("\n场景 2 - 显式指定为 low thinking:")
    print("  response = await client.generate_content(")
    print("      prompt='快速预览视频内容...',")
    print("      thinking_level='low'  # 覆盖配置")
    print("  )")
    print("  # 使用 thinking_level='low'（运行时指定）")


async def example_3_compare_performance():
    """示例3：对比不同思考模式的性能"""
    print("\n" + "=" * 80)
    print("示例 3: 对比不同思考模式的性能")
    print("=" * 80)
    
    print("\n说明: 这是一个性能对比示例（不实际调用API）")
    print("\n假设场景: 转换一个5000字的HTML文章")
    
    # 模拟性能数据
    scenarios = [
        {
            "mode": "Low Thinking",
            "thinking_level": "low",
            "avg_time": 3.5,
            "quality_score": 92,
            "use_case": "快速转换，格式准确"
        },
        {
            "mode": "Medium Thinking",
            "thinking_level": "medium",
            "avg_time": 6.0,
            "quality_score": 95,
            "use_case": "平衡速度和质量"
        },
        {
            "mode": "High Thinking",
            "thinking_level": "high",
            "avg_time": 10.0,
            "quality_score": 97,
            "use_case": "最高质量，深度理解"
        }
    ]
    
    print("\n性能对比:")
    print("-" * 80)
    print(f"{'模式':<20} {'响应时间':<12} {'质量分数':<12} {'适用场景':<30}")
    print("-" * 80)
    
    for scenario in scenarios:
        print(f"{scenario['mode']:<20} "
              f"{scenario['avg_time']:.1f}s{'':<8} "
              f"{scenario['quality_score']}/100{'':<6} "
              f"{scenario['use_case']:<30}")
    
    print("-" * 80)
    
    # 计算性能提升
    low_time = scenarios[0]['avg_time']
    high_time = scenarios[2]['avg_time']
    speedup = (high_time / low_time - 1) * 100
    
    print(f"\n性能提升: Low Thinking 比 High Thinking 快 {speedup:.1f}%")
    print(f"质量差异: {scenarios[2]['quality_score'] - scenarios[0]['quality_score']} 分")


async def example_4_task_specific_recommendations():
    """示例4：不同任务的推荐配置"""
    print("\n" + "=" * 80)
    print("示例 4: 不同任务的推荐配置")
    print("=" * 80)
    
    recommendations = [
        {
            "task": "HTML转Markdown",
            "task_type": "html_to_markdown",
            "recommended": "low",
            "reason": "格式转换任务，结构明确，不需要深度理解"
        },
        {
            "task": "视频摘要",
            "task_type": "video_summary",
            "recommended": "high",
            "reason": "需要理解内容、提炼要点、创作文章"
        },
        {
            "task": "PDF分析",
            "task_type": "pdf_processing",
            "recommended": "high",
            "reason": "多模态分析，需要理解图表和文本的关联"
        },
        {
            "task": "可视化生成",
            "task_type": "visual_generation",
            "recommended": "high",
            "reason": "需要创造性和设计能力"
        },
        {
            "task": "文档解读",
            "task_type": "document_analysis",
            "recommended": "high",
            "reason": "需要深度理解和分析能力"
        }
    ]
    
    print("\n任务类型推荐:")
    print("-" * 80)
    
    for rec in recommendations:
        client = get_model_client(rec['task_type'])
        actual = "low" if client.config.low_thinking else "high"
        status = "✅" if actual == rec['recommended'] else "⚠️"
        
        print(f"\n{status} {rec['task']} ({rec['task_type']})")
        print(f"   推荐: {rec['recommended']} thinking")
        print(f"   当前: {actual} thinking")
        print(f"   原因: {rec['reason']}")


async def example_5_dynamic_selection():
    """示例5：根据场景动态选择思考模式"""
    print("\n" + "=" * 80)
    print("示例 5: 根据场景动态选择思考模式")
    print("=" * 80)
    
    print("\n实际应用场景:")
    
    scenarios = [
        {
            "scenario": "用户预览",
            "description": "用户想快速预览文档内容",
            "thinking_level": "low",
            "reason": "速度优先，质量要求不高"
        },
        {
            "scenario": "正式发布",
            "description": "生成最终发布的内容",
            "thinking_level": "high",
            "reason": "质量优先，可以接受较长等待"
        },
        {
            "scenario": "批量处理",
            "description": "批量转换100个文档",
            "thinking_level": "low",
            "reason": "成本和速度优先"
        },
        {
            "scenario": "重要客户",
            "description": "为重要客户生成定制报告",
            "thinking_level": "high",
            "reason": "质量和准确性最重要"
        }
    ]
    
    print("\n动态选择策略:")
    print("-" * 80)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n场景 {i}: {scenario['scenario']}")
        print(f"  描述: {scenario['description']}")
        print(f"  选择: {scenario['thinking_level']} thinking")
        print(f"  原因: {scenario['reason']}")
        
        print(f"\n  代码示例:")
        print(f"    client = get_model_client('html_to_markdown')")
        print(f"    response = await client.generate_content(")
        print(f"        prompt='...',")
        print(f"        thinking_level='{scenario['thinking_level']}'")
        print(f"    )")


async def main():
    """运行所有示例"""
    print("\n" + "=" * 80)
    print("Low Thinking 模式使用示例")
    print("=" * 80)
    
    # 运行所有示例
    await example_1_use_config_default()
    await example_2_override_thinking_level()
    await example_3_compare_performance()
    await example_4_task_specific_recommendations()
    await example_5_dynamic_selection()
    
    # 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print("\n关键要点:")
    print("1. 配置文件中设置默认的 thinking 模式")
    print("2. 运行时可以通过 thinking_level 参数覆盖")
    print("3. 格式转换任务推荐使用 low_thinking")
    print("4. 深度分析任务推荐使用 high_thinking")
    print("5. 根据实际场景动态选择合适的模式")
    
    print("\n更多信息:")
    print("- 配置文件: config/model_config.yaml")
    print("- 文档: docs/low_thinking_mode.md")
    print("- 测试: python tests/test_low_thinking_config.py")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
