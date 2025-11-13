#!/usr/bin/env python3
"""
DashScope 使用示例

演示如何在项目中使用 DashScope 模型。
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


async def example_basic_usage():
    """示例 1: 基础使用"""
    print("\n" + "="*60)
    print("示例 1: 基础文本生成")
    print("="*60)
    
    from reinvent_insight.model_config import get_model_client
    
    # 使用配置文件中的 dashscope_test 任务
    client = get_model_client("dashscope_test")
    
    # 生成内容
    prompt = "请用一句话介绍阿里云的核心优势。"
    result = await client.generate_content(prompt)
    
    print(f"提示词: {prompt}")
    print(f"响应: {result}")


async def example_json_output():
    """示例 2: JSON 格式输出"""
    print("\n" + "="*60)
    print("示例 2: JSON 格式输出")
    print("="*60)
    
    from reinvent_insight.model_config import get_model_client
    import json
    
    # 使用配置文件中的 dashscope_test 任务
    client = get_model_client("dashscope_test")
    
    prompt = """
请分析以下产品评论的情感倾向：

评论：这款产品质量很好，物流也很快，非常满意！

请以JSON格式返回：
{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "keywords": ["关键词1", "关键词2"]
}
"""
    
    result = await client.generate_content(prompt, is_json=True)
    
    print(f"提示词: {prompt.strip()}")
    print(f"\n响应 (JSON):")
    
    try:
        data = json.loads(result)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(result)


async def example_multimodal():
    """示例 3: 多模态文档分析"""
    print("\n" + "="*60)
    print("示例 3: 多模态文档分析")
    print("="*60)
    
    from reinvent_insight.model_config import get_model_client
    
    # 检查是否有测试文件
    test_file = "test.pdf"
    if not os.path.exists(test_file):
        print(f"⚠️  未找到测试文件 {test_file}，跳过多模态示例")
        print("   提示: 创建一个 test.pdf 文件来测试多模态功能")
        return
    
    # 使用配置文件中的 dashscope_pdf_processing 任务
    client = get_model_client("dashscope_pdf_processing")
    
    # 上传文件
    file_info = await client.upload_file(test_file)
    print(f"文件: {test_file}")
    
    # 分析文档
    prompt = "请简要总结这个文档的主要内容，不超过100字。"
    result = await client.generate_content_with_file(prompt, file_info)
    
    print(f"提示词: {prompt}")
    print(f"响应: {result}")


async def example_different_models():
    """示例 4: 使用不同的任务配置"""
    print("\n" + "="*60)
    print("示例 4: 使用不同的任务配置")
    print("="*60)
    
    from reinvent_insight.model_config import get_model_client
    
    prompt = "请用一句话解释什么是云计算。"
    
    # 使用配置文件中定义的不同任务
    tasks = [
        ("dashscope_test", "测试任务 (qwen-turbo)"),
        ("dashscope_video_summary", "视频摘要任务 (qwen-max)"),
    ]
    
    for task_name, description in tasks:
        print(f"\n{description}:")
        
        try:
            client = get_model_client(task_name)
            result = await client.generate_content(prompt)
            print(f"  模型: {client.config.model_name}")
            print(f"  响应: {result}")
        except Exception as e:
            print(f"  ⚠️  跳过 (可能需要更高配额): {e}")


async def example_with_config_file():
    """示例 5: 查看配置信息"""
    print("\n" + "="*60)
    print("示例 5: 查看配置信息")
    print("="*60)
    
    from reinvent_insight.model_config import ModelConfigManager
    
    # 获取配置管理器
    manager = ModelConfigManager.get_instance()
    
    # 查看 DashScope 相关的任务配置
    dashscope_tasks = [
        "dashscope_test",
        "dashscope_video_summary",
        "dashscope_pdf_processing"
    ]
    
    print("配置文件中的 DashScope 任务:\n")
    
    for task_name in dashscope_tasks:
        try:
            config = manager.get_config(task_name)
            print(f"  • {task_name}:")
            print(f"    - 提供商: {config.provider}")
            print(f"    - 模型: {config.model_name}")
            print(f"    - 温度: {config.temperature}")
            print(f"    - 最大输出: {config.max_output_tokens}")
            print()
        except Exception as e:
            print(f"  • {task_name}: 配置不存在")
    
    print("提示: 可以在 config/model_config.yaml 中修改这些配置")


async def main():
    """主函数"""
    print("="*60)
    print("DashScope 使用示例")
    print("="*60)
    
    # 检查 API Key
    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key:
        print("\n❌ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("   请运行: export DASHSCOPE_API_KEY=your-api-key")
        return
    
    print(f"\n✓ API Key: {api_key[:8]}...{api_key[-4:]}")
    
    # 运行示例
    try:
        await example_basic_usage()
        await example_json_output()
        await example_multimodal()
        await example_different_models()
        await example_with_config_file()
        
        print("\n" + "="*60)
        print("✓ 所有示例运行完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n示例被用户中断")
        sys.exit(130)
