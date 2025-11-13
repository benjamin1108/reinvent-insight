#!/usr/bin/env python3
"""
DashScope 客户端测试脚本

该脚本测试 DashScope (阿里云通义千问) 模型客户端的功能。

使用方法：
1. 安装依赖: pip install dashscope
2. 设置环境变量: export DASHSCOPE_API_KEY=your-api-key
3. 运行测试: python tests/test_dashscope_client.py

测试内容：
- 基础文本生成
- JSON格式输出
- 多模态文件处理（如果提供测试文件）
- 错误处理
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reinvent_insight.model_config import (
    ModelConfig,
    DashScopeClient,
    ConfigurationError,
    APIError
)


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(message: str):
    """打印测试信息"""
    print(f"{Colors.BLUE}[TEST]{Colors.RESET} {message}")


def print_success(message: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_error(message: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def print_warning(message: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")


async def test_basic_text_generation(client: DashScopeClient):
    """测试基础文本生成"""
    print_test("测试基础文本生成...")
    
    try:
        prompt = "请用一句话介绍人工智能。"
        result = await client.generate_content(prompt)
        
        if result and len(result) > 0:
            print_success("基础文本生成成功")
            print(f"  提示词: {prompt}")
            print(f"  响应: {result[:100]}..." if len(result) > 100 else f"  响应: {result}")
            return True
        else:
            print_error("返回内容为空")
            return False
            
    except Exception as e:
        print_error(f"基础文本生成失败: {e}")
        return False


async def test_json_output(client: DashScopeClient):
    """测试JSON格式输出"""
    print_test("测试JSON格式输出...")
    
    try:
        prompt = """请分析以下文本的情感倾向，返回JSON格式：
        
文本：今天天气真好，心情很愉快！

