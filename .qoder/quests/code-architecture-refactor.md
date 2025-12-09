# 代码架构重构设计

## 背景与问题

### 当前架构问题

通过代码审查，识别出以下核心架构问题：

| 问题类型 | 具体表现 | 影响 |
|---------|---------|------|
| 超长文件 | api.py (3250行/123.6KB)<br>workflow.py (1560行/66.9KB)<br>model_config.py (64.1KB)<br>prompts.py (34.7KB) | 可维护性差、定位困难、并发编辑冲突 |
| 职责混乱 | api.py 混杂路由、业务逻辑、缓存管理、文件服务 | 违反单一职责原则、难以测试 |
| 缺乏分层 | 无明确的层次边界，业务逻辑直接操作底层 | 耦合度高、难以扩展 |
| 目录混乱 | 功能相关代码散落在根目录 | 逻辑不清晰、难以导航 |
| 重复代码 | 多处元数据解析、哈希计算、文件操作逻辑 | 维护成本高、易引入bug |

### 具体问题清单

**api.py (3250行)** 的职责过载：
- HTTP路由定义（30+个端点）
- 业务逻辑处理（文件列表、任务管理）
- 缓存映射管理（hash_to_filename、hash_to_versions）
- 文件元数据解析
- 静态文件服务配置
- 认证token管理
- TTS服务初始化

**workflow.py (1560行)** 的职责过载：
- 大纲生成逻辑
- 章节并发生成
- 报告组装
- 文件清理
- 辅助函数（解析、格式化等）

**目录结构问题**：
- 根目录堆积9个Cookie相关模块，缺乏组织
- services目录仅有4个文件，功能划分不充分
- tools目录包含非工具类功能

## 重构目标

### 核心原则

| 原则 | 说明 | 实施标准 |
|-----|------|---------|
| 单一职责 | 每个模块仅负责一个明确的功能域 | 文件行数≤500，类方法数≤20 |
| 分层架构 | 严格的层次划分和依赖方向 | 只允许向下依赖，禁止循环依赖 |
| 高内聚低耦合 | 相关功能聚合，不相关功能隔离 | 模块间接口清晰，依赖最小化 |
| 可测试性 | 核心逻辑可独立测试 | 业务逻辑与框架代码分离 |
| 渐进重构 | 保持系统运行，逐步优化 | 每次重构可独立部署验证 |

### 量化指标

| 指标 | 当前状态 | 目标状态 |
|-----|---------|---------|
| 最大文件行数 | 3250行 | ≤500行 |
| 平均文件行数 | ~800行 | ≤300行 |
| 根目录文件数 | 40+ | ≤10 |
| API路由文件行数 | 3250行 | ≤300行 |
| 模块依赖深度 | 无限制 | ≤3层 |

## 目标架构设计

### 分层架构模型

```
┌─────────────────────────────────────────────────────┐
│                   API层 (FastAPI)                    │
│  - 路由定义（routes/）                                │
│  - 请求/响应模型（schemas/）                          │
│  - 依赖注入配置                                       │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                   服务层 (Services)                   │
│  - 业务逻辑封装                                       │
│  - 跨领域协调                                        │
│  - 事务管理                                          │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                   领域层 (Domain)                     │
│  - 核心业务实体                                       │
│  - 领域模型和规则                                     │
│  - 无外部依赖                                        │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│               基础设施层 (Infrastructure)              │
│  - 数据持久化                                        │
│  - 外部API集成                                       │
│  - 文件系统操作                                       │
└─────────────────────────────────────────────────────┘
```

### 新目录结构

