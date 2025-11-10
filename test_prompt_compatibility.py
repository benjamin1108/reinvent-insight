#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Prompt 系统的向后兼容性
"""

import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from reinvent_insight import prompts
from reinvent_insight.prompt_manager import get_prompt_manager

def test_backward_compatibility():
    """测试向后兼容的常量访问"""
    print("=" * 60)
    print("测试向后兼容性")
    print("=" * 60)
    
    # 测试旧的常量访问方式（应该触发弃用警告）
    print("\n1. 测试旧常量访问（应该看到弃用警告）:")
    try:
        markdown_rules = prompts.MARKDOWN_BOLD_RULES
        print(f"✓ MARKDOWN_BOLD_RULES 可访问，长度: {len(markdown_rules)}")
    except Exception as e:
        print(f"✗ MARKDOWN_BOLD_RULES 访问失败: {e}")
    
    try:
        pdf_guide = prompts.PDF_MULTIMODAL_GUIDE
        print(f"✓ PDF_MULTIMODAL_GUIDE 可访问，长度: {len(pdf_guide)}")
    except Exception as e:
        print(f"✗ PDF_MULTIMODAL_GUIDE 访问失败: {e}")

def test_new_api():
    """测试新的 API"""
    print("\n" + "=" * 60)
    print("测试新 API")
    print("=" * 60)
    
    # 测试 get_prompt
    print("\n2. 测试 get_prompt():")
    try:
        base_prompt = prompts.get_prompt('youtube_deep_summary_base')
        print(f"✓ 获取 youtube_deep_summary_base，长度: {len(base_prompt)}")
    except Exception as e:
        print(f"✗ 获取失败: {e}")
    
    # 测试 format_prompt
    print("\n3. 测试 format_prompt():")
    try:
        formatted = prompts.format_prompt(
            'outline_template',
            content_type='测试内容类型',
            content_description='测试描述',
            full_content='测试内容'
        )
        print(f"✓ 格式化 outline_template，长度: {len(formatted)}")
        # 验证参数是否被替换
        if '测试内容类型' in formatted:
            print("✓ 参数替换成功")
        else:
            print("✗ 参数替换失败")
    except Exception as e:
        print(f"✗ 格式化失败: {e}")
    
    # 测试 list_available_prompts
    print("\n4. 测试 list_available_prompts():")
    try:
        prompts_list = prompts.list_available_prompts()
        print(f"✓ 可用 prompts 数量: {len(prompts_list)}")
        print("  可用的 prompts:")
        for config in prompts_list:
            print(f"    - {config.key} ({config.type}): {config.description}")
    except Exception as e:
        print(f"✗ 列表获取失败: {e}")

def test_prompt_manager():
    """测试 PromptManager 直接使用"""
    print("\n" + "=" * 60)
    print("测试 PromptManager 直接使用")
    print("=" * 60)
    
    print("\n5. 测试 PromptManager:")
    try:
        manager = get_prompt_manager()
        
        # 测试验证
        validation_result = manager.validate_prompts()
        print(f"✓ Prompt 验证完成")
        if validation_result['errors']:
            print(f"  错误: {len(validation_result['errors'])}")
            for error in validation_result['errors']:
                print(f"    - {error}")
        else:
            print("  ✓ 没有错误")
        
        if validation_result['warnings']:
            print(f"  警告: {len(validation_result['warnings'])}")
            for warning in validation_result['warnings']:
                print(f"    - {warning}")
        else:
            print("  ✓ 没有警告")
            
    except Exception as e:
        print(f"✗ PromptManager 测试失败: {e}")

def test_include_resolution():
    """测试 include 解析"""
    print("\n" + "=" * 60)
    print("测试 Include 解析")
    print("=" * 60)
    
    print("\n6. 测试 {{include:key}} 语法:")
    try:
        # 获取包含 includes 的模板
        chapter_template = prompts.get_prompt('chapter_template')
        
        # 检查是否包含了 markdown_bold_rules 的内容
        if '加粗样式规则' in chapter_template:
            print("✓ Include 解析成功，markdown_bold_rules 已被包含")
        else:
            print("✗ Include 解析失败，未找到预期内容")
            
        # 检查是否包含了 base prompt 的内容
        if '角色设定' in chapter_template or '中英双语技术解构官' in chapter_template:
            print("✓ Base prompt 已被包含")
        else:
            print("✗ Base prompt 未被包含")
            
    except Exception as e:
        print(f"✗ Include 解析测试失败: {e}")

if __name__ == '__main__':
    try:
        test_backward_compatibility()
        test_new_api()
        test_prompt_manager()
        test_include_resolution()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
