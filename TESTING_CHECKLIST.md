# 音频按钮重构 - 测试清单

## 紧急修复
✅ 修复了 `articleHash is not defined` 错误
- 从 ReadingView.js 的 return 语句中移除了 `articleHash` 和 `articleText`

## 必须测试的功能

### 1. 基本功能
- [ ] 文章能正常显示
- [ ] 目录能正常显示/隐藏
- [ ] 文章内容可以正常滚动
- [ ] 版本切换功能正常

### 2. 音频播放按钮
- [ ] 按钮在阅读模式的AppHeader中显示
- [ ] 按钮位置：目录按钮右侧
- [ ] 点击播放按钮，音频开始播放
- [ ] 播放时图标变为暂停 (⏸)
- [ ] 点击暂停，音频暂停
- [ ] 暂停后再点击，音频继续播放（不是重新开始）
- [ ] 加载时显示加载图标 (⏳)

### 3. 错误处理
- [ ] 空文章时显示错误提示
- [ ] 网络错误时显示错误提示
- [ ] 错误提示3秒后自动消失

### 4. 样式检查
- [ ] 按钮样式与AppHeader其他按钮一致
- [ ] 按钮hover效果正常
- [ ] 按钮大小合适（桌面40px，移动36px）
- [ ] 按钮与其他元素间距合理

### 5. 响应式
- [ ] 桌面端显示正常
- [ ] 平板端显示正常
- [ ] 移动端显示正常
- [ ] 不同屏幕尺寸下按钮不会被挤压

### 6. 兼容性
- [ ] 高对比度模式下可见
- [ ] 减少动画模式下正常工作
- [ ] 键盘可访问（Tab键可聚焦）

## 已知问题修复

### 问题1: articleHash is not defined
**状态**: ✅ 已修复
**原因**: ReadingView.js 的 return 语句中引用了已删除的变量
**解决**: 从 return 语句中移除 `articleHash` 和 `articleText`

## 回滚方案

如果出现严重问题，可以快速回滚：

1. 恢复 ReadingView.html 中的 AudioControlBar：
```html
<!-- TTS 音频播放器 - 固定在底部 -->
<audio-control-bar v-if="articleHash && articleText" :article-hash="articleHash" :article-text="articleText">
</audio-control-bar>
```

2. 恢复 ReadingView.js 中的依赖：
```javascript
dependencies: [
  ['audio-control-bar', '/components/shared/AudioControlBar', 'AudioControlBar']
],
```

3. 从 AppHeader.html 中移除 SimpleAudioButton

4. 从 index.html 中移除音频相关props

## 性能检查
- [ ] 页面加载速度没有明显变慢
- [ ] 音频加载不阻塞页面渲染
- [ ] 内存使用正常

## 浏览器兼容性
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari
- [ ] 移动浏览器（iOS Safari, Chrome Mobile）