```
src/reinvent_insight/
├── api/                          # API层（新增）
│   ├── __init__.py
│   ├── app.py                    # FastAPI应用初始化（<100行）
│   ├── dependencies.py           # 依赖注入配置（<150行）
│   ├── routes/                   # 路由模块
│   │   ├── __init__.py
│   │   ├── auth.py              # 认证相关（<100行）
│   │   ├── analysis.py          # 分析任务（<200行）
│   │   ├── documents.py         # 文档管理（<300行）
│   │   ├── tts.py               # TTS服务（<250行）
│   │   └── system.py            # 系统信息（<100行）
│   └── schemas/                  # 请求/响应模型
│       ├── __init__.py
│       ├── auth.py
│       ├── analysis.py
│       ├── documents.py
│       └── tts.py
│
├── services/                     # 服务层（重组）
│   ├── __init__.py
│   ├── analysis/                 # 分析服务
│   │   ├── __init__.py
│   │   ├── task_orchestrator.py # 任务编排（<300行）
│   │   ├── workflow_engine.py   # 工作流引擎（<400行）
│   │   └── chapter_generator.py # 章节生成（<350行）
│   ├── document/                 # 文档服务
│   │   ├── __init__.py
│   │   ├── document_manager.py  # 文档管理器（<250行）
│   │   ├── metadata_service.py  # 元数据服务（<200行）
│   │   ├── hash_registry.py     # 哈希注册表（<200行）
│   │   └── version_tracker.py   # 版本追踪（<150行）
│   ├── tts/                      # TTS服务（重组）
│   │   ├── __init__.py
│   │   ├── tts_service.py       # 保留现有
│   │   ├── audio_cache.py       # 保留现有
│   │   ├── pregeneration_service.py  # 重命名
│   │   └── text_preprocessor.py      # 重命名
│   └── cookie/                   # Cookie管理（新增）
│       ├── __init__.py
│       ├── cookie_manager.py    # 整合管理逻辑
│       ├── cookie_store.py      # 保留
│       ├── health_checker.py    # 重命名
│       ├── refresher.py         # 重命名
│       └── scheduler.py         # 重命名
│
├── domain/                       # 领域层（新增）
│   ├── __init__.py
│   ├── models/                   # 领域模型
│   │   ├── __init__.py
│   │   ├── document.py          # 文档实体
│   │   ├── analysis_task.py     # 分析任务实体
│   │   ├── outline.py           # 大纲模型
│   │   └── chapter.py           # 章节模型
│   ├── workflows/                # 工作流定义
│   │   ├── __init__.py
│   │   ├── base.py              # 工作流基类
│   │   ├── youtube_workflow.py  # YouTube分析流程
│   │   └── pdf_workflow.py      # PDF分析流程
│   └── repositories/             # 仓储接口（抽象）
│       ├── __init__.py
│       ├── document_repository.py
│       └── task_repository.py
│
├── infrastructure/               # 基础设施层（新增）
│   ├── __init__.py
│   ├── persistence/              # 持久化实现
│   │   ├── __init__.py
│   │   ├── file_document_repository.py  # 文件系统实现
│   │   └── memory_task_repository.py    # 内存实现
│   ├── ai/                       # AI集成
│   │   ├── __init__.py
│   │   ├── model_client.py      # 从model_config重构
│   │   ├── providers/           # 各提供商实现
│   │   │   ├── gemini.py
│   │   │   ├── dashscope.py
│   │   │   └── openai.py
│   │   └── prompt_manager.py    # 从prompts.py重构
│   ├── media/                    # 媒体处理
│   │   ├── __init__.py
│   │   ├── youtube_downloader.py
│   │   ├── pdf_processor.py
│   │   └── audio_utils.py
│   └── file_system/              # 文件系统
│       ├── __init__.py
│       ├── watcher.py
│       └── storage.py
│
├── core/                         # 核心工具（新增）
│   ├── __init__.py
│   ├── config.py                 # 配置管理
│   ├── logger.py                 # 日志配置
│   ├── exceptions.py             # 异常定义
│   └── utils/                    # 通用工具
│       ├── __init__.py
│       ├── text_utils.py
│       ├── hash_utils.py
│       └── file_utils.py
│
└── legacy/                       # 遗留代码（过渡期）
    ├── __init__.py
    ├── api.py                    # 标记为deprecated
    └── workflow.py               # 标记为deprecated
```

## 重构策略

### 阶段一：结构重组（风险：低）

**目标**：建立新目录结构，不改变现有代码逻辑

**实施步骤**：

1. 创建新目录结构
   - 创建api、services、domain、infrastructure、core目录
   - 创建各子目录和__init__.py文件

2. 移动现有文件到合适位置
   - 将现有api.py、workflow.py移入legacy目录
   - 添加deprecation警告
   - 更新导入路径（通过__init__.py转发）

3. 文件分组迁移
   - Cookie相关：移入services/cookie/
   - Worker相关：移入services/analysis/
   - 文档处理：移入services/document/
   - TTS相关：保持services/tts/

**验证标准**：
- 所有现有测试通过
- API端点正常响应
- 日志无错误警告

