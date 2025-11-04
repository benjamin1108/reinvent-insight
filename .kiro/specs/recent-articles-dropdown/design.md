# Design Document

## Overview

本设计文档描述了"近期解读"下拉菜单功能的技术实现方案。该功能将在AppHeader组件中添加一个新的导航按钮，通过鼠标悬停交互显示最近创建的文章列表，为用户提供快速访问最新内容的便捷方式。

## Architecture

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue.js)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AppHeader Component                      │  │
│  │  ┌────────────┐  ┌──────────────────────────────┐   │  │
│  │  │ 近期解读按钮 │  │  RecentArticlesDropdown      │   │  │
│  │  │  (Hover)   │──│  - 文章列表                   │   │  │
│  │  └────────────┘  │  - 时间格式化                 │   │  │
│  │                  │  - 点击导航                   │   │  │
│  │                  └──────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           │ API Request                      │
│                           ▼                                  │
└───────────────────────────────────────────────────────────┘
                            │
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         /api/public/summaries (existing)             │  │
│  │  - 返回所有文章列表                                   │  │
│  │  - 包含创建时间、标题等元数据                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 组件层次结构

```
AppHeader
├── Brand Logo
├── Navigation Buttons
│   ├── 新解读
│   ├── 笔记库
│   └── 近期解读 (NEW)
│       └── RecentArticlesDropdown (NEW)
│           ├── Article Item 1
│           ├── Article Item 2
│           └── ...
└── Auth Buttons
```

## Components and Interfaces

### 1. RecentArticlesDropdown 组件

新建独立组件，负责显示最近文章的下拉列表。

#### 组件位置
`web/components/common/RecentArticlesDropdown/`

#### 文件结构
```
RecentArticlesDropdown/
├── RecentArticlesDropdown.html    # 模板
├── RecentArticlesDropdown.js      # 逻辑
├── RecentArticlesDropdown.css     # 样式
└── README.md                      # 文档
```

#### Props
```javascript
{
  // 是否显示下拉列表
  visible: {
    type: Boolean,
    default: false
  },
  
  // 文章列表数据
  articles: {
    type: Array,
    default: () => []
  },
  
  // 加载状态
  loading: {
    type: Boolean,
    default: false
  }
}
```

#### Events
```javascript
{
  // 文章点击事件
  'article-click': (article) => {},
  
  // 鼠标进入下拉区域
  'mouseenter': () => {},
  
  // 鼠标离开下拉区域
  'mouseleave': () => {}
}
```

#### 数据结构
```javascript
// Article 对象结构
{
  hash: String,           // 文章hash，用于导航
  title_cn: String,       // 中文标题
  title_en: String,       // 英文标题
  modified_at: Number,    // 修改时间戳
  is_pdf: Boolean,        // 是否为PDF文档
  content_type: String    // 内容类型
}
```

### 2. AppHeader 组件修改

#### 新增状态
```javascript
{
  // 下拉列表显示状态
  showRecentDropdown: ref(false),
  
  // 最近文章列表
  recentArticles: ref([]),
  
  // 加载状态
  recentArticlesLoading: ref(false),
  
  // 鼠标悬停定时器
  hoverTimer: ref(null)
}
```

#### 新增方法
```javascript
{
  // 处理鼠标进入"近期解读"按钮
  handleRecentButtonEnter() {
    clearTimeout(hoverTimer.value);
    showRecentDropdown.value = true;
    if (recentArticles.value.length === 0) {
      loadRecentArticles();
    }
  },
  
  // 处理鼠标离开
  handleRecentButtonLeave() {
    hoverTimer.value = setTimeout(() => {
      showRecentDropdown.value = false;
    }, 300);
  },
  
  // 加载最近文章
  async loadRecentArticles() {
    recentArticlesLoading.value = true;
    try {
      const response = await axios.get('/api/public/summaries');
      const allArticles = response.data.summaries || [];
      
      // 按修改时间排序，取前10篇
      recentArticles.value = allArticles
        .sort((a, b) => b.modified_at - a.modified_at)
        .slice(0, 10);
    } catch (error) {
      console.error('加载最近文章失败:', error);
    } finally {
      recentArticlesLoading.value = false;
    }
  },
  
  // 处理文章点击
  handleRecentArticleClick(article) {
    showRecentDropdown.value = false;
    emit('article-click', article);
  }
}
```

