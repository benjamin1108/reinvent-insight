# 音频播放UI简化重构

## 概述

将原本位于ReadingView底部的复杂音频播放控制条简化为一个极简的播放/暂停按钮，并集成到顶部AppHeader中。

## 改动内容

### 1. 新增组件：SimpleAudioButton

**位置**: `web/components/shared/SimpleAudioButton/`

**功能**:
- 极简设计，只有一个圆形按钮
- 点击播放/暂停切换
- 状态：播放 (▶) / 暂停 (⏸) / 加载中 (⏳)
- 错误提示悬浮显示
- 与网站整体科技风格一致

**文件**:
- `SimpleAudioButton.js` - 组件逻辑
- `SimpleAudioButton.html` - 组件模板
- `SimpleAudioButton.css` - 组件样式

### 2. 更新AppHeader组件

**文件**: `web/components/common/AppHeader/`

**改动**:
- 添加音频播放按钮到阅读模式的控制按钮组
- 新增props: `articleHash`, `articleText`
- 添加依赖: `simple-audio-button`
- 按钮位置：目录切换按钮右侧

### 3. 更新ReadingView组件

**文件**: `web/components/views/ReadingView/`

**改动**:
- 移除底部的 `AudioControlBar` 组件
- 移除 `audio-control-bar` 依赖
- 移除TTS相关的computed属性（articleHash, articleText）
- 保持HTML模板简洁

### 4. 更新主应用

**文件**: `web/index.html`, `web/js/app.js`

**改动**:
- 在 `app.js` 中添加 `articleTextForTTS` computed属性
- 在 `index.html` 中将音频相关props传递给AppHeader
- 文本提取逻辑移至主应用层

## 设计理念

### 极简主义
- 去除进度条、时间显示、速度控制等复杂UI
- 只保留最核心的播放/暂停功能
- 减少视觉干扰，提升阅读体验

### 一致性
- 按钮样式与AppHeader中其他按钮保持一致
- 使用网站统一的青色主题 (#22d3ee)
- 圆形按钮设计，符合现代UI趋势

### 可访问性
- 支持高对比度模式
- 支持减少动画模式
- 提供清晰的aria-label和title
- 移动端适配

## 用户体验改进

1. **位置优化**: 从底部移至顶部，更易访问
2. **视觉简化**: 去除复杂控制，降低认知负担
3. **状态清晰**: 图标直观表示当前状态
4. **错误友好**: 错误信息悬浮显示，3秒后自动消失

## 技术细节

### 音频播放逻辑
- 使用相同的 `AudioPlayer` 工具类
- 支持暂停/恢复（不是停止）
- 自动缓存音频
- 默认语音：Cherry
- 默认速度：1.0x

### 文本提取
- 从HTML内容中提取纯文本
- 移除图片、代码块、脚本等
- 限制最大长度6000字符
- 在句子边界智能截断

### 响应式设计
- 桌面端：40px圆形按钮
- 移动端：36px圆形按钮
- 错误提示自适应宽度

## 兼容性

- 保持与现有AudioPlayer工具类的兼容
- 不影响其他组件功能
- 向后兼容，可随时恢复旧版UI

## 未来扩展

如需恢复高级功能（进度条、速度控制等），可以：
1. 在按钮上添加右键菜单
2. 点击按钮展开浮动面板
3. 在设置中添加音频控制选项

## 测试建议

1. 测试播放/暂停切换
2. 测试错误处理（空文本、网络错误等）
3. 测试移动端显示
4. 测试与其他AppHeader按钮的布局
5. 测试高对比度和减少动画模式