### 阶段二：API层拆分（风险：中）

**目标**：将api.py拆分为多个路由模块

**拆分方案**：

| 原api.py内容 | 目标位置 | 预估行数 |
|------------|---------|---------|
| 认证相关（/login） | api/routes/auth.py | ~80行 |
| 分析任务（/summarize, /websocket） | api/routes/analysis.py | ~200行 |
| 文档列表与查询 | api/routes/documents.py | ~300行 |
| TTS相关端点 | api/routes/tts.py | ~250行 |
| 系统信息（/api/env） | api/routes/system.py | ~50行 |
| 静态文件服务 | api/app.py | ~100行 |

**实施步骤**：

1. 提取路由到独立文件
   - 创建schemas定义请求/响应模型
   - 创建routes文件定义路由处理函数
   - 提取业务逻辑到services层

2. 创建依赖注入配置
   - 在api/dependencies.py统一管理依赖
   - 重构全局变量为依赖注入
   - 统一错误处理

3. 重构app初始化
   - 在api/app.py创建应用工厂
   - 注册路由
   - 配置中间件

**迁移示例**（认证路由）：

迁移前（api.py片段）：
```
session_tokens: Set[str] = set()

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(req: LoginRequest):
    # 认证逻辑
```

迁移后（api/routes/auth.py）：
```
# 业务逻辑移至services层
from services.auth.auth_service import AuthService

# 模型定义移至schemas
from api.schemas.auth import LoginRequest, LoginResponse

# 路由定义清晰分离
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login")
async def login(
    req: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    return await auth_service.authenticate(req.username, req.password)
```

**验证标准**：
- 所有API端点保持相同行为
- 响应格式不变
- 性能无明显下降

### 阶段三：服务层提取（风险：中）

**目标**：从路由中提取业务逻辑到服务层

**服务设计**：

**DocumentService（文档服务）**
- 职责：文档元数据管理、版本追踪、哈希映射
- 方法：
  - list_documents() - 列出所有文档
  - get_document(hash) - 获取文档详情
  - get_versions(hash) - 获取文档版本
  - update_hash_mapping() - 更新哈希映射

**AnalysisService（分析服务）**
- 职责：分析任务编排、进度管理
- 方法：
  - create_task(url, priority) - 创建分析任务
  - check_duplicate(video_id) - 检查重复
  - get_task_status(task_id) - 获取任务状态

**WorkflowEngine（工作流引擎）**
- 职责：执行分析流程、章节生成
- 方法：
  - execute_workflow(task_id, content) - 执行工作流
  - generate_outline(content) - 生成大纲
  - generate_chapters(outline) - 生成章节

**实施步骤**：

1. 创建服务类
   - 定义清晰的接口
   - 实现业务逻辑
   - 添加日志和错误处理

2. 重构路由使用服务
   - 通过依赖注入获取服务实例
   - 路由仅负责参数验证和响应格式化
   - 业务逻辑完全委托给服务层

3. 提取和去重代码
   - 识别重复的元数据解析逻辑
   - 统一哈希计算方法
   - 集中配置管理

**验证标准**：
- 业务逻辑可独立单元测试
- 路由函数行数≤50行
- 服务类职责单一明确

### 阶段四：workflow.py重构（风险：高）

**目标**：将1560行的workflow.py拆分为多个模块

**拆分方案**：

| 当前功能 | 目标位置 | 说明 |
|---------|---------|------|
| DeepSummaryWorkflow类 | domain/workflows/base.py | 工作流基类（<200行） |
| YouTube特定逻辑 | domain/workflows/youtube_workflow.py | YouTube分析流程（<300行） |
| PDF特定逻辑 | domain/workflows/pdf_workflow.py | PDF分析流程（<300行） |
| 大纲生成器 | services/analysis/outline_generator.py | 大纲生成服务（<400行） |
| 章节生成器 | services/analysis/chapter_generator.py | 章节生成服务（<350行） |
| 工具函数 | core/utils/ | 文本处理工具（<200行） |

**实施步骤**：

1. 提取工具函数
   - create_anchor() → core/utils/text_utils.py
   - remove_parenthetical_english() → core/utils/text_utils.py
   - parse_outline() → core/utils/markdown_utils.py

2. 拆分OutlineGenerator
   - 保持接口不变
   - 移入services/analysis/
   - 依赖注入配置和模型客户端

