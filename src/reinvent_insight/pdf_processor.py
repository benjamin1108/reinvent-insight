import logging
import asyncio
import json
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from google.generativeai import types
from . import config

logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF处理器，使用Gemini多模态能力处理PDF文件"""
    
    def __init__(self):
        """初始化Gemini客户端"""
        if not config.GEMINI_API_KEY:
            raise ValueError("Gemini API Key未配置")
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model_name = "gemini-2.0-flash-exp"  # 使用最新的Gemini模型
    
    async def upload_pdf(self, pdf_file_path: str) -> Dict[str, Any]:
        """
        将PDF文件上传到Gemini API
        
        Args:
            pdf_file_path: PDF文件路径
            
        Returns:
            包含文件信息的字典
        """
        try:
            # 使用异步执行器避免阻塞
            loop = asyncio.get_event_loop()
            
            # 调用Gemini Files API上传PDF
            pdf_file = await loop.run_in_executor(
                None, 
                lambda: genai.upload_file(path=pdf_file_path)
            )
            
            # 返回文件信息
            file_info = {
                "name": pdf_file.name,
                "display_name": pdf_file.display_name,
                "mime_type": pdf_file.mime_type,
                "size_bytes": pdf_file.size_bytes,
                "create_time": pdf_file.create_time,
                "expiration_time": pdf_file.expiration_time,
                "uri": pdf_file.uri
            }
            
            logger.info(f"PDF上传成功: {file_info['name']}")
            return file_info
            
        except Exception as e:
            logger.error(f"PDF上传失败: {str(e)}")
            raise
    
    async def generate_outline(self, pdf_file_info: Dict[str, Any], title: Optional[str] = None) -> Dict[str, Any]:
        """
        使用Gemini生成内容大纲
        
        Args:
            pdf_file_info: PDF文件信息
            title: 可选的文档标题
            
        Returns:
            包含大纲的字典
        """
        try:
            # 获取已上传的PDF文件引用
            pdf_file = genai.get_file(name=pdf_file_info["name"])
            
            # 构建提示词
            prompt = self._build_outline_prompt(title)
            
            # 创建模型实例
            model = genai.GenerativeModel(self.model_name)
            
            # 调用Gemini生成内容API
            response = await model.generate_content_async(
                [prompt, pdf_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=8000,
                    response_mime_type="application/json"
                )
            )
            
            # 解析响应
            outline_json = json.loads(response.text)
            
            # 记录API使用情况
            if hasattr(response, 'usage_metadata'):
                usage_metadata = response.usage_metadata
                logger.info(f"Prompt tokens: {usage_metadata.prompt_token_count}")
                logger.info(f"Response tokens: {usage_metadata.candidates_token_count}")
                logger.info(f"Total tokens: {usage_metadata.total_token_count}")
            
            return {
                "outline": outline_json,
                "file_id": pdf_file_info["name"],
                "usage": getattr(response, 'usage_metadata', None)
            }
            
        except Exception as e:
            logger.error(f"生成大纲失败: {str(e)}")
            raise
    
    async def generate_section_content(
        self,
        outline_item: Dict[str, Any], 
        context: str, 
        pdf_file_id: str
    ) -> str:
        """
        使用Gemini生成章节内容
        
        Args:
            outline_item: 大纲项目
            context: 上下文信息
            pdf_file_id: PDF文件ID
            
        Returns:
            生成的章节内容
        """
        try:
            # 获取已上传的PDF文件引用
            pdf_file = genai.get_file(name=pdf_file_id)
            
            # 构建章节生成的完整prompt
            prompt = self._build_section_prompt(outline_item, context)
            
            # 创建模型实例
            model = genai.GenerativeModel(self.model_name)
            
            # 调用Gemini生成API
            response = await model.generate_content_async(
                [prompt, pdf_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=8000
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"生成章节内容失败: {str(e)}")
            raise
    
    def _build_outline_prompt(self, title: Optional[str] = None) -> str:
        """构建大纲生成的提示词"""
        # 如果用户提供了标题，使用用户标题；否则让AI根据内容生成
        title_instruction = f'"title": "{title}",' if title else '"title": "基于PDF内容生成一个简洁、准确、有吸引力的中文标题（10-30字）",'
        
        return f"""
