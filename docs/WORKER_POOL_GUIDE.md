# Worker Pool 任务队列系统使用指南

> 版本: 1.0.0  
> 更新时间: 2025-12-04  
> 实现方案: Worker Pool + 优先级队列

---

## 📋 功能概述

Worker Pool 是一个完整的任务队列管理系统，用于控制分析任务的并发执行，支持：

- ✅ **优先级队列**: 支持 4 级优先级 (LOW, NORMAL, HIGH, URGENT)
- ✅ **并发控制**: 可配置的最大并发 worker 数量
- ✅ **队列管理**: 可配置的最大队列长度
- ✅ **超时处理**: 单个任务的超时保护
- ✅ **状态监控**: 实时队列统计信息
- ✅ **自动重试**: 失败任务的错误处理
- ✅ **多任务类型**: 支持 YouTube、PDF、文档分析

---

## 🎯 核心组件

### 1. Worker Pool (`worker_pool.py`)

主要类和接口：

```python
from reinvent_insight.worker_pool import worker_pool, TaskPriority

# 任务优先级枚举
class TaskPriority(Enum):
    LOW = 0      # 低优先级
    NORMAL = 1   # 普通优先级（默认）
    HIGH = 2     # 高优先级
    URGENT = 3   # 紧急优先级

# 全局 Worker Pool 实例
worker_pool = WorkerPool(
    max_workers=3,        # 最大并发数
    max_queue_size=100,   # 最大队列长度
    task_timeout=3600     # 任务超时（秒）
)
```

### 2. 配置项 (`config.py`)

```python
# 从环境变量读取
MAX_CONCURRENT_ANALYSIS_TASKS = 3    # 最大并发数
ANALYSIS_QUEUE_MAX_SIZE = 100        # 队列容量
ANALYSIS_TASK_TIMEOUT = 3600         # 超时时间（秒）
```

### 3. API 端点集成

所有分析端点现已使用队列系统：

- `POST /summarize` - YouTube 视频分析
- `POST /analyze-pdf` - PDF 文档分析
- `POST /analyze-document` - 通用文档分析

---

## 🚀 使用方式

### 1. 环境配置

编辑 `.env` 文件：

```bash
# ========================================
# 任务队列配置（Worker Pool）
# ========================================

# 最大并发分析任务数（同时运行的 worker 数量）
# 建议值：2-5，根据服务器性能和 API 配额调整
MAX_CONCURRENT_ANALYSIS_TASKS=3

# 任务队列最大长度（等待中的任务数量限制）
# 超过此限制时，新任务将被拒绝（返回 503 错误）
ANALYSIS_QUEUE_MAX_SIZE=100

# 单个分析任务的最大执行时间（秒）
# 超时任务将被自动终止
ANALYSIS_TASK_TIMEOUT=3600
```

### 2. API 调用（带优先级）

#### YouTube 视频分析

```bash
# 普通优先级（默认）
curl -X POST "http://localhost:8001/summarize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=xxxxx"}'

# 高优先级
curl -X POST "http://localhost:8001/summarize?priority=2" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=xxxxx"}'

# 紧急优先级
curl -X POST "http://localhost:8001/summarize?priority=3" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=xxxxx"}'
```

#### Python 客户端示例

```python
import requests

class ReinventClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token
    
    def analyze(self, url, priority=1):
        """
        提交分析任务
        
        Args:
            url: YouTube URL 或文件路径
            priority: 优先级 (0=LOW, 1=NORMAL, 2=HIGH, 3=URGENT)
        """
        response = requests.post(
            f"{self.base_url}/summarize",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"url": url},
            params={"priority": priority}
        )
        response.raise_for_status()
        return response.json()
    
    def get_queue_stats(self):
        """获取队列统计"""
        response = requests.get(f"{self.base_url}/api/queue/stats")
        return response.json()

# 使用示例
client = ReinventClient("http://localhost:8001", "your_token")

# 提交紧急任务
result = client.analyze(
    "https://www.youtube.com/watch?v=xxxxx",
    priority=3  # URGENT
)
print(f"任务 ID: {result['task_id']}")
print(f"状态: {result['message']}")

# 查看队列状态
stats = client.get_queue_stats()
print(f"队列长度: {stats['queue_size']}")
print(f"正在处理: {stats['current_processing']}")
print(f"已完成: {stats['total_success']}")
```

### 3. 查询队列状态

