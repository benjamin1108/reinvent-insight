#!/usr/bin/env python3
"""测试百分号修复"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.reinvent_insight.services.tts_text_preprocessor import TTSTextPreprocessor

def test_percent_fix():
    """测试百分号处理修复"""
    preprocessor = TTSTextPreprocessor()
    
    # 测试用例
    test_cases = [
        ("降低 40% 成本", "降低 百分之40 成本"),
        ("提升 100% 性能", "提升 百分之100 性能"),
        ("增长 25%", "增长 百分之25"),
        ("下降15%的趋势", "下降百分之15的趋势"),
    ]
    
    print("测试百分号处理:")
    print("=" * 60)
    
    all_passed = True
    for input_text, expected in test_cases:
        result = preprocessor.replace_special_symbols(input_text)
        passed = result == expected
        all_passed = all_passed and passed
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}")
        print(f"  输入: {input_text}")
        print(f"  期望: {expected}")
        print(f"  实际: {result}")
        print()
    
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("❌ 有测试失败")
        sys.exit(1)

if __name__ == "__main__":
    test_percent_fix()
