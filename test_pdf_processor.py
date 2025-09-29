#!/usr/bin/env python3
"""
PDF处理器测试脚本
"""

import asyncio
import os
import sys
from src.reinvent_insight.pdf_processor import PDFProcessor
from src.reinvent_insight.utils import generate_pdf_identifier, is_pdf_document, extract_pdf_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

async def test_pdf_processor():
    """测试PDF处理器功能"""
    try:
        # 检查是否设置了Gemini API密钥
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("错误: 请设置GEMINI_API_KEY环境变量")
            return False
        
        # 测试PDF唯一标识符生成
        print("测试PDF唯一标识符功能...")
        
        # 生成两个不同的PDF标识符
        pdf_id1 = generate_pdf_identifier("测试文档1", "这是第一个测试文档")
        pdf_id2 = generate_pdf_identifier("测试文档2", "这是第二个测试文档")
        
        print(f"PDF标识符1: {pdf_id1}")
        print(f"PDF标识符2: {pdf_id2}")
        
        # 验证标识符是否唯一
        if pdf_id1 != pdf_id2:
            print("✓ PDF标识符生成成功，且保证唯一性")
        else:
            print("✗ 错误: 两个不同的PDF生成了相同的标识符")
            return False
        
        # 测试标识符识别功能
        if is_pdf_document(pdf_id1) and is_pdf_document(pdf_id2):
            print("✓ PDF文档识别功能正常")
        else:
            print("✗ 错误: PDF文档识别功能异常")
            return False
        
        # 测试hash提取功能
        hash1 = extract_pdf_hash(pdf_id1)
        hash2 = extract_pdf_hash(pdf_id2)
        
        if hash1 and hash2 and hash1 != hash2:
            print(f"✓ PDF hash提取功能正常: {hash1[:8]}..., {hash2[:8]}...")
        else:
            print("✗ 错误: PDF hash提取功能异常")
            return False
        
        # 测试非-PDF URL
        youtube_url = "https://www.youtube.com/watch?v=example"
        if not is_pdf_document(youtube_url):
            print("✓ YouTube URL正确识别为非-PDF")
        else:
            print("✗ 错误: YouTube URL被错误识别为PDF")
            return False
        
        # 初始化PDF处理器
        processor = PDFProcessor()
        print("✓ PDF处理器初始化成功")
        
        # 创建一个内容丰富的测试PDF文件
        c = canvas.Canvas("test.pdf", pagesize=letter)
        
        # 添加标题
        c.setFont("Helvetica-Bold", 18)
        c.drawString(100, 750, "企业数字化转型实施指南")
        
        # 添加内容
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "随着云计算、人工智能和物联网技术的快速发展，")
        c.drawString(100, 680, "企业数字化转型已成为保持竞争优势的关键战略。")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 650, "第一章：数字化转型趋势分析")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 620, "• 云原生架构的普及")
        c.drawString(100, 600, "• AI驱动的业务流程优化")
        c.drawString(100, 580, "• 数据驱动决策体系建设")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 550, "第二章：技术架构设计")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 520, "• 微服务架构设计原则")
        c.drawString(100, 500, "• 容器化部署策略")
        c.drawString(100, 480, "• DevOps流程优化")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 450, "第三章：实施路径规划")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 420, "• 分阶段实施计划")
        c.drawString(100, 400, "• 风险控制措施")
        c.drawString(100, 380, "• ROI评估方法")
        
        c.save()
        
        print("✓ 测试PDF文件创建成功")
        
        # 上传PDF文件
        print("正在上传PDF文件...")
        file_info = await processor.upload_pdf("test.pdf")
        print(f"✓ PDF文件上传成功: {file_info['name']}")
        
        # 生成大纲（不传入标题，让AI根据内容自动生成）
        print("正在生成大纲...")
        outline_result = await processor.generate_outline(file_info)  # 不传标题
        print(f"✓ 大纲生成成功，AI生成的标题: {outline_result['outline']['title']}")
        print(f"✓ 生成的简介: {outline_result['outline']['introduction'][:100]}...")
        
        # 清理测试文件
        os.unlink("test.pdf")
        await processor.delete_file(file_info["name"])
        print("✓ 测试文件清理完成")
        
        return True
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        # 清理测试文件（如果存在）
        if os.path.exists("test.pdf"):
            os.unlink("test.pdf")
        return False


if __name__ == "__main__":
    # 添加项目根目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 运行测试
    success = asyncio.run(test_pdf_processor())
    if success:
        print("✓ 所有测试通过！PDF功能已完全修复")
        sys.exit(0)
    else:
        print("✗ 测试失败！")
        sys.exit(1)