# 可视化监控 Metadata 同步问题修复

## 问题描述

可视化内容监控总是失效，当 HTML 文件实际不存在但 metadata（`.visual_processed.json`）中有记录时，监控器不会重新生成文件。

## 问题根源

在 `visual_watcher.py` 的 `_should_generate_visual()` 方法中，检查逻辑存在缺陷：

```python
# 旧逻辑（有问题）
if file_key in self.processed_files:
    return False  # 直接返回，不检查文件是否真实存在
```

这导致：
- 如果 metadata 中记录了文件已处理
- 但实际 HTML 文件被删除或不存在
- 监控器会认为文件已处理，不会重新生成

## 解决方案

修改 `_should_generate_visual()` 方法，增加文件真实性验证：

```python
# 新逻辑（已修复）
# 1. 先检查 HTML 文件是否存在
visual_html = self._get_visual_html_path(md_file)
html_exists = visual_html.exists()

# 2. 检查 metadata 记录
if file_key in self.processed_files:
    # 如果 metadata 有记录但文件不存在，清理 metadata 并重新生成
    if not html_exists:
        logger.warning(
            f"检测到 metadata 记录存在但 HTML 文件缺失: {md_file.name}，"
            f"将从 metadata 中移除并重新生成"
        )
        self.processed_files.discard(file_key)
        self._save_processed_files()
        return True
    return False
```

## 修复效果

✅ **修复前：**
- Metadata 有记录 + HTML 不存在 → 不生成（错误）

✅ **修复后：**
- Metadata 有记录 + HTML 不存在 → 清理 metadata + 重新生成（正确）
- Metadata 有记录 + HTML 存在 → 不生成（正确）
- Metadata 无记录 + HTML 不存在 → 生成（正确）

## 测试验证

### 单元测试
已通过 4 个测试场景验证：
1. ✅ Metadata 有记录 + HTML 不存在 → 清理 metadata + 重新生成
2. ✅ Metadata 有记录 + HTML 存在 → 不生成
3. ✅ Metadata 无记录 + HTML 不存在 → 生成
4. ✅ Metadata 无记录 + HTML 存在 → 不生成

### 集成测试
已通过以下集成测试：
1. ✅ 监控器初始化和文件扫描
2. ✅ 现有文件状态一致性检查
3. ✅ 临时文件清理验证
4. ✅ Metadata 完整性验证
5. ✅ 文件丢失恢复测试

### 原子写入测试
已通过以下原子写入机制测试：
1. ✅ 原子写入流程：临时文件 → 原子重命名 → 最终文件
2. ✅ 监控器自动清理残留临时文件
3. ✅ 批量清理多个残留临时文件
4. ✅ 小文件处理（当前实现只检查存在性，不检查大小）

### 测试结果
```
总计: 4/4 单元测试通过
总计: 5/5 集成测试通过
总计: 4/4 原子写入测试通过
🎉 所有测试通过！
```

## 相关文件

- `src/reinvent_insight/visual_watcher.py` - 主要修复文件
- `downloads/summaries/.visual_processed.json` - Metadata 存储文件

## 日期

2024-11-27
