# Deep-Insight vs Quick-Insight UI设计规范

## 🎯 设计理念

### 核心价值主张
- **Deep-Insight**: 传统深度阅读，强调沉浸式思考体验
- **Quick-Insight**: AI视觉化呈现，强调快速理解和洞察

### 品牌契合度
完美对称的命名方案，与"reinvent-insight"品牌DNA高度契合，形成完整的洞察产品矩阵。

---

## 🎨 UI组件设计

### 1. 模式切换器 (Mode Switcher)

#### 1.1 组件位置
- **位置**: ReadingView的AppHeader区域，右上角
- **层级**: 与版本选择器同级，但优先级更高
- **响应式**: 移动端保持可见，可能调整布局

#### 1.2 视觉设计
```html
<div class="insight-mode-switcher">
  <tech-button 
    :variant="currentMode === 'deep' ? 'primary' : 'secondary'"
    @click="switchMode('deep')"
    class="mode-btn mode-btn--deep">
    📚 Deep-Insight
  </tech-button>
  
  <tech-button 
    :variant="currentMode === 'quick' ? 'primary' : 'secondary'"
    @click="switchMode('quick')"
    class="mode-btn mode-btn--quick">
    ⚡ Quick-Insight
  </tech-button>
</div>
```

#### 1.3 样式规范
```css
.insight-mode-switcher {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  padding: 0.5rem;
  background: rgba(30, 30, 30, 0.8);
  border-radius: 0.5rem;
  backdrop-filter: blur(10px);
}

.mode-btn--deep.tech-btn--primary {
  background: linear-gradient(135deg, #2563EB, #1E40AF);
  color: #E0E0E0;
}

.mode-btn--quick.tech-btn--primary {
  background: linear-gradient(135deg, #06B6D4, #0891B2);
  color: #E0E0E0;
}

.mode-btn {
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.mode-btn::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: width 0.3s ease, height 0.3s ease;
}

.mode-btn:hover::before {
  width: 100%;
  height: 100%;
}
```

---

## 🔄 交互流程设计

### 2. 状态管理

#### 2.1 组件状态
```javascript
// ReadingView.js 中的状态管理
const currentInsightMode = ref('deep'); // 'deep' | 'quick'
const hasQuickInsight = ref(false);
const quickInsightLoading = ref(false);
const quickInsightContent = ref('');

// 检查Quick-Insight可用性
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
```

#### 2.2 模式切换逻辑
```javascript
const switchInsightMode = async (mode) => {
  if (mode === currentInsightMode.value) return;
  
  if (mode === 'quick' && !hasQuickInsight.value) {
    // 显示提示：Quick-Insight不可用
    eventBus.emit('show-toast', {
      type: 'warning',
      message: '该文章暂无Quick-Insight版本'
    });
    return;
  }
  
  // 切换加载状态
  quickInsightLoading.value = true;
  
  try {
    if (mode === 'quick' && !quickInsightContent.value) {
      // 首次加载Quick-Insight内容
      const response = await axios.get(`/insights/${articleId}.html`);
      quickInsightContent.value = response.data;
    }
    
    currentInsightMode.value = mode;
    
    // 触发切换动画
    await nextTick();
    
    // 平滑滚动到顶部
    const container = document.querySelector('.reading-view__content');
    if (container) {
      container.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
  } catch (error) {
    console.error('切换模式失败:', error);
    eventBus.emit('show-toast', {
      type: 'error',
      message: '切换模式失败，请稍后重试'
    });
  } finally {
    quickInsightLoading.value = false;
  }
};
```

---

## 🎭 视觉效果设计

### 3. 切换动画

#### 3.1 内容切换动画
```css
.insight-content {
  transition: all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.insight-content-enter-active,
.insight-content-leave-active {
  transition: all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.insight-content-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.98);
}

.insight-content-leave-to {
  opacity: 0;
  transform: translateY(-20px) scale(0.98);
}

.insight-content-enter-to,
.insight-content-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}
```

#### 3.2 加载状态动画
```css
.quick-insight-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #06B6D4;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(6, 182, 212, 0.3);
  border-top: 3px solid #06B6D4;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 1rem;
  font-size: 0.9rem;
  color: #B0B0B0;
}
```

---

## 📱 响应式设计

### 4. 移动端适配

#### 4.1 移动端布局调整
```css
@media (max-width: 768px) {
  .insight-mode-switcher {
    position: fixed;
    bottom: 2rem;
    right: 1rem;
    z-index: 1000;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.5rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  }
  
  .mode-btn {
    width: 100%;
    font-size: 0.75rem;
    padding: 0.5rem 0.75rem;
  }
  
  .mode-btn .emoji {
    display: none; /* 移动端隐藏emoji */
  }
}

@media (max-width: 480px) {
  .insight-mode-switcher {
    bottom: 1rem;
    right: 0.5rem;
  }
}
```

#### 4.2 触摸优化
```css
.mode-btn {
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  min-height: 44px; /* iOS推荐的最小触摸目标 */
}

.mode-btn:active {
  transform: scale(0.95);
}
```

---

## 🎯 用户体验优化

### 5. 交互细节

