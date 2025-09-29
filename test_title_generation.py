#!/usr/bin/env python3
"""
PDF标题生成质量测试脚本
验证AI生成的中文标题是否符合质量要求
"""

import asyncio
import os
import sys
import tempfile
import shutil
from src.reinvent_insight.pdf_processor import PDFProcessor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_test_pdf(title, content_lines, filename):
    """创建测试PDF文件"""
    c = canvas.Canvas(filename, pagesize=letter)
    
    # 设置字体
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 750, title)
    
    # 添加内容
    c.setFont("Helvetica", 12)
    y_position = 700
    for line in content_lines:
        c.drawString(100, y_position, line)
        y_position -= 20
        if y_position < 100:  # 换页
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = 750
    
    c.save()

async def test_title_generation():
    """测试PDF标题生成功能"""
    
    # 检查API密钥
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置GEMINI_API_KEY环境变量")
        return False
    
    # 测试用例
    test_cases = [
        {
            "name": "云计算技术白皮书",
            "content": [
                "随着数字化转型的加速，云计算技术已成为企业IT基础设施的核心。",
                "本文档详细介绍了云原生架构、容器化技术、微服务设计模式，",
                "以及如何构建高可用、高扩展性的云端应用程序。",
                "",
                "第一章：云原生架构设计原则",
                "• 可扩展性设计",
                "• 容错与恢复机制", 
                "• 服务网格架构",
                "",
                "第二章：容器化最佳实践",
                "• Docker容器优化",
                "• Kubernetes集群管理",
                "• CI/CD流水线集成",
                "",
                "第三章：性能监控与运维",
                "• 实时监控系统",
                "• 日志管理策略",
                "• 自动化运维工具"
            ]
        },
        {
            "name": "人工智能应用开发指南",
            "content": [
                "人工智能技术正在重塑各行各业的业务模式和工作流程。",
                "本指南介绍了如何利用机器学习、深度学习和自然语言处理技术",
                "构建智能化的企业应用系统。",
                "",
                "核心技术栈：",
                "• TensorFlow / PyTorch深度学习框架",
                "• Transformer模型与大语言模型",
                "• 计算机视觉与图像识别",
                "• 语音识别与语音合成",
                "",
                "应用场景：",
                "• 智能客服与对话系统",
                "• 文档智能处理与分析",
                "• 预测性维护与异常检测",
                "• 个性化推荐与内容生成"
            ]
        },
        {
            "name": "区块链技术与数字金融",
            "content": [
                "区块链技术作为分布式账本技术的代表，正在推动金融科技创新。",
                "本文探讨了区块链在数字货币、智能合约、DeFi等领域的应用。",
                "",
                "技术架构：",
                "• 共识机制（PoW, PoS, DPoS）",
                "• 智能合约平台（Ethereum, Solana）",
                "• 跨链协议与互操作性",
                "• 隐私保护与零知识证明",
                "",
                "应用领域：",
                "• 数字支付与跨境汇款",
                "• 供应链溯源与防伪",
                "• 数字身份认证",
                "• 去中心化金融（DeFi）",
                "",
                "发展趋势：",
                "• Web3与元宇宙生态",
                "• 央行数字货币（CBDC）",
                "• NFT与数字资产交易"
            ]
        }
    ]
    
    processor = PDFProcessor()
    results = []
    
    print("🚀 开始测试PDF标题生成功能...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"📝 测试用例 {i}: {test_case['name']}")
        
        # 创建临时PDF文件
        temp_pdf = f"test_case_{i}.pdf"
        try:
            create_test_pdf(test_case['name'], test_case['content'], temp_pdf)
            print(f"  ✓ 已创建测试PDF: {temp_pdf}")
            
            # 上传PDF
            print("  📤 上传PDF文件...")
            file_info = await processor.upload_pdf(temp_pdf)
            print(f"  ✓ 上传成功: {file_info['name']}")
            
            # 生成大纲（不传入标题，让AI自动生成）
            print("  🤖 AI正在分析内容并生成标题...")
            outline_result = await processor.generate_outline(file_info)
            
            generated_title = outline_result['outline']['title']
            introduction = outline_result['outline']['introduction']
            
            print(f"  📋 原始文件名: {test_case['name']}")
            print(f"  ✨ AI生成标题: {generated_title}")
            print(f"  📄 生成简介: {introduction[:80]}...")
            
            # 评估标题质量
            quality_score = evaluate_title_quality(test_case['name'], generated_title)
            print(f"  📊 标题质量评分: {quality_score}/10")
            
            results.append({
                'original': test_case['name'],
                'generated': generated_title,
                'quality_score': quality_score,
                'introduction': introduction
            })
            
            # 清理文件
            await processor.delete_file(file_info["name"])
            print("  🗑️  已清理临时文件\n")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {str(e)}\n")
            results.append({
                'original': test_case['name'],
                'generated': '生成失败',
                'quality_score': 0,
                'error': str(e)
            })
        finally:
            # 清理本地文件
            if os.path.exists(temp_pdf):
                os.unlink(temp_pdf)
    
    # 生成测试报告
    print("=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    total_score = 0
    successful_tests = 0
    
    for i, result in enumerate(results, 1):
        print(f"\n测试 {i}:")
        print(f"  原始标题: {result['original']}")
        print(f"  生成标题: {result['generated']}")
        if 'error' not in result:
            print(f"  质量评分: {result['quality_score']}/10")
            total_score += result['quality_score']
            successful_tests += 1
        else:
            print(f"  错误信息: {result['error']}")
    
    if successful_tests > 0:
        avg_score = total_score / successful_tests
        print(f"\n📈 平均质量评分: {avg_score:.1f}/10")
        print(f"📊 成功测试: {successful_tests}/{len(test_cases)}")
        
        if avg_score >= 8.0:
            print("🎉 优秀！AI标题生成质量很高")
        elif avg_score >= 6.0:
            print("✅ 良好！AI标题生成质量符合要求")
        else:
            print("⚠️  需要改进标题生成质量")
    else:
        print("❌ 所有测试都失败了")
    
    return successful_tests > 0 and (total_score / successful_tests if successful_tests > 0 else 0) >= 6.0

def evaluate_title_quality(original_title, generated_title):
    """评估生成标题的质量"""
    score = 10  # 满分10分
    
    # 检查是否为空或错误
    if not generated_title or generated_title == "生成失败":
        return 0
    
    # 检查长度（理想长度10-30字）
    length = len(generated_title)
    if length < 5:
        score -= 3  # 太短
    elif length > 50:
        score -= 2  # 太长
    elif 10 <= length <= 30:
        score += 1  # 理想长度，加分
    
    # 检查是否包含通用词汇（减分）
    generic_words = ['解决方案', '白皮书', '指南', '手册', '文档']
    for word in generic_words:
        if word in generated_title:
            score -= 1
    
    # 检查是否包含技术特色词汇（加分）
    tech_words = ['云原生', '智能', '数字化', '区块链', 'AI', '架构', '平台', '系统', '技术', '创新']
    tech_score = 0
    for word in tech_words:
        if word in generated_title:
            tech_score += 0.5
    score += min(tech_score, 2)  # 最多加2分
    
    # 检查是否与原标题完全相同（减分）
    if generated_title == original_title:
        score -= 2
    
    # 检查字符质量（是否有乱码）
    if '?' in generated_title or '�' in generated_title:
        score -= 3
    
    return max(0, min(10, score))

if __name__ == "__main__":
    # 添加项目根目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 运行测试
    success = asyncio.run(test_title_generation())
    if success:
        print("\n✅ 标题生成功能测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 标题生成功能需要改进！")
        sys.exit(1)