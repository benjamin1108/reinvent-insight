# Bug修复：discover_versions函数参数缺失

## 问题描述

**错误类型**：TypeError  
**错误信息**：`discover_versions() missing 1 required positional argument: 'output_dir'`

**触发场景**：
用户访问文档详情页时，前端请求 `/api/public/doc/{hash}` 触发

**堆栈跟踪**：
```
documents.py:208 in get_public_summary
    versions = discover_versions(video_url)
TypeError: discover_versions() missing 1 required positional argument: 'output_dir'
```

## 根本原因

在重构过程中，`discover_versions()`函数被移至`metadata_service.py`并修改了签名：

**原始签名（legacy/api.py）**：
```python
def discover_versions(video_url: str) -> List[Dict[str, any]]:
    # 使用全局变量 config.OUTPUT_DIR
```

**新签名（metadata_service.py）**：
```python
def discover_versions(video_url: str, output_dir, metadata_parser=None) -> list:
    # 需要显式传入 output_dir 参数
```

**调用处未更新**：
- `api/routes/documents.py:208` - 缺少 output_dir
- `api/routes/versions.py:48` - 缺少 output_dir

## 修复方案

### 修复1：documents.py
```python
# 修复前
versions = discover_versions(video_url)

# 修复后
versions = discover_versions(video_url, config.OUTPUT_DIR)
```

### 修复2：versions.py
```python
# 修复前
versions = discover_versions(video_url)

# 修复后  
versions = discover_versions(video_url, config.OUTPUT_DIR)
```

## 影响范围

**受影响的API端点**：
- `GET /api/public/summaries/{filename}` - 获取文档详情
- `GET /api/public/doc/{hash}` - 通过hash获取文档
- `GET /api/public/doc/{hash}/{version}` - 获取指定版本

**已验证的调用处**：
- ✅ `documents.py:208` - 已修复
- ✅ `versions.py:48` - 已修复
- ✅ `document_service.py` - 已正确传参（无需修改）

## 验证结果

### 代码层面
- ✅ 所有调用处参数一致
- ✅ 函数签名明确
- ✅ 无编译错误

### 运行时验证
- ✅ 服务器正常运行（进程13328）
- ✅ 自动重载已应用修复
- ✅ 文档详情API可正常访问

## 经验教训

### 问题根源
重构时函数签名变更，但未全面更新所有调用处。

### 预防措施
1. **类型检查**：使用mypy等工具进行静态类型检查
2. **搜索验证**：函数签名变更后，全局搜索所有调用处
3. **集成测试**：API端点的集成测试可及时发现此类问题
4. **渐进重构**：避免同时修改函数签名和迁移位置

## 修复时间线

- **发现时间**：2025-12-10 01:46
- **修复完成**：2025-12-10 01:47
- **修复耗时**：1分钟

**状态**：✅ 已完全修复
