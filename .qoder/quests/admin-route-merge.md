# Admin 管理页面整合设计

## 一、需求概述

创建统一的 Admin 管理页面，整合现有的回收站功能，并新增文章管理能力，提升管理操作的安全性和易用性。

### 核心目标

- 将分散的管理功能集中到独立的 Admin 页面
- 整合现有 Trash 回收站功能
- 新增文章级别的 Ultra Deep 解读触发能力
- 新增文章直接删除能力
- 移除卡片上的删除按钮，降低误操作风险
- 仅对已登录用户开放访问

## 二、功能设计

### 2.1 页面结构

Admin 页面采用标签页(Tab)结构，包含两个核心功能模块：

#### Tab 1: 文章管理 (Article Management)

文章管理页面以表格形式展示所有已解读的文章，提供批量操作和单篇操作能力。

**展示内容**：

| 列名 | 数据来源 | 说明 |
|------|---------|------|
| 标题 | metadata.title_cn / title_en | 优先显示中文标题，支持点击跳转阅读 |
| 类型 | metadata.source_type | YouTube / 文档 / 其他 |
| 字数 | 统计计算 | 展示纯文本字数 |
| 版本 | hash_to_versions | 展示当前版本号 |
| 创建时间 | metadata.created_at | 首次生成时间 |
| 操作 | - | Ultra Deep / 删除按钮 |

**操作能力**：

1. **Ultra Deep 解读触发**
   - 检查当前文章是否已存在 Ultra 版本
   - 调用 `POST /api/article/{doc_hash}/ultra-deep` 触发生成
   - 显示任务状态（排队中 / 生成中 / 已完成）
   - 章节数超过15章时禁用按钮并提示

2. **删除文章**
   - 触发软删除：调用 `DELETE /api/summaries/{doc_hash}`
   - 确认弹窗提示文件名和影响范围
   - 删除后移动到回收站，支持恢复

3. **批量操作**
   - 支持多选文章
   - 批量删除到回收站

#### Tab 2: 回收站 (Trash)

直接复用现有 TrashView 组件，保持功能不变。

**功能列表**：

| 功能 | API 端点 | 说明 |
|------|---------|------|
| 查看回收站列表 | GET /api/admin/trash | 展示已删除文章 |
| 恢复文章 | POST /api/admin/trash/{doc_hash}/restore | 恢复到文章库 |
| 永久删除 | DELETE /api/admin/trash/{doc_hash} | 物理删除，不可恢复 |
| 清空回收站 | DELETE /api/admin/trash | 清空所有回收站内容 |

### 2.2 数据获取策略

**文章列表获取流程**：

```
1. 读取 hash_to_filename 映射获取所有文档哈希
2. 遍历每个文档，读取元数据（标题、类型、时间）
3. 统计纯文本字数
4. 查询 hash_to_versions 获取版本信息
5. 查询 Ultra Deep 状态（通过 /api/article/{doc_hash}/ultra-deep/status）
6. 组装表格数据并按创建时间倒序排列
```

**实时状态更新**：

- Ultra Deep 生成任务启动后，通过轮询更新状态
- 删除操作后刷新文章列表
- 回收站恢复后刷新文章列表

### 2.3 路由与访问控制

#### 前端路由

在 Vue Router 中新增路由：

| 路由路径 | 组件 | 访问要求 |
|---------|------|---------|
| /admin | AdminView | 需登录 |

#### 访问控制逻辑

```
进入 /admin 路由时：
1. 检查 localStorage 中的认证状态（auth token）
2. 未登录：自动弹出登录弹窗
3. 登录成功后：显示 Admin 页面
4. 登录失败：跳转回主页并提示
```

## 三、现有功能调整

### 3.1 移除卡片删除按钮

**调整范围**：

- SummaryCard 组件：移除 delete 按钮及相关逻辑
- LibraryView 组件：移除 delete 事件监听和处理

**保留内容**：

- isAuthenticated 属性保留，用于其他需要登录判断的功能
- delete 事件触发逻辑代码删除，不再响应删除操作

**影响评估**：

| 组件/文件 | 变更内容 | 风险 |
|----------|---------|------|
| SummaryCard.html | 移除删除按钮 DOM 结构 | 低 |
| SummaryCard.js | 移除 delete 相关方法和状态 | 低 |
| LibraryView.js | 移除 delete 事件处理器 | 低 |

