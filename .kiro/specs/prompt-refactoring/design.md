# Design Document

## Overview

本设计文档描述了 Prompt 管理系统的重构方案，旨在实现单一数据源原则，提高 prompt 的可维护性和可复用性。核心思想是将所有 prompt 定义从代码中分离出来，统一存储在配置文件中，并通过一个中心化的 Prompt Manager 来管理和提供 prompt 内容。

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  (workflow.py, summarizer.py, etc.)                         │
└────────────────────┬────────────────────────────────────────┘
                     │ 使用 PromptManager API
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Prompt Manager                            │
│  - load_prompts()                                           │
│  - get_prompt(key)                                          │
│  - format_prompt(key, **params)                             │
│  - reload_prompts()                                         │
└────────────────────┬────────────────────────────────────────┘
                     │ 读取配置
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Prompt Configuration Files                      │
│  prompt/                                                     │
│  ├── config.yaml          (主配置文件)                       │
│  ├── base/                                                   │
│  │   ├── youtube-deep-summary.txt                          │
│  │   └── text2html.txt                                     │
│  ├── templates/                                             │
│  │   ├── outline.txt                                       │
│  │   ├── chapter.txt                                       │
│  │   └── conclusion.txt                                    │
│  └── fragments/                                             │
│      ├── markdown-bold-rules.txt                           │
│      └── pdf-multimodal-guide.txt                          │
└─────────────────────────────────────────────────────────────┘
```

### 目录结构设计

```
prompt/
├── config.yaml                    # 主配置文件，定义所有 prompt 的元数据
├── base/                          # 基础 prompt，定义角色和核心规则
│   ├── youtube-deep-summary.txt   # YouTube 视频深度分析基础 prompt
│   └── text2html.txt              # Markdown 转 HTML 基础 prompt
├── templates/                     # 任务模板 prompt
│   ├── outline.txt                # 生成大纲的模板
│   ├── chapter.txt                # 生成章节的模板
│   └── conclusion.txt             # 生成结论的模板
└── fragments/                     # 可复用的 prompt 片段
    ├── markdown-bold-rules.txt    # Markdown 加粗规则
    └── pdf-multimodal-guide.txt   # PDF 多模态分析指南
```

## Components and Interfaces

### 1. PromptConfig (配置数据类)

```python
@dataclass
class PromptConfig:
    """Prompt 配置数据类"""
    key: str                          # prompt 唯一标识符
    type: str                         # prompt 类型: base, template, fragment
    file_path: str                    # 文件路径（相对于 prompt/ 目录）
    description: str                  # 描述信息
    version: str = "1.0"              # 版本号
    required_params: List[str] = None # 必需参数列表
    optional_params: Dict[str, str] = None  # 可选参数及默认值
    includes: List[str] = None        # 包含的其他 prompt 片段
```

### 2. PromptManager (核心管理类)

```python
class PromptManager:
    """Prompt 管理器，负责加载、缓存和提供 prompt"""
    
    def __init__(self, config_path: str = "./prompt/config.yaml", 
                 enable_hot_reload: bool = False):
        """
        初始化 Prompt Manager
        
        Args:
            config_path: 配置文件路径
            enable_hot_reload: 是否启用热重载（开发模式）
        """
        
    def load_prompts(self) -> None:
        """加载所有 prompt 配置和内容"""
        
    def get_prompt(self, key: str, raw: bool = False) -> str:
        """
        获取 prompt 内容
        
        Args:
            key: prompt 标识符
            raw: 是否返回原始内容（不进行片段组合）
            
        Returns:
            prompt 内容字符串
            
        Raises:
            PromptNotFoundError: prompt 不存在
        """
        
    def format_prompt(self, key: str, **params) -> str:
        """
        格式化 prompt 模板，替换占位符
        
        Args:
            key: prompt 标识符
            **params: 模板参数
            
        Returns:
            格式化后的 prompt 字符串
            
        Raises:
            PromptNotFoundError: prompt 不存在
            MissingParameterError: 缺少必需参数
        """
        
    def reload_prompts(self) -> None:
        """重新加载所有 prompt（用于热重载）"""
        
    def validate_prompts(self) -> Dict[str, List[str]]:
        """
        验证所有 prompt 的完整性
        
        Returns:
            验证结果字典，包含错误和警告信息
        """
        
    def list_prompts(self) -> List[PromptConfig]:
        """列出所有可用的 prompt 配置"""
