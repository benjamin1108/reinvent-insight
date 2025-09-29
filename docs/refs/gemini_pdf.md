# PDF2Solution - 基于Gemini的PDF多模态处理流程详解

## 项目概述

PDF2Solution 是一个基于Google Gemini多模态AI的智能PDF文档处理系统，能够自动将PDF文档（包含文本、图表、架构图等多种信息）转换为结构化的专业解决方案文档。本文档详细介绍使用Gemini API的具体实现细节和处理流程。

## 核心技术架构

### 1. 系统架构设计

```
┌─────────────────────────────────────────────────────┐
│                   用户接口层                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │   CLI    │  │ Web API  │  │  WebSocket       │  │
│  │ Interface│  │ REST API │  │  Real-time       │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────┐
│                   业务逻辑层                          │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ Task Manager │  │ File Service│  │  PDF      │  │
│  │  任务管理器   │  │  文件服务    │  │  Adapter  │  │
│  └──────────────┘  └─────────────┘  └───────────┘  │
└─────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────┐
│                Gemini AI处理引擎                      │
│  ┌──────────────────────────────────────────────┐  │
│  │         Google Gemini 2.0 Flash Exp           │  │
│  │  - 原生PDF支持                                │  │
│  │  - 多模态理解（文本+图像）                      │  │
│  │  - 结构化JSON输出                             │  │
│  │  - 流式内容生成                               │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────┐
│                   数据存储层                          │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │  SQLite  │  │   File   │  │  JSON Metadata  │  │
│  │  Database│  │  System  │  │                 │  │
│  └──────────┘  └──────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 2. Gemini API 客户端初始化

```python
from google import genai
from google.genai import types

class GeminiClient:
    def __init__(self, config: Config):
        # 初始化Gemini客户端
        self.client = genai.Client(api_key=config.ai.api_key)
        
        # 模型配置
        self.model_name = "gemini-2.0-flash-exp"  # 最新的Gemini模型
        self.temperature = 0.8  # 创造性程度
        self.max_tokens = 8000  # 最大输出token数

## Gemini API 处理核心流程

### 第一阶段：PDF文件上传到Gemini

```python
# 详细的Gemini文件上传API调用
async def upload_pdf_to_gemini(self, pdf_file_path: str) -> Dict[str, Any]:
    """
    将PDF文件上传到Gemini API
    
    Gemini Files API 特点：
    - 支持直接上传PDF文件，无需转换
    - 文件会被Gemini缓存24小时
    - 返回文件URI用于后续的内容生成请求
    """
    try:
        # 使用异步执行器避免阻塞
        loop = asyncio.get_event_loop()
        
        # 调用Gemini Files API上传PDF
        # API endpoint: https://generativelanguage.googleapis.com/v1beta/files
        pdf_file = await loop.run_in_executor(
            None, 
            lambda: self.client.files.upload(
                file=pdf_file_path,
                # 文件会自动识别为application/pdf类型
            )
        )
        
        # 返回的文件对象结构
        file_info = {
            "name": pdf_file.name,  # 格式: files/xxx-xxx-xxx
            "display_name": pdf_file.display_name,  # 原始文件名
            "mime_type": pdf_file.mime_type,  # application/pdf
            "size_bytes": pdf_file.size_bytes,  # 文件大小
            "create_time": pdf_file.create_time,  # 创建时间
            "expiration_time": pdf_file.expiration_time,  # 24小时后过期
            "uri": pdf_file.uri  # 用于内容生成的URI
        }
        
        print(f"PDF上传成功: {file_info['name']}")
        print(f"文件大小: {file_info['size_bytes'] / 1024 / 1024:.2f} MB")
        print(f"过期时间: {file_info['expiration_time']}")
        
        return file_info
        
    except Exception as e:
        print(f"PDF上传失败: {str(e)}")
        raise
```

### 第二阶段：使用Gemini生成结构化大纲

