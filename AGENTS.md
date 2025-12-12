# Reinvent Insight 开发规范

> 本文件用于指导 AI 辅助开发，确保架构一致性

---

## 分层架构

```
src/reinvent_insight/
├── api/              # API 层 - HTTP 路由、请求响应
├── core/             # 核心层 - 配置、日志、通用工具
├── domain/           # 领域层 - 业务模型、提示词、工作流定义
├── infrastructure/   # 基础设施层 - 外部服务适配器
├── services/         # 服务层 - 业务逻辑实现
└── tools/            # 工具脚本 - 独立命令行工具
```

---

## 各层职责

| 层 | 职责 | 可依赖 |
|---|------|--------|
| `api/` | HTTP 路由、认证、请求校验 | services, core |
| `core/` | 配置、日志、纯工具函数 | 无依赖 |
| `domain/` | 业务实体、提示词模板、工作流定义 | core |
| `infrastructure/` | 封装第三方库(AI SDK, yt-dlp等) | core |
| `services/` | 业务逻辑、任务调度 | domain, infrastructure, core |
| `tools/` | 独立脚本 | 任意 |

---

## 已有组件清单（禁止重复造轮子）

### AI 相关
- `infrastructure/ai/model_config.py` - **AI 模型客户端获取** `get_model_client()`
- `infrastructure/ai/base_client.py` - **AI 调用基类**
- `infrastructure/ai/gemini_client.py` - **Gemini API 封装**
- `domain/prompts/` - **所有提示词模板**

### 任务管理
- `services/analysis/task_manager.py` - **任务状态管理** `manager`
- `services/analysis/worker_pool.py` - **Worker 池调度**

### 文档处理
- `services/document/document_processor.py` - **文档分析处理**
- `services/document/hash_registry.py` - **文档哈希映射**
- `core/utils/file_utils.py` - **文件操作工具**

### TTS 相关
- `services/tts_service.py` - **TTS 服务**
- `services/audio_cache.py` - **音频缓存**
- `services/tts_pregeneration_service.py` - **TTS 预生成**

### 媒体处理
- `infrastructure/media/youtube_downloader.py` - **YouTube 下载**
- `infrastructure/audio/` - **音频处理**

### 认证
- `api/routes/auth.py` - **认证逻辑** `verify_token()`, `get_current_user()`

### 后处理管道
- `services/analysis/post_processors/base.py` - **后处理器基类** `PostProcessor`, `PostProcessorContext`
- `services/analysis/post_processors/pipeline.py` - **管道执行** `PostProcessorPipeline`, `register_processor()`
- `services/analysis/post_processors/visual_insight.py` - **Visual 生成处理器**

---

## 导入规范

```python
# ✅ 正确：绝对导入
from reinvent_insight.core import config
from reinvent_insight.services.analysis.task_manager import manager
from reinvent_insight.infrastructure.ai.model_config import get_model_client

# ✅ 正确：同目录相对导入
from .utils import some_function

# ❌ 错误：跨层相对导入
from ..services.xxx import yyy
```

---

## 新功能开发流程

### 1. 先查后写
开发前必须检查是否已有相关实现：
- 搜索现有代码库
- 查阅本文件的组件清单
- 确认无重复后再开发

### 2. 确定归属层
| 功能类型 | 放置位置 |
|---------|---------|
| 新 API 端点 | `api/routes/` |
| 新提示词 | `domain/prompts/` |
| 新业务实体 | `domain/models/` |
| 新外部服务 | `infrastructure/` |
| 新业务逻辑 | `services/` |
| 新配置项 | `core/config.py` |
| 新工具函数 | `core/utils/` |

### 3. 注册路由
新路由必须在 `api/app.py` 中注册：
```python
from reinvent_insight.api.routes import new_router
app.include_router(new_router.router)
```

### 4. 更新文档
API 变更必须同步更新 `API_SUMMARY.md`

---

## 禁止事项