```

### 3. config.yaml 配置文件格式

```yaml
version: "1.0"
base_dir: "./prompt"

prompts:
  # 基础 prompt
  youtube_deep_summary_base:
    type: base
    file: base/youtube-deep-summary.txt
    description: "YouTube 视频深度分析基础 prompt"
    version: "1.0"
    
  text2html_base:
    type: base
    file: base/text2html.txt
    description: "Markdown 转 HTML 基础 prompt"
    version: "1.0"
  
  # 可复用片段
  markdown_bold_rules:
    type: fragment
    file: fragments/markdown-bold-rules.txt
    description: "Markdown 加粗样式规则"
    version: "1.0"
    
  pdf_multimodal_guide:
    type: fragment
    file: fragments/pdf-multimodal-guide.txt
    description: "PDF 多模态分析指南"
    version: "1.0"
  
  # 任务模板
  outline_template:
    type: template
    file: templates/outline.txt
    description: "生成大纲和标题的模板"
    version: "1.0"
    required_params:
      - base_prompt
      - content_type
      - content_description
      - full_content
    includes:
      - youtube_deep_summary_base
      
  chapter_template:
    type: template
    file: templates/chapter.txt
    description: "生成单个章节内容的模板"
    version: "1.0"
    required_params:
      - base_prompt
      - content_type
      - content_description
      - full_content
      - full_outline
      - chapter_number
      - current_chapter_title
    optional_params:
      markdown_bold_rules: ""
    includes:
      - youtube_deep_summary_base
      - markdown_bold_rules
      
  conclusion_template:
    type: template
    file: templates/conclusion.txt
    description: "生成洞见与金句的模板"
    version: "1.0"
    required_params:
      - base_prompt
      - content_type
      - content_description
      - full_content
      - all_generated_chapters
    optional_params:
      markdown_bold_rules: ""
    includes:
      - youtube_deep_summary_base
      - markdown_bold_rules
```

### 4. 向后兼容层

为了保持向后兼容，在 `prompts.py` 中提供兼容接口：

```python
# src/reinvent_insight/prompts.py
from .prompt_manager import get_prompt_manager

# 全局 PromptManager 实例
_manager = get_prompt_manager()

# 向后兼容的常量（使用 @property 或函数）
def _get_pdf_multimodal_guide():
    logger.warning("直接访问 PDF_MULTIMODAL_GUIDE 已弃用，请使用 PromptManager")
    return _manager.get_prompt("pdf_multimodal_guide")

PDF_MULTIMODAL_GUIDE = property(lambda self: _get_pdf_multimodal_guide())

# 或者使用模块级别的 __getattr__
def __getattr__(name):
    if name == "PDF_MULTIMODAL_GUIDE":
        logger.warning("直接访问 PDF_MULTIMODAL_GUIDE 已弃用")
        return _manager.get_prompt("pdf_multimodal_guide")
    # ... 其他常量
    raise AttributeError(f"module {__name__} has no attribute {name}")
```

## Data Models

### Prompt 内容组织

每个 prompt 文件都是纯文本文件，支持以下特殊语法：

1. **包含其他片段**: `{{include:fragment_key}}`
2. **参数占位符**: `{param_name}`
3. **条件包含**: `{{if:param_name}}...{{endif}}`

示例 `templates/chapter.txt`:

```
{{include:youtube_deep_summary_base}}