## 1. 角色与任务

你是一位顶级的解决方案架构师和行业分析师。你的目标读者是企业的中高层技术决策者。

你的核心任务是深入分析用户提供的PDF文档。这份文档同时包含**文字、架构图、流程图、数据图表**等多种信息。你必须发挥你的多模态分析能力，**将从文本内容中获得的理解与从视觉元素中获得的洞察力相结合**。

## 2. 多模态分析指南

### 文本分析重点：
- 核心概念和技术术语
- 业务价值和技术优势
- 问题描述和解决方案

### 视觉元素分析重点：
- **架构图**: 系统组件、数据流、部署结构
- **流程图**: 业务流程、操作步骤、决策树
- **数据图表**: 性能指标、趋势分析、对比数据
- **截图**: UI设计、配置示例、代码片段

### 关联分析：
- 文本中提到的概念如何在图中体现
- 图表数据如何支撑文本论述
- 架构设计如何解决文本中的问题

## 3. 标题生成要求

{"请根据PDF文档的主要内容生成一个吸引人的中文标题，要求：" if not title else ""}
{"- 标题应简洁明了，10-30个字" if not title else ""}
{"- 准确反映文档的核心主题和价值" if not title else ""}
{"- 避免使用\"解决方案\"、\"白皮书\"等通用词汇" if not title else ""}
{"- 突出文档的技术特色或业务价值" if not title else ""}

## 4. 语言质量要求

- **使用标准简体中文**：确保所有文字使用标准简体中文字符
- **避免字符编码错误**：检查并确保没有乱码或错误字符
- **保持用词准确**：使用准确的技术术语和表达
- **语言简洁明了**：避免冗余表达，保持语言简洁

## 5. 输出格式要求

你必须严格按照以下JSON格式输出：

{{
  {title_instruction}
  "introduction": "200-300字的引人入胜的导语",
  "table_of_contents": [
    {{
      "id": 1,
      "title": "章节标题",
      "summary": "章节内容概要"
    }}
  ]
}}
"""
    
    def _build_section_prompt(self, outline_item: Dict[str, Any], context: str) -> str:
        """构建章节内容生成的提示词"""
        return f"""
## 角色定义
你是一位专业的解决方案内容撰写专家，面向技术决策者撰写高质量的技术方案文档。

## 任务说明
基于PDF文档中的信息，撰写以下章节的详细内容：

### 当前章节
- **标题**: {outline_item['title']}
- **概要**: {outline_item['summary']}

### 写作要求
1. **充分利用PDF内容**: 
   - 引用文档中的具体数据和案例
   - 参考架构图和流程图进行详细说明
   - 使用图表数据支撑论点

2. **保持连贯性**:
   {"- 承接上文内容：" + context[-500:] if context else "- 这是第一章节"}

3. **内容深度**:
   - 提供技术细节和实施要点
   - 分析方案的价值和优势
   - 给出具体的实施建议

4. **语言质量保证**:
   - 使用标准简体中文，避免繁体字或字符编码错误
   - 确保所有技术术语准确无误
   - 保持语言简洁明了，避免冗余表达

## 输出要求
- 直接输出章节内容，无需标题
- 使用Markdown格式
- 篇幅：1000-2000字
- 必要时使用子标题组织内容
"""
    
    async def delete_file(self, file_id: str) -> bool:
        """
        删除Gemini上传的文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            删除是否成功
        """
        try:
            # 使用异步执行器避免阻塞
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: genai.delete_file(name=file_id))
            logger.info(f"已删除文件: {file_id}")
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False