1. **禁止重复造轮子** - 使用已有组件，不要新建功能相近的类/函数
2. **禁止 core 层依赖业务层** - core 只能被依赖，不能依赖其他层
3. **禁止 api 层包含业务逻辑** - 业务逻辑放 services
4. **禁止 domain 层包含 I/O** - domain 只定义，不执行
5. **禁止 `from xxx import *`** - 显式导入
6. **禁止在 services 直接操作 HTTP** - HTTP 相关只在 api 层
7. **禁止创建新的配置文件** - 配置统一在 `core/config.py`
8. **禁止自定义日志器** - 使用 `from reinvent_insight.core.logger import setup_logger`

---

## 常用导入速查

```python
# 配置
from reinvent_insight.core import config
from reinvent_insight.core.config import OUTPUT_DIR, PROJECT_ROOT

# 日志
from reinvent_insight.core.logger import setup_logger
logger = setup_logger(__name__)

# AI 模型
from reinvent_insight.infrastructure.ai.model_config import get_model_client
client = get_model_client("gemini_pro")

# 任务管理
from reinvent_insight.services.analysis.task_manager import manager

# 文件工具
from reinvent_insight.core.utils.file_utils import (
    generate_document_identifier,
    generate_pdf_identifier
)

# 认证
from reinvent_insight.api.routes.auth import verify_token, get_current_user
```

---

## 技术栈约束

- **后端**: Python 3.9+, FastAPI, asyncio
- **AI**: Gemini API (主), 预留 XAI/阿里云
- **前端**: Vue 3 (免构建), Axios
- **异步**: 所有 I/O 必须 async
- **超时**: AI 调用必须设置 `asyncio.wait_for()` 超时

---

## 后处理管道机制

文章生成后的精加工通过后处理管道实现，支持同步/异步两种执行模式。

### 架构设计

```
文章生成完成 → PostProcessorPipeline.run()
                    ↓
    ┌───────────────┴───────────────┐
    │ 同步处理器 (is_async=False)    │ → 顺序执行，等待结果，可修改内容
    │ 异步处理器 (is_async=True)     │ → 仅触发，不等待，不阻塞返回
    └───────────────────────────────┘
```

### 处理器类型

| 类型 | `is_async` | 执行方式 | 适用场景 |
|-----|-----------|---------|----------|
| 同步 | `False` | 执行并等待结果 | 内容润色、格式修正 |
| 异步 | `True` | 仅触发不等待 | Visual 生成、图片增强 |

### 创建新处理器

```python
from reinvent_insight.services.analysis.post_processors import (
    PostProcessor, PostProcessorContext, PostProcessorResult, ProcessorPriority
)

class MyProcessor(PostProcessor):
    name = "my_processor"
    description = "我的处理器"
    priority = ProcessorPriority.NORMAL  # HIGH/NORMAL/LOW/LOWEST
    is_async = False  # True=异步触发，False=同步等待
    
    async def should_run(self, context: PostProcessorContext) -> bool:
        """判断是否需要运行"""
        return True
    
    async def process(self, context: PostProcessorContext) -> PostProcessorResult:
        """执行处理逻辑"""
        # 同步处理器：返回修改后的内容
        # 异步处理器：触发后台任务，返回成功即可
        return PostProcessorResult(
            success=True,
            content=context.content,  # 同步处理器需返回修改后内容
            message="处理完成"
        )
```

### 注册处理器

在 `services/startup_service.py` 的 `init_post_processors()` 中注册：

```python
from reinvent_insight.services.analysis.post_processors import register_processor
from .my_processor import MyProcessor

register_processor(MyProcessor())
```

### 防重机制

- 异步处理器通过 `task_manager` 注册任务（任务ID格式：`{type}_{name}_{timestamp}`）
- `visual_watcher` 等监控器会检查 `task_manager` 中的任务状态，避免重复触发
- 共享 `task_manager` 是防重的关键

### 上下文数据

`PostProcessorContext` 包含：
- `content`: 文章内容
- `title`: 文章标题
- `doc_hash`: 文档哈希
- `chapter_count`: 章节数
- `outline`: 大纲内容
- `extra`: 扩展数据（如 `article_path`）

---

*更新时间: 2025-12-12*