3. 重构DeepSummaryWorkflow
   - 创建抽象基类定义流程接口
   - 实现YouTube和PDF特定子类
   - 使用策略模式处理不同内容类型

**工作流重构示例**：

重构前（workflow.py片段）：
```
class DeepSummaryWorkflow:
    def __init__(self, task_id, model_name, content, ...):
        # 大量初始化逻辑
        if isinstance(content, str):
            self.content_type = "transcript"
        elif isinstance(content, DocumentContent):
            self.content_type = content.content_type
        # ... 更多判断逻辑
    
    async def run(self):
        # 超长方法，混合多种职责
```

重构后（domain/workflows/base.py + youtube_workflow.py）：
```
# base.py - 抽象基类
class AnalysisWorkflow(ABC):
    def __init__(self, task_id: str, config: WorkflowConfig):
        self.task_id = task_id
        self.config = config
    
    @abstractmethod
    async def generate_outline(self) -> OutlinePlan:
        pass
    
    @abstractmethod
    async def generate_chapters(self, outline: OutlinePlan) -> List[Chapter]:
        pass
    
    async def run(self) -> AnalysisResult:
        # 模板方法，定义标准流程
        outline = await self.generate_outline()
        chapters = await self.generate_chapters(outline)
        return await self.assemble_report(outline, chapters)

# youtube_workflow.py - YouTube特定实现
class YouTubeAnalysisWorkflow(AnalysisWorkflow):
    def __init__(self, task_id: str, transcript: str, metadata: VideoMetadata):
        super().__init__(task_id, WorkflowConfig.for_youtube())
        self.transcript = transcript
        self.metadata = metadata
    
    async def generate_outline(self) -> OutlinePlan:
        # YouTube特定的大纲生成逻辑
```

**验证标准**：
- 工作流执行结果与原代码一致
- 各模块可独立测试
- 扩展新内容类型更容易

### 阶段五：提取领域层（风险：中）

**目标**：提取核心业务实体和规则，实现领域驱动设计

**领域模型设计**：

**Document（文档聚合根）**
- 属性：
  - document_id: 唯一标识
  - hash: 内容哈希
  - metadata: 元数据
  - versions: 版本列表
  - status: 文档状态
- 方法：
  - add_version(version) - 添加新版本
  - get_latest_version() - 获取最新版本
  - mark_as_deleted() - 软删除

**AnalysisTask（分析任务聚合根）**
- 属性：
  - task_id: 任务ID
  - source: 来源信息
  - status: 任务状态
  - progress: 进度信息
  - result: 分析结果
- 方法：
  - start() - 开始任务
  - update_progress(progress) - 更新进度
  - complete(result) - 完成任务
  - fail(error) - 标记失败

**OutlinePlan（大纲值对象）**
- 属性：
  - title: 标题
  - introduction: 引言
  - chapters: 章节列表
- 方法：
  - validate() - 验证大纲合法性
  - to_markdown() - 转换为Markdown

**实施步骤**：

1. 定义领域实体
   - 创建domain/models/下的各实体类
   - 实现业务规则和验证逻辑
   - 保持实体无外部依赖

2. 定义仓储接口
   - 在domain/repositories/定义抽象接口
   - 不包含具体实现
   - 使用领域语言命名

3. 重构服务层使用领域模型
   - 服务层操作领域实体
   - 通过仓储接口持久化
   - 业务逻辑在领域层

**验证标准**：
- 领域模型无外部依赖
- 业务规则集中在领域层
- 仓储接口可替换实现

### 阶段六：基础设施层实现（风险：低）

**目标**：实现领域层仓储接口，封装外部依赖

**实施内容**：

1. 实现文档仓储
   - FileDocumentRepository - 基于文件系统
   - 实现CRUD操作
   - 管理哈希映射持久化

2. 重构AI集成
   - 从model_config.py提取
   - 统一接口设计
   - 各提供商独立实现

3. 重构媒体处理
   - 整合downloader、pdf_processor等
   - 统一错误处理
   - 改进日志记录

**验证标准**：
- 仓储实现通过单元测试
- 外部依赖可mock测试
- 配置通过依赖注入

## 数据迁移与兼容性

### 向后兼容策略

**legacy模块维护期**：
- 保留legacy/api.py和legacy/workflow.py至少2个版本周期
- 添加deprecation警告提示使用新API
- 提供迁移指南

