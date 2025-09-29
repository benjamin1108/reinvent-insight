#!/usr/bin/env python3
"""
简化版PDF标题生成测试
"""

import asyncio
import os
import sys
from src.reinvent_insight.pdf_processor import PDFProcessor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

async def quick_test():
    """快速测试标题生成功能"""
    
    # 检查API密钥
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置GEMINI_API_KEY环境变量")
        return False
    
    print("🚀 开始快速测试PDF标题生成...")
    
    # 创建一个内容丰富的测试PDF
    test_pdf = "quick_test.pdf"
    c = canvas.Canvas(test_pdf, pagesize=letter)
    
    # 添加技术内容
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 750, "企业级微服务架构设计与实践")
    
    c.setFont("Helvetica", 12)
    content = [
        "随着云原生技术的快速发展，微服务架构已成为现代企业数字化转型的核心技术选择。",
        "本文档详细介绍了如何设计和实施可扩展、高可用的微服务架构体系。",
        "",
        "核心技术栈：",
        "• Kubernetes容器编排平台",
        "• Service Mesh服务网格",
        "• API Gateway与服务治理",
        "• 分布式数据库与存储",
        "• 监控告警与可观测性",
        "",
        "架构优势：",
        "• 技术栈多样化与团队自主性",
        "• 独立部署与快速迭代",
        "• 弹性扩展与故障隔离",
        "• DevOps流程标准化"
    ]
    
    y_pos = 700
    for line in content:
        c.drawString(100, y_pos, line)
        y_pos -= 20
    
    c.save()
    print(f"✓ 已创建测试PDF: {test_pdf}")
    
    try:
        processor = PDFProcessor()
        
        # 上传PDF
        print("📤 上传PDF文件...")
        file_info = await processor.upload_pdf(test_pdf)
        print(f"✓ 上传成功: {file_info['name']}")
        
        # 生成大纲（不传入标题，让AI自动生成）
        print("🤖 AI正在分析内容并生成标题...")
        outline_result = await processor.generate_outline(file_info)
        
        generated_title = outline_result['outline']['title']
        introduction = outline_result['outline']['introduction']
        
        print(f"\n📋 原始文件名: 企业级微服务架构设计与实践")
        print(f"✨ AI生成标题: {generated_title}")
        print(f"📄 生成简介: {introduction[:120]}...")
        
        # 简单质量检查
        quality_checks = {
            "长度合适 (10-40字)": 10 <= len(generated_title) <= 40,
            "包含技术特色": any(word in generated_title for word in ['微服务', '架构', '云原生', '容器', '平台', '系统', '技术']),
            "避免通用词汇": not any(word in generated_title for word in ['解决方案', '白皮书', '指南']),
            "不含乱码": '?' not in generated_title and '�' not in generated_title,
            "与原标题不同": generated_title != "企业级微服务架构设计与实践"
        }
        
        print(f"\n📊 质量检查结果:")
        passed_checks = 0
        for check, result in quality_checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check}")
            if result:
                passed_checks += 1
        
        score = (passed_checks / len(quality_checks)) * 100
        print(f"\n📈 质量评分: {score:.0f}% ({passed_checks}/{len(quality_checks)})")
        
        # 清理
        await processor.delete_file(file_info["name"])
        os.unlink(test_pdf)
        print("🗑️  已清理临时文件")
        
        if score >= 80:
            print("\n🎉 优秀！PDF标题生成功能运行良好")
            return True
        elif score >= 60:
            print("\n✅ 良好！PDF标题生成功能基本符合要求")
            return True
        else:
            print("\n⚠️  PDF标题生成功能需要进一步优化")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        # 清理
        if os.path.exists(test_pdf):
            os.unlink(test_pdf)
        return False

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    success = asyncio.run(quick_test())
    if success:
        print("\n🎯 PDF标题生成功能测试通过！")
    else:
        print("\n🔧 需要进一步优化PDF标题生成功能")