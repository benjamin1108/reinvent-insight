# Bug修复：时间显示不正确

## 问题描述

在"近期解读"下拉列表中，所有文章都显示为"1分钟前"，即使它们是很久之前创建的。

## 根本原因

API在返回文章列表时使用了文件系统的 `stat.st_mtime`（修改时间）作为 `modified_at` 字段。当应用重新部署时，文件被复制或重新创建，导致文件系统的修改时间被更新为当前时间。

## 解决方案

修改 `src/reinvent_insight/api.py` 中的 `list_public_summaries` 函数，优先使用markdown文件metadata中的 `created_at` 字段（ISO格式字符串），而不是文件系统的时间戳。

### 修改内容

1. **添加datetime导入**
   ```python
   from datetime import datetime
   ```

2. **解析metadata中的时间**
   ```python
   # 优先使用metadata中的created_at，如果不存在则使用文件时间
   created_at_value = stat.st_ctime
   modified_at_value = stat.st_mtime
   
   # 尝试从metadata中获取created_at（ISO格式字符串）
   if metadata.get("created_at"):
       try:
           # 解析ISO格式时间字符串为时间戳
           dt = datetime.fromisoformat(metadata.get("created_at").replace('Z', '+00:00'))
           created_at_value = dt.timestamp()
           # 如果有metadata中的时间，也用它作为modified_at（更准确）
           modified_at_value = created_at_value
       except (ValueError, AttributeError) as e:
           logger.warning(f"解析文件 {md_file.name} 的created_at失败: {e}")
   ```

## 测试方法

1. 重启API服务器
2. 访问应用并悬停在"近期解读"按钮上
3. 检查文章的相对时间是否正确显示

或者运行测试脚本：
```bash
python test_time_fix.py
```

## 预期结果

- 文章的相对时间应该基于metadata中保存的原始创建时间
- 即使重新部署，时间显示也应该保持正确
- 例如：2天前创建的文章应该显示"2天前"，而不是"1分钟前"

## 影响范围

- 仅影响 `/api/public/summaries` 端点
- 不影响其他功能
- 向后兼容：如果metadata中没有 `created_at` 字段，会回退到使用文件系统时间

## 相关文件

- `src/reinvent_insight/api.py` - API实现
- `web/components/common/RecentArticlesDropdown/RecentArticlesDropdown.js` - 时间格式化函数
- `test_time_fix.py` - 测试脚本