### 3. 时间格式化工具

#### 位置
在 `RecentArticlesDropdown.js` 中实现

#### 实现
```javascript
// 格式化相对时间
function formatRelativeTime(timestamp) {
  const now = Date.now() / 1000; // 转换为秒
  const diff = now - timestamp;
  
  if (diff < 60) {
    return '刚刚';
  } else if (diff < 3600) {
    const minutes = Math.floor(diff / 60);
    return `${minutes}分钟前`;
  } else if (diff < 86400) {
    const hours = Math.floor(diff / 3600);
    return `${hours}小时前`;
  } else if (diff < 604800) {
    const days = Math.floor(diff / 86400);
    return `${days}天前`;
  } else if (diff < 2592000) {
    const weeks = Math.floor(diff / 604800);
    return `${weeks}周前`;
  } else if (diff < 31536000) {
    const months = Math.floor(diff / 2592000);
    return `${months}个月前`;
  } else {
    const years = Math.floor(diff / 31536000);
    return `${years}年前`;
  }
}
```

## Data Models

### RecentArticle 数据模型

```typescript
interface RecentArticle {
  // 文章唯一标识
  hash: string;
  
  // 文章标题
  title_cn: string;
  title_en: string;
  
  // 时间信息
  created_at: number;    // 创建时间戳
  modified_at: number;   // 修改时间戳
  
  // 文章元数据
  filename: string;
  video_url: string;
  is_pdf: boolean;
  content_type: string;
  
  // 可选字段
  course_code?: string;
  level?: string;
  word_count?: number;
}
```

## Error Handling

### 错误场景和处理策略

#### 1. API请求失败
```javascript
try {
  const response = await axios.get('/api/public/summaries');
  // 处理响应
} catch (error) {
  console.error('加载最近文章失败:', error);
  // 显示空状态，不阻塞用户操作
  recentArticles.value = [];
  // 可选：显示错误提示
  showToast('加载最近文章失败', 'warning');
}
```

#### 2. 数据格式异常
```javascript
// 确保数据格式正确
const allArticles = Array.isArray(response.data.summaries) 
  ? response.data.summaries 
  : [];

// 过滤无效数据
const validArticles = allArticles.filter(article => 
  article && article.hash && (article.title_cn || article.title_en)
);
```

#### 3. 时间戳无效
```javascript
function formatRelativeTime(timestamp) {
  // 验证时间戳
  if (!timestamp || isNaN(timestamp) || timestamp <= 0) {
    return '未知时间';
  }
  
  // 处理未来时间
  const now = Date.now() / 1000;
  if (timestamp > now) {
    return '刚刚';
  }
  
  // 正常处理
  // ...
}
```

#### 4. 导航失败
```javascript
function handleArticleClick(article) {
  try {
    if (!article || !article.hash) {
      throw new Error('无效的文章数据');
    }
    
    // 关闭下拉列表
    showRecentDropdown.value = false;
    
    // 触发导航
    emit('article-click', article);
  } catch (error) {
    console.error('文章导航失败:', error);
    showToast('打开文章失败', 'danger');
  }
}
```

## Testing Strategy

### 单元测试

#### 1. 时间格式化函数测试
```javascript
describe('formatRelativeTime', () => {
  it('应该正确格式化刚刚', () => {
    const now = Date.now() / 1000;
    expect(formatRelativeTime(now)).toBe('刚刚');
  });
  
  it('应该正确格式化分钟前', () => {
    const fiveMinutesAgo = Date.now() / 1000 - 300;
    expect(formatRelativeTime(fiveMinutesAgo)).toBe('5分钟前');
  });
  
  it('应该处理无效时间戳', () => {
    expect(formatRelativeTime(null)).toBe('未知时间');
    expect(formatRelativeTime(0)).toBe('未知时间');
  });
});
```

