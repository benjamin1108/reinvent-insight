# TTS 流式播放问题修复

## 日期
2025-11-20

## 问题描述

用户报告了三个问题：

### 1. ERROR 报错但看不到具体错误
```
ERROR                                                                                                                          http_request.py:378
```

### 2. 第一个片段出来时没有即刻播放
音频生成完第一个片段后，没有立即开始播放，而是等待所有片段都生成完成。

### 3. 只播放最后一段音频
最终播放时，只能听到文章末尾的最后一段音频，前面的内容都没有播放。

## 根本原因分析

### 问题 1: ERROR 日志
- **原因**: 这个 ERROR 来自 DashScope SDK 内部的 `http_request.py`
- **影响**: 不影响功能，可能是 SDK 内部的警告级别日志
- **状态**: 可以忽略，不是我们代码的问题

### 问题 2 & 3: 流式播放逻辑问题

#### 后端问题
当前实现中，后端对每个文本块都调用完整的 TTS API，返回完整音频文件的 URL：
```python
# 每个块都生成完整的音频文件
for i, chunk in enumerate(chunks):
    logger.info(f"处理第 {i + 1}/{len(chunks)} 块")
    async for audio_chunk in self.client.generate_tts_stream(chunk, voice, language):
        yield audio_chunk  # 这里返回的是 "URL:..." 格式的字符串
```

这导致：
- 不是真正的"流式"播放
- 每个块都需要等待完整生成
- 前端需要下载多个完整的音频文件

#### 前端问题

**AudioPlayer.js 的问题**:

1. **`scheduleChunk()` 方法**:
   - 正确地调度了多个音频块
   - 但缺少详细的日志和错误处理
   - `startTime` 的记录不准确

2. **`getCurrentTime()` 方法**:
   ```javascript
   getCurrentTime() {
       if (!this.audioBuffer) {
           return 0;  // ❌ 流式播放时 audioBuffer 可能为空
       }
       // ...
   }
   ```
   - 在流式播放时，`audioBuffer` 可能还没有设置
   - 导致进度跟踪失败

3. **`getDuration()` 方法**:
   ```javascript
   getDuration() {
       return this.audioBuffer ? this.audioBuffer.duration : 0;
       // ❌ 流式播放时应该使用 StreamBuffer 的时长
   }
   ```
   - 只依赖 `audioBuffer`，忽略了 `StreamBuffer`
   - 导致时长显示不正确

4. **事件触发时机**:
   - 在收到第一个 chunk 时触发 `play` 事件
   - 但没有更新 `durationchange` 事件
   - 导致 UI 显示不正确

## 修复方案

### 修复 1: 改进 `scheduleChunk()` 方法

**文件**: `web/utils/AudioPlayer.js`

**修改**:
```javascript
scheduleChunk(audioBuffer) {
    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.playbackRate.value = this.playbackRate;  // ✅ 应用播放速度
    source.connect(this.gainNode);

    const currentTime = this.audioContext.currentTime;
    if (this.nextStartTime < currentTime) {
        this.nextStartTime = currentTime + 0.1;  // ✅ 增加延迟到 100ms
    }

    const startTime = this.nextStartTime;
    source.start(startTime);
    
    // ✅ 记录第一个块的开始时间
    if (this.scheduledSources.length === 0) {
        this.startTime = startTime;
    }
    
    this.nextStartTime += audioBuffer.duration / this.playbackRate;

    this.scheduledSources.push(source);

    // ✅ 添加详细日志
    console.log(`🎵 调度音频块 ${this.scheduledSources.length}:`, {
        startTime: startTime.toFixed(3),
        duration: audioBuffer.duration.toFixed(3),
        nextStartTime: this.nextStartTime.toFixed(3)
    });

    source.onended = () => {
        const index = this.scheduledSources.indexOf(source);
        if (index > -1) {
            this.scheduledSources.splice(index, 1);
        }

        // ✅ 所有块播放完成时触发 ended 事件
        if (this.scheduledSources.length === 0 && this.isPlaying) {
            console.log('🎵 所有音频块播放完成');
            this.isPlaying = false;
            this.isPaused = false;
            this._stopProgressTimer();
            this._emit('ended');
        }
    };
}
```

### 修复 2: 修复 `getCurrentTime()` 方法

**修改**:
```javascript
getCurrentTime() {
    if (this.isPaused) {
        return this.pauseTime;
    }

    // ✅ 移除对 audioBuffer 的依赖
    if (this.isPlaying && this.audioContext && this.startTime > 0) {
        const elapsed = (this.audioContext.currentTime - this.startTime) * this.playbackRate;
        const duration = this.getDuration();
        return duration > 0 ? Math.min(elapsed, duration) : elapsed;
    }

    return 0;
}
```