```python
async def generate_outline(self, pdf_file_path: str, prompt: str) -> Dict[str, Any]:
    """
    使用Gemini的多模态能力生成解决方案大纲
    
    API调用详解：
    1. 使用generate_content API
    2. 通过response_schema确保返回JSON格式
    3. 利用多模态能力同时理解文本和图像
    """
    
    # 步骤1: 上传PDF文件
    pdf_file = await self.upload_pdf_to_gemini(pdf_file_path)
    
    # 步骤2: 构建API请求内容
    # Gemini支持混合内容输入
    contents = [
        prompt,      # 文本提示词
        pdf_file     # PDF文件对象
    ]
    
    # 步骤3: 定义JSON Schema确保输出格式
    # 这是Gemini的强大功能之一：结构化输出
    response_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "解决方案标题"
            },
            "introduction": {
                "type": "string", 
                "description": "200-300字的导语"
            },
            "table_of_contents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"}
                    },
                    "required": ["id", "title", "summary"]
                }
            }
        },
        "required": ["title", "introduction", "table_of_contents"]
    }
    
    # 步骤4: 调用Gemini生成内容API
    # API endpoint: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: self.client.models.generate_content(
            model=self.model_name,  # "gemini-2.0-flash-exp"
            contents=contents,
            config=types.GenerateContentConfig(
                # 温度参数：控制创造性
                temperature=self.config.ai.temperature,  # 0.8
                
                # 最大输出token数
                max_output_tokens=self.config.ai.max_tokens,  # 8000
                
                # 关键：指定返回JSON格式
                response_mime_type="application/json",
                
                # 关键：提供schema确保格式正确
                response_schema=response_schema
            )
        )
    )
    
    # 步骤5: 解析响应
    outline_json = json.loads(response.text)
    
    # 步骤6: 记录API使用情况
    usage_metadata = response.usage_metadata
    print(f"Prompt tokens: {usage_metadata.prompt_token_count}")
    print(f"Response tokens: {usage_metadata.candidates_token_count}")
    print(f"Total tokens: {usage_metadata.total_token_count}")
    
    # 返回结果包含大纲和文件信息
    return {
        "outline": outline_json,
        "file_id": pdf_file.name,
        "usage": usage_metadata
    }
```

### 第三阶段：使用Gemini流式生成章节内容

```python
async def generate_solution_streaming(
    self,
    outline_item: Dict[str, Any], 
    context: str, 
    prompt: str,
    pdf_file_id: str
) -> AsyncIterator[str]:
    """
    使用Gemini流式API生成单个章节的详细内容
    
    Gemini流式生成特点：
    1. 实时返回生成内容，无需等待完整响应
    2. 降低首字节延迟，提升用户体验
    3. 支持长内容生成（最多8000 tokens）
    """
    
    # 步骤1: 获取已上传的PDF文件引用
    # 使用之前上传的file_id获取文件对象
    loop = asyncio.get_event_loop()
    pdf_file = await loop.run_in_executor(
        None,
        lambda: self.client.files.get(name=pdf_file_id)
    )
    
    # 步骤2: 构建章节生成的完整prompt
    full_prompt = f"""
{prompt}

当前章节信息：
- 章节标题：{outline_item['title']}
- 章节概要：{outline_item['summary']}

上下文信息：
{context}
"""
    
    # 步骤3: 构建API请求内容
    contents = [
        full_prompt,  # 包含章节要求和上下文
        pdf_file      # PDF文件供AI参考
    ]
    
    # 步骤4: 调用Gemini流式生成API
    # API endpoint: https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent
    stream = await loop.run_in_executor(
        None,
        lambda: self.client.models.generate_content_stream(
            model=self.model_name,  # "gemini-2.0-flash-exp"
            contents=contents,
            config=types.GenerateContentConfig(
                # 温度设置：较高的值产生更有创造性的内容
                temperature=self.config.ai.temperature,  # 0.8
                
                # 最大输出长度
                max_output_tokens=self.config.ai.max_tokens,  # 8000
                
                # 可选：设置stop sequences
                # stop_sequences=["## ", "### "]  # 在遇到新章节标题时停止
            )
        )
    )
    
    # 步骤5: 流式处理响应
    full_response = ""
    try:
        for chunk in stream:
            if chunk.text:
                # 实时返回生成的文本片段
                full_response += chunk.text
                yield chunk.text
                
                # 可选：实时保存进度
                if self.config.ai.streaming.real_time_save:
                    await self.save_partial_content(
                        outline_item['id'], 
                        full_response
                    )
    
    except Exception as e:
        print(f"流式生成错误: {str(e)}")
        raise
    
    # 步骤6: 记录完整响应和使用情况
    # 注意：流式API的usage_metadata可能在最后一个chunk中
    print(f"章节 {outline_item['title']} 生成完成")
    print(f"生成字符数: {len(full_response)}")
```