#### 2. 组件逻辑测试
```javascript
describe('RecentArticlesDropdown', () => {
  it('应该正确渲染文章列表', () => {
    const articles = [
      { hash: 'abc123', title_cn: '测试文章', modified_at: Date.now() / 1000 }
    ];
    // 测试渲染逻辑
  });
  
  it('应该在空列表时显示提示', () => {
    const articles = [];
    // 测试空状态
  });
});
```

### 集成测试

#### 1. 鼠标悬停交互测试
- 测试鼠标进入按钮时显示下拉列表
- 测试鼠标离开时延迟关闭
- 测试鼠标在下拉列表内移动时保持显示

#### 2. 数据加载测试
- 测试首次悬停时加载数据
- 测试数据缓存机制
- 测试加载失败的降级处理

#### 3. 导航测试
- 测试点击文章后正确导航
- 测试导航后下拉列表关闭
- 测试URL更新正确

### 手动测试清单

#### 桌面端
- [ ] 鼠标悬停显示下拉列表
- [ ] 鼠标离开延迟关闭
- [ ] 文章列表正确显示
- [ ] 时间格式化正确
- [ ] 点击文章正确导航
- [ ] 空状态显示正确
- [ ] 加载状态显示正确

#### 移动端
- [ ] 点击按钮显示下拉列表
- [ ] 点击外部区域关闭
- [ ] 触摸目标尺寸足够
- [ ] 列表宽度适应屏幕
- [ ] 滚动流畅

#### 响应式
- [ ] 不同屏幕尺寸下布局正确
- [ ] 极小屏幕下可用性良好
- [ ] 横竖屏切换正常

## UI/UX Design

### 视觉设计

#### 下拉列表样式
```css
.recent-articles-dropdown {
  /* 定位 */
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 0.5rem;
  
  /* 尺寸 */
  min-width: 320px;
  max-width: 400px;
  max-height: 500px;
  overflow-y: auto;
  
  /* 科技风格背景 */
  background: linear-gradient(
    135deg,
    rgba(15, 23, 42, 0.95) 0%,
    rgba(30, 41, 59, 0.9) 100%
  );
  backdrop-filter: blur(12px);
  
  /* 边框和阴影 */
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 0.75rem;
  box-shadow: 
    0 10px 25px -5px rgba(0, 0, 0, 0.3),
    0 0 20px rgba(34, 211, 238, 0.1);
  
  /* 动画 */
  animation: fadeInDown 0.2s ease-out;
  
  /* 层级 */
  z-index: 50;
}
```

#### 文章条目样式
```css
.article-item {
  /* 布局 */
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  
  /* 边框 */
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  
  /* 交互 */
  cursor: pointer;
  transition: all 0.2s ease;
}

.article-item:hover {
  background: rgba(34, 211, 238, 0.1);
  border-left: 3px solid #22d3ee;
  padding-left: calc(1rem - 3px);
}

.article-item:last-child {
  border-bottom: none;
}
```

#### 标题样式
```css
.article-title {
  color: #e5e7eb;
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.4;
  
  /* 文本溢出处理 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

#### 时间标签样式
```css
.article-time {
  color: #9ca3af;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.article-time svg {
  width: 0.875rem;
  height: 0.875rem;
}
```

### 动画效果

#### 淡入下拉动画
```css
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

#### 悬停高亮动画
```css
.article-item {
  transition: 
    background-color 0.2s ease,
    border-left-color 0.2s ease,
    padding-left 0.2s ease;
}
```

### 响应式设计

#### 移动端适配
```css
@media (max-width: 768px) {
  .recent-articles-dropdown {
    /* 适应屏幕宽度 */
    left: 0;
    right: 0;
    min-width: auto;
    max-width: calc(100vw - 2rem);
    margin-left: 1rem;
    margin-right: 1rem;
  }
  
  .article-item {
    /* 增大触摸目标 */
    padding: 1rem;
    min-height: 44px;
  }
  
  .article-title {
    /* 移动端字体稍大 */
    font-size: 0.9375rem;
  }
}
```

#### 极小屏幕适配
```css
@media (max-width: 480px) {
  .recent-articles-dropdown {
    max-height: 400px;
  }
  
  .article-item {
    padding: 0.875rem;
  }
}
```

