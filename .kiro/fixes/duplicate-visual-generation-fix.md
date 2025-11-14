# 修复：重复生成可视化解读

## 问题描述

在分析任务完成后，系统会生成两次可视化解读：

1. **第一次**：由 `DeepSummaryWorkflow` 在完成深度解读后立即触发
2. **第二次**：由 `VisualWatcher` 在检测到新的 .md 文件后触发

这导致了资源浪费和不必要的 API 调用。

## 问题原因

`VisualWatcher` 每 30 秒扫描一次 `downloads/summaries/` 目录，当发现新的 .md 文件且对应的 _visual.html 文件不存在时，就会触发生成任务。

但是，当 `DeepSummaryWorkflow` 完成并触发可视化生成时，HTML 文件还在生成中（需要约 1 分钟），此时 `VisualWatcher` 扫描到新文件，发现 HTML 不存在，就会再次触发生成。

## 解决方案

在 `VisualWatcher._should_generate_visual()` 方法中添加检查逻辑：

1. 检查是否已有相关的可视化任务正在运行
2. 遍历 `task_manager.tasks`，查找包含 `_visual` 标识的任务
3. 检查任务 ID 是否与当前文件相关
4. 如果找到正在运行的相关任务，跳过生成

## 修改内容

### 文件：`src/reinvent_insight/visual_watcher.py`

在 `_should_generate_visual()` 方法中添加了第 2 步检查：

```python
# 2. 检查是否有正在运行的可视化任务（避免重复生成）
base_name = md_file.stem
# 移除版本号后缀以获取基础名称
version_match = re.match(r'^(.+)_v(\d+)$', base_name)
if version_match:
    base_name = version_match.group(1)

# 检查是否有相关的可视化任务正在运行
for task_id, task_state in task_manager.tasks.items():
    # 检查任务 ID 是否包含 _visual 标识
    if '_visual' not in task_id:
        continue
    
    # 检查任务状态是否为运行中或待处理
    if task_state.status not in ['pending', 'running']:
        continue
    
    # 检查任务 ID 是否与当前文件相关
    normalized_base = base_name.replace(' ', '_')
    if normalized_base in task_id or base_name in task_id:
        logger.info(
            f"跳过 {md_file.name}，已有可视化任务正在运行: {task_id} (状态: {task_state.status})"
        )
        return False
```

## 验证方法

1. 提交一个 YouTube URL 进行分析
2. 观察日志输出
3. 确认只生成一次可视化解读
4. 检查日志中是否出现 "跳过 XXX，已有可视化任务正在运行" 的消息

## 预期效果

- 每个深度解读文件只生成一次可视化解读
- 减少不必要的 API 调用
- 节省处理时间和资源

## 任务 ID 格式

- **Workflow 触发**：`{原始任务ID}_visual`
  - 例如：`dced607b-0ec1-4f48-ba01-cc8a99205797_visual`
  
- **Watcher 触发**：`visual_{文件名}_{时间戳}`
  - 例如：`visual_The_Frugal_Architect_The_Keys_to_AWS_Optimization_S15_E6_1763122708`

## 相关文件

- `src/reinvent_insight/visual_watcher.py` - 文件监控器
- `src/reinvent_insight/workflow.py` - 工作流（触发可视化生成）
- `src/reinvent_insight/task_manager.py` - 任务管理器
