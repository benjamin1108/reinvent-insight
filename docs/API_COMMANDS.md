# Reinvent Insight API 指令手册

> 域名: `https://ri.mindfree.top`

---

## 认证

```bash
# 登录获取 Token
curl -X POST https://ri.mindfree.top/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"你的密码"}'

curl -X POST https://ri-dev.mindfree.top/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"你的密码"}'

# 返回示例: {"token":"xxx","username":"admin","role":"admin"}
# 后续请求需要带上 Header: Authorization: Bearer xxx
```

---

## 视频解读任务

```bash
# 提交 YouTube 视频解读（priority: 0-3, 3最高）
curl -X POST "https://ri.mindfree.top/summarize?priority=1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}'

# 强制重新解读（忽略已存在）
curl -X POST "https://ri.mindfree.top/summarize?force=true" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}'

# 查看任务状态
curl https://ri.mindfree.top/api/tasks/{task_id}/status

# SSE 实时进度流
curl "https://ri.mindfree.top/api/tasks/{task_id}/stream?token=YOUR_TOKEN"
```

---

## 文档查询

```bash
# 公开文档列表（无需认证）
curl https://ri.mindfree.top/api/public/summaries

# 分页查询
curl "https://ri.mindfree.top/api/public/summaries/paginated?page=1&page_size=20"

# 查询 video_id 是否已有解读
curl https://ri.mindfree.top/api/public/summary/{video_id}

# 通过 doc_hash 获取文档
curl https://ri.mindfree.top/api/public/doc/{doc_hash}
```

---

## Ultra DeepInsight

```bash
# 查询 Ultra 状态
curl https://ri.mindfree.top/api/article/{doc_hash}/ultra-deep/status

# 批量查询 Ultra 状态
curl -X POST https://ri.mindfree.top/api/article/batch-ultra-status \
  -H "Content-Type: application/json" \
  -d '["hash1","hash2","hash3"]'

# 触发 Ultra 生成
curl -X POST https://ri.mindfree.top/api/article/{doc_hash}/ultra-deep \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Visual Insight

```bash
# 获取可视化 HTML
curl https://ri.mindfree.top/api/article/{doc_hash}/visual

# 查询可视化生成状态
curl https://ri.mindfree.top/api/article/{doc_hash}/visual/status

# 强制生成长图（需认证）
curl -X POST "https://ri.mindfree.top/api/article/{doc_hash}/visual/to-image?force_regenerate=true" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取长图
curl https://ri.mindfree.top/api/article/{doc_hash}/visual/image -o visual.png

# 触发后处理器（需认证）
curl -X POST https://ri.mindfree.top/api/article/{doc_hash}/post-process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"processor":"visual_insight","force":true}'

curl -X POST https://ri-dev.mindfree.top/api/article/{doc_hash}/post-process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"processor":"visual_insight","force":true}'
```

---

## 字幕

```bash
# 获取原始字幕
curl https://ri.mindfree.top/api/public/subtitle/{video_id}

# 获取翻译字幕
curl https://ri.mindfree.top/api/public/subtitle/{video_id}/translated

# 强制重新翻译
curl "https://ri.mindfree.top/api/public/subtitle/{video_id}/translated?force=true"
```

---

## 下载

```bash
# 下载 Markdown
curl https://ri.mindfree.top/api/public/summaries/{filename}/markdown -o article.md

# 下载 PDF
curl https://ri.mindfree.top/api/public/summaries/{filename}/pdf -o article.pdf
```

---

## 文章删除与恢复

```bash
# 软删除文章（移动到回收站）
curl -X DELETE https://ri.mindfree.top/api/summaries/{doc_hash} \
  -H "Authorization: Bearer YOUR_TOKEN"

# 查看回收站
curl https://ri.mindfree.top/api/admin/trash \
  -H "Authorization: Bearer YOUR_TOKEN"

# 从回收站恢复
curl -X POST https://ri.mindfree.top/api/admin/trash/{doc_hash}/restore \
  -H "Authorization: Bearer YOUR_TOKEN"

# 永久删除
curl -X DELETE https://ri.mindfree.top/api/admin/trash/{doc_hash} \
  -H "Authorization: Bearer YOUR_TOKEN"

# 清空回收站
curl -X DELETE https://ri.mindfree.top/api/admin/trash \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 系统管理

```bash
# 健康检查（公开）
curl https://ri.mindfree.top/api/health

# 队列统计
curl https://ri.mindfree.top/api/queue/stats

# 队列任务列表
curl https://ri.mindfree.top/api/queue/tasks

# Cookie 状态（需认证）
curl https://ri.mindfree.top/api/admin/cookie-status \
  -H "Authorization: Bearer YOUR_TOKEN"

# 刷新缓存
curl -X POST https://ri.mindfree.top/api/admin/refresh-cache \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## PDF/文档分析

```bash
# 上传 PDF 分析
curl -X POST https://ri.mindfree.top/analyze-pdf \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "title=文档标题"

# 上传通用文档分析（支持 TXT, MD, PDF, DOCX）
curl -X POST https://ri.mindfree.top/analyze-document \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/document.md" \
  -F "title=文档标题"
```

---

## 用户管理（仅管理员）

```bash
# 检查是否为管理员
curl https://ri.mindfree.top/api/auth/check-admin \
  -H "Authorization: Bearer YOUR_TOKEN"

# 注册新用户
curl -X POST https://ri.mindfree.top/api/auth/register \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","password":"password123","role":"user"}'

# 获取用户列表
curl https://ri.mindfree.top/api/auth/users \
  -H "Authorization: Bearer YOUR_TOKEN"

# 删除用户
curl -X DELETE https://ri.mindfree.top/api/auth/users/{username} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 认证要求摘要

| 端点 | 方法 | 需要认证 |
|-----|-----|--------|
| `/login` | POST | × |
| `/summarize` | POST | ✓ |
| `/analyze-pdf` | POST | ✓ |
| `/analyze-document` | POST | ✓ |
| `/api/public/*` | GET | × |
| `/api/tasks/{id}/status` | GET | × |
| `/api/tasks/{id}/stream` | GET | Token可选 |
| `/api/article/{hash}/visual` | GET | × |
| `/api/article/{hash}/visual/to-image` | POST | ✓ |
| `/api/article/{hash}/post-process` | POST | ✓ |
| `/api/article/{hash}/ultra-deep` | POST | ✓ |
| `/api/summaries/{hash}` | DELETE | ✓ |
| `/api/admin/*` | ALL | ✓ |
| `/api/auth/register` | POST | ✓ (管理员) |
| `/api/auth/users` | GET/DELETE | ✓ (管理员) |

---

*更新时间: 2024-12-14*
