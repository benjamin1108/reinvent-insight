# TechButton 组件

统一的科技风格按钮组件，提供项目中所有按钮的一致样式和行为。这是一个基础组件，用于替代项目中所有的tech-btn按钮。

## 设计理念

TechButton组件是为解决项目中按钮样式不一致而创建的统一组件，具有以下设计原则：

- 🎨 **样式统一**: 确保项目中所有按钮具有一致的科技风格外观
- 🧩 **高度可配置**: 支持多种变体、尺寸、状态和图标
- 📱 **响应式设计**: 在不同设备尺寸下都有最佳表现
- ♿ **无障碍友好**: 支持高对比度模式和减少动画
- 🔧 **易于使用**: 简单的API设计，开箱即用

## 功能特性

### 按钮变体
- **primary**: 主要操作按钮（橙色渐变）
- **secondary**: 次要操作按钮（灰色科技风）
- **success**: 成功/确认按钮（绿色科技风）
- **warning**: 警告按钮（黄色科技风）
- **danger**: 危险/删除按钮（红色科技风）

### 按钮尺寸
- **sm**: 小尺寸按钮（32px高）
- **normal**: 标准尺寸按钮（40px高）
- **lg**: 大尺寸按钮（48px高）

### 状态支持
- **加载状态**: 内置旋转图标和禁用点击
- **禁用状态**: 视觉反馈和功能禁用
- **图标支持**: 前置图标、后置图标、图标专用按钮

### 特殊功能
- **全宽按钮**: 适配容器宽度
- **自定义最小宽度**: 灵活的尺寸控制
- **工具提示**: title属性支持

## 使用方法

### 基础使用

```html
<!-- 基本按钮 -->
<tech-button @click="handleClick">点击我</tech-button>

<!-- 不同变体 -->
<tech-button variant="primary" @click="save">保存</tech-button>
<tech-button variant="danger" @click="delete">删除</tech-button>

<!-- 不同尺寸 -->
<tech-button size="sm">小按钮</tech-button>
<tech-button size="lg">大按钮</tech-button>
```

### 带图标的按钮

```html
<!-- 前置图标 -->
<tech-button 
  variant="primary" 
  icon-before="M12 6v6m0 0v6m0-6h6m-6 0H6"
  @click="addItem">
  添加项目
</tech-button>

<!-- 后置图标 -->
<tech-button 
  variant="secondary" 
  icon-after="M14 5l7 7m0 0l-7 7m7-7H3"
  @click="next">
  下一步
</tech-button>

<!-- 图标专用按钮 -->
<tech-button 
  variant="primary" 
  icon-before="M12 6v6m0 0v6m0-6h6m-6 0H6"
  icon-only
  title="添加"
  @click="add">
</tech-button>
```

### 状态按钮

```html
<!-- 加载状态 -->
<tech-button 
  variant="primary" 
  :loading="isLoading"
  loading-text="处理中..."
  @click="process">
  {{ isLoading ? '处理中...' : '开始处理' }}
</tech-button>

<!-- 禁用状态 -->
<tech-button 
  variant="secondary" 
  :disabled="!canSubmit"
  @click="submit">
  提交
</tech-button>
```

### 特殊布局

```html
<!-- 全宽按钮 -->
<tech-button 
  variant="primary" 
  full-width
  @click="submit">
  提交表单
</tech-button>

<!-- 自定义最小宽度 -->
<tech-button 
  variant="secondary" 
  min-width="200px"
  @click="action">
  较宽按钮
</tech-button>
```

## Props API

| 属性名 | 类型 | 默认值 | 可选值 | 说明 |
|--------|------|--------|--------|------|
| `variant` | String | `'secondary'` | `'primary'`, `'secondary'`, `'success'`, `'warning'`, `'danger'` | 按钮变体 |
| `size` | String | `'normal'` | `'sm'`, `'normal'`, `'lg'` | 按钮尺寸 |
| `type` | String | `'button'` | `'button'`, `'submit'`, `'reset'` | 按钮类型 |
| `text` | String | `''` | - | 按钮文字 |
| `loadingText` | String | `'加载中...'` | - | 加载状态文字 |
| `disabled` | Boolean | `false` | - | 是否禁用 |
| `loading` | Boolean | `false` | - | 是否显示加载状态 |
| `iconBefore` | String | `''` | - | 前置图标SVG路径 |
| `iconAfter` | String | `''` | - | 后置图标SVG路径 |
| `title` | String | `''` | - | 悬停提示文字 |
| `iconOnly` | Boolean | `false` | - | 是否为图标专用按钮 |
| `fullWidth` | Boolean | `false` | - | 是否为全宽按钮 |
| `minWidth` | String | `''` | - | 自定义最小宽度 |

## Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| `click` | `event: MouseEvent` | 按钮点击事件 |

## 插槽 (Slots)

| 插槽名 | 说明 |
|--------|------|
| `default` | 按钮内容，优先级高于text属性 |

## 图标系统

TechButton使用SVG路径字符串来定义图标。以下是常用图标的路径：

```javascript
const icons = {
  // 基础操作
  plus: 'M12 6v6m0 0v6m0-6h6m-6 0H6',
  edit: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
  trash: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
  check: 'M5 13l4 4L19 7',
  
  // 导航
  arrowRight: 'M14 5l7 7m0 0l-7 7m7-7H3',
  arrowLeft: 'M10 19l-7-7m0 0l7-7m-7 7h18',
  
  // 系统
  download: 'M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  upload: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12',
  externalLink: 'M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14'
};
```

## 样式定制

TechButton组件包含完整的样式系统，包括：

### 科技风格特效
- 渐变背景和边框
- 悬停时的发光效果
- 滑动光效动画
- 微动画反馈

### 响应式设计
- 桌面端：完整尺寸和交互
- 平板端：适中的尺寸调整
- 移动端：触摸友好的尺寸
- 极小屏幕：进一步优化

### 无障碍支持
- 高对比度模式适配
- 减少动画模式支持
- 语义化HTML结构
- 键盘导航友好

## 迁移指南

### 从原生tech-btn迁移

**原代码：**
```html
<button class="tech-btn tech-btn-primary" @click="save">
  <svg class="w-4 h-4 mr-1">...</svg>
  保存
</button>
```

**迁移后：**
```html
<tech-button 
  variant="primary" 
  icon-before="M12 6v6m0 0v6m0-6h6m-6 0H6"
  @click="save">
  保存
</tech-button>
```

### 批量迁移建议

1. **逐步迁移**: 从新功能开始使用TechButton
2. **统一图标**: 建立项目图标库，使用统一的SVG路径
3. **样式一致性**: 确保所有按钮使用相同的变体规范
4. **测试验证**: 使用测试页面验证所有场景

## 最佳实践

### 变体选择
- **Primary**: 页面主要操作（保存、提交、确认）
- **Secondary**: 次要操作（取消、编辑、查看）
- **Success**: 成功确认（完成、通过）
- **Warning**: 警告操作（重试、警告确认）
- **Danger**: 危险操作（删除、清除）

### 尺寸使用
- **Small**: 紧凑布局、表格操作、辅助按钮
- **Normal**: 大部分场景的标准选择
- **Large**: 重要操作、首屏CTA、表单提交

### 图标使用
- 保持图标语义明确
- 优先使用通用图标
- 图标专用按钮需要title提示
- 避免过多图标造成视觉混乱

## 测试

运行测试页面查看所有功能：

```bash
# 访问测试页面
http://localhost:8002/test/test-tech-button.html
```

测试页面包含：
- 所有按钮变体展示
- 不同尺寸对比
- 图标按钮演示
- 状态切换测试
- 交互式控制面板
- 事件日志追踪

## 技术规格

- **Vue版本**: Vue 3 Composition API
- **样式系统**: 独立CSS，无外部依赖
- **图标系统**: SVG路径字符串
- **浏览器支持**: 现代浏览器，IE11+
- **包大小**: 轻量级，约2KB（gzipped）

## 版本历史

### v1.0.0
- 初始版本发布
- 支持5种按钮变体
- 支持3种按钮尺寸
- 完整的图标系统
- 加载和禁用状态
- 响应式设计
- 无障碍支持

## 相关组件

- `AppHeader`: 应用头部导航栏
- `ProgressBar`: 进度条组件
- `LoginModal`: 登录模态框

## 技术支持

如有问题请查看：
1. 测试页面的完整演示
2. 浏览器开发者工具控制台
3. 项目ES6模块规范文档 