### 第四阶段：非流式批量生成（备选方案）

```python
async def generate_solution_batch(
    self,
    outline_item: Dict[str, Any], 
    context: str, 
    prompt: str,
    pdf_file_id: str
) -> str:
    """
    使用Gemini标准API生成内容（非流式）
    
    适用场景：
    - 需要一次性获取完整内容
    - 对延迟不敏感的后台处理
    - 需要精确的token使用统计
    """
    
    # 获取PDF文件引用
    loop = asyncio.get_event_loop()
    pdf_file = await loop.run_in_executor(
        None,
        lambda: self.client.files.get(name=pdf_file_id)
    )
    
    # 构建请求内容
    contents = [
        f"{prompt}\n\n当前章节：{outline_item['title']}\n{context}",
        pdf_file
    ]
    
    # 调用标准生成API
    response = await loop.run_in_executor(
        None,
        lambda: self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=self.config.ai.temperature,
                max_output_tokens=self.config.ai.max_tokens,
                # 可选：添加安全设置
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_NONE"
                    )
                ]
            )
        )
    )
    
    # 获取生成的文本
    generated_text = response.text
    
    # 获取详细的使用统计
    usage = response.usage_metadata
    print(f"Input tokens: {usage.prompt_token_count}")
    print(f"Output tokens: {usage.candidates_token_count}")
    print(f"Total tokens: {usage.total_token_count}")
    
    # 可选：检查响应的安全评分
    if response.prompt_feedback:
        print(f"Safety ratings: {response.prompt_feedback.safety_ratings}")
    
    return generated_text
```

### 第五阶段：Gemini文件管理和清理

```python
async def manage_gemini_files(self):
    """
    管理Gemini上传的文件
    
    Gemini Files API管理功能：
    1. 列出所有已上传的文件
    2. 获取文件详情
    3. 删除不再需要的文件
    """
    
    # 列出所有文件
    # API endpoint: https://generativelanguage.googleapis.com/v1beta/files
    files = self.client.files.list()
    
    print(f"当前已上传文件数: {len(files)}")
    for file in files:
        print(f"- {file.name}")
        print(f"  大小: {file.size_bytes / 1024 / 1024:.2f} MB")
        print(f"  创建时间: {file.create_time}")
        print(f"  过期时间: {file.expiration_time}")
    
    # 获取特定文件信息
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        try:
            file_info = self.client.files.get(name=file_id)
            return {
                "name": file_info.name,
                "display_name": file_info.display_name,
                "mime_type": file_info.mime_type,
                "size_bytes": file_info.size_bytes,
                "create_time": file_info.create_time,
                "update_time": file_info.update_time,
                "expiration_time": file_info.expiration_time,
                "sha256_hash": file_info.sha256_hash,
                "uri": file_info.uri
            }
        except Exception as e:
            print(f"获取文件信息失败: {str(e)}")
            raise
    
    # 删除文件（任务完成后清理）
    def delete_file(self, file_id: str) -> bool:
        try:
            self.client.files.delete(name=file_id)
            print(f"已删除文件: {file_id}")
            return True
        except Exception as e:
            print(f"删除文件失败: {str(e)}")
            return False
```

## Gemini API 高级功能

### 多模态提示词工程

