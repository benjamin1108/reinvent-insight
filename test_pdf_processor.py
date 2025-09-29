#!/usr/bin/env python3
"""
PDF处理器测试脚本
"""

import asyncio
import os
import sys
from src.reinvent_insight.pdf_processor import PDFProcessor
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
        
        # 初始化PDF处理器
        processor = PDFProcessor()
        print("PDF处理器初始化成功")
        
        # 创建一个真正的测试PDF文件
        c = canvas.Canvas("test.pdf", pagesize=letter)
        c.setFont("Helvetica", 12)
        
        # 添加标题
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "测试文档")
        
        # 添加内容
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "这是一个用于测试的简单PDF文档。")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 650, "章节1")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 620, "这是第一个章节的内容。")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 580, "章节2")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 550, "这是第二个章节的内容。")
        
        c.save()
        
        print("测试PDF文件创建成功")
        
        # 上传PDF文件
        print("正在上传PDF文件...")
        file_info = await processor.upload_pdf("test.pdf")
        print(f"PDF文件上传成功: {file_info['name']}")
        
        # 生成大纲
        print("正在生成大纲...")
        outline_result = await processor.generate_outline(file_info, "测试文档")
        print(f"大纲生成成功: {outline_result['outline']['title']}")
        
        # 清理测试文件
        os.unlink("test.pdf")
        await processor.delete_file(file_info["name"])
        print("测试文件清理完成")
        
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
        print("所有测试通过!")
        sys.exit(0)
    else:
        print("测试失败!")
        sys.exit(1)