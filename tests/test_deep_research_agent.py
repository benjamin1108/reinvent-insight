"""
Gemini Deep Research Agent 体验 Demo

测试新的 Interactions API 中的 Deep Research Agent 功能。
这个 Agent 可以自动进行网络搜索、分析和综合研究报告。

用法:
    python tests/test_deep_research_agent.py

环境变量:
    GEMINI_API_KEY: Gemini API 密钥
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 手动加载 .env 文件
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())


async def test_deep_research_sync():
    """后台模式：启动研究并轮询等待结果"""
    print("\n" + "="*60)
    print("测试 1: Deep Research Agent")
    print("="*60)
    
    try:
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ 错误: GEMINI_API_KEY 环境变量未设置")
            return
        
        client = genai.Client(api_key=api_key)
        
        # 简单的研究查询
        query = "2024年AI Agent技术的最新进展有哪些？请总结主要趋势。"
        
        print(f"\n📝 研究问题: {query}")
        print("\n🚀 启动深度研究任务...")
        
        start_time = time.time()
        
        # Deep Research Agent 必须使用 background=True
        interaction = client.interactions.create(
            agent="deep-research-pro-preview-12-2025",
            input=query,
            background=True,  # 必须后台运行
        )
        
        print(f"\n✅ 任务已启动!")
        print(f"   ID: {interaction.id}")
        print(f"   状态: {interaction.status}")
        
        # 轮询等待完成
        print("\n⏳ 等待研究完成（预计2-5分钟）...")
        max_wait = 600  # 最长等待10分钟
        poll_interval = 10
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(poll_interval)
            waited += poll_interval
            
            current = client.interactions.get(id=interaction.id)
            status = current.status
            
            print(f"   [{waited}s] 状态: {status}")
            
            if status == "completed":
                elapsed = time.time() - start_time
                print(f"\n🎉 研究完成! 总耗时: {elapsed:.1f}秒")
                
                if current.outputs:
                    for output in current.outputs:
                        if hasattr(output, 'text') and output.text:
                            text = output.text
                            
                            # 保存完整报告到文件
                            report_file = project_root / "downloads" / f"deep_research_{int(time.time())}.md"
                            report_file.parent.mkdir(exist_ok=True)
                            report_file.write_text(text, encoding='utf-8')
                            print(f"\n📄 完整报告已保存: {report_file}")
                            print(f"   报告长度: {len(text)} 字符")
                            
                            # 控制台只显示摘要
                            print("\n" + "-"*50)
                            print("📊 报告预览 (前2000字符):")
                            print("-"*50)
                            print(text[:2000] + "\n...")
                
                if current.usage:
                    print("\n📈 Token 统计:")
                    print(f"   输入: {current.usage.total_input_tokens}")
                    print(f"   输出: {current.usage.total_output_tokens}")
                    if hasattr(current.usage, 'total_reasoning_tokens'):
                        print(f"   推理: {current.usage.total_reasoning_tokens}")
                
                return current
            
            elif status in ["failed", "cancelled"]:
                print(f"\n❌ 研究{status}")
                return None
        
        print(f"\n⚠️ 超时，可稍后用ID查询: {interaction.id}")
        return None
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_deep_research_background():
    """后台模式：异步研究，通过 ID 查询状态"""
    print("\n" + "="*60)
    print("测试 2: Deep Research Agent (后台模式)")
    print("="*60)
    
    try:
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ 错误: GEMINI_API_KEY 环境变量未设置")
            return
        
        client = genai.Client(api_key=api_key)
        
        # 更复杂的研究查询
        query = """
        请深入研究以下主题并提供详细报告:
        
        主题: Transformer架构在2024年的最新变体和优化方向
        
        要求:
        1. 主要的架构改进（如 Mamba、RWKV、RetNet 等）
        2. 效率优化技术（稀疏注意力、线性注意力等）
        3. 多模态 Transformer 的进展
        4. 实际应用案例
        """
        
        print(f"\n📝 研究问题:\n{query}")
        print("\n🚀 启动后台研究任务...")
        
        # 使用后台模式启动研究
        interaction = client.interactions.create(
            agent="deep-research-pro-preview-12-2025",
            input=query,
            background=True,  # 后台模式
            agent_config={
                "type": "deep-research",
                "thinking_summaries": "auto"  # 获取思维摘要
            }
        )
        
        print(f"\n✅ 任务已启动!")
        print(f"   Interaction ID: {interaction.id}")
        print(f"   状态: {interaction.status}")
        
        # 轮询检查状态
        print("\n⏳ 等待研究完成...")
        max_wait = 300  # 最长等待 5 分钟
        poll_interval = 10  # 每 10 秒检查一次
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(poll_interval)
            waited += poll_interval
            
            # 获取最新状态
            current = client.interactions.get(id=interaction.id)
            
            status = current.status
            print(f"   [{waited}s] 状态: {status}")
            
            if status == "completed":
                print("\n🎉 研究完成!")
                
                # 显示结果
                if current.outputs:
                    for output in current.outputs:
                        if hasattr(output, 'text') and output.text:
                            print("\n" + "-"*40)
                            print("📊 研究报告:")
                            print("-"*40)
                            text = output.text
                            if len(text) > 3000:
                                print(text[:3000] + f"\n\n... [报告已截断，完整内容共 {len(text)} 字符]")
                            else:
                                print(text)
                
                # Token 统计
                if current.usage:
                    print("\n📈 Token 使用统计:")
                    print(f"   输入: {current.usage.total_input_tokens}")
                    print(f"   输出: {current.usage.total_output_tokens}")
                    print(f"   推理: {current.usage.total_reasoning_tokens}")
                    print(f"   总计: {current.usage.total_tokens}")
                
                return current
            
            elif status == "failed":
                print("\n❌ 研究失败!")
                return None
            
            elif status == "cancelled":
                print("\n⚠️ 研究被取消")
                return None
        
        print(f"\n⚠️ 超时: 研究未能在 {max_wait} 秒内完成")
        print(f"   你可以稍后使用 ID 查询结果: {interaction.id}")
        return None
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_deep_research_streaming():
    """流式模式：实时获取研究进度"""
    print("\n" + "="*60)
    print("测试 3: Deep Research Agent (流式模式)")
    print("="*60)
    
    try:
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ 错误: GEMINI_API_KEY 环境变量未设置")
            return
        
        client = genai.Client(api_key=api_key)
        
        query = "请简要介绍 GPT-4o 和 Claude 3.5 的主要区别"
        
        print(f"\n📝 研究问题: {query}")
        print("\n📡 启动流式研究...")
        
        # 使用流式模式
        interaction = client.interactions.create(
            agent="deep-research-pro-preview-12-2025",
            input=query,
            stream=True,  # 流式模式
        )
        
        print("\n" + "-"*40)
        print("📊 实时研究输出:")
        print("-"*40)
        
        # 处理流式响应
        full_text = ""
        for event in interaction:
            # 检查事件类型
            if hasattr(event, 'event_type'):
                if event.event_type == 'content.delta':
                    if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                        chunk = event.delta.text
                        print(chunk, end='', flush=True)
                        full_text += chunk
                elif event.event_type == 'interaction.complete':
                    print("\n\n✅ 流式输出完成!")
            elif hasattr(event, 'text'):
                # 直接文本输出
                print(event.text, end='', flush=True)
                full_text += event.text
        
        print(f"\n\n📏 总输出长度: {len(full_text)} 字符")
        return full_text
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主测试入口"""
    print("\n" + "="*60)
    print("🔬 Gemini Deep Research Agent 体验 Demo")
    print("="*60)
    
    # 检查 SDK
    try:
        from google import genai
        print("\n✅ google-genai SDK 已安装")
    except ImportError:
        print("\n❌ 请先安装 SDK: pip install google-genai")
        return
    
    # 检查 API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 请设置 GEMINI_API_KEY 环境变量")
        return
    print(f"✅ API Key 已配置 ({api_key[:8]}...)")
    
    # 运行测试
    print("\n" + "="*60)
    print("选择测试模式:")
    print("  1. 同步模式 (等待完成，适合短查询)")
    print("  2. 后台模式 (异步执行，适合长研究)")
    print("  3. 流式模式 (实时输出)")
    print("  4. 运行所有测试")
    print("="*60)
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == "1":
        await test_deep_research_sync()
    elif choice == "2":
        await test_deep_research_background()
    elif choice == "3":
        await test_deep_research_streaming()
    elif choice == "4":
        await test_deep_research_sync()
        await test_deep_research_background()
        await test_deep_research_streaming()
    else:
        print("无效选项，运行同步模式...")
        await test_deep_research_sync()
    
    print("\n" + "="*60)
    print("🎉 Demo 完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
