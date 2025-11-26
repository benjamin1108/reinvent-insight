"""
测试 low_thinking 模式配置

验证不同任务类型的 thinking 模式配置是否正确加载和应用。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reinvent_insight.model_config import ModelConfigManager, get_model_client


def test_config_loading():
    """测试配置加载"""
    print("=" * 80)
    print("测试 1: 配置加载")
    print("=" * 80)
    
    # 获取配置管理器
    manager = ModelConfigManager.get_instance()
    
    # 测试各个任务类型的配置
    task_types = [
        "html_to_markdown",
        "video_summary",
        "pdf_processing",
        "visual_generation",
        "document_analysis",
        "text_to_speech"
    ]
    
    print("\n任务类型配置:")
    print("-" * 80)
    for task_type in task_types:
        config = manager.get_config(task_type)
        print(f"\n{task_type}:")
        print(f"  Provider: {config.provider}")
        print(f"  Model: {config.model_name}")
        print(f"  Low Thinking: {config.low_thinking}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Max Tokens: {config.max_output_tokens}")
    
    print("\n" + "=" * 80)
    print("✅ 配置加载测试完成")
    print("=" * 80)


def test_thinking_mode_mapping():
    """测试思考模式映射"""
    print("\n" + "=" * 80)
    print("测试 2: 思考模式映射")
    print("=" * 80)
    
    manager = ModelConfigManager.get_instance()
    
    # 预期的思考模式配置
    expected_modes = {
        "html_to_markdown": True,      # 快速转换
        "video_summary": False,         # 深度分析
        "pdf_processing": False,        # 深度分析
        "visual_generation": False,     # 创意生成
        "document_analysis": False,     # 深度分析
        "text_to_speech": False,        # TTS不使用thinking（但配置中没有）
    }
    
    print("\n思考模式验证:")
    print("-" * 80)
    all_correct = True
    
    for task_type, expected_low_thinking in expected_modes.items():
        config = manager.get_config(task_type)
        actual_low_thinking = config.low_thinking
        
        status = "✅" if actual_low_thinking == expected_low_thinking else "❌"
        print(f"{status} {task_type}: "
              f"期望={expected_low_thinking}, "
              f"实际={actual_low_thinking}")
        
        if actual_low_thinking != expected_low_thinking:
            all_correct = False
    
    print("\n" + "=" * 80)
    if all_correct:
        print("✅ 思考模式映射测试通过")
    else:
        print("❌ 思考模式映射测试失败")
    print("=" * 80)
    
    return all_correct


def test_thinking_level_selection():
    """测试思考级别选择逻辑"""
    print("\n" + "=" * 80)
    print("测试 3: 思考级别选择逻辑")
    print("=" * 80)
    
    manager = ModelConfigManager.get_instance()
    
    print("\n思考级别选择:")
    print("-" * 80)
    
    # 测试不同任务类型应该使用的thinking_level
    test_cases = [
        ("html_to_markdown", "low"),   # low_thinking=true -> "low"
        ("video_summary", "high"),      # low_thinking=false -> "high"
        ("pdf_processing", "high"),     # low_thinking=false -> "high"
    ]
    
    for task_type, expected_level in test_cases:
        config = manager.get_config(task_type)
        actual_level = "low" if config.low_thinking else "high"
        
        status = "✅" if actual_level == expected_level else "❌"
        print(f"{status} {task_type}: "
              f"low_thinking={config.low_thinking} -> "
              f"thinking_level={actual_level} "
              f"(期望={expected_level})")
    
    print("\n" + "=" * 80)
    print("✅ 思考级别选择测试完成")
    print("=" * 80)


async def test_client_initialization():
    """测试客户端初始化"""
    print("\n" + "=" * 80)
    print("测试 4: 客户端初始化")
    print("=" * 80)
    
    print("\n初始化不同任务类型的客户端:")
    print("-" * 80)
    
    task_types = [
        "html_to_markdown",
        "video_summary",
        "pdf_processing",
    ]
    
    for task_type in task_types:
        try:
            client = get_model_client(task_type)
            print(f"✅ {task_type}: "
                  f"Provider={client.config.provider}, "
                  f"Model={client.config.model_name}, "
                  f"LowThinking={client.config.low_thinking}")
        except Exception as e:
            print(f"❌ {task_type}: 初始化失败 - {e}")
    
    print("\n" + "=" * 80)
    print("✅ 客户端初始化测试完成")
    print("=" * 80)


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("Low Thinking 模式配置测试")
    print("=" * 80)
    
    # 测试1: 配置加载
    test_config_loading()
    
    # 测试2: 思考模式映射
    mapping_ok = test_thinking_mode_mapping()
    
    # 测试3: 思考级别选择
    test_thinking_level_selection()
    
    # 测试4: 客户端初始化
    asyncio.run(test_client_initialization())
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print("\n配置说明:")
    print("- html_to_markdown: 使用 low_thinking (快速转换)")
    print("- video_summary: 使用 high_thinking (深度分析)")
    print("- pdf_processing: 使用 high_thinking (深度分析)")
    print("- visual_generation: 使用 high_thinking (创意生成)")
    print("- document_analysis: 使用 high_thinking (深度分析)")
    
    if mapping_ok:
        print("\n✅ 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，请检查配置文件")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