### 3.2 导航入口新增

在 AppHeader 或主导航中新增 Admin 入口：

- 仅登录用户可见
- 点击跳转到 /admin 路由
- 可使用齿轮图标或 "管理" 文字标识

## 四、后端 API 复用清单

无需新增 API，完全复用现有接口：

| 功能 | API 端点 | 文件位置 |
|------|---------|---------|
| 获取文章列表 | 前端组装 | hash_registry.py |
| 查询 Ultra Deep 状态 | GET /api/article/{doc_hash}/ultra-deep/status | ultra_deep.py |
| 触发 Ultra Deep | POST /api/article/{doc_hash}/ultra-deep | ultra_deep.py |
| 删除文章 | DELETE /api/summaries/{doc_hash} | trash.py |
| 获取回收站列表 | GET /api/admin/trash | trash.py |
| 恢复文章 | POST /api/admin/trash/{doc_hash}/restore | trash.py |
| 永久删除 | DELETE /api/admin/trash/{doc_hash} | trash.py |
| 清空回收站 | DELETE /api/admin/trash | trash.py |

## 五、前端组件结构

### 5.1 新增组件

#### AdminView 组件

```
AdminView/
├── AdminView.html    # 标签页布局 + 文章管理表格
├── AdminView.js      # 数据加载、状态管理、事件处理
└── AdminView.css     # 管理页面样式
```

**组件职责**：

- 标签页切换逻辑
- 文章列表数据加载和渲染
- Ultra Deep 状态查询和任务触发
- 删除确认和执行
- 集成 TrashView 组件

### 5.2 组件复用

- 直接引入 TrashView 组件作为 Tab 2 内容
- 监听 TrashView 的事件（restore / delete / empty）
- 统一管理登录状态和认证

## 六、UI/UX 设计原则

### 6.1 布局设计

- 采用响应式设计，支持桌面端和移动端
- 标签页切换流畅，状态保持
- 表格支持排序和筛选（按类型、时间等）

### 6.2 交互反馈

- 所有异步操作显示 loading 状态
- 操作成功/失败显示 Toast 提示
- 危险操作（删除、清空）二次确认

### 6.3 状态提示

| 状态 | 显示样式 | 说明 |
|------|---------|------|
| Ultra 未生成 | 蓝色按钮 "生成 Ultra Deep" | 可点击触发 |
| Ultra 生成中 | 灰色进度条 + 百分比 | 禁用交互 |
| Ultra 已完成 | 绿色标签 "已有 Ultra" | 展示版本号 |
| 不符合条件 | 灰色禁用按钮 + Tooltip | 提示原因（如章节过多） |

## 七、实现优先级

### 第一阶段：核心功能

1. 创建 AdminView 组件基础结构
2. 实现文章列表展示和数据加载
3. 集成 TrashView 组件
4. 实现访问控制和登录拦截

### 第二阶段：管理功能

1. 实现删除文章功能
2. 实现 Ultra Deep 状态查询和触发
3. 移除 SummaryCard 删除按钮
4. 新增导航入口

### 第三阶段：优化体验

1. 添加批量操作能力
2. 优化表格排序和筛选
3. 完善移动端适配
4. 添加操作日志记录（可选）

## 八、风险评估

| 风险 | 影响程度 | 缓解措施 |
|------|---------|---------|
| 误删操作 | 中 | 二次确认 + 软删除机制 + 回收站恢复 |
| 访问控制失效 | 高 | 前后端双重验证，后端强制 verify_token |
| 数据加载慢 | 中 | 分页加载 + 虚拟滚动 + 缓存优化 |
| Ultra 任务堆积 | 中 | 显示队列状态 + 限制并发数 |

## 九、测试建议

### 9.1 功能测试

- 未登录访问 /admin 是否正确拦截
- 登录后能否正常展示文章列表
- Ultra Deep 触发和状态更新是否正常
- 删除操作是否正确移动到回收站
- 回收站恢复和永久删除是否正常

### 9.2 边界测试

- 空文章列表展示
- 空回收站展示
- 网络异常时的错误提示
- 多个 Ultra 任务并发时的状态管理

### 9.3 兼容性测试

- 桌面端 Chrome / Firefox / Safari
- 移动端 iOS Safari / Android Chrome
- 不同屏幕尺寸下的布局适配