```python
class GeminiPromptBuilder:
    """
    构建优化的Gemini提示词
    专门针对PDF多模态分析场景
    """
    
    @staticmethod
    def build_outline_prompt() -> str:
        """
        构建大纲生成的提示词
        充分利用Gemini的多模态理解能力
        """
        return """
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

## 3. 输出格式要求

你必须严格按照以下JSON格式输出：

{
  "title": "从PDF中提炼出的解决方案主标题",
  "introduction": "200-300字的引人入胜的导语",
  "table_of_contents": [
    {
      "id": 1,
      "title": "章节标题",
      "summary": "章节内容概要"
    }
  ]
}
"""

    @staticmethod
    def build_section_prompt(
        section_title: str,
        section_summary: str,
        previous_content: str = "",
        style_guide: str = ""
    ) -> str:
        """
        构建章节内容生成的提示词
        """
        return f"""
## 角色定义
你是一位专业的解决方案内容撰写专家，面向技术决策者撰写高质量的技术方案文档。

## 任务说明
基于PDF文档中的信息，撰写以下章节的详细内容：

### 当前章节
- **标题**: {section_title}
- **概要**: {section_summary}

### 写作要求
1. **充分利用PDF内容**: 
   - 引用文档中的具体数据和案例
   - 参考架构图和流程图进行详细说明
   - 使用图表数据支撑论点

2. **保持连贯性**:
   {"- 承接上文内容：" + previous_content[-500:] if previous_content else "- 这是第一章节"}

3. **遵循风格指南**:
{style_guide}

4. **内容深度**:
   - 提供技术细节和实施要点
   - 分析方案的价值和优势
   - 给出具体的实施建议

## 输出要求
- 直接输出章节内容，无需标题
- 使用Markdown格式
- 篇幅：1000-2000字
- 必要时使用子标题组织内容
"""

### 错误处理和重试机制

```python
import asyncio
from typing import Optional, TypeVar, Callable
from google.api_core import retry
from google.api_core.exceptions import GoogleAPIError

T = TypeVar('T')

class GeminiErrorHandler:
    """
    Gemini API错误处理和重试机制
    """
    
    @staticmethod
    async def with_retry(
        func: Callable,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0
    ) -> T:
        """
        带有指数退避的重试机制
        
        Gemini API常见错误：
        - 429: Rate limit exceeded
        - 500: Internal server error  
        - 503: Service unavailable
        """
        attempt = 0
        delay = initial_delay
        
        while attempt < max_attempts:
            try:
                # 执行API调用
                result = await func()
                return result
                
            except GoogleAPIError as e:
                attempt += 1
                
                # 检查错误类型
                if e.code == 429:  # Rate limit
                    print(f"触发速率限制，等待 {delay} 秒后重试...")
                elif e.code in [500, 502, 503]:  # Server errors
                    print(f"服务器错误 ({e.code})，等待 {delay} 秒后重试...")
                elif e.code == 400:  # Bad request
                    print(f"请求错误: {e.message}")
                    raise  # 不重试客户端错误
                else:
                    print(f"未知错误 ({e.code}): {e.message}")
                    if attempt >= max_attempts:
                        raise
                
                # 等待后重试
                if attempt < max_attempts:
                    await asyncio.sleep(delay)
                    delay = min(delay * multiplier, max_delay)
                else:
                    raise
                    
        raise Exception(f"重试{max_attempts}次后仍然失败")

    @staticmethod
    def handle_safety_ratings(response):
        """
        处理Gemini的安全评级
        
        Gemini会对内容进行安全检查，可能会阻止某些内容
        """
        if hasattr(response, 'prompt_feedback'):
            feedback = response.prompt_feedback
            if feedback.block_reason:
                print(f"内容被阻止: {feedback.block_reason}")
                # 处理不同的阻止原因
                if feedback.block_reason == "SAFETY":
                    safety_ratings = feedback.safety_ratings
                    for rating in safety_ratings:
                        if rating.probability != "NEGLIGIBLE":
                            print(f"- {rating.category}: {rating.probability}")
                    # 可以尝试修改prompt或调整安全设置
                    return False
        return True
```

### 批量处理优化

```python
class GeminiBatchProcessor:
    """
    批量处理多个章节，优化API调用
    """
    
    def __init__(self, client: GeminiClient, max_concurrent: int = 3):
        self.client = client
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_chapters_batch(
        self,
        chapters: List[Dict],
        pdf_file_id: str,
        prompt_template: str
    ) -> Dict[int, str]:
        """
        并发处理多个章节
        
        优化策略：
        1. 限制并发数，避免触发速率限制
        2. 使用信号量控制并发
        3. 收集所有结果后统一返回
        """
        results = {}
        tasks = []
        
        async def process_single_chapter(chapter: Dict):
            async with self.semaphore:
                try:
                    # 为每个章节生成内容
                    content = await self.client.generate_solution_batch(
                        outline_item=chapter,
                        context="",  # 可以传入上下文
                        prompt=prompt_template,
                        pdf_file_id=pdf_file_id
                    )
                    return chapter['id'], content
                except Exception as e:
                    print(f"处理章节 {chapter['title']} 失败: {e}")
                    return chapter['id'], None
        
        # 创建所有任务
        for chapter in chapters:
            task = asyncio.create_task(process_single_chapter(chapter))
            tasks.append(task)
        
        # 等待所有任务完成
        completed = await asyncio.gather(*tasks)
        
        # 整理结果
        for chapter_id, content in completed:
            if content:
                results[chapter_id] = content
        
        return results
