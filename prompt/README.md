# Prompt 配置指南

本目录包含所有 AI 模型的提示词（prompts）配置，采用统一的管理方式，实现单一数据源原则。

## 目录结构

```
prompt/
├── config.yaml              # 主配置文件，定义所有 prompt 的元数据
├── base/                    # 基础 prompt，定义角色和核心规则
│   ├── youtube-deep-summary.txt
│   └── text2html.txt
├── templates/               # 任务模板 prompt
│   ├── outline.txt
│   ├── chapter.txt
│   └── conclusion.txt
└── fragments/               # 可复用的 prompt 片段
    ├── markdown-bold-rules.txt
    └── pdf-multimodal-guide.txt
```

## Prompt 类型

### 1. Base Prompts (基础提示词)

定义 AI 的角色、风格和核心要求，通常较长且完整。

**示例**: `base/youtube-deep-summary.txt`

### 2. Templates (模板)

包含占位符的提示词，用于动态生成具体任务的提示词。

**示例**: `templates/chapter.txt`

### 3. Fragments (片段)

可复用的提示词片段，可以被其他 prompt 包含。

**示例**: `fragments/markdown-bold-rules.txt`

## 配置文件格式

`config.yaml` 定义了所有 prompt 的元数据：

```yaml
version: "1.0"
base_dir: "./prompt"

prompts:
  prompt_key:
    type: base|template|fragment
    file: relative/path/to/file.txt
    description: "描述信息"
    version: "1.0"
    required_params:  # 仅用于 template 类型
      - param1
      - param2
    optional_params:  # 仅用于 template 类型
      param3: "default_value"
    includes:  # 可选，列出依赖的其他 prompts
      - other_prompt_key
```

## 特殊语法

### 1. 包含其他片段: `{{include:key}}`

在 prompt 文件中使用此语法可以包含其他 prompt 的内容：

```
{{include:markdown_bold_rules}}
```

这会在运行时被替换为 `markdown_bold_rules` prompt 的完整内容。

### 2. 参数占位符: `{param_name}`

在模板中使用此语法定义参数占位符：

```
## 当前任务
你的任务是分析 {content_type} 的内容。
```

使用时通过 `format_prompt()` 提供参数值。

### 3. 条件包含: `{{if:param}}...{{endif}}`

根据参数是否存在来决定是否包含某段内容：

```
{{if:pdf_multimodal_guide}}
{{include:pdf_multimodal_guide}}
{{endif}}
```

只有当 `pdf_multimodal_guide` 参数为真值时，才会包含该片段。

## 使用方法

### Python API

```python
from reinvent_insight import prompts

# 方法 1: 获取 prompt 内容
base_prompt = prompts.get_prompt('youtube_deep_summary_base')

# 方法 2: 格式化模板
formatted_prompt = prompts.format_prompt(
    'chapter_template',
    content_type='完整英文字幕',
    content_description='完整字幕',
    full_content=transcript,
    full_outline=outline,
    chapter_number=1,
    current_chapter_title='Introduction'
)

# 方法 3: 列出所有可用的 prompts
all_prompts = prompts.list_available_prompts()
for config in all_prompts:
    print(f"{config.key}: {config.description}")

# 方法 4: 热重载（开发模式）
prompts.reload_prompts()
```

### 直接使用 PromptManager

```python
from reinvent_insight.prompt_manager import get_prompt_manager

manager = get_prompt_manager(enable_hot_reload=True)

# 获取 prompt
content = manager.get_prompt('markdown_bold_rules')

# 格式化模板
formatted = manager.format_prompt('outline_template', **params)

# 验证所有 prompts
validation_result = manager.validate_prompts()
if validation_result['errors']:
    print("发现错误:", validation_result['errors'])
```

## 最佳实践

### 1. 保持片段的原子性

每个 fragment 应该只包含一个独立的规则或概念，便于复用。

**好的示例**:
- `markdown-bold-rules.txt` - 只包含 Markdown 加粗规则
- `pdf-multimodal-guide.txt` - 只包含 PDF 多模态分析指南

**不好的示例**:
- `all-rules.txt` - 包含所有规则（难以复用）

