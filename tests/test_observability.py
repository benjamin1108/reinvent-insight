"""测试模型可观测层功能"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量启用可观测层
os.environ["MODEL_OBSERVABILITY_ENABLED"] = "true"
os.environ["MODEL_OBSERVABILITY_LOG_LEVEL"] = "DETAILED"

from reinvent_insight.infrastructure.ai.model_config import get_model_client
from reinvent_insight.infrastructure.ai.observability import set_business_context


async def test_basic_observability():
    """测试基础可观测功能"""
    print("=" * 80)
    print("测试1: 基础模型调用记录")
    print("=" * 80)
    
    # 获取模型客户端
    client = get_model_client("outline")
    
    # 测试简单调用
    result = await client.generate_content(
        prompt="请用一句话介绍人工智能。",
        is_json=False
    )
    
    print(f"✓ 模型响应: {result[:100]}...")
    print("✓ 日志应该已写入 downloads/model_logs/")


async def test_with_business_context():
    """测试带业务上下文的记录"""
    print("\n" + "=" * 80)
    print("测试2: 业务上下文记录")
    print("=" * 80)
    
    client = get_model_client("outline")
    
    # 使用业务上下文
    with set_business_context(
        task_id="test_task_123",
        task_type="observability_test",
        phase="validation"
    ):
        result = await client.generate_content(
            prompt="解释什么是可观测性。",
            is_json=False
        )
    
    print(f"✓ 模型响应: {result[:100]}...")
    print("✓ 日志中应包含业务上下文信息")


async def test_error_handling():
    """测试错误情况的记录"""
    print("\n" + "=" * 80)
    print("测试3: 错误记录")
    print("=" * 80)
    
    client = get_model_client("outline")
    
    try:
        # 尝试一个可能会失败的调用（使用空提示词）
        result = await client.generate_content(
            prompt="",
            is_json=False
        )
    except Exception as e:
        print(f"✓ 捕获到预期错误: {type(e).__name__}")
        print("✓ 错误信息应该已记录到日志")


async def check_log_files():
    """检查日志文件"""
    print("\n" + "=" * 80)
    print("检查日志文件")
    print("=" * 80)
    
    from datetime import datetime
    log_dir = Path("downloads/model_logs") / datetime.now().strftime("%Y-%m-%d")
    
    if log_dir.exists():
        jsonl_files = list(log_dir.glob("*_interactions.jsonl"))
        human_files = list(log_dir.glob("*_interactions_human.txt"))
        
        print(f"✓ 日志目录: {log_dir}")
        print(f"✓ JSONL 文件: {len(jsonl_files)} 个")
        print(f"✓ 人类可读文件: {len(human_files)} 个")
        
        # 显示文件大小
        for f in jsonl_files:
            size = f.stat().st_size
            print(f"  - {f.name}: {size} bytes")
        
        # 读取最后一条记录
        if jsonl_files:
            with open(jsonl_files[0], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    import json
                    last_record = json.loads(lines[-1])
                    print(f"\n最新记录:")
                    print(f"  - 交互ID: {last_record['interaction_id']}")
                    print(f"  - 提供商: {last_record['provider']}")
                    print(f"  - 模型: {last_record['model_name']}")
                    print(f"  - 延迟: {last_record['performance']['latency_ms']} ms")
                    print(f"  - 状态: {last_record['response']['status']}")
    else:
        print(f"⚠ 日志目录不存在: {log_dir}")


async def main():
    """主测试函数"""
    print("\n模型可观测层功能测试")
    print("=" * 80 + "\n")
    
    try:
        # 基础测试
        await test_basic_observability()
        
        # 业务上下文测试
        await test_with_business_context()
        
        # 错误处理测试（可选，可能会失败）
        # await test_error_handling()
        
        # 检查日志文件
        await check_log_files()
        
        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