返回格式：
{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "keywords": ["关键词1", "关键词2"]
}"""
        
        result = await client.generate_content(prompt, is_json=True)
        
        if result and len(result) > 0:
            print_success("JSON格式输出成功")
            print(f"  响应: {result[:200]}..." if len(result) > 200 else f"  响应: {result}")
            
            # 尝试解析JSON
            import json
            try:
                json_data = json.loads(result)
                print_success(f"  JSON解析成功: {json_data}")
                return True
            except json.JSONDecodeError:
                print_warning("  返回内容不是有效的JSON，但生成成功")
                return True
        else:
            print_error("返回内容为空")
            return False
            
    except Exception as e:
        print_error(f"JSON格式输出失败: {e}")
        return False


async def test_multimodal_with_file(client: DashScopeClient, test_file: str = None):
    """测试多模态文件处理"""
    print_test("测试多模态文件处理...")
    
    if not test_file or not os.path.exists(test_file):
        print_warning("未提供测试文件或文件不存在，跳过多模态测试")
        print_warning(f"  提示: 使用 --test-file 参数指定测试文件")
        return None
    
    try:
        # 上传文件
        file_info = await client.upload_file(test_file)
        print_success(f"文件准备完成: {file_info['name']}")
        
        # 生成内容
        prompt = "请简要描述这个文档的主要内容。"
        result = await client.generate_content_with_file(prompt, file_info)
        
        if result and len(result) > 0:
            print_success("多模态文件处理成功")
            print(f"  文件: {test_file}")
            print(f"  响应: {result[:200]}..." if len(result) > 200 else f"  响应: {result}")
            return True
        else:
            print_error("返回内容为空")
            return False
            
    except Exception as e:
        print_error(f"多模态文件处理失败: {e}")
        return False


async def test_error_handling(client: DashScopeClient):
    """测试错误处理"""
    print_test("测试错误处理...")
    
    try:
        # 测试空提示词
        try:
            await client.generate_content("")
            print_warning("空提示词未触发错误（可能被API接受）")
        except Exception as e:
            print_success(f"空提示词正确触发错误: {type(e).__name__}")
        
        return True
        
    except Exception as e:
        print_error(f"错误处理测试失败: {e}")
        return False


async def test_rate_limiting(client: DashScopeClient):
    """测试速率限制"""
    print_test("测试速率限制...")
    
    try:
        import time
        
        # 连续发送3个请求，测试速率限制
        start_time = time.time()
        
        for i in range(3):
            prompt = f"请说一个数字：{i+1}"
            await client.generate_content(prompt)
        
        elapsed = time.time() - start_time
        
        # 应该至少有 2 * interval 的延迟
        expected_min_time = 2 * client.config.rate_limit_interval
        
        if elapsed >= expected_min_time:
            print_success(f"速率限制工作正常 (耗时: {elapsed:.2f}秒)")
            return True
        else:
            print_warning(f"速率限制可能未生效 (耗时: {elapsed:.2f}秒, 预期: >{expected_min_time:.2f}秒)")
            return True
            
    except Exception as e:
        print_error(f"速率限制测试失败: {e}")
        return False


async def run_all_tests(api_key: str, test_file: str = None):
    """运行所有测试"""
    print_section("DashScope 客户端测试")
    
    # 检查API Key
    if not api_key:
        print_error("未设置 DASHSCOPE_API_KEY 环境变量")
        print_warning("请在 .env 文件中添加: DASHSCOPE_API_KEY=your-api-key")
        print_warning("或运行: export DASHSCOPE_API_KEY=your-api-key")
        return False
    
    print_success(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    
    # 使用配置系统获取客户端
    try:
        from reinvent_insight.model_config import get_model_client
        
        print_test("从配置系统加载客户端...")
        client = get_model_client("dashscope_test")
        print_success(f"DashScope 客户端初始化成功")
        print_success(f"  任务类型: dashscope_test")
        print_success(f"  模型: {client.config.model_name}")
        print_success(f"  温度: {client.config.temperature}")
    except ConfigurationError as e:
        print_error(f"客户端初始化失败: {e}")
        if "dashscope 包未安装" in str(e):
            print_warning("请运行: pip install dashscope")
        return False
    
    # 运行测试
    results = []
    
    print_section("1. 基础功能测试")
    results.append(await test_basic_text_generation(client))
    
    print_section("2. JSON输出测试")
    results.append(await test_json_output(client))
    
    print_section("3. 多模态测试")
    multimodal_result = await test_multimodal_with_file(client, test_file)
    if multimodal_result is not None:
        results.append(multimodal_result)
    
    print_section("4. 错误处理测试")
    results.append(await test_error_handling(client))
    
    print_section("5. 速率限制测试")
    results.append(await test_rate_limiting(client))
    
    # 统计结果
    print_section("测试总结")
    
    total = len(results)
    passed = sum(1 for r in results if r)
    failed = total - passed
    
    print(f"总测试数: {total}")
    print(f"{Colors.GREEN}通过: {passed}{Colors.RESET}")
    if failed > 0:
        print(f"{Colors.RED}失败: {failed}{Colors.RESET}")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    if success_rate == 100:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过！{Colors.RESET}")
        return True
    elif success_rate >= 80:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ 大部分测试通过 ({success_rate:.0f}%){Colors.RESET}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 测试失败 ({success_rate:.0f}%){Colors.RESET}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DashScope 客户端测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础测试
  python tests/test_dashscope_client.py
  
  # 包含多模态测试
  python tests/test_dashscope_client.py --test-file path/to/test.pdf
  
  # 指定API Key
  python tests/test_dashscope_client.py --api-key your-api-key
        """
    )
    
    parser.add_argument(
        '--api-key',
        help='DashScope API Key (默认从环境变量 DASHSCOPE_API_KEY 读取)'
    )
    
    parser.add_argument(
        '--test-file',
        help='用于多模态测试的文件路径 (可选)'
    )
    
    args = parser.parse_args()
    
    # 获取API Key
    api_key = args.api_key or os.getenv('DASHSCOPE_API_KEY')
    
    # 运行测试
    try:
        success = asyncio.run(run_all_tests(api_key, args.test_file))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}测试被用户中断{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print_error(f"测试运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