**导入路径兼容**：
- 在顶层__init__.py导出常用类
- 保持关键接口签名不变
- 使用类型别名过渡

**配置兼容**：
- 旧配置变量继续支持
- 自动转换为新配置格式
- 记录警告提示更新

### 测试策略

**测试覆盖目标**：

| 层次 | 测试类型 | 覆盖率目标 |
|-----|---------|-----------|
| 领域层 | 单元测试 | 90%+ |
| 服务层 | 单元测试 | 85%+ |
| API层 | 集成测试 | 80%+ |
| 端到端 | E2E测试 | 关键流程100% |

**测试实施**：

1. 为新代码编写测试
   - 领域实体：纯单元测试
   - 服务类：mock依赖测试
   - API路由：集成测试

2. 回归测试保护
   - 保留现有测试
   - 针对重构部分增加测试
   - 持续运行测试套件

3. 性能测试
   - 对比重构前后性能
   - 监控关键指标
   - 及时优化瓶颈

## 风险评估与缓解

### 风险矩阵

| 风险 | 概率 | 影响 | 应对措施 |
|-----|------|------|---------|
| 重构引入bug | 中 | 高 | 充分测试、灰度发布、快速回滚 |
| 性能下降 | 低 | 中 | 性能基准测试、持续监控 |
| API不兼容 | 低 | 高 | 保留legacy、版本管理 |
| 进度延期 | 中 | 中 | 阶段性验证、渐进式重构 |
| 团队适应期 | 中 | 低 | 文档培训、代码审查 |

### 回滚机制

**版本标记**：
- 每个阶段完成后打tag
- 记录关键变更点
- 可快速回退到稳定版本

**灰度发布**：
- 新旧代码路径并存
- 通过配置开关切换
- 逐步增加新路径流量

**监控告警**：
- 部署后持续监控
- 异常自动告警
- 快速定位问题

## 实施时间表

### 分阶段交付

| 阶段 | 预计时间 | 关键产出 | 验收标准 |
|-----|---------|---------|---------|
| 阶段一 | 2天 | 新目录结构、文件迁移 | 所有测试通过、无功能影响 |
| 阶段二 | 3天 | API层拆分、路由模块化 | API端点正常、响应格式不变 |
| 阶段三 | 4天 | 服务层提取、业务逻辑分离 | 业务逻辑可测试、代码复用提升 |
| 阶段四 | 5天 | workflow重构、工作流模块化 | 工作流结果一致、扩展性提升 |
| 阶段五 | 3天 | 领域层提取、DDD实施 | 领域模型清晰、仓储接口定义 |
| 阶段六 | 3天 | 基础设施实现、依赖封装 | 外部依赖解耦、可替换实现 |

**总计**：约20个工作日

### 里程碑

**M1 - 结构就绪（第2天）**：
- 新目录结构创建完成
- 现有代码迁移至合适位置
- 导入路径更新、系统正常运行

**M2 - API现代化（第5天）**：
- api.py完全拆分
- 路由职责单一
- 依赖注入配置完成

**M3 - 服务解耦（第9天）**：
- 业务逻辑提取到服务层
- 路由仅负责HTTP处理
- 代码复用率显著提升

**M4 - 核心重构（第14天）**：
- workflow.py拆分完成
- 工作流模块化、可扩展
- 代码行数达标

**M5 - 架构完善（第20天）**：
- 领域层和基础设施层完成
- 依赖关系清晰
- 架构分层明确

## 后续优化方向

### 长期改进

**数据库引入**：
- 当前基于文件系统存储，扩展性受限
- 考虑引入SQLite或PostgreSQL
- 实现DocumentRepository的数据库版本

**缓存策略优化**：
- 当前内存缓存，重启丢失
- 引入Redis缓存层
- 实现分布式缓存一致性

**异步优化**：
- 进一步优化异步IO
- 减少阻塞操作
- 提升并发性能

**监控完善**：
- 引入APM工具（如Sentry）
- 性能指标收集
- 业务指标监控

### 技术债务清理

**遗留代码清理**：
- 2个版本周期后移除legacy模块
- 清理废弃的配置项
- 统一代码风格

**文档完善**：
- 架构设计文档
- API文档自动生成
- 开发者指南

**测试增强**：
- 提升测试覆盖率至90%+
- 引入突变测试
- 性能回归测试自动化