```

## 完整使用示例

### 使用Gemini API处理PDF的完整流程

```python
import asyncio
import os
from typing import Dict, List
from google import genai
from google.genai import types

class PDFSolutionGenerator:
    """
    使用Gemini API生成PDF解决方案的完整示例
    """
    
    def __init__(self, api_key: str):
        """初始化Gemini客户端"""
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.0-flash-exp"
    
    async def process_pdf(self, pdf_path: str, project_name: str) -> str:
        """
        完整的PDF处理流程
        """
        print(f"开始处理PDF: {pdf_path}")
        
        # 1. 上传PDF到Gemini
        print("步骤1: 上传PDF文件...")
        pdf_file = await self._upload_pdf(pdf_path)
        print(f"PDF上传成功: {pdf_file.name}")
        
        # 2. 生成大纲
        print("\n步骤2: 生成解决方案大纲...")
        outline = await self._generate_outline(pdf_file)
        print(f"大纲生成成功，包含 {len(outline['table_of_contents'])} 个章节")
        
        # 3. 批量生成章节内容
        print("\n步骤3: 生成章节内容...")
        contents = await self._generate_all_sections(
            outline['table_of_contents'],
            pdf_file.name
        )
        
        # 4. 组装最终文档
        print("\n步骤4: 组装最终文档...")
        final_doc = self._assemble_document(outline, contents)
        
        # 5. 保存输出
        output_path = f"{project_name}_solution.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_doc)
        
        print(f"\n✅ 处理完成！输出文件: {output_path}")
        
        # 6. 清理上传的文件
        await self._cleanup_file(pdf_file.name)
        
        return output_path
    
    async def _upload_pdf(self, pdf_path: str):
        """上传PDF到Gemini"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.files.upload(file=pdf_path)
        )
    
    async def _generate_outline(self, pdf_file) -> Dict:
        """生成大纲"""
        prompt = self._get_outline_prompt()
        
        # 定义输出schema
        response_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "introduction": {"type": "string"},
                "table_of_contents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "title": {"type": "string"},
                            "summary": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        # 调用API
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, pdf_file],
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=8000,
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )
        )
        
        import json
        return json.loads(response.text)
    
    async def _generate_all_sections(
        self, 
        chapters: List[Dict], 
        pdf_file_id: str
    ) -> Dict[int, str]:
        """并发生成所有章节"""
        # 使用批量处理器
        processor = GeminiBatchProcessor(self, max_concurrent=3)
        return await processor.process_chapters_batch(
            chapters=chapters,
            pdf_file_id=pdf_file_id,
            prompt_template=self._get_section_prompt()
        )
    
    def _assemble_document(
        self, 
        outline: Dict, 
        contents: Dict[int, str]
    ) -> str:
        """组装最终文档"""
        doc = [f"# {outline['title']}\n\n"]
        doc.append(f"{outline['introduction']}\n\n")
        
        for chapter in outline['table_of_contents']:
            chapter_id = chapter['id']
            if chapter_id in contents:
                doc.append(f"## {chapter_id}. {chapter['title']}\n\n")
                doc.append(f"{contents[chapter_id]}\n\n")
        
        return "".join(doc)
    
    async def _cleanup_file(self, file_id: str):
        """清理上传的文件"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.files.delete(name=file_id)
            )
            print(f"已清理临时文件: {file_id}")
        except Exception as e:
            print(f"清理文件失败: {e}")
    
    def _get_outline_prompt(self) -> str:
        """获取大纲生成提示词"""
        return """[这里放入之前定义的大纲提示词]"""
    
    def _get_section_prompt(self) -> str:
        """获取章节生成提示词"""
        return """[这里放入之前定义的章节提示词]"""

