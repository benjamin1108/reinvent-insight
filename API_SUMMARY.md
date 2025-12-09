# Reinvent Insight API 接口文档

> 版本: 0.1.1  
> 更新时间: 2025-12-10  
> 基于 FastAPI 构建的高性能异步 API 服务

---

## 目录

1. [认证系统](#认证系统)
2. [内容分析 API](#内容分析-api)
3. [文档管理 API](#文档管理-api)
4. [TTS 语音合成 API](#tts-语音合成-api)
5. [任务管理 API](#任务管理-api)
6. [系统管理 API](#系统管理-api)
7. [数据模型](#数据模型)

---

## 认证系统

### 1. 用户登录
**端点**: `POST /login`  
**描述**: 验证用户名密码，返回 Bearer Token  
**认证**: 无需认证  

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "token": "string"
}
```

**认证方式**: 后续请求需在 Header 中添加:
```
Authorization: Bearer {token}
```

---

## 内容分析 API

### 1. YouTube 视频分析
**端点**: `POST /summarize`  
**描述**: 分析 YouTube 视频，生成深度解读  
**认证**: 需要 Token  

**请求体**:
```json
{
  "url": "https://www.youtube.com/watch?v=xxxxx",
  "task_id": "可选，用于重新连接"
}
```

**响应**:
```json
{
  "task_id": "uuid-string",
  "message": "任务已创建，请连接 WebSocket。",
  "status": "created|reconnected"
}
```

### 2. PDF 文档分析
**端点**: `POST /analyze-pdf`  
**描述**: 使用 Gemini 多模态能力分析 PDF 文件  
**认证**: 需要 Token  

**请求**: `multipart/form-data`
- `file`: PDF 文件
- `title`: 可选标题（不提供时 AI 自动生成）

**响应**: 同 YouTube 分析

### 3. 通用文档分析
**端点**: `POST /analyze-document`  
**描述**: 分析多种格式文档（TXT, MD, PDF, DOCX）  
**认证**: 需要 Token  

**请求**: `multipart/form-data`
- `file`: 文档文件
- `title`: 可选标题

**支持格式**: `.txt`, `.md`, `.pdf`, `.docx`  
**文件大小限制**:
- 文本文件（TXT/MD）: `MAX_TEXT_FILE_SIZE`
- 二进制文件（PDF/DOCX）: `MAX_BINARY_FILE_SIZE`

**响应**: 同 YouTube 分析

---

## 文档管理 API

### 1. 获取文档列表（公开）
**端点**: `GET /api/public/summaries`  
**描述**: 获取所有已生成的深度解读列表  
**认证**: 无需认证  

**响应**:
```json
{
  "summaries": [
    {
      "filename": "string",
      "title_cn": "中文标题",
      "title_en": "英文标题",
      "size": 123456,
      "word_count": 10000,
      "created_at": 1701234567.89,
      "modified_at": 1701234567.89,
      "upload_date": "20241102",
      "video_url": "https://...",
      "is_reinvent": false,
      "course_code": "ABC123",
      "level": 300,
      "hash": "doc-hash",
      "version": 1,
      "is_pdf": false,
      "content_type": "YouTube视频|PDF文档"
    }
  ]
}
```

### 2. 检查视频是否已解析
**端点**: `GET /api/public/summary/{video_id}`  
**描述**: 根据 YouTube video_id 查询是否存在已解析的深度解读  
**认证**: 无需认证  

**参数**:
- `video_id`: YouTube 视频 ID（11位字符，如 `abc123xyz_-`）

**响应**:
```json
{
  "exists": true,
  "hash": "abc123def456",
  "title": "视频标题"
}
```

**字段说明**:
- `exists`: 是否存在已解析的内容
- `hash`: 文档哈希（不存在时为 null）
- `title`: 文档标题（不存在时为 null）

**错误响应**:
```json
{
  "exists": false,
  "hash": null,
  "title": null,
  "error": "无效的 video_id 格式"
}
```

### 3. 获取文档内容（按文件名）
**端点**: `GET /api/public/summaries/{filename}`  
**描述**: 获取指定文档的完整内容  
**认证**: 无需认证  

**响应**:
```json
{
  "filename": "string",
  "title": "标题",
  "title_cn": "中文标题",
  "title_en": "英文标题",
  "content": "Markdown 内容（已清理元数据）",
  "video_url": "https://...",
  "versions": [
    {
      "filename": "string",
      "version": 1,
      "created_at": "2024-11-02T10:00:00",
      "title_cn": "中文标题",
      "title_en": "英文标题"
    }
  ]
}
```

### 4. 获取文档内容（按 Hash）
**端点**: `GET /api/public/doc/{doc_hash}`  
**描述**: 通过文档 Hash 获取最新版本内容  
**认证**: 无需认证  

**响应**: 同按文件名获取

### 5. 获取文档特定版本
**端点**: `GET /api/public/doc/{doc_hash}/{version}`  
**描述**: 获取文档的指定版本  
**认证**: 无需认证  

**参数**:
- `doc_hash`: 文档哈希值
- `version`: 版本号（整数）

**响应**: 同按文件名获取

### 6. 下载 Markdown 文件
**端点**: `GET /api/public/summaries/{filename}/markdown`  
**描述**: 下载去除元数据的 Markdown 文件  
**认证**: 无需认证  

**响应**: `text/markdown` 文件下载

### 7. 下载 PDF 文件
**端点**: `GET /api/public/summaries/{filename}/pdf`  
**描述**: 生成并下载 PDF 格式文档  
**认证**: 无需认证  

**响应**: `application/pdf` 文件下载

### 8. 获取可视化解读
**端点**: `GET /api/article/{doc_hash}/visual`  
**描述**: 获取文章的可视化 HTML 解读  
**认证**: 无需认证  

**查询参数**:
- `version`: 可选版本号

**响应**: HTML 内容

### 9. 获取可视化解读状态
**端点**: `GET /api/article/{doc_hash}/visual/status`  
**描述**: 查询可视化解读的生成状态  
**认证**: 无需认证  

**响应**:
```json
{
  "status": "pending|processing|completed|failed",
  "file": "visual_filename.html",
  "generated_at": "2024-11-02T10:00:00",
  "version": 1
}
```

### 10. 软删除文章（管理员）
**端点**: `DELETE /api/summaries/{doc_hash}`  
**描述**: 软删除文章，移动到回收站（可恢复）  
**认证**: 需要 Token  

**移动内容**:
- 所有版本的 Markdown 文件
- 对应的 PDF 文件
- 可视化解读 HTML 文件

**响应**:
```json
{
  "success": true,
  "message": "已移动 3 个文件到回收站",
  "deleted_files": [
    "/path/to/trash/hash_timestamp_article.md",
    "/path/to/trash/pdfs/hash_timestamp_article.pdf"
  ],
  "errors": null
}
```

**错误响应**:
- `401 Unauthorized`: 未登录或 Token 无效
- `404 Not Found`: 文档未找到
- `500 Internal Server Error`: 移动失败

### 11. 获取回收站列表
**端点**: `GET /api/admin/trash`  
**描述**: 获取回收站中的文章列表  
**认证**: 需要 Token  

**响应**:
```json
{
  "items": [
    {
      "doc_hash": "abc123",
      "original_filename": "article.md",
      "trash_filename": "abc123_20241102_120000_article.md",
      "title_cn": "中文标题",
      "title_en": "English Title",
      "deleted_at": "2024-11-02T12:00:00",
      "size": 12345
    }
  ]
}
```

### 12. 恢复文章
**端点**: `POST /api/admin/trash/{doc_hash}/restore`  
**描述**: 从回收站恢复文章  
**认证**: 需要 Token  

**响应**:
```json
{
  "success": true,
  "message": "已恢复 3 个文件",
  "restored_files": ["article.md", "article_visual.html"],
  "errors": null
}
```

**错误响应**:
- `401 Unauthorized`: 未登录或 Token 无效
- `404 Not Found`: 回收站中未找到该文档

### 13. 永久删除文章
**端点**: `DELETE /api/admin/trash/{doc_hash}`  
**描述**: 从回收站永久删除文章（不可恢复）  
**认证**: 需要 Token  

**删除内容**:
- 回收站中的 Markdown/HTML 文件
- 回收站中的 PDF 文件
- TTS 音频缓存

**响应**:
```json
{
  "success": true,
  "message": "已永久删除 3 个文件",
  "deleted_files": ["hash_timestamp_article.md", "tts_cache/abc123"],
  "errors": null
}
```

### 14. 清空回收站
**端点**: `DELETE /api/admin/trash`  
**描述**: 清空整个回收站  
**认证**: 需要 Token  

**响应**:
```json
{
  "success": true,
  "message": "已清空回收站，删除了 5 篇文章的相关文件"
}
```

---

## TTS 语音合成 API

### 1. 生成 TTS 音频（非流式）
**端点**: `POST /api/tts/generate`  
**描述**: 生成完整 TTS 音频，优先返回缓存  
**认证**: 无需认证  

**请求体**:
```json
{
  "article_hash": "string",
  "text": "要合成的文本",
  "voice": "Kai|可选",
  "language": "Chinese|可选",
  "use_cache": true,
  "skip_code_blocks": true
}
```

**响应**:
```json
{
  "audio_url": "/api/tts/cache/{audio_hash}",
  "duration": 120.5,
  "cached": true,
  "voice": "Kai",
  "language": "Chinese"
}
```

### 2. 流式生成 TTS 音频（SSE）
**端点**: `POST /api/tts/stream`  
**描述**: 实时流式生成音频，支持边生成边播放  
**认证**: 无需认证  

**请求体**: 同非流式

**响应**: Server-Sent Events (SSE)

**事件类型**:

**chunk 事件** - 音频数据块:
```json
{
  "index": 1,
  "data": "base64_encoded_pcm",
  "chunk_size": 48000,
  "total_bytes": 96000,
  "buffered_duration": 2.0,
  "elapsed_time": 1.5,
  "from_cache": false
}
```

**complete 事件** - 生成完成:
```json
{
  "audio_url": "/api/tts/cache/{audio_hash}",
  "duration": 120.5,
  "chunk_count": 60,
  "total_bytes": 2880000,
  "generation_time": 30.2,
  "audio_hash": "hash-string"
}
```

**error 事件** - 生成失败:
```json
{
  "error": "错误信息",
  "message": "音频生成失败"
}
```

### 3. 获取缓存音频
**端点**: `GET /api/tts/cache/{audio_hash}`  
**描述**: 获取已缓存的音频文件  
**认证**: 无需认证  

**响应**: `audio/wav` 文件流

**特性**:
- 支持 Range 请求（断点续传）
- 长期缓存（1年）
- CORS 支持

### 4. 查询 TTS 状态
**端点**: `GET /api/tts/status/{article_hash}`  
**描述**: 查询文章的 TTS 音频生成状态  
**认证**: 无需认证  

**响应**:
```json
{
  "has_audio": true,
  "audio_url": "/api/tts/cache/{audio_hash}",
  "duration": 120.5,
  "status": "ready|processing|none",
  "voice": "Kai",
  "generated_at": "2024-11-02T10:00:00",
  "has_partial": false,
  "partial_url": null,
  "partial_duration": null,
  "chunks_generated": 0,
  "total_chunks": 0,
  "progress_percent": 0
}
```

**状态说明**:
- `ready`: 音频已生成完成
- `processing`: 正在生成中（包含进度信息）
- `none`: 未生成

### 5. 获取 TTS 预处理文本
**端点**: `GET /api/tts/text/{article_hash}`  
**描述**: 获取文章的 TTS 专用预处理文本  
**认证**: 无需认证  

**响应**: `text/plain` 纯文本

### 6. 手动触发 TTS 预生成
**端点**: `POST /api/tts/pregenerate`  
**描述**: 手动触发 TTS 音频预生成任务  
**认证**: 无需认证  

**请求体**:
```json
{
  "filename": "可选，文件名",
  "article_hash": "可选，文章哈希",
  "text": "可选，直接提供文本"
}
```

**注意**: `filename` 和 `article_hash` 至少提供一个

**响应**:
```json
{
  "task_id": "uuid-string|null",
  "status": "queued|skipped",
  "message": "任务已添加到队列: uuid-string"
}
```

### 7. 获取 TTS 队列统计
**端点**: `GET /api/tts/queue/stats`  
**描述**: 获取预生成队列的统计信息  
**认证**: 无需认证  

**响应**:
```json
{
  "queue_size": 5,
  "total_tasks": 100,
  "pending": 5,
  "processing": 1,
  "completed": 90,
  "failed": 3,
  "skipped": 1,
  "is_running": true
}
```

### 8. 获取 TTS 任务列表
**端点**: `GET /api/tts/queue/tasks`  
**描述**: 获取 TTS 预生成任务列表  
**认证**: 无需认证  

**查询参数**:
- `status`: 可选，按状态筛选 (`pending|processing|completed|failed|skipped`)
- `limit`: 返回数量限制，默认 50

**响应**:
```json
{
  "tasks": [
    {
      "task_id": "uuid-string",
      "article_hash": "hash",
      "source_file": "filename.md",
      "status": "completed",
      "created_at": "2024-11-02T10:00:00",
      "started_at": "2024-11-02T10:00:05",
      "completed_at": "2024-11-02T10:02:30",
      "retry_count": 0,
      "error_message": null,
      "audio_hash": "audio-hash"
    }
  ],
  "total": 100
}
```

---

## 任务管理 API

### 1. 获取任务队列统计
**端点**: `GET /api/queue/stats`  
**描述**: 获取主任务队列的统计信息（YouTube/PDF 解析）  
**认证**: 无需认证  

**响应**:
```json
{
  "total_processed": 150,
  "total_success": 142,
  "total_failed": 5,
  "total_timeout": 3,
  "current_processing": 2,
  "queue_size": 8,
  "max_workers": 3,
  "max_queue_size": 100,
  "is_running": true
}
```

**字段说明**:
- `total_processed`: 总处理任务数
- `total_success`: 成功任务数
- `total_failed`: 失败任务数
- `total_timeout`: 超时任务数
- `current_processing`: 当前正在处理的任务数
- `queue_size`: 队列中等待的任务数
- `max_workers`: 最大并发数
- `max_queue_size`: 队列最大容量
- `is_running`: 服务是否运行中

### 2. 获取任务队列详情
**端点**: `GET /api/queue/tasks`  
**描述**: 获取正在处理和排队中的任务详细列表  
**认证**: 无需认证  

**响应**:
```json
{
  "processing": [
    {
      "task_id": "uuid-123",
      "status": "running",
      "progress": 45,
      "url": "https://youtube.com/watch?v=abc123xyz_-",
      "video_id": "abc123xyz_-",
      "doc_hash": null
    }
  ],
  "queued": [
    {
      "task_id": "uuid-456",
      "task_type": "youtube",
      "url": "https://youtu.be/def456uvw_-",
      "video_id": "def456uvw_-",
      "priority": "NORMAL",
      "status": "queued",
      "created_at": "2024-12-04T20:00:00",
      "queue_position": 1,
      "doc_hash": null
    }
  ],
  "total_processing": 1,
  "total_queued": 1
}
```

**字段说明**:
- `processing`: 正在处理的任务列表
  - `task_id`: 任务ID
  - `status`: 任务状态（running）
  - `progress`: 进度百分比（0-100）
  - `url`: 任务原始 URL
  - `video_id`: YouTube 视频 ID（11位唯一标识，用于准确比对，非 YouTube 任务为 null）
  - `doc_hash`: 文档哈希（处理中为 null，完成后才生成）
- `queued`: 排队中的任务列表
  - `task_type`: 任务类型（youtube/pdf/document）
  - `video_id`: YouTube 视频 ID（用于准确比对）
  - `priority`: 优先级（LOW/NORMAL/HIGH/URGENT）
  - `queue_position`: 在队列中的位置
  - `created_at`: 创建时间

**注意**: 
- `video_id` 从 URL 中提取，可用于准确匹配任务，避免 URL 格式差异导致对比失败
- `doc_hash` 只有在任务完成后才会生成

### 3. SSE 流式任务更新
**端点**: `GET /api/tasks/{task_id}/stream`  
**描述**: 通过 SSE 实时接收任务进度更新  
**认证**: 需要 Token（支持查询参数 `?token=xxx`）  

**查询参数**:
- `token`: 认证令牌（EventSource 不支持自定义 Header）

**响应**: Server-Sent Events (SSE)

**事件类型**:

**message 事件** - 任务进度:
```json
{
  "type": "log|progress|result|error",
  "message": "日志消息",
  "percentage": 50
}
```

**heartbeat 事件** - 保持连接:
```json
{
  "type": "heartbeat"
}
```

### 4. 获取任务状态
**端点**: `GET /api/tasks/{task_id}/status`  
**描述**: 获取任务状态（不使用流式传输）  
**认证**: 无需认证  

**响应**:
```json
{
  "task_id": "uuid-string",
  "status": "pending|running|completed|error",
  "progress": 50,
  "logs": ["最近登录消息..."],
  "completed": false,
  "failed": false
}
```

### 5. 获取任务结果（管理员）
**端点**: `GET /api/admin/tasks/{task_id}/result`  
**描述**: 获取已完成任务的结果文件  
**认证**: 需要 Token  

**响应**: Markdown 文件下载

---

## Ultra Deep 深度分析 API

### 1. 获取 Ultra Deep 状态
**端点**: `GET /api/article/{doc_hash}/ultra-deep/status`  
**描述**: 查询文章的 Ultra 深度分析状态  
**认证**: 无需认证  

**查询参数**:
- `version`: 可选版本号

**响应**:
```json
{
  "exists": true,
  "status": "pending|processing|completed|failed",
  "task_id": "uuid-string",
  "version": 1,
  "result": {
    "generated_at": "2024-11-02T10:00:00"
  }
}
```

### 2. 触发 Ultra Deep 分析
**端点**: `POST /api/article/{doc_hash}/ultra-deep`  
**描述**: 触发文章的 Ultra 深度分析任务  
**认证**: 需要 Token  

**查询参数**:
- `version`: 可选版本号

**响应**:
```json
{
  "task_id": "uuid-string",
  "message": "Ultra 深度分析任务已创建",
  "status": "queued"
}
```

---

## 系统管理 API

### 1. 健康检查
**端点**: `GET /api/health`  
**描述**: 检查系统健康状态（包括 Cookie Manager）  
**认证**: 无需认证  

**响应**:
```json
{
  "status": "healthy|degraded|error",
  "timestamp": "2024-11-02T10:00:00",
  "components": {
    "api": {
      "status": "healthy",
      "message": "API 服务运行正常"
    },
    "cookies": {
      "status": "healthy|warning|error",
      "service_running": true,
      "file_status": "ok",
      "content_valid": true,
      "issues": [],
      "warnings": []
    }
  }
}
```

### 2. 获取配置信息
**端点**: `GET /api/config`  
**描述**: 获取前端所需的配置项  
**认证**: 无需认证  

**响应**:
```json
{
  "tts_audio_button_enabled": true
}
```

### 3. 获取环境信息
**端点**: `GET /api/env`  
**描述**: 获取当前运行环境信息  
**认证**: 无需认证  

**响应**:
```json
{
  "environment": "development|production",
  "project_root": "/path/to/project",
  "host": "hostname",
  "port": "8001",
  "version": "0.1.0",
  "is_development": true
}
```

### 4. 刷新缓存（管理员）
**端点**: `POST /api/admin/refresh-cache`  
**描述**: 手动刷新文档哈希映射缓存  
**认证**: 需要 Token  

**响应**:
```json
{
  "message": "服务器端缓存已成功刷新。"
}
```

### 5. Cookie 状态（管理员）
**端点**: `GET /api/admin/cookie-status`  
**描述**: 获取详细的 Cookie 健康状态和建议  
**认证**: 需要 Token  

**响应**:
```json
{
  "overall_status": "healthy|warning|error",
  "timestamp": "2024-11-02T10:00:00",
  "service": {
    "running": true,
    "pid": 12345,
    "status": "active"
  },
  "file": {
    "exists": true,
    "path": "/path/to/cookies.txt",
    "size": 1024,
    "modified": "2024-11-02T10:00:00",
    "status": "ok"
  },
  "content": {
    "valid": true,
    "cookie_count": 10,
    "has_session": true,
    "domains": ["youtube.com"]
  },
  "issues": [],
  "warnings": [],
  "recommendations": [
    "建议定期检查 Cookie 有效性"
  ]
}
```

---

## 数据模型

### 文档版本信息
```typescript
interface VersionInfo {
  filename: string;
  version: number;
  created_at: string;
  title_cn: string;
  title_en: string;
}
```

### 文档摘要信息
```typescript
interface SummaryInfo {
  filename: string;
  title_cn: string;
  title_en: string;
  size: number;
  word_count: number;
  created_at: number;
  modified_at: number;
  upload_date: string;
  video_url: string;
  is_reinvent: boolean;
  course_code?: string;
  level?: number;
  hash: string;
  version: number;
  is_pdf: boolean;
  content_type: "YouTube视频" | "PDF文档";
}
```

### 任务状态
```typescript
type TaskStatus = "pending" | "processing" | "completed" | "failed" | "skipped";
```

### TTS 任务信息
```typescript
interface TTSTaskInfo {
  task_id: string;
  article_hash: string;
  source_file: string;
  status: TaskStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  retry_count: number;
  error_message?: string;
  audio_hash?: string;
}
```

---

## 使用示例

### 1. 完整的分析流程

```javascript
// 1. 登录获取 Token
const loginRes = await fetch('/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'password'
  })
});
const { token } = await loginRes.json();

// 2. 提交分析任务
const analyzeRes = await fetch('/summarize', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    url: 'https://www.youtube.com/watch?v=xxxxx'
  })
});
const { task_id } = await analyzeRes.json();