```bash
# 获取队列统计信息
curl http://localhost:8001/api/queue/stats
```

**响应示例**:

```json
{
  "total_processed": 150,     // 总处理任务数
  "total_success": 142,        // 成功任务数
  "total_failed": 5,           // 失败任务数
  "total_timeout": 3,          // 超时任务数
  "current_processing": 2,     // 正在处理的任务数
  "queue_size": 8,             // 队列中等待的任务数
  "max_workers": 3,            // 最大并发数
  "max_queue_size": 100,       // 最大队列容量
  "is_running": true           // Worker Pool 运行状态
}
```

---

## 📊 工作流程

### 1. 任务提交流程

```
用户请求
   ↓
API 验证认证
   ↓
创建任务占位状态 (status="queued")
   ↓
添加到优先级队列
   ↓
返回任务 ID + 队列信息
```

### 2. 任务执行流程

```
Worker 从队列获取任务
   ↓
更新状态 (status="running")
   ↓
执行对应 worker (YouTube/PDF/Document)
   ↓
设置超时保护
   ↓
任务完成/失败/超时
   ↓
更新统计信息
```

### 3. 优先级排序

队列使用 Python 的 `PriorityQueue`，任务按优先级排序：

```
URGENT (3) → 最先执行
HIGH (2)
NORMAL (1) → 默认优先级
LOW (0)    → 最后执行
```

同优先级的任务按 FIFO (先进先出) 顺序执行。

---

## ⚙️ 配置建议

### 1. 并发数 (`MAX_CONCURRENT_ANALYSIS_TASKS`)

| 服务器配置 | 建议并发数 | 说明 |
|-----------|-----------|------|
| 1核2G | 1-2 | 避免资源竞争 |
| 2核4G | 2-3 | 平衡性能和稳定性 |
| 4核8G | 3-5 | 充分利用多核 |
| 8核16G+ | 5-8 | 高性能处理 |

**注意事项**:
- Gemini API 有速率限制（RPM/TPM），并发过高可能触发限流
- 需要考虑网络带宽和 I/O 性能
- 建议从小值开始，逐步调优

### 2. 队列容量 (`ANALYSIS_QUEUE_MAX_SIZE`)

| 使用场景 | 建议容量 | 说明 |
|---------|---------|------|
| 个人使用 | 10-20 | 轻量级队列 |
| 小团队 | 50-100 | 支持多用户并发 |
| 生产环境 | 100-200 | 高并发场景 |
| 大规模部署 | 200-500 | 需要更多内存 |

**注意事项**:
- 每个队列任务约占 1-2KB 内存
- 队列过大会增加内存占用
- 超过容量的请求会返回 503 错误

### 3. 超时时间 (`ANALYSIS_TASK_TIMEOUT`)

| 内容类型 | 建议超时 | 说明 |
|---------|---------|------|
| 短视频 (< 10分钟) | 1800s (30分钟) | 快速处理 |
| 中等视频 (10-30分钟) | 3600s (1小时) | 默认设置 |
| 长视频 (> 30分钟) | 5400s (1.5小时) | 复杂内容 |
| 大型 PDF | 7200s (2小时) | 图文混排 |

**注意事项**:
- 超时任务会被自动终止，释放 worker
- 超时过短可能导致正常任务被中断
- 超时过长会浪费资源

---

## 🔍 监控和调试

### 1. 查看日志

```bash
# 查看 Worker Pool 启动日志
grep "Worker Pool" logs/app.log

# 查看任务执行日志
grep "任务执行" logs/app.log

# 查看队列状态
grep "队列长度" logs/app.log
```

### 2. 常见日志信息

```
✅ Worker Pool 已启动: 并发数=3, 队列容量=100
任务已加入队列: task_id=xxx, type=youtube, priority=NORMAL, queue_size=5/100
Worker 0 获取任务: xxx, 优先级: 1, 队列剩余: 4
任务执行成功: xxx
Worker 0 完成任务: xxx, 成功: True
```

### 3. 性能监控

实时监控队列状态：

```python
import requests
import time

def monitor_queue(base_url, interval=5):
    """实时监控队列状态"""
    while True:
        try:
            response = requests.get(f"{base_url}/api/queue/stats")
            stats = response.json()
            
            print(f"\r队列: {stats['queue_size']}/{stats['max_queue_size']} | "
                  f"处理中: {stats['current_processing']}/{stats['max_workers']} | "
                  f"成功: {stats['total_success']} | "
                  f"失败: {stats['total_failed']}", 
                  end='', flush=True)
            
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n监控已停止")
            break

monitor_queue("http://localhost:8001")
```

