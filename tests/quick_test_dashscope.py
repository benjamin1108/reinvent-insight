#!/usr/bin/env python3
"""
DashScope 快速测试脚本

快速验证 DashScope 集成是否正常工作。

使用方法：
  export DASHSCOPE_API_KEY=your-api-key
  python tests/quick_test_dashscope.py
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


async def quick_test():
    """快速测试"""
    print("=" * 60)
    print("DashScope 快速测试")
    print("=" * 60)
    
    # 检查API Key
    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key:
        print("❌ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("   请在 .env 文件中添加: DASHSCOPE_API_KEY=your-api-key")
        print("   或运行: export DASHSCOPE_API_KEY=your-api-key")
        return False
    
    print(f"✓ API Key: {api_key[:8]}...{api_key[-4:]}\n")
    
    # 测试导入
    try:
        from reinvent_insight.model_config import get_model_client
        print("✓ 模块导入成功\n")
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    
    # 使用配置系统获取客户端
    try:
        print("使用配置系统获取客户端...")
        client = get_model_client("dashscope_test")
        print("✓ DashScope 客户端初始化成功")
        print(f"  任务类型: dashscope_test")
        print(f"  模型: {client.config.model_name}\n")
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        if "dashscope 包未安装" in str(e):
            print("   请运行: pip install dashscope")
        return False
    
    # 测试文本生成
    try:
        print("测试文本生成...")
        prompt = "请用一句话介绍阿里云。"
        result = await client.generate_content(prompt)
        
        print(f"✓ 生成成功!")
        print(f"  提示词: {prompt}")
        print(f"  响应: {result}\n")
        
    except Exception as e:
        print(f"❌ 文本生成失败: {e}\n")
        return False
    
    # 测试配置系统集成
    try:
        print("测试配置系统集成...")
        
        # 使用项目配置文件中的 dashscope_test 任务
        from reinvent_insight.model_config import get_model_client
        
        test_client = get_model_client("dashscope_test")
        result = await test_client.generate_content("测试配置系统")
        
        print("✓ 配置系统集成成功")
        print(f"  响应: {result[:50]}...\n" if len(result) > 50 else f"  响应: {result}\n")
        
    except Exception as e:
        print(f"❌ 配置系统集成失败: {e}\n")
        return False
    
    print("=" * 60)
    print("✓ 所有快速测试通过！")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(quick_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
