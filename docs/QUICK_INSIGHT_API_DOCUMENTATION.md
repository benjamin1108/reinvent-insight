# Quick-Insight API 文档

## 📋 概述

Quick-Insight API是reinvent-insight项目Phase 2开发的API接口，用于检查和获取文章的Quick-Insight（AI生成的视觉化HTML版本）。

### 功能特性
- **状态检查**: 检查指定文章是否有Quick-Insight版本
- **内容获取**: 获取Quick-Insight的HTML内容
- **批量列表**: 列出所有可用的Quick-Insight文件
- **元数据支持**: 提供完整的生成信息和统计数据

---

## 🔗 API端点

### 1. 检查文章Quick-Insight状态

**GET** `/api/articles/{article_id}/insight`

检查指定文章是否有Quick-Insight版本，并返回相关元数据。

#### 请求参数
| 参数 | 类型 | 位置 | 必需 | 描述 |
|------|------|------|------|------|
| article_id | string | path | 是 | 文章的统一hash ID，长度至少8个字符 |

#### 响应格式
```json
{
  "has_insight": true,
  "generated_at": "2025-07-03T23:36:22.693370",
  "insight_url": "/downloads/insights/filename.html",
  "metadata": {
    "file_size": 34579,
    "word_count": 31068,
    "generation_time": 76.5,
    "ai_model": "Gemini",
    "template_used": "enhanced",
    "html_file": "/path/to/file.html",
    "json_file": "/path/to/file.json"
  }
}
```

#### 响应字段说明
| 字段 | 类型 | 描述 |
|------|------|------|
| has_insight | boolean | 是否存在Quick-Insight版本 |
| generated_at | string/null | 生成时间（ISO格式）|
| insight_url | string/null | Quick-Insight文件的访问URL |
| metadata | object/null | 详细的文件和生成信息 |

#### 示例请求
```bash
curl -X GET "http://localhost:8002/api/articles/7b774e79/insight"
```

#### 示例响应
**有Quick-Insight版本:**
```json
{
  "has_insight": true,
  "generated_at": "2025-07-03T23:36:22.693370",
  "insight_url": "/downloads/insights/Yuval Noah Harari on AI and Human Evolution WSJ Leadership Institute.html",
  "metadata": {
    "file_size": 34579,
    "word_count": 31068,
    "generation_time": 0,
    "ai_model": "Gemini",
    "template_used": "unknown",
    "html_file": "/home/benjamin/reinvent-insight/downloads/insights/Yuval Noah Harari on AI and Human Evolution WSJ Leadership Institute.html",
    "json_file": "/home/benjamin/reinvent-insight/downloads/insights/Yuval Noah Harari on AI and Human Evolution WSJ Leadership Institute.json"
  }
}
```

**无Quick-Insight版本:**
```json
{
  "has_insight": false,
  "generated_at": null,
  "insight_url": null,
  "metadata": null
}
```

#### 错误响应
| 状态码 | 描述 | 示例 |
|--------|------|------|
| 400 | 无效的文章ID | `{"detail": "无效的文章ID：ID长度必须至少8个字符"}` |
| 500 | 服务器内部错误 | `{"detail": "检查Quick-Insight状态时发生内部错误"}` |

---

### 2. 获取Quick-Insight HTML内容

**GET** `/api/articles/{article_id}/insight/content`

获取指定文章的Quick-Insight HTML内容，直接返回可渲染的HTML。

#### 请求参数
| 参数 | 类型 | 位置 | 必需 | 描述 |
|------|------|------|------|------|
| article_id | string | path | 是 | 文章的统一hash ID，长度至少8个字符 |

#### 响应格式
直接返回HTML内容，Content-Type为`text/html; charset=utf-8`

#### 示例请求
```bash
curl -X GET "http://localhost:8002/api/articles/7b774e79/insight/content"
```

#### 示例响应
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>异类智能降临：尤瓦尔·赫拉利深度剖析...</title>
    <style>
        /* 完整的内联CSS样式 */
    </style>
</head>
<body>
    <!-- AI生成的精美HTML内容 -->