---

## ⚠️ 故障处理

### 1. 队列已满（503 错误）

**现象**: 提交任务时返回 503 错误

**原因**: 队列中等待任务数超过 `ANALYSIS_QUEUE_MAX_SIZE`

**解决方案**:
```bash
# 1. 增加队列容量
ANALYSIS_QUEUE_MAX_SIZE=200

# 2. 增加并发数（加快处理速度）
MAX_CONCURRENT_ANALYSIS_TASKS=5

# 3. 等待当前任务完成后重试
```

### 2. 任务超时

**现象**: 任务状态变为 `error`，错误类型为 `timeout`

**原因**: 任务执行时间超过 `ANALYSIS_TASK_TIMEOUT`

**解决方案**:
```bash
# 增加超时时间
ANALYSIS_TASK_TIMEOUT=7200  # 2小时
```

### 3. Worker Pool 未启动

**现象**: 任务提交后一直处于 `queued` 状态

**检查**:
```bash
# 查看启动日志
grep "Worker Pool 已启动" logs/app.log

# 查看错误日志
grep "启动 Worker Pool 失败" logs/app.log
```

**解决方案**:
- 检查配置文件语法
- 检查依赖是否安装
- 重启服务

---

## 📈 性能优化建议

### 1. 合理设置并发数

```python
# 计算公式：并发数 = min(CPU核心数, API限额/平均任务时间)
# 例如：4核CPU, API限额60 RPM, 平均任务5分钟
# 并发数 = min(4, 60/12) = min(4, 5) = 4
MAX_CONCURRENT_ANALYSIS_TASKS=4
```

### 2. 队列容量与内存

```python
# 队列内存占用 ≈ ANALYSIS_QUEUE_MAX_SIZE * 2KB
# 例如：100个任务 * 2KB = 200KB
# 建议保留足够内存空间
```

### 3. 优先级策略

- **URGENT (3)**: 仅用于真正紧急的任务（如 VIP 用户、重要业务）
- **HIGH (2)**: 需要优先处理的任务（如付费用户）
- **NORMAL (1)**: 默认优先级，大部分任务
- **LOW (0)**: 后台批量任务、测试任务

---

## 🔄 版本升级

从旧版本（无队列）升级到 Worker Pool：

### 1. 更新配置

```bash
# 复制新的配置到 .env
cp .env.example .env
# 编辑并设置队列参数
```

### 2. 重启服务

```bash
# 开发环境
./run-dev.sh

# 生产环境
systemctl restart reinvent-insight
```

### 3. 验证

```bash
# 检查 Worker Pool 是否启动
curl http://localhost:8001/api/queue/stats

# 提交测试任务
curl -X POST "http://localhost:8001/summarize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

---

## 📝 常见问题 (FAQ)

### Q1: 如何临时禁用队列系统？

A: 暂不支持禁用，但可以设置为"无限制"模式：

```bash
MAX_CONCURRENT_ANALYSIS_TASKS=999
ANALYSIS_QUEUE_MAX_SIZE=99999
```

### Q2: 队列中的任务可以取消吗？

A: 当前版本不支持取消排队任务。正在执行的任务会受超时保护自动终止。

### Q3: 优先级相同时，任务如何排序？

A: 按照提交时间的先后顺序（FIFO）。

### Q4: Worker Pool 崩溃后，队列中的任务会丢失吗？

A: 是的，队列中的任务存储在内存中，服务重启后会丢失。建议：
- 实现任务持久化（未来版本）
- 客户端实现重试机制

### Q5: 如何监控 API 限流情况？

A: 查看失败任务的错误信息，Gemini API 限流通常返回 429 错误。

---

## 🎉 总结

Worker Pool 提供了完整的任务队列解决方案，主要优势：

✅ **资源控制**: 避免同时处理过多任务导致服务器过载  
✅ **公平调度**: 优先级队列确保重要任务优先处理  
✅ **容错能力**: 超时保护和错误处理机制  
✅ **可观测性**: 实时统计信息便于监控和调优  
✅ **易于配置**: 环境变量即可调整所有参数

开始使用 Worker Pool，让你的分析服务更稳定、更高效！ 🚀