// 3. 通过 SSE 接收进度
const eventSource = new EventSource(
  `/api/tasks/${task_id}/stream?token=${token}`
);

eventSource.addEventListener('message', (e) => {
  const data = JSON.parse(e.data);
  console.log('进度:', data);
  
  if (data.type === 'result') {
    console.log('任务完成');
    eventSource.close();
  }
});
```

### 2. TTS 流式播放

```javascript
// 1. 流式生成音频
const response = await fetch('/api/tts/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    article_hash: 'doc-hash',
    text: '要合成的文本内容'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
const audioContext = new AudioContext();
const chunks = [];

// 2. 接收并播放音频块
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  const lines = text.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      
      if (data.data) {
        // 解码并播放音频块
        const pcmData = atob(data.data);
        chunks.push(pcmData);
        // ... 播放逻辑
      }
    }
  }
}
```

### 3. 文档管理

```javascript
// 1. 获取文档列表
const listRes = await fetch('/api/public/summaries');
const { summaries } = await listRes.json();

// 2. 获取特定文档
const docRes = await fetch(`/api/public/doc/${summaries[0].hash}`);
const doc = await docRes.json();

// 3. 下载 PDF
window.location.href = `/api/public/summaries/${doc.filename}/pdf`;
```

---

## 错误处理

所有 API 在发生错误时返回标准 HTTP 错误码：

- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证或 Token 无效
- `404 Not Found`: 资源不存在
- `413 Payload Too Large`: 文件过大
- `500 Internal Server Error`: 服务器内部错误

错误响应格式：
```json
{
  "detail": "错误详细信息"
}
```

---

## 技术特性

### 高性能特性
- ✅ 异步非阻塞 I/O（FastAPI + asyncio）
- ✅ 流式响应（SSE）支持实时进度
- ✅ 音频缓存系统（减少重复生成）
- ✅ 文件系统监控（自动更新缓存）
- ✅ 并发任务处理

### 安全特性
- ✅ Bearer Token 认证
- ✅ 文件名路径验证（防止目录遍历）
- ✅ 文件大小限制
- ✅ CORS 配置

### 可扩展性
- ✅ 版本管理（支持同一文档多版本）
- ✅ 模块化服务设计
- ✅ 可配置的模型切换
- ✅ 插件式 TTS 服务

---

## 配置说明

关键环境变量（`.env` 文件）：

```bash
# 认证
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_password