## Implementation Notes

### 性能优化

#### 1. 数据缓存
```javascript
// 缓存最近文章数据，避免重复请求
const recentArticlesCache = {
  data: null,
  timestamp: 0,
  ttl: 5 * 60 * 1000 // 5分钟缓存
};

async function loadRecentArticles() {
  const now = Date.now();
  
  // 检查缓存
  if (recentArticlesCache.data && 
      now - recentArticlesCache.timestamp < recentArticlesCache.ttl) {
    recentArticles.value = recentArticlesCache.data;
    return;
  }
  
  // 加载新数据
  recentArticlesLoading.value = true;
  try {
    const response = await axios.get('/api/public/summaries');
    const articles = processArticles(response.data.summaries);
    
    // 更新缓存
    recentArticlesCache.data = articles;
    recentArticlesCache.timestamp = now;
    recentArticles.value = articles;
  } finally {
    recentArticlesLoading.value = false;
  }
}
```

#### 2. 防抖处理
```javascript
// 鼠标离开时延迟关闭，避免误操作
let hoverTimer = null;

function handleMouseLeave() {
  hoverTimer = setTimeout(() => {
    showRecentDropdown.value = false;
  }, 300);
}

function handleMouseEnter() {
  clearTimeout(hoverTimer);
  showRecentDropdown.value = true;
}
```

#### 3. 虚拟滚动（可选）
如果文章数量很大，可以考虑实现虚拟滚动：
```javascript
// 仅渲染可见区域的文章
// 使用 vue-virtual-scroller 或自定义实现
```

### 可访问性

#### 1. 键盘导航
```html
<!-- 支持Tab键导航 -->
<div 
  class="article-item" 
  tabindex="0"
  @keydown.enter="handleArticleClick(article)"
  @keydown.space.prevent="handleArticleClick(article)">
  <!-- 内容 -->
</div>
```

#### 2. ARIA属性
```html
<div 
  class="recent-articles-dropdown"
  role="menu"
  aria-label="最近文章列表">
  <div 
    class="article-item"
    role="menuitem"
    :aria-label="`打开文章：${article.title_cn}`">
    <!-- 内容 -->
  </div>
</div>
```

#### 3. 焦点管理
```javascript
// 下拉列表打开时，焦点移到第一个文章
function handleDropdownOpen() {
  nextTick(() => {
    const firstItem = document.querySelector('.article-item');
    if (firstItem) {
      firstItem.focus();
    }
  });
}
```

### 浏览器兼容性

#### 支持的浏览器
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- 移动端浏览器（iOS Safari 14+, Chrome Mobile）

#### 降级策略
```css
/* backdrop-filter降级 */
.recent-articles-dropdown {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

@supports not (backdrop-filter: blur(12px)) {
  .recent-articles-dropdown {
    background: rgba(15, 23, 42, 0.98);
  }
}
```

## Security Considerations

### XSS防护
```javascript
// 使用Vue的自动转义
// 标题显示使用 {{ article.title_cn }}，不使用 v-html

// 如果需要显示HTML内容，使用DOMPurify清理
import DOMPurify from 'dompurify';

const sanitizedTitle = DOMPurify.sanitize(article.title_cn);
```

### API安全
```javascript
// 使用公开API端点，无需认证
// 确保不暴露敏感信息
const response = await axios.get('/api/public/summaries');
```

## Future Enhancements

### 可能的功能扩展

1. **搜索功能**
   - 在下拉列表顶部添加搜索框
   - 实时过滤文章列表

2. **分类标签**
   - 显示文章类型（YouTube视频/PDF文档）
   - 显示文章分类标签

3. **收藏功能**
   - 允许用户收藏文章
   - 在下拉列表中优先显示收藏文章

4. **阅读进度**
   - 显示文章阅读进度
   - 标记已读/未读状态

5. **个性化推荐**
   - 基于用户阅读历史推荐相关文章
   - 智能排序

6. **快捷键支持**
   - 使用快捷键打开下拉列表
   - 键盘快速导航