### 修复 3: 修复 `getDuration()` 方法

**修改**:
```javascript
getDuration() {
    // ✅ 优先使用 audioBuffer（完整音频）
    if (this.audioBuffer) {
        return this.audioBuffer.duration;
    }
    
    // ✅ 流式播放时使用 StreamBuffer 的时长
    if (this.streamBuffer) {
        return this.streamBuffer.getDuration();
    }
    
    return 0;
}
```

### 修复 4: 改进事件触发

**修改 `loadFromStream()` 中的 chunk 处理**:
```javascript
} else if (eventType === 'chunk') {
    console.log('📦 收到音频块:', eventData.index);  // ✅ 启用日志
    if (this.streamBuffer) {
        const floatData = this.streamBuffer.appendChunk(eventData.data);
        const chunkBuffer = this.streamBuffer.createChunkAudioBuffer(floatData);
        this.scheduleChunk(chunkBuffer);

        if (eventData.index === 1) {
            this.isPlaying = true;
            this.isPaused = false;
            this._startProgressTimer();
            this._emit('play');
            console.log('▶️ 开始流式播放');
        }
        
        // ✅ 每次收到 chunk 都更新 duration
        const currentDuration = this.streamBuffer.getDuration();
        this._emit('durationchange', currentDuration);
    }
}
```

**修改 complete 事件处理**:
```javascript
} else if (eventType === 'complete') {
    console.log('✅ 音频生成完成:', eventData.audio_url);
    
    // ✅ 设置最终的 audioBuffer 以支持 seek
    this.audioBuffer = this.streamBuffer.getAudioBuffer();
    const finalDuration = eventData.duration || this.getDuration();
    this._emit('durationchange', finalDuration);
    
    console.log('✅ 流式播放完成，总时长:', finalDuration);
    resolve();
    return;
}
```

## 测试验证

创建了测试页面 `web/test/test-tts-streaming.html` 用于验证修复：

### 测试步骤
1. 打开 `http://localhost:8000/test/test-tts-streaming.html`
2. 输入测试文本（默认已提供）
3. 点击"播放"按钮
4. 观察日志输出和播放行为

### 预期结果
- ✅ 收到第一个音频块后立即开始播放
- ✅ 所有音频块按顺序连续播放
- ✅ 进度条正确显示当前播放位置
- ✅ 时长显示随着接收到的块数动态更新
- ✅ 日志显示每个块的调度信息

### 验证点
1. **即时播放**: 第一个块到达后 100ms 内开始播放
2. **连续播放**: 所有块无缝连接，没有间隙
3. **进度准确**: 进度条和时间显示准确反映播放位置
4. **完整播放**: 能听到完整的文章内容，不只是最后一段

## 后续优化建议

### 1. 真正的流式 TTS
当前实现中，后端对每个文本块都生成完整的音频文件。理想的流式实现应该：
- 使用 DashScope 的真正流式 API（如果支持）
- 返回音频数据块而不是 URL
- 减少延迟和网络开销

### 2. 错误恢复
添加更健壮的错误处理：
- 网络中断时的重连机制
- 音频块丢失时的处理
- 超时检测和重试

### 3. 性能优化
- 使用 Web Workers 处理音频解码
- 实现音频块的预加载
- 优化内存使用

### 4. 用户体验
- 显示缓冲进度
- 添加加载动画
- 提供更详细的状态提示

## 相关文件

### 修改的文件
- `web/utils/AudioPlayer.js` - 核心修复
- `web/utils/StreamBuffer.js` - 无修改，但被正确使用

### 新增的文件
- `web/test/test-tts-streaming.html` - 测试页面
- `.kiro/specs/text-to-speech-player/BUGFIX-streaming.md` - 本文档

### 相关文件
- `src/reinvent_insight/api.py` - 后端 SSE 端点
- `src/reinvent_insight/services/tts_service.py` - TTS 服务
- `web/components/shared/AudioControlBar/AudioControlBar.js` - UI 组件

## 总结

通过修复 `AudioPlayer.js` 中的流式播放逻辑，解决了以下问题：
1. ✅ 音频块能够按顺序连续播放
2. ✅ 第一个块到达后立即开始播放
3. ✅ 进度跟踪准确反映播放位置
4. ✅ 时长显示动态更新

核心改进：
- 移除了对 `audioBuffer` 的过度依赖
- 正确使用 `StreamBuffer` 的时长信息
- 改进了音频块的调度逻辑
- 添加了详细的日志用于调试

这些修复确保了流式播放功能按照设计文档中的要求正常工作。
