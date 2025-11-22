# AudioControlBar Component

音频控制条组件，为 ReadingView 提供文本转语音（TTS）播放功能。

## Features

- ▶️ 播放/暂停/停止控制
- 📊 实时进度条和时间显示
- 🎤 17 种音色选择
- 🏃 播放速度调节（0.5x - 2x）
- 🔊 音量控制
- 💾 用户偏好持久化
- 📱 响应式设计（移动端适配）
- ♿ 无障碍支持（ARIA 标签）
- 🎨 精致的渐变 UI 设计

## Usage

### 在 ReadingView 中使用

```javascript
import AudioControlBar from '/components/shared/AudioControlBar/AudioControlBar.js';

export default {
  components: {
    AudioControlBar
  },
  
  data() {
    return {
      articleHash: 'abc123',
      articleText: '这是文章内容...'
    };
  }
};
```

```html
<AudioControlBar
  :article-hash="articleHash"
  :article-text="articleText"
/>
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `articleHash` | String | Yes | 文章的唯一标识符，用于缓存 |
| `articleText` | String | Yes | 文章的文本内容 |

## Data Properties

### Playback State
- `isPlaying` - 是否正在播放
- `isPaused` - 是否已暂停
- `isLoading` - 是否正在加载

### Time Tracking
- `currentTime` - 当前播放位置（秒）
- `duration` - 总时长（秒）
- `buffered` - 已缓冲时长（秒）

### Audio Controls
- `volume` - 音量（0.0 - 1.0）
- `playbackRate` - 播放速度（0.5 - 2.0）
- `selectedVoice` - 选中的音色

### Available Options
- `availableVoices` - 可用音色列表（17 种）
- `playbackRates` - 可用播放速度列表

## Methods

### Playback Control
- `play()` - 开始播放或恢复播放
- `pause()` - 暂停播放
- `stop()` - 停止播放并重置进度
- `seek(event)` - 跳转到指定位置

### Audio Settings
- `setVolume(event)` - 设置音量
- `setPlaybackRate(event)` - 设置播放速度
- `setVoice(event)` - 设置音色

### Preferences
- `loadPreferences()` - 从 localStorage 加载用户偏好
- `savePreferences()` - 保存用户偏好到 localStorage

## Available Voices

支持 17 种 Qwen3-TTS 音色：

### 中文音色
- Cherry (女声)
- Ethan (男声)
- Stella (女声)
- Luna (女声)
- Aria (女声)
- Bella (女声)
- Chloe (女声)
- David (男声)
- Emily (女声)
- Frank (男声)
- Grace (女声)
- Henry (男声)
- Ivy (女声)
- Jack (男声)
- Kate (女声)

### 英文音色
- Jennifer (女声)
- William (男声)

## Playback Speeds

- 0.5x - 慢速
- 0.75x - 较慢
- 1.0x - 正常（默认）
- 1.25x - 较快
- 1.5x - 快速
- 2.0x - 极快

## Events

组件内部使用 AudioPlayer 的事件系统：

- `timeupdate` - 播放位置更新
- `durationchange` - 总时长变化
- `ended` - 播放结束
- `error` - 播放错误
- `buffered` - 缓冲进度更新

## Styling

组件使用 BEM 命名规范，主要类名：

- `.audio-control-bar` - 根容器
- `.audio-control-bar__main` - 主控制条
- `.audio-control-bar__buttons` - 按钮组
- `.audio-control-bar__progress` - 进度区域
- `.audio-control-bar__controls` - 控制区域
- `.audio-control-bar__error` - 错误提示

### 自定义样式

可以通过覆盖 CSS 变量来自定义样式：

```css
.audio-control-bar {
  /* 自定义背景渐变 */
  --bg-gradient-start: rgba(15, 23, 42, 0.95);
  --bg-gradient-end: rgba(30, 41, 59, 0.9);
  
  /* 自定义主题色 */
  --primary-color: #22d3ee;
  --secondary-color: #3b82f6;
}
```

## Responsive Design

组件在不同屏幕尺寸下自动适配：

- **Desktop (>768px)**: 完整布局，所有控件横向排列
- **Tablet (≤768px)**: 进度条移到顶部，控件紧凑排列
- **Mobile (≤480px)**: 控件分两行显示，优化触摸操作

## Accessibility

组件遵循 WCAG 2.1 AA 标准：

- ✅ 所有交互元素都有 ARIA 标签
- ✅ 支持键盘导航
- ✅ 支持屏幕阅读器
- ✅ 高对比度模式支持
- ✅ 减少动画模式支持
- ✅ Focus 可见性

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- 需要 Web Audio API 支持

## Dependencies

- AudioPlayer.js - 音频播放器类
- StreamBuffer.js - 流式缓冲管理
- Backend TTS API - `/api/tts/stream` 端点

## Error Handling

组件会显示友好的错误消息：

- "无法播放：文章内容为空" - 文章内容为空
- "播放失败：[错误信息]" - 播放过程中出错
- "音色已更改，请重新播放" - 播放中切换音色

## Performance

- 懒加载 AudioPlayer（仅在首次播放时加载）
- 使用 requestAnimationFrame 更新进度
- 防抖/节流优化用户交互
- 自动清理资源（组件卸载时）

## Testing

参见 `tasks.md` 中的测试任务：
- 9.9 - UI 响应性单元测试
- 10.5 - 偏好持久化属性测试
- 10.6 - 速度偏好属性测试

## Future Enhancements

- 播放列表支持
- 书签功能
- 键盘快捷键
- 可视化波形显示
- 离线下载支持