# AI 模型
GEMINI_API_KEY=your_api_key
PREFERRED_MODEL=gemini-2.0-flash-exp

# 文件限制
MAX_TEXT_FILE_SIZE=10485760  # 10MB
MAX_BINARY_FILE_SIZE=52428800  # 50MB

# TTS 配置
TTS_AUDIO_BUTTON_ENABLED=true
TTS_PREGENERATE_ENABLED=false

# 可视化解读
VISUAL_INTERPRETATION_ENABLED=true

# 日志
LOG_LEVEL=INFO
```

---

## 性能建议

### 客户端最佳实践

1. **使用 SSE 而非轮询**: 任务进度用 SSE 实时接收
2. **启用音频缓存**: `use_cache=true` 提高响应速度
3. **流式音频播放**: 使用 `/api/tts/stream` 减少等待时间
4. **批量请求**: 列表查询时使用分页参数

### 服务端优化

1. **文件系统缓存**: 自动维护哈希映射，避免重复扫描
2. **音频预生成**: 后台异步生成常用音频
3. **连接池管理**: 复用 HTTP 连接和模型客户端
4. **异步任务队列**: 避免阻塞主线程

---

## 版本历史

- **v0.1.1** (2025-12-10): 架构重构版本
  - 新增 Ultra Deep 深度分析 API
  - 新增任务状态查询 API
  - 补全 TTS 队列统计和任务列表 API
  - 分层架构重构

- **v0.1.0** (2024-11-02): 初始版本
  - YouTube 视频分析
  - PDF/文档分析
  - TTS 语音合成
  - 完整的任务管理系统

---

## 支持与反馈

如需帮助或报告问题，请参考项目文档或联系开发团队。