</body>
</html>
```

#### 错误响应
| 状态码 | 描述 | 示例 |
|--------|------|------|
| 400 | 无效的文章ID | `{"detail": "无效的文章ID：ID长度必须至少8个字符"}` |
| 404 | 文章没有Quick-Insight版本 | `{"detail": "该文章没有Quick-Insight版本"}` |
| 404 | Quick-Insight文件不存在 | `{"detail": "Quick-Insight文件不存在"}` |
| 500 | 服务器内部错误 | `{"detail": "获取Quick-Insight内容时发生内部错误"}` |

---

### 3. 列出所有Quick-Insight文件

**GET** `/api/insights/list`

获取所有可用的Quick-Insight文件列表，包含详细的元数据信息。

#### 请求参数
无

#### 响应格式
```json
{
  "insights": [
    {
      "article_id": "7b774e79",
      "filename": "Yuval Noah Harari on AI and Human Evolution WSJ Leadership Institute",
      "generated_at": "2025-07-03T23:36:22.693370",
      "file_size": 34579,
      "word_count": 31068,
      "generation_time": 76.5,
      "ai_model": "Gemini",
      "template_used": "enhanced",
      "article_title": "异类智能降临：尤瓦尔·赫拉利深度剖析 AI 对权力、信仰与人类未来的重塑",
      "insight_url": "/downloads/insights/filename.html"
    }
  ],
  "total_count": 1
}
```

#### 响应字段说明
| 字段 | 类型 | 描述 |
|------|------|------|
| insights | array | Quick-Insight文件信息数组 |
| total_count | integer | 总文件数量 |

#### 单个insight对象字段
| 字段 | 类型 | 描述 |
|------|------|------|
| article_id | string | 文章的统一hash ID |
| filename | string | 文件名（不含扩展名）|
| generated_at | string | 生成时间（ISO格式）|
| file_size | integer | HTML文件大小（字节）|
| word_count | integer | 原始文章字数 |
| generation_time | number | AI生成耗时（秒）|
| ai_model | string | 使用的AI模型 |
| template_used | string | 使用的模板类型 |
| article_title | string | 文章标题 |
| insight_url | string | Quick-Insight文件的访问URL |

#### 示例请求
```bash
curl -X GET "http://localhost:8002/api/insights/list"
```

#### 示例响应
```json
{
  "insights": [
    {
      "article_id": "7b774e79",
      "filename": "Yuval Noah Harari on AI and Human Evolution WSJ Leadership Institute",
      "generated_at": "2025-07-03T23:36:22.693370",
      "file_size": 34579,
      "word_count": 31068,
      "generation_time": 0,
      "ai_model": "Gemini",
      "template_used": "unknown",
      "article_title": "Yuval Noah Harari on AI and Human Evolution WSJ Leadership Institute",
      "insight_url": "/downloads/insights/Yuval Noah Harari on AI and Human Evolution WSJ Leadership Institute.html"
    },
    {
      "article_id": "3e97e996",
      "filename": "AWS reInvent 2016 Amazon Global Network Overview with James Hamilton",
      "generated_at": "2025-07-03T23:24:34.217511",
      "file_size": 15399,
      "word_count": 33145,
      "generation_time": 0,
      "ai_model": "Gemini",
      "template_used": "unknown",
      "article_title": "AWS reInvent 2016 Amazon Global Network Overview with James Hamilton",
      "insight_url": "/downloads/insights/AWS reInvent 2016 Amazon Global Network Overview with James Hamilton.html"
    }
  ],
  "total_count": 2
}
```

#### 错误响应
| 状态码 | 描述 | 示例 |
|--------|------|------|
| 500 | 服务器内部错误 | `{"detail": "列出Quick-Insight文件时发生内部错误"}` |

---

## 🔧 技术实现

### 文章ID与文件名映射
API使用现有的hash系统将文章ID映射到对应的文件名：
- **hash_to_filename**: hash → 最新版本文件名
- **filename_to_hash**: 文件名 → hash
- **hash_to_versions**: hash → 所有版本文件列表

### 文件结构
```
downloads/
└── insights/
    ├── {filename}.html          # Quick-Insight HTML文件
    └── {filename}.json          # 元数据文件
```

### 元数据格式
JSON元数据文件包含以下信息：
```json
{
  "article_title": "文章标题",
  "generated_at": "2025-07-03T23:36:22.693370",
  "word_count": 31068,
  "generation_time": 76.5,
  "ai_model": "Gemini",
  "template_used": "enhanced",
  "file_size": 34579,
  "html_checksum": "md5hash"
}
```

---

## 🧪 测试

### 运行API测试
项目包含完整的API测试脚本：

```bash
# 运行完整测试
python src/reinvent_insight/tools/test_quick_insight_api.py

# 只测试列表API
python src/reinvent_insight/tools/test_quick_insight_api.py --list-only

# 测试特定文章
python src/reinvent_insight/tools/test_quick_insight_api.py --article-id 7b774e79