{{if:pdf_multimodal_guide}}
{{include:pdf_multimodal_guide}}
{{endif}}

## 全局上下文
- **{content_type}**: {full_content}
- **完整大纲**: 
{full_outline}

---
## 当前任务
你的任务是为上述 **完整大纲** 中的**特定一章**撰写详细内容。

**当前章节**：第 `{chapter_number}` 章 - `{current_chapter_title}`

...

{{include:markdown_bold_rules}}
```

## Error Handling

### 异常类型

```python
class PromptError(Exception):
    """Prompt 相关错误的基类"""
    pass

class PromptNotFoundError(PromptError):
    """Prompt 不存在"""
    pass

class PromptLoadError(PromptError):
    """Prompt 加载失败"""
    pass

class MissingParameterError(PromptError):
    """缺少必需参数"""
    pass

class PromptValidationError(PromptError):
    """Prompt 验证失败"""
    pass
```

### 错误处理策略

1. **启动时验证**: 系统启动时验证所有 prompt 文件是否存在且格式正确
2. **详细错误信息**: 错误信息应包含具体的 prompt key、缺失的参数等
3. **降级策略**: 如果热重载失败，继续使用缓存的旧版本
4. **日志记录**: 所有 prompt 加载和使用都应记录日志

## Testing Strategy

### 单元测试

1. **PromptManager 测试**
   - 测试 prompt 加载和缓存
   - 测试参数替换功能
   - 测试片段包含和组合
   - 测试错误处理

2. **配置解析测试**
   - 测试 YAML 配置解析
   - 测试配置验证
   - 测试版本信息提取

3. **向后兼容性测试**
   - 测试旧接口是否正常工作
   - 测试弃用警告是否正确触发

### 集成测试

1. **工作流集成测试**
   - 测试在实际工作流中使用新的 PromptManager
   - 测试 PDF 和视频两种模式
   - 测试完整的生成流程

2. **热重载测试**
   - 测试修改 prompt 文件后是否自动重载
   - 测试重载失败时的降级行为

### 性能测试

1. **加载性能**: 测试大量 prompt 的加载时间
2. **缓存效率**: 测试缓存命中率和内存使用
3. **格式化性能**: 测试大型模板的格式化速度

## Migration Plan

### 阶段 1: 创建新系统（不影响现有功能）

1. 创建 `prompt/` 目录结构
2. 实现 `PromptManager` 类
3. 创建 `config.yaml` 配置文件
4. 迁移现有 prompt 内容到新文件

### 阶段 2: 添加向后兼容层

1. 在 `prompts.py` 中添加兼容接口
2. 确保现有代码无需修改即可运行
3. 添加弃用警告

### 阶段 3: 逐步迁移现有代码

1. 更新 `workflow.py` 使用新的 PromptManager
2. 更新其他使用 prompt 的模块
3. 移除旧的硬编码 prompt

### 阶段 4: 清理和优化

1. 移除向后兼容层
2. 优化 prompt 组织结构
3. 添加更多可复用片段

## Implementation Notes

### 关键设计决策

1. **使用 YAML 而非 JSON**: YAML 更易读，支持注释
2. **文件分离而非数据库**: 便于版本控制和人工编辑
3. **延迟加载 vs 预加载**: 生产环境预加载，开发环境延迟加载
4. **缓存策略**: 使用 LRU 缓存，限制内存使用

### 性能考虑

1. **文件 I/O**: 启动时一次性加载所有 prompt，避免频繁读取
2. **模板编译**: 预编译模板，提高格式化速度
3. **内存使用**: 对于大型 prompt，考虑使用弱引用

### 安全考虑

1. **路径遍历**: 验证文件路径，防止访问 prompt 目录外的文件
2. **注入攻击**: 对用户提供的参数进行转义
3. **敏感信息**: 确保 prompt 文件不包含敏感信息（API key 等）