# 使用示例
async def main():
    # 设置API密钥
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # 创建生成器实例
    generator = PDFSolutionGenerator(api_key)
    
    # 处理PDF
    result = await generator.process_pdf(
        pdf_path="example.pdf",
        project_name="企业数字化转型"
    )
    
    print(f"生成的解决方案文档: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Gemini API 配置参数详解

```python
# Gemini配置参数说明
config = types.GenerateContentConfig(
    # 温度参数（0.0-2.0）
    # 0.0: 最确定和保守的输出
    # 0.8: 平衡创造性和连贯性（推荐用于解决方案生成）
    # 2.0: 最有创意但可能不够连贯
    temperature=0.8,
    
    # 最大输出token数
    # gemini-2.0-flash-exp 支持最多 8192 tokens
    max_output_tokens=8000,
    
    # Top-K 采样（可选）
    # 限制模型只考虑概率最高的K个token
    top_k=40,
    
    # Top-P 采样（可选）
    # 累积概率采样，与top_k互斥
    top_p=0.95,
    
    # 停止序列（可选）
    # 当生成这些序列时停止
    stop_sequences=["## ", "### "],
    
    # 响应MIME类型
    # "text/plain": 普通文本（默认）
    # "application/json": JSON格式
    response_mime_type="application/json",
    
    # JSON Schema（当response_mime_type为json时）
    response_schema={...},
    
    # 安全设置
    safety_settings=[
        types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="BLOCK_ONLY_HIGH"
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT", 
            threshold="BLOCK_NONE"  # 对技术内容放宽限制
        )
    ]
)
```

## API 限制和最佳实践

### Gemini API 限制

1. **速率限制**
   - 免费层级: 60 RPM (每分钟请求数)
   - 付费层级: 360 RPM
   - 建议使用指数退避重试

2. **文件限制**
   - 单文件最大: 20MB (PDF)
   - 文件保留时间: 24小时
   - 同时上传文件数: 20个

3. **Token限制**
   - 输入: 最多 1M tokens (包括PDF内容)
   - 输出: 最多 8192 tokens
   - 总计: 输入 + 输出不超过限制

### 最佳实践

1. **PDF优化**
   ```python
   # 检查PDF大小
   def check_pdf_size(pdf_path: str) -> bool:
       size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
       if size_mb > 20:
           print(f"PDF文件过大: {size_mb:.2f} MB")
           return False
       return True
   ```

2. **错误处理**
   ```python
   # 使用装饰器处理常见错误
   def gemini_error_handler(func):
       async def wrapper(*args, **kwargs):
           try:
               return await func(*args, **kwargs)
           except Exception as e:
               if "rate_limit" in str(e).lower():
                   print("触发速率限制，等待60秒...")
                   await asyncio.sleep(60)
                   return await func(*args, **kwargs)
               raise
       return wrapper
   ```

3. **监控和日志**
   ```python
   # 记录API使用情况
   class UsageTracker:
       def __init__(self):
           self.total_input_tokens = 0
           self.total_output_tokens = 0
           self.api_calls = 0
       
       def track(self, usage_metadata):
           self.total_input_tokens += usage_metadata.prompt_token_count
           self.total_output_tokens += usage_metadata.candidates_token_count
           self.api_calls += 1
           
       def report(self):
           print(f"API调用次数: {self.api_calls}")
           print(f"输入Tokens: {self.total_input_tokens:,}")
           print(f"输出Tokens: {self.total_output_tokens:,}")
           print(f"预估费用: ${self.estimate_cost():.4f}")
   ```

## 总结

本文档详细介绍了如何使用Google Gemini API进行PDF多模态处理，包括：

1. **核心API调用**: 文件上传、内容生成、流式输出
2. **高级功能**: 结构化输出、批量处理、错误处理
3. **最佳实践**: 性能优化、错误重试、使用监控

Gemini的原生PDF支持和强大的多模态理解能力，使其成为处理复杂文档的理想选择。通过合理的提示词设计和API调用优化，可以生成高质量的结构化解决方案文档。

---

*基于 Google Gemini 2.0 Flash Exp API*