# 使用不同的服务器地址
python src/reinvent_insight/tools/test_quick_insight_api.py --base-url http://localhost:8001
```

### 测试覆盖范围
- ✅ API服务器健康检查
- ✅ 列出所有Quick-Insight文件
- ✅ 检查有Quick-Insight的文章状态
- ✅ 检查无Quick-Insight的文章状态
- ✅ 获取Quick-Insight HTML内容
- ✅ 无效文章ID处理
- ✅ 错误情况处理

---

## 📊 使用示例

### JavaScript/TypeScript示例
```typescript
interface QuickInsightResponse {
  has_insight: boolean;
  generated_at?: string;
  insight_url?: string;
  metadata?: {
    file_size: number;
    word_count: number;
    generation_time: number;
    ai_model: string;
    template_used: string;
    html_file: string;
    json_file?: string;
  };
}

class QuickInsightAPI {
  constructor(private baseURL: string = 'http://localhost:8002') {}

  async checkInsightStatus(articleId: string): Promise<QuickInsightResponse> {
    const response = await fetch(`${this.baseURL}/api/articles/${articleId}/insight`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    return response.json();
  }

  async getInsightContent(articleId: string): Promise<string> {
    const response = await fetch(`${this.baseURL}/api/articles/${articleId}/insight/content`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    return response.text();
  }

  async listAllInsights(): Promise<{insights: any[], total_count: number}> {
    const response = await fetch(`${this.baseURL}/api/insights/list`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    return response.json();
  }
}

// 使用示例
const api = new QuickInsightAPI();

// 检查文章是否有Quick-Insight版本
const status = await api.checkInsightStatus('7b774e79');
if (status.has_insight) {
  console.log('文章有Quick-Insight版本:', status.insight_url);
  
  // 获取HTML内容
  const htmlContent = await api.getInsightContent('7b774e79');
  document.getElementById('content').innerHTML = htmlContent;
}

// 列出所有Quick-Insight文件
const allInsights = await api.listAllInsights();
console.log(`找到 ${allInsights.total_count} 个Quick-Insight文件`);
```

### Python示例
```python
import requests
from typing import Optional, Dict, List

class QuickInsightAPI:
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
    
    def check_insight_status(self, article_id: str) -> Dict:
        """检查文章Quick-Insight状态"""
        response = requests.get(f"{self.base_url}/api/articles/{article_id}/insight")
        response.raise_for_status()
        return response.json()
    
    def get_insight_content(self, article_id: str) -> str:
        """获取Quick-Insight HTML内容"""
        response = requests.get(f"{self.base_url}/api/articles/{article_id}/insight/content")
        response.raise_for_status()
        return response.text
    
    def list_all_insights(self) -> Dict:
        """列出所有Quick-Insight文件"""
        response = requests.get(f"{self.base_url}/api/insights/list")
        response.raise_for_status()
        return response.json()

# 使用示例
api = QuickInsightAPI()

# 检查文章状态
status = api.check_insight_status('7b774e79')
if status['has_insight']:
    print(f"文章有Quick-Insight版本: {status['insight_url']}")
    
    # 获取HTML内容
    html_content = api.get_insight_content('7b774e79')
    with open('output.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

# 列出所有文件
all_insights = api.list_all_insights()
print(f"找到 {all_insights['total_count']} 个Quick-Insight文件")
```

---

## 🔄 集成到前端

Phase 3将开发前端UI集成，API调用将被集成到ReadingView组件中：

```javascript
// 在ReadingView中的集成示例
const checkQuickInsightAvailability = async (articleId) => {
  try {
    const response = await axios.get(`/api/articles/${articleId}/insight`);
    hasQuickInsight.value = response.data.has_insight;
    return response.data;
  } catch (error) {
    console.error('检查Quick-Insight失败:', error);
    hasQuickInsight.value = false;
    return null;
  }
};

const loadQuickInsightContent = async (articleId) => {
  try {
    const response = await axios.get(`/api/articles/${articleId}/insight/content`);
    quickInsightContent.value = response.data;
  } catch (error) {
    console.error('加载Quick-Insight内容失败:', error);
  }
};
```

---

## 📝 更新日志

### v2.0 - Phase 2 完成 (2025-01-XX)
- ✅ 实现 `/api/articles/{id}/insight` 端点
- ✅ 实现 `/api/articles/{id}/insight/content` 端点  
- ✅ 实现 `/api/insights/list` 端点
- ✅ 完善错误处理和参数验证
- ✅ 创建完整的API测试套件
- ✅ 编写完整的API文档

### 下一阶段预览 (Phase 3)
- 🔄 前端UI集成
- 🔄 ReadingView模式切换器
- 🔄 Deep-Insight vs Quick-Insight切换
- 🔄 用户体验优化

---

## 🤝 贡献

如需修改或扩展API功能，请：
1. 更新相应的API端点代码
2. 更新API测试脚本
3. 更新此文档
4. 运行完整测试确保兼容性

---

**文档版本**: 2.0  
**最后更新**: 2025-01-XX  
**维护团队**: reinvent-insight team 