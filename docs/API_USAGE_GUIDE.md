# Reinvent Insight API 使用文档

> 版本: v1.0  
> 更新时间: 2025-12-04  
> 基础 URL: `http://your-server:8001`

---

## 📚 目录

1. [快速开始](#快速开始)
2. [认证系统](#认证系统)
3. [分析任务 API](#分析任务-api)
4. [文档管理 API](#文档管理-api)
5. [TTS 语音合成 API](#tts-语音合成-api)
6. [队列管理 API](#队列管理-api)
7. [系统管理 API](#系统管理-api)
8. [错误处理](#错误处理)
9. [最佳实践](#最佳实践)

---

## 🚀 快速开始

### 1. 基本工作流程

```
登录获取 Token → 提交分析任务 → 实时接收进度 → 获取结果
```

### 2. 完整示例

```python
import requests
import json

# 基础配置
BASE_URL = "http://localhost:8001"
USERNAME = "admin"
PASSWORD = "your_password"

# 1. 登录获取 Token
login_response = requests.post(
    f"{BASE_URL}/login",
    json={
        "username": USERNAME,
        "password": PASSWORD
    }
)
token = login_response.json()["token"]
print(f"✅ 登录成功，Token: {token[:20]}...")

# 2. 提交分析任务
analyze_response = requests.post(
    f"{BASE_URL}/summarize",
    headers={"Authorization": f"Bearer {token}"},
    json={"url": "https://www.youtube.com/watch?v=xxxxx"},
    params={"priority": 1}  # 可选：设置优先级
)
task_id = analyze_response.json()["task_id"]
print(f"✅ 任务已创建: {task_id}")

# 3. 通过 SSE 接收实时进度
from sseclient import SSEClient

sse_url = f"{BASE_URL}/api/tasks/{task_id}/stream?token={token}"
messages = SSEClient(sse_url)

for msg in messages:
    if msg.event == 'message':
        data = json.loads(msg.data)
        print(f"进度: {data.get('message', data.get('type'))}")
        
        if data.get('type') == 'result':
            print(f"✅ 任务完成!")
            print(f"文档 Hash: {data.get('hash')}")
            break

# 4. 获取文档内容
doc_hash = data['hash']
doc_response = requests.get(f"{BASE_URL}/api/public/doc/{doc_hash}")
document = doc_response.json()

print(f"标题: {document['title_cn']}")
print(f"内容长度: {len(document['content'])} 字符")
```

---

## 🔐 认证系统

### 登录

**端点**: `POST /login`  
**认证**: 无需认证  
**说明**: 验证用户名密码，返回 Bearer Token

**请求体**:
```json
{
  "username": "admin",
  "password": "your_password"
}
```

**响应**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**使用示例**:

```bash
# cURL
curl -X POST "http://localhost:8001/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Python
import requests

response = requests.post(
    "http://localhost:8001/login",
    json={"username": "admin", "password": "your_password"}
)
token = response.json()["token"]

# JavaScript
const response = await fetch('http://localhost:8001/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'your_password'
  })
});
const { token } = await response.json();
```

### 使用 Token

在后续请求中，需要在 Header 中携带 Token：

```
Authorization: Bearer YOUR_TOKEN
```

---

## 📊 分析任务 API

### 1. YouTube 视频分析

**端点**: `POST /summarize`  
**认证**: 需要 Token  
**说明**: 分析 YouTube 视频，生成深度解读

**查询参数**:
- `priority` (可选): 优先级 (0-3)
  - `0`: LOW - 低优先级
  - `1`: NORMAL - 普通优先级（默认）
  - `2`: HIGH - 高优先级
  - `3`: URGENT - 紧急优先级

**请求体**:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "task_id": "可选，用于重新连接"
}
```

**响应**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "任务已加入队列（优先级: NORMAL，排队: 3 个任务），请连接 WebSocket。",
  "status": "created"
}
```

**使用示例**:

```bash
# cURL - 普通优先级
curl -X POST "http://localhost:8001/summarize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# cURL - 高优先级
curl -X POST "http://localhost:8001/summarize?priority=2" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

```python
# Python
def analyze_video(url, priority=1):
    response = requests.post(
        f"{BASE_URL}/summarize",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": url},
        params={"priority": priority}
    )
    return response.json()

# 普通优先级
result = analyze_video("https://www.youtube.com/watch?v=xxxxx")

# 紧急优先级
urgent_result = analyze_video("https://www.youtube.com/watch?v=xxxxx", priority=3)
```

### 2. PDF 文档分析

**端点**: `POST /analyze-pdf`  
**认证**: 需要 Token  
**说明**: 使用 Gemini 多模态能力分析 PDF 文件

**表单参数**:
- `file` (必需): PDF 文件
- `title` (可选): 文档标题
- `priority` (可选): 优先级 (0-3)

**响应**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "message": "PDF分析任务已加入队列（排队: 1 个任务），请连接 WebSocket。",
  "status": "created"
}
```

**使用示例**:

```bash
# cURL
curl -X POST "http://localhost:8001/analyze-pdf?priority=1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "title=我的文档"
```

```python
# Python
def analyze_pdf(file_path, title=None, priority=1):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {}
        if title:
            data['title'] = title
        
        response = requests.post(
            f"{BASE_URL}/analyze-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
            params={"priority": priority}
        )
    return response.json()

result = analyze_pdf("/path/to/document.pdf", "技术白皮书")
```

### 3. 通用文档分析

**端点**: `POST /analyze-document`  
**认证**: 需要 Token  
**说明**: 分析多种格式文档（TXT, MD, PDF, DOCX）

**支持格式**: `.txt`, `.md`, `.pdf`, `.docx`

**文件大小限制**:
- 文本文件（TXT/MD）: 10MB
- 二进制文件（PDF/DOCX）: 50MB

**表单参数**:
- `file` (必需): 文档文件
- `title` (可选): 文档标题
- `priority` (可选): 优先级 (0-3)

**响应**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440002",
  "message": "文档分析任务已加入队列（TXT，排队: 0 个任务），请连接 WebSocket。",
  "status": "created"
}
```

**使用示例**:

```python
# Python
def analyze_document(file_path, title=None, priority=1):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {}
        if title:
            data['title'] = title
        
        response = requests.post(
            f"{BASE_URL}/analyze-document",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
            params={"priority": priority}
        )
    return response.json()

# 分析 Markdown 文件
result = analyze_document("/path/to/article.md", "技术文章")

# 分析 Word 文档
result = analyze_document("/path/to/report.docx", "季度报告", priority=2)
```

### 4. 实时进度监控（SSE）

**端点**: `GET /api/tasks/{task_id}/stream`  
**认证**: 需要 Token（通过查询参数）  
**说明**: 通过 Server-Sent Events 实时接收任务进度

**查询参数**:
- `token` (必需): 认证令牌

**事件类型**:

| 事件 | 说明 | 数据格式 |
|------|------|---------|
| `message` | 进度消息 | `{type: "log", message: "..."}` |
| `message` | 进度更新 | `{type: "progress", progress: 50, message: "..."}` |
| `message` | 任务完成 | `{type: "result", title: "...", summary: "...", hash: "..."}` |
| `message` | 任务失败 | `{type: "error", message: "...", error_type: "..."}` |
| `heartbeat` | 心跳保持连接 | `{type: "heartbeat"}` |

**使用示例**:

```python
# Python - 使用 sseclient-py
from sseclient import SSEClient
import json

def monitor_task(task_id, token):
    url = f"{BASE_URL}/api/tasks/{task_id}/stream?token={token}"
    messages = SSEClient(url)
    
    for msg in messages:
        if msg.event == 'message':
            data = json.loads(msg.data)
            
            if data['type'] == 'log':
                print(f"📝 {data['message']}")
            elif data['type'] == 'progress':
                print(f"⏳ 进度: {data['progress']}% - {data['message']}")
            elif data['type'] == 'result':
                print(f"✅ 任务完成!")
                print(f"   标题: {data['title']}")
                print(f"   Hash: {data['hash']}")
                return data
            elif data['type'] == 'error':
                print(f"❌ 错误: {data['message']}")
                return None

result = monitor_task(task_id, token)
```

```javascript
// JavaScript - 使用 EventSource
function monitorTask(taskId, token) {
  const url = `${BASE_URL}/api/tasks/${taskId}/stream?token=${token}`;
  const eventSource = new EventSource(url);
  
  eventSource.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
      case 'log':
        console.log('📝', data.message);
        break;
      case 'progress':
        console.log(`⏳ 进度: ${data.progress}%`);
        updateProgressBar(data.progress);
        break;
      case 'result':
        console.log('✅ 任务完成!', data);
        eventSource.close();
        handleResult(data);
        break;
      case 'error':
        console.error('❌ 错误:', data.message);
        eventSource.close();
        break;
    }
  });
  
  eventSource.addEventListener('heartbeat', () => {
    console.log('💓 心跳');
  });
}
```

---

## 📄 文档管理 API

### 1. 获取文档列表

**端点**: `GET /api/public/summaries`  
**认证**: 无需认证  
**说明**: 获取所有已生成的深度解读列表

**响应**:
```json
{
  "summaries": [
    {
      "filename": "video_title.md",
      "title_cn": "中文标题",
      "title_en": "English Title",
      "size": 123456,
      "word_count": 10000,
      "created_at": 1701234567.89,
      "modified_at": 1701234567.89,
      "upload_date": "20241102",
      "video_url": "https://www.youtube.com/watch?v=xxxxx",
      "is_reinvent": false,
      "course_code": "ABC123",
      "level": 300,
      "hash": "doc-hash-string",
      "version": 1,
      "is_pdf": false,
      "content_type": "YouTube视频"
    }
  ]
}
```

**使用示例**:

```python
# Python
def get_all_documents():
    response = requests.get(f"{BASE_URL}/api/public/summaries")
    return response.json()['summaries']

documents = get_all_documents()
for doc in documents:
    print(f"{doc['title_cn']} - {doc['word_count']} 字")
```

### 2. 获取文档内容（按文件名）

**端点**: `GET /api/public/summaries/{filename}`  
**认证**: 无需认证  
**说明**: 获取指定文档的完整内容

**响应**:
```json
{
  "filename": "video_title.md",
  "title": "标题",
  "title_cn": "中文标题",
  "title_en": "English Title",
  "content": "# 标题\n\n文档内容...",
  "video_url": "https://...",
  "versions": [
    {
      "filename": "video_title_v1.md",
      "version": 1,
      "created_at": "2024-11-02T10:00:00",
      "title_cn": "中文标题",
      "title_en": "English Title"
    }
  ]
}
```

**使用示例**:

```python
# Python
def get_document_by_filename(filename):
    response = requests.get(
        f"{BASE_URL}/api/public/summaries/{filename}"
    )
    return response.json()

doc = get_document_by_filename("video_title.md")
print(doc['content'])
```

### 3. 获取文档内容（按 Hash）

**端点**: `GET /api/public/doc/{doc_hash}`  
**认证**: 无需认证  
**说明**: 通过文档 Hash 获取最新版本内容

**使用示例**:

```python
# Python
def get_document_by_hash(doc_hash):
    response = requests.get(f"{BASE_URL}/api/public/doc/{doc_hash}")
    return response.json()

doc = get_document_by_hash("abc123def456")
```

### 4. 获取特定版本

**端点**: `GET /api/public/doc/{doc_hash}/{version}`  
**认证**: 无需认证  
**说明**: 获取文档的指定版本

**使用示例**:

```python
# Python
def get_document_version(doc_hash, version):
    response = requests.get(
        f"{BASE_URL}/api/public/doc/{doc_hash}/{version}"
    )
    return response.json()

# 获取第 2 版本
doc_v2 = get_document_version("abc123def456", 2)
```

### 5. 下载 Markdown 文件

**端点**: `GET /api/public/summaries/{filename}/markdown`  
**认证**: 无需认证  
**说明**: 下载去除元数据的 Markdown 文件

**使用示例**:

```python
# Python
def download_markdown(filename, save_path):
    response = requests.get(
        f"{BASE_URL}/api/public/summaries/{filename}/markdown"
    )
    
    with open(save_path, 'wb') as f:
        f.write(response.content)
    
    print(f"✅ 已下载到: {save_path}")

download_markdown("video_title.md", "/path/to/save.md")
```

### 6. 下载 PDF 文件

**端点**: `GET /api/public/summaries/{filename}/pdf`  
**认证**: 无需认证  
**说明**: 生成并下载 PDF 格式文档

**使用示例**:

```python
# Python
def download_pdf(filename, save_path):
    response = requests.get(
        f"{BASE_URL}/api/public/summaries/{filename}/pdf"
    )
    
    with open(save_path, 'wb') as f:
        f.write(response.content)
    
    print(f"✅ PDF 已下载到: {save_path}")

download_pdf("video_title.md", "/path/to/save.pdf")
```

### 7. 获取可视化解读

**端点**: `GET /api/article/{doc_hash}/visual`  
**认证**: 无需认证  
**说明**: 获取文章的可视化 HTML 解读

**查询参数**:
- `version` (可选): 版本号

**使用示例**:

```python
# Python
def get_visual_interpretation(doc_hash, version=None):
    params = {'version': version} if version else {}
    response = requests.get(
        f"{BASE_URL}/api/article/{doc_hash}/visual",
        params=params
    )
    return response.text  # HTML 内容

html_content = get_visual_interpretation("abc123def456")
```

### 8. 查询可视化状态

**端点**: `GET /api/article/{doc_hash}/visual/status`  
**认证**: 无需认证  

**响应**:
```json
{
  "status": "completed",
  "file": "video_title_visual.html",
  "generated_at": "2024-11-02T10:00:00",
  "version": 1
}
```

---

## 🎙️ TTS 语音合成 API

### 1. 生成 TTS 音频（非流式）

**端点**: `POST /api/tts/generate`  
**认证**: 无需认证  
**说明**: 生成完整 TTS 音频，优先返回缓存

**请求体**:
```json
{
  "article_hash": "abc123def456",
  "text": "要合成的文本内容",
  "voice": "Kai",
  "language": "Chinese",
  "use_cache": true,
  "skip_code_blocks": true
}
```

**响应**:
```json
{
  "audio_url": "/api/tts/cache/audio_hash_123",
  "duration": 120.5,
  "cached": true,
  "voice": "Kai",
  "language": "Chinese"
}
```

**使用示例**:

```python
# Python
def generate_tts(text, article_hash):
    response = requests.post(
        f"{BASE_URL}/api/tts/generate",
        json={
            "article_hash": article_hash,
            "text": text,
            "voice": "Kai",
            "language": "Chinese"
        }
    )
    result = response.json()
    
    print(f"音频 URL: {result['audio_url']}")
    print(f"时长: {result['duration']}秒")
    print(f"是否缓存: {result['cached']}")
    
    return result

audio = generate_tts("你好，世界！", "doc_hash_123")
```

### 2. 流式生成 TTS 音频（SSE）

**端点**: `POST /api/tts/stream`  
**认证**: 无需认证  
**说明**: 实时流式生成音频，支持边生成边播放

**请求体**: 同非流式

**SSE 事件**:

**chunk 事件** - 音频数据块:
```json
{
  "index": 1,
  "data": "base64_encoded_pcm_data",
  "chunk_size": 48000,
  "total_bytes": 96000,
  "buffered_duration": 2.0,
  "from_cache": false
}
```

**complete 事件** - 生成完成:
```json
{
  "audio_url": "/api/tts/cache/audio_hash_123",
  "duration": 120.5,
  "chunk_count": 60,
  "total_bytes": 2880000,
  "audio_hash": "audio_hash_123"
}
```

**使用示例**:

```python
# Python
import base64

def stream_tts(text, article_hash):
    response = requests.post(
        f"{BASE_URL}/api/tts/stream",
        json={
            "article_hash": article_hash,
            "text": text
        },
        stream=True
    )
    
    audio_chunks = []
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                
                if 'data' in data:
                    # 解码音频数据
                    pcm_data = base64.b64decode(data['data'])
                    audio_chunks.append(pcm_data)
                    print(f"收到音频块 {data['index']}, "
                          f"已缓冲 {data['buffered_duration']:.1f}秒")
    
    return audio_chunks

chunks = stream_tts("这是一段很长的文本...", "doc_hash_123")
```

### 3. 获取缓存音频

**端点**: `GET /api/tts/cache/{audio_hash}`  
**认证**: 无需认证  
**说明**: 获取已缓存的音频文件

**响应**: WAV 格式音频流

**使用示例**:

```python
# Python
def download_audio(audio_hash, save_path):
    response = requests.get(f"{BASE_URL}/api/tts/cache/{audio_hash}")
    
    with open(save_path, 'wb') as f:
        f.write(response.content)
    
    print(f"✅ 音频已下载: {save_path}")

download_audio("audio_hash_123", "/path/to/audio.wav")
```

### 4. 查询 TTS 状态

**端点**: `GET /api/tts/status/{article_hash}`  
**认证**: 无需认证  

**响应**:
```json
{
  "has_audio": true,
  "audio_url": "/api/tts/cache/audio_hash_123",
  "duration": 120.5,
  "status": "ready",
  "voice": "Kai",
  "generated_at": "2024-11-02T10:00:00",
  "has_partial": false,
  "progress_percent": 0
}
```

**状态值**:
- `ready`: 音频已生成完成
- `processing`: 正在生成中
- `none`: 未生成

**使用示例**:

```python
# Python
def check_tts_status(article_hash):
    response = requests.get(
        f"{BASE_URL}/api/tts/status/{article_hash}"
    )
    status = response.json()
    
    if status['status'] == 'ready':
        print(f"✅ 音频已就绪: {status['audio_url']}")
        return status['audio_url']
    elif status['status'] == 'processing':
        print(f"⏳ 正在生成中: {status['progress_percent']}%")
        return None
    else:
        print("❌ 音频未生成")
        return None

audio_url = check_tts_status("doc_hash_123")
```

### 5. 手动触发 TTS 预生成

**端点**: `POST /api/tts/pregenerate`  
**认证**: 无需认证  

**请求体**:
```json
{
  "article_hash": "abc123def456",
  "filename": "video_title.md"
}
```

**响应**:
```json
{
  "task_id": "tts_task_123",
  "status": "queued",
  "message": "任务已添加到队列: tts_task_123"
}
```

---

## ⚙️ 队列管理 API

### 1. 获取队列统计

**端点**: `GET /api/queue/stats`  
**认证**: 无需认证  
**说明**: 获取任务队列的实时统计信息

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

**使用示例**:

```python
# Python
def get_queue_stats():
    response = requests.get(f"{BASE_URL}/api/queue/stats")
    return response.json()

stats = get_queue_stats()
print(f"队列长度: {stats['queue_size']}/{stats['max_queue_size']}")
print(f"处理中: {stats['current_processing']}/{stats['max_workers']}")
print(f"成功率: {stats['total_success']}/{stats['total_processed']}")
```

**实时监控示例**:

```python
import time

def monitor_queue(interval=5):
    """实时监控队列状态"""
    while True:
        stats = get_queue_stats()
        
        print(f"\r队列: {stats['queue_size']:2d} | "
              f"处理中: {stats['current_processing']} | "
              f"成功: {stats['total_success']:3d} | "
              f"失败: {stats['total_failed']:2d}",
              end='', flush=True)
        
        time.sleep(interval)

# 运行监控
monitor_queue()
```

### 2. 获取 TTS 队列统计

**端点**: `GET /api/tts/queue/stats`  
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

### 3. 获取 TTS 任务列表

**端点**: `GET /api/tts/queue/tasks`  
**认证**: 无需认证  

**查询参数**:
- `status` (可选): 按状态筛选 (pending/processing/completed/failed/skipped)
- `limit` (可选): 返回数量限制，默认 50

**响应**:
```json
{
  "tasks": [
    {
      "task_id": "tts_task_123",
      "article_hash": "doc_hash",
      "source_file": "video.md",
      "status": "completed",
      "created_at": "2024-11-02T10:00:00",
      "completed_at": "2024-11-02T10:02:30",
      "audio_hash": "audio_hash_123"
    }
  ],
  "total": 100
}
```

---

## 🛠️ 系统管理 API

### 1. 健康检查

**端点**: `GET /api/health`  
**认证**: 无需认证  

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-11-02T10:00:00",
  "components": {
    "api": {
      "status": "healthy",
      "message": "API 服务运行正常"
    },
    "cookies": {
      "status": "healthy",
      "service_running": true,
      "file_status": "ok"
    }
  }
}
```

### 2. 获取配置信息

**端点**: `GET /api/config`  
**认证**: 无需认证  

**响应**:
```json
{
  "tts_audio_button_enabled": true
}
```

### 3. 获取环境信息

**端点**: `GET /api/env`  
**认证**: 无需认证  

**响应**:
```json
{
  "environment": "development",
  "project_root": "/path/to/project",
  "version": "0.1.0",
  "is_development": true
}
```

### 4. 刷新缓存（管理员）

**端点**: `POST /api/admin/refresh-cache`  
**认证**: 需要 Token  

**响应**:
```json
{
  "message": "服务器端缓存已成功刷新。"
}
```

---

## ❌ 错误处理

### 错误响应格式

所有错误都返回标准格式：

```json
{
  "detail": "错误详细信息"
}
```

### HTTP 状态码

| 状态码 | 说明 | 处理建议 |
|--------|------|---------|
| 200 | 成功 | - |
| 400 | 请求参数错误 | 检查请求参数 |
| 401 | 未认证或 Token 无效 | 重新登录获取 Token |
| 404 | 资源不存在 | 检查资源 ID 或路径 |
| 413 | 文件过大 | 压缩文件或分段处理 |
| 503 | 队列已满 | 等待后重试 |
| 500 | 服务器内部错误 | 查看日志或联系管理员 |

### 错误处理示例

```python
# Python
import requests
from requests.exceptions import HTTPError

def safe_request(url, **kwargs):
    try:
        response = requests.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    except HTTPError as e:
        status_code = e.response.status_code
        
        if status_code == 401:
            print("❌ Token 已失效，请重新登录")
            # 重新登录逻辑
        elif status_code == 404:
            print("❌ 资源不存在")
        elif status_code == 503:
            print("⏳ 队列已满，10秒后重试...")
            time.sleep(10)
            return safe_request(url, **kwargs)  # 重试
        else:
            print(f"❌ 请求失败: {e.response.json()['detail']}")
        
        return None
```

---

## 💡 最佳实践

### 1. Token 管理

```python
class APIClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.token_file = Path.home() / ".reinvent_token"
    
    def login(self):
        """登录并缓存 Token"""
        response = requests.post(
            f"{self.base_url}/login",
            json={"username": self.username, "password": self.password}
        )
        self.token = response.json()['token']
        
        # 缓存 Token
        with open(self.token_file, 'w') as f:
            json.dump({'token': self.token}, f)
        
        return self.token
    
    def get_token(self):
        """获取 Token（优先从缓存读取）"""
        if self.token:
            return self.token
        
        # 尝试从缓存加载
        if self.token_file.exists():
            with open(self.token_file, 'r') as f:
                data = json.load(f)
                self.token = data.get('token')
                
                # 验证 Token 是否有效
                if self.validate_token():
                    return self.token
        
        # Token 无效，重新登录
        return self.login()
    
    def validate_token(self):
        """验证 Token 是否有效"""
        try:
            response = requests.get(
                f"{self.base_url}/api/env",
                timeout=3
            )
            return response.status_code == 200
        except:
            return False
```

### 2. 批量处理

```python
def batch_analyze(urls, priority=1, max_concurrent=3):
    """批量分析视频"""
    import asyncio
    import aiohttp
    
    async def analyze_one(session, url):
        async with session.post(
            f"{BASE_URL}/summarize",
            headers={"Authorization": f"Bearer {token}"},
            json={"url": url},
            params={"priority": priority}
        ) as response:
            return await response.json()
    
    async def batch():
        async with aiohttp.ClientSession() as session:
            tasks = [analyze_one(session, url) for url in urls]
            return await asyncio.gather(*tasks)
    
    return asyncio.run(batch())

# 批量分析
urls = [
    "https://www.youtube.com/watch?v=video1",
    "https://www.youtube.com/watch?v=video2",
    "https://www.youtube.com/watch?v=video3"
]
results = batch_analyze(urls, priority=0)  # 低优先级批量任务
```

### 3. 错误重试

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def analyze_with_retry(url):
    """带重试的分析"""
    response = requests.post(
        f"{BASE_URL}/summarize",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": url}
    )
    
    if response.status_code == 503:
        raise Exception("队列已满，重试...")
    
    response.raise_for_status()
    return response.json()
```

### 4. 进度回调

```python
def analyze_with_callback(url, on_progress=None, on_complete=None):
    """带回调的分析"""
    # 提交任务
    response = requests.post(
        f"{BASE_URL}/summarize",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": url}
    )
    task_id = response.json()['task_id']
    
    # 监控进度
    sse_url = f"{BASE_URL}/api/tasks/{task_id}/stream?token={token}"
    messages = SSEClient(sse_url)
    
    for msg in messages:
        if msg.event == 'message':
            data = json.loads(msg.data)
            
            if data['type'] == 'progress' and on_progress:
                on_progress(data['progress'], data['message'])
            
            elif data['type'] == 'result' and on_complete:
                on_complete(data)
                break

# 使用回调
def show_progress(progress, message):
    print(f"⏳ {progress}%: {message}")

def handle_result(result):
    print(f"✅ 完成: {result['title']}")

analyze_with_callback(
    "https://www.youtube.com/watch?v=xxxxx",
    on_progress=show_progress,
    on_complete=handle_result
)
```

---

## 📚 完整示例项目

### Python SDK 封装

```python
# reinvent_client.py
import requests
import json
from pathlib import Path
from sseclient import SSEClient

class ReinventInsightClient:
    """Reinvent Insight API 客户端"""
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
    
    def login(self):
        """登录"""
        response = requests.post(
            f"{self.base_url}/login",
            json={"username": self.username, "password": self.password}
        )
        response.raise_for_status()
        self.token = response.json()['token']
        return self.token
    
    def analyze_youtube(self, url, priority=1, callback=None):
        """分析 YouTube 视频"""
        if not self.token:
            self.login()
        
        # 提交任务
        response = requests.post(
            f"{self.base_url}/summarize",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"url": url},
            params={"priority": priority}
        )
        response.raise_for_status()
        task_id = response.json()['task_id']
        
        # 监控进度
        if callback:
            return self._monitor_task(task_id, callback)
        
        return task_id
    
    def _monitor_task(self, task_id, callback):
        """监控任务进度"""
        sse_url = f"{self.base_url}/api/tasks/{task_id}/stream?token={self.token}"
        messages = SSEClient(sse_url)
        
        for msg in messages:
            if msg.event == 'message':
                data = json.loads(msg.data)
                
                if callback:
                    callback(data)
                
                if data['type'] in ['result', 'error']:
                    return data
    
    def get_document(self, doc_hash):
        """获取文档"""
        response = requests.get(f"{self.base_url}/api/public/doc/{doc_hash}")
        response.raise_for_status()
        return response.json()
    
    def list_documents(self):
        """获取文档列表"""
        response = requests.get(f"{self.base_url}/api/public/summaries")
        response.raise_for_status()
        return response.json()['summaries']
    
    def get_queue_stats(self):
        """获取队列统计"""
        response = requests.get(f"{self.base_url}/api/queue/stats")
        response.raise_for_status()
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = ReinventInsightClient(
        base_url="http://localhost:8001",
        username="admin",
        password="your_password"
    )
    
    # 分析视频
    def on_progress(data):
        if data['type'] == 'progress':
            print(f"⏳ {data['progress']}%")
        elif data['type'] == 'result':
            print(f"✅ 完成: {data['title']}")
    
    result = client.analyze_youtube(
        "https://www.youtube.com/watch?v=xxxxx",
        priority=2,
        callback=on_progress
    )
```

---

## 🎉 总结

本 API 提供完整的文档分析和管理功能：

✅ **多种输入源**: YouTube、PDF、TXT、MD、DOCX  
✅ **优先级队列**: 4 级优先级控制  
✅ **实时进度**: SSE 流式推送  
✅ **TTS 合成**: 文字转语音  
✅ **版本管理**: 支持多版本文档  
✅ **公开访问**: 大部分 API 无需认证  

**相关资源**:
- [Worker Pool 使用指南](WORKER_POOL_GUIDE.md)
- [API 总结文档](../API_SUMMARY.md)
- [配置示例](../.env.example)

祝使用愉快！🚀