### 2. 使用描述性的 key 名称

Prompt key 应该清晰地表达其用途：

- ✅ `youtube_deep_summary_base`
- ✅ `markdown_bold_rules`
- ❌ `prompt1`
- ❌ `temp`

### 3. 为模板定义清晰的参数

在 `config.yaml` 中明确列出所有必需参数和可选参数：

```yaml
chapter_template:
  type: template
  required_params:
    - content_type
    - chapter_number
    - current_chapter_title
  optional_params:
    pdf_multimodal_guide: ""
```

### 4. 避免循环引用

不要创建循环的 include 关系：

```
# ❌ 错误示例
prompt_a.txt: {{include:prompt_b}}
prompt_b.txt: {{include:prompt_a}}
```

系统会检测并报告循环引用错误。

### 5. 使用版本号

为每个 prompt 指定版本号，便于追踪变更：

```yaml
markdown_bold_rules:
  version: "1.0"
```

## 开发模式

在开发环境中，可以启用热重载功能：

```bash
export PROMPT_HOT_RELOAD=true
python your_script.py
```

或在代码中：

```python
manager = get_prompt_manager(enable_hot_reload=True)
```

启用后，修改 prompt 文件会自动重新加载，无需重启程序。

## 故障排查

### 问题 1: Prompt 文件未找到

**错误信息**: `Prompt file not found: prompt/base/xxx.txt`

**解决方法**:
1. 检查文件路径是否正确
2. 确认文件确实存在
3. 检查 `config.yaml` 中的 `base_dir` 配置

### 问题 2: 缺少必需参数

**错误信息**: `Missing required parameters for prompt 'xxx': param1, param2`

**解决方法**:
1. 检查 `format_prompt()` 调用时是否提供了所有必需参数
2. 查看 `config.yaml` 中该 prompt 的 `required_params` 列表

### 问题 3: 循环引用

**错误信息**: `Circular include detected: prompt_a -> prompt_b -> prompt_a`

**解决方法**:
1. 检查 prompt 文件中的 `{{include:xxx}}` 语法
2. 移除循环引用，重新组织 prompt 结构

### 问题 4: 参数未被替换

**症状**: 格式化后的 prompt 中仍然包含 `{param_name}`

**解决方法**:
1. 确认使用的是 `format_prompt()` 而不是 `get_prompt()`
2. 检查参数名是否拼写正确
3. 确认参数值已传递给 `format_prompt()`

## 迁移指南

### 从旧系统迁移

如果你的代码使用了旧的 prompt 常量，可以按以下方式迁移：

**旧方式**:
```python
from reinvent_insight import prompts

# 直接访问常量（已弃用）
markdown_rules = prompts.MARKDOWN_BOLD_RULES

# 使用 .format() 方法（已弃用）
prompt = prompts.CHAPTER_PROMPT_TEMPLATE.format(
    base_prompt=base_prompt,
    content_type=content_type,
    # ...
)
```

**新方式**:
```python
from reinvent_insight import prompts

# 使用 get_prompt()
markdown_rules = prompts.get_prompt('markdown_bold_rules')

# 使用 format_prompt()
prompt = prompts.format_prompt(
    'chapter_template',
    content_type=content_type,
    # ...
)
```

### 向后兼容性

旧的常量访问方式仍然可用，但会触发弃用警告。建议尽快迁移到新 API。

## 贡献指南

### 添加新的 Prompt

1. 在适当的目录下创建 prompt 文件（base/, templates/, 或 fragments/）
2. 在 `config.yaml` 中添加配置
3. 运行验证：`manager.validate_prompts()`
4. 更新本 README 文档

### 修改现有 Prompt

1. 直接编辑 prompt 文件
2. 如果修改了参数，同步更新 `config.yaml`
3. 增加版本号
4. 测试所有使用该 prompt 的功能

## 参考资料

- [PromptManager API 文档](../src/reinvent_insight/prompt_manager.py)
- [Prompts 模块文档](../src/reinvent_insight/prompts.py)
- [设计文档](../.kiro/specs/prompt-refactoring/design.md)