#### 5.1 首次使用引导
```javascript
// 首次使用Quick-Insight的引导提示
const showQuickInsightTip = () => {
  if (hasQuickInsight.value && !localStorage.getItem('quick-insight-tip-shown')) {
    eventBus.emit('show-toast', {
      type: 'info',
      message: '🎉 发现新功能！点击 Quick-Insight 体验AI视觉化阅读',
      duration: 5000
    });
    localStorage.setItem('quick-insight-tip-shown', 'true');
  }
};
```

#### 5.2 键盘快捷键
```javascript
// 键盘快捷键支持
const handleKeyboardShortcuts = (event) => {
  if (event.ctrlKey || event.metaKey) {
    switch (event.key) {
      case '1':
        event.preventDefault();
        switchInsightMode('deep');
        break;
      case '2':
        event.preventDefault();
        if (hasQuickInsight.value) {
          switchInsightMode('quick');
        }
        break;
    }
  }
};
```

#### 5.3 状态持久化
```javascript
// 保存用户的模式偏好
const saveUserPreference = (mode) => {
  localStorage.setItem('preferred-insight-mode', mode);
};

// 加载用户偏好
const loadUserPreference = () => {
  const preference = localStorage.getItem('preferred-insight-mode');
  if (preference && (preference === 'deep' || preference === 'quick')) {
    return preference;
  }
  return 'deep'; // 默认模式
};
```

---

## 🔧 技术实现要点

### 6. 前端集成

#### 6.1 ReadingView组件修改
```javascript
// ReadingView.js 主要修改点
export default {
  // ... 现有代码
  
  setup(props, { emit }) {
    // ... 现有setup代码
    
    // 新增：洞察模式相关状态
    const currentInsightMode = ref('deep');
    const hasQuickInsight = ref(false);
    const quickInsightContent = ref('');
    const quickInsightLoading = ref(false);
    
    // 新增：检查Quick-Insight可用性
    const checkQuickInsightAvailability = async () => {
      // 实现逻辑
    };
    
    // 新增：模式切换方法
    const switchInsightMode = async (mode) => {
      // 实现逻辑
    };
    
    // 监听文章变化，重新检查Quick-Insight
    watch(() => props.content, () => {
      checkQuickInsightAvailability();
    });
    
    return {
      // ... 现有返回值
      currentInsightMode,
      hasQuickInsight,
      quickInsightContent,
      quickInsightLoading,
      switchInsightMode
    };
  }
};
```

#### 6.2 模板修改
```html
<!-- ReadingView.html 主要修改点 -->
<div class="reading-view">
  <!-- ... 现有代码 -->
  
  <!-- 新增：模式切换器 -->
  <div v-if="hasQuickInsight" class="insight-mode-switcher">
    <tech-button 
      :variant="currentInsightMode === 'deep' ? 'primary' : 'secondary'"
      @click="switchInsightMode('deep')"
      class="mode-btn mode-btn--deep">
      📚 Deep-Insight
    </tech-button>
    
    <tech-button 
      :variant="currentInsightMode === 'quick' ? 'primary' : 'secondary'"
      @click="switchInsightMode('quick')"
      class="mode-btn mode-btn--quick">
      ⚡ Quick-Insight
    </tech-button>
  </div>
  
  <!-- 修改：内容渲染区域 -->
  <div class="reading-view__content-wrapper">
    <!-- Deep-Insight模式 (现有的markdown渲染) -->
    <transition name="insight-content">
      <div v-if="currentInsightMode === 'deep'" class="deep-insight-content">
        <!-- 现有的markdown内容渲染 -->
        <div v-html="cleanContent" class="reading-view__body prose-tech"></div>
      </div>
    </transition>
    
    <!-- Quick-Insight模式 -->
    <transition name="insight-content">
      <div v-if="currentInsightMode === 'quick'" class="quick-insight-content">
        <div v-if="quickInsightLoading" class="quick-insight-loading">
          <div class="loading-spinner"></div>
          <div class="loading-text">正在加载Quick-Insight...</div>
        </div>
        
        <div v-else-if="quickInsightContent" 
             v-html="quickInsightContent" 
             class="quick-insight-body">
        </div>
      </div>
    </transition>
  </div>
</div>
```

---

## 📊 性能优化

### 7. 优化策略

#### 7.1 延迟加载
- Quick-Insight内容仅在用户首次切换时加载
- 使用浏览器缓存避免重复请求
- 预加载机制：在用户hover时开始预加载

#### 7.2 内存管理
- 及时清理不再使用的HTML内容
- 使用虚拟DOM diff优化大型HTML的渲染
- 图片懒加载机制

#### 7.3 用户体验优化
- 切换动画使用CSS Transform而非重排
- 骨架屏显示加载状态
- 错误边界处理异常情况

---

## 🎉 总结

Deep-Insight vs Quick-Insight 的设计完美体现了：

1. **品牌一致性**: 与reinvent-insight品牌高度契合
2. **用户体验**: 流畅的切换体验和清晰的价值区分
3. **技术可行性**: 基于现有架构的渐进式增强
4. **扩展性**: 为未来功能预留了足够的设计空间

这将是一个令人眼前一亮的功能！🚀 