/**
 * AudioPlayer - Web Audio API 音频播放器
 * 
 * 提供音频播放、暂停、停止、seek、速度和音量控制功能
 */

import StreamBuffer from './StreamBuffer.js';

export class AudioPlayer {
  constructor() {
    // Web Audio API 上下文
    this.audioContext = null;
    this.sourceNode = null;
    this.gainNode = null;
    this.audioBuffer = null;

    // 播放状态
    this.isPlaying = false;
    this.isPaused = false;
    this.startTime = 0;
    this.pauseTime = 0;
    this.playbackRate = 1.0;

    // 事件监听器
    this.listeners = {
      timeupdate: [],
      durationchange: [],
      ended: [],
      error: [],
      play: [],
      pause: [],
      stop: [],
      buffered: []
    };

    // 进度更新定时器
    this.progressTimer = null;

    // 流式播放相关
    this.streamBuffer = null;
    this.scheduledSources = [];
    this.nextStartTime = 0;
    this.isTTSComplete = false;      // TTS是否已完成
    this.shouldScheduleChunks = true; // 是否应该调度新的音频块
    this.isStreamMode = false;        // 是否为流式播放模式
    this.streamAbortController = null; // 用于中止流请求

    console.log('🎵 AudioPlayer 初始化');
  }

  /**
   * 初始化 Audio Context（延迟初始化）
   */
  _initAudioContext() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.gainNode = this.audioContext.createGain();
      this.gainNode.connect(this.audioContext.destination);
      console.log('✅ AudioContext 已初始化');
    }
  }

  /**
   * 从 URL 加载音频
   * @param {string} audioUrl - 音频文件 URL
   */
  async loadFromUrl(audioUrl) {
    try {
      this._initAudioContext();

      console.log('📥 开始加载音频:', audioUrl);

      // 获取音频数据
      const response = await fetch(audioUrl);
      if (!response.ok) {
        throw new Error(`加载音频失败: ${response.status}`);
      }

      const arrayBuffer = await response.arrayBuffer();

      console.log('📦 音频数据已下载:', {
        size: arrayBuffer.byteLength,
        sizeMB: (arrayBuffer.byteLength / 1024 / 1024).toFixed(2)
      });

      // 解码音频数据
      try {
        this.audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      } catch (decodeError) {
        console.error('❌ 音频解码失败:', decodeError);
        console.error('ArrayBuffer 信息:', {
          byteLength: arrayBuffer.byteLength,
          firstBytes: new Uint8Array(arrayBuffer.slice(0, 44))
        });
        throw new Error(`音频解码失败: ${decodeError.message}`);
      }

      console.log('✅ 音频加载完成:', {
        duration: this.audioBuffer.duration,
        sampleRate: this.audioBuffer.sampleRate,
        channels: this.audioBuffer.numberOfChannels
      });

      this._emit('durationchange', this.getDuration());

      return this.audioBuffer;

    } catch (error) {
      console.error('❌ 加载音频失败:', error);
      this._emit('error', error);
      throw error;
    }
  }

  /**
   * 从 SSE 流加载音频
   * @param {Object} requestData - 请求数据对象
   * @param {string} requestData.article_hash - 文章哈希
   * @param {string} requestData.text - 要转换的文本
   * @param {string} requestData.voice - 音色
   * @param {string} requestData.language - 语言
   * @param {boolean} requestData.use_cache - 是否使用缓存
   */
  async loadFromStream(requestData) {
    try {
      this._initAudioContext();

      // 先停止之前的播放和流（如果有）
      if (this.isPlaying || this.isPaused) {
        console.log('🛑 检测到新的播放请求，停止当前播放');
        this.stop();
      }

      // 中止之前的流请求（如果有）
      if (this.streamAbortController) {
        console.log('🛑 中止之前的流请求');
        this.streamAbortController.abort();
        this.streamAbortController = null;
      }

      // 初始化 StreamBuffer
      if (!this.streamBuffer) {
        this.streamBuffer = new StreamBuffer(this.audioContext);
      } else {
        this.streamBuffer.clear();
      }

      // 重置调度时间
      this.nextStartTime = 0;
      this.scheduledSources = [];

      // 清空旧的 audioBuffer
      this.audioBuffer = null;

      // 设置流式模式标志
      this.isStreamMode = true;
      this.isTTSComplete = false;
      this.shouldScheduleChunks = true;

      console.log('📡 开始流式加载音频');

      // 创建新的 AbortController 用于取消请求
      this.streamAbortController = new AbortController();

      // 使用 fetch 发送 POST 请求
      const response = await fetch('/api/tts/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify(requestData),
        signal: this.streamAbortController.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // 启动后台流处理（非阻塞）
      this._processStream(response).catch(error => {
        console.error('❌ 流处理错误:', error);
        this._emit('error', error);
      });

      // 立即返回，不等待流完成
      console.log('✅ 流式加载已启动（后台处理）');

    } catch (error) {
      console.error('❌ 流式加载音频失败:', error);
      this._emit('error', error);
      throw error;
    }
  }

  /**
   * 后台处理 SSE 流（非阻塞）
   * @private
   * @param {Response} response - Fetch Response 对象
   */
  async _processStream(response) {
    try {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        // 检查是否被中止
        if (this.streamAbortController?.signal.aborted) {
          console.log('🛑 流处理已被中止');
          reader.cancel();
          break;
        }

        const { done, value } = await reader.read();

        if (done) {
          console.log('📡 流读取完成');
          break;
        }

        // 解码数据块
        buffer += decoder.decode(value, { stream: true });

        // 处理完整的事件
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // 保留不完整的部分

        for (const line of lines) {
          if (!line.trim()) continue;

          // 解析 SSE 事件
          const eventMatch = line.match(/^event:\s*(.+)$/m);
          const dataMatch = line.match(/^data:\s*(.+)$/m);

          if (!eventMatch || !dataMatch) continue;

          const eventType = eventMatch[1].trim();
          const eventData = JSON.parse(dataMatch[1]);

          // 处理不同类型的事件
          if (eventType === 'cached') {
            console.log('💾 使用缓存音频:', eventData.audio_url);
            await this.loadFromUrl(eventData.audio_url);
            return;
          } else if (eventType === 'chunk') {
            console.log('📦 收到音频块:', eventData.index, '| shouldSchedule:', this.shouldScheduleChunks);
            if (this.streamBuffer) {
              const floatData = this.streamBuffer.appendChunk(eventData.data);
              const chunkBuffer = this.streamBuffer.createChunkAudioBuffer(floatData);

              // 只在允许调度时才调度播放（支持暂停时继续缓冲）
              if (this.shouldScheduleChunks) {
                this.scheduleChunk(chunkBuffer);
                console.log('✅ 已调度音频块', eventData.index);
              } else {
                console.log('⏸️ 暂停中，仅缓存块', eventData.index, '不调度播放');
              }

              // 如果是第一个块，触发播放事件并更新 duration
              if (eventData.index === 1 && this.shouldScheduleChunks) {
                this.isPlaying = true;
                this.isPaused = false;
                this._startProgressTimer();
                this._emit('play');
                console.log('▶️ 开始流式播放');
              }

              // 更新总时长（基于已接收的数据）
              const currentDuration = this.streamBuffer.getDuration();
              this._emit('durationchange', currentDuration);
            }
          } else if (eventType === 'complete') {
            console.log('✅ 音频生成完成:', eventData.audio_url);

            // 标记TTS已完成
            this.isTTSComplete = true;

            // 更新最终的 audioBuffer 以支持 seek 功能
            this.audioBuffer = this.streamBuffer.getAudioBuffer();
            const finalDuration = eventData.duration || this.getDuration();
            this._emit('durationchange', finalDuration);

            console.log('✅ 流式播放完成，总时长:', finalDuration);
            return;
          } else if (eventType === 'error') {
            const errorMessage = eventData.message || eventData.error || '音频生成失败';
            console.error('❌ SSE 错误:', errorMessage);
            const error = new Error(errorMessage);
            this._emit('error', error);
            throw error;
          }
        }
      }

    } catch (error) {
      console.error('❌ SSE 连接错误:', error);
      const err = new Error('网络连接失败: ' + error.message);
      this._emit('error', err);
      throw err;
    }
  }

  /**
   * 调度音频块播放
   * @param {AudioBuffer} audioBuffer 
   */
  scheduleChunk(audioBuffer) {
    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.playbackRate.value = this.playbackRate;
    source.connect(this.gainNode);

    // 计算开始时间
    // 如果是第一个块或落后了，立即开始（加一点延迟）
    const currentTime = this.audioContext.currentTime;
    if (this.nextStartTime < currentTime) {
      this.nextStartTime = currentTime + 0.1; // 100ms 延迟，给第一个块足够的准备时间
    }

    const startTime = this.nextStartTime;
    source.start(startTime);

    // 记录这个块的开始时间，用于计算当前播放位置
    if (this.scheduledSources.length === 0) {
      this.startTime = startTime;
    }

    this.nextStartTime += audioBuffer.duration / this.playbackRate;

    this.scheduledSources.push(source);

    console.log(`🎵 调度音频块 ${this.scheduledSources.length}:`, {
      startTime: startTime.toFixed(3),
      duration: audioBuffer.duration.toFixed(3),
      nextStartTime: this.nextStartTime.toFixed(3)
    });

    // 清理
    source.onended = () => {
      const index = this.scheduledSources.indexOf(source);
      if (index > -1) {
        this.scheduledSources.splice(index, 1);
      }

      // 如果所有源都播放完了，触发结束事件
      if (this.scheduledSources.length === 0 && this.isPlaying) {
        console.log('🎵 所有音频块播放完成');
        this.isPlaying = false;
        this.isPaused = false;
        this._stopProgressTimer();
        this._emit('ended');
      }
    };
  }

  /**
   * 播放音频
   */
  play() {
    // 如果是流式模式且已在播放，跳过（避免重复播放）
    if (this.isStreamMode && this.isPlaying && !this.isPaused) {
      console.log('ℹ️ 流式播放已在进行中，跳过 play() 调用');
      return;
    }

    // 流式模式下，如果还没有 audioBuffer，等待第一个块到达
    if (this.isStreamMode && !this.audioBuffer) {
      console.log('ℹ️ 流式模式：等待音频数据...');
      return;
    }

    if (!this.audioBuffer) {
      console.warn('⚠️ 没有可播放的音频');
      return;
    }

    this._initAudioContext();

    // 如果已经在播放，先停止
    if (this.isPlaying) {
      this._stopSource();
    }

    // 创建新的 source node
    this.sourceNode = this.audioContext.createBufferSource();
    this.sourceNode.buffer = this.audioBuffer;
    this.sourceNode.playbackRate.value = this.playbackRate;
    this.sourceNode.connect(this.gainNode);

    // 监听播放结束
    this.sourceNode.onended = () => {
      if (this.isPlaying) {
        console.log('🎵 播放结束');
        this.isPlaying = false;
        this.isPaused = false;
        this._stopProgressTimer();
        this._emit('ended');
      }
    };

    // 计算开始位置
    const offset = this.isPaused ? this.pauseTime : 0;

    // 开始播放
    this.sourceNode.start(0, offset);
    this.startTime = this.audioContext.currentTime - offset;
    this.isPlaying = true;
    this.isPaused = false;

    // 开始进度更新
    this._startProgressTimer();

    console.log('▶️ 开始播放:', { offset, playbackRate: this.playbackRate });
    this._emit('play');
  }

  /**
   * 暂停播放
   */
  pause() {
    if (!this.isPlaying) {
      console.log('⚠️ 当前未播放，无需暂停');
      return;
    }

    console.log('⏸️ 开始暂停播放...');

    // 停止所有流式调度的音频块
    this.scheduledSources.forEach(source => {
      try {
        source.stop();
      } catch (e) {
        // 忽略已经停止的错误
      }
    });
    this.scheduledSources = [];
    this.nextStartTime = 0;

    // 记录暂停位置
    this.pauseTime = this.getCurrentTime();

    // 停止调度新块，但继续接收数据（关键！）
    this.shouldScheduleChunks = false;

    // 停止播放
    this._stopSource();
    this.isPlaying = false;
    this.isPaused = true;

    // 停止进度更新
    this._stopProgressTimer();

    console.log('⏸️ 暂停播放完成:', { pauseTime: this.pauseTime });
    this._emit('pause');
  }

  /**
   * 恢复播放
   */
  resume() {
    if (!this.isPaused) {
      console.warn('⚠️ 当前未暂停，无需恢复');
      return;
    }

    console.log('▶️ 恢复播放，位置:', this.pauseTime, {
      isStreamMode: this.isStreamMode,
      isTTSComplete: this.isTTSComplete,
      hasAudioBuffer: !!this.audioBuffer,
      hasStreamBuffer: !!this.streamBuffer
    });

    // 将已缓存的数据转换为完整的 AudioBuffer
    if (this.streamBuffer) {
      const newBuffer = this.streamBuffer.getAudioBuffer();
      if (newBuffer) {
        this.audioBuffer = newBuffer;
        console.log('📦 从 StreamBuffer 更新 AudioBuffer，时长:', this.audioBuffer.duration.toFixed(2), '秒');
      }
    }

    if (!this.audioBuffer) {
      console.error('❌ 无法恢复播放：没有可用的音频数据');
      return;
    }

    // 标记流式模式结束，切换到标准播放模式
    // 这样可以避免双重播放问题（不再调度新块）
    if (this.isStreamMode) {
      console.log('🔄 切换到标准播放模式（避免双重播放）');
      this.isStreamMode = false;
      this.shouldScheduleChunks = false; // 关键：不再调度新块
    }

    // 使用标准 play() 方法从暂停位置播放完整音频
    this.play();

    console.log('✅ 恢复播放成功，从', this.pauseTime.toFixed(2), '秒开始');
    
    // 注意：后台 TTS 请求继续接收数据到 StreamBuffer
    // 但不会再调度播放，避免双重声音
  }


  /**
   * 停止播放
   */
  stop() {
    const wasPlaying = this.isPlaying || this.isPaused;
    
    if (!wasPlaying) {
      // 即使没有播放，也要清理流请求和资源
      if (this.streamAbortController) {
        console.log('🛑 清理未播放的流请求');
        this.streamAbortController.abort();
        this.streamAbortController = null;
      }
      return;
    }

    console.log('⏹️ 停止播放...');

    // 中止流请求
    if (this.streamAbortController) {
      this.streamAbortController.abort();
      this.streamAbortController = null;
      console.log('🛑 已中止流请求');
    }

    // 停止播放
    this._stopSource();

    // 停止所有调度的源
    this.scheduledSources.forEach(s => {
      try { s.stop(); } catch (e) { }
    });
    this.scheduledSources = [];
    this.nextStartTime = 0;
    if (this.streamBuffer) {
      this.streamBuffer.clear();
    }

    this.isPlaying = false;
    this.isPaused = false;
    this.pauseTime = 0;
    this.startTime = 0;
    this.isStreamMode = false;
    this.isTTSComplete = false;
    this.shouldScheduleChunks = true;

    // 停止进度更新
    this._stopProgressTimer();

    console.log('⏹️ 停止播放完成');
    this._emit('stop');
  }

  /**
   * 跳转到指定位置
   * @param {number} time - 目标时间（秒）
   */
  seek(time) {
    if (!this.audioBuffer) {
      return;
    }

    const duration = this.getDuration();
    const targetTime = Math.max(0, Math.min(time, duration));

    const wasPlaying = this.isPlaying;

    if (wasPlaying) {
      this._stopSource();
    }

    this.pauseTime = targetTime;
    this.isPaused = true;
    this.isPlaying = false;

    if (wasPlaying) {
      this.play();
    }

    console.log('⏩ Seek 到:', targetTime);
  }

  /**
   * 设置音量
   * @param {number} volume - 音量 (0.0 - 1.0)
   */
  setVolume(volume) {
    const clampedVolume = Math.max(0, Math.min(1, volume));

    if (this.gainNode) {
      this.gainNode.gain.value = clampedVolume;
      console.log('🔊 音量设置为:', clampedVolume);
    }
  }

  /**
   * 设置播放速度
   * @param {number} rate - 播放速度 (0.5 - 2.0)
   */
  setPlaybackRate(rate) {
    const clampedRate = Math.max(0.5, Math.min(2.0, rate));
    this.playbackRate = clampedRate;

    // 如果正在播放，更新当前 source 的速度
    if (this.sourceNode && this.isPlaying) {
      this.sourceNode.playbackRate.value = clampedRate;
    }

    console.log('🏃 播放速度设置为:', clampedRate);
  }

  /**
   * 获取当前播放位置
   * @returns {number} 当前时间（秒）
   */
  getCurrentTime() {
    if (this.isPaused) {
      return this.pauseTime;
    }

    if (this.isPlaying && this.audioContext && this.startTime > 0) {
      const elapsed = (this.audioContext.currentTime - this.startTime) * this.playbackRate;
      const duration = this.getDuration();
      return duration > 0 ? Math.min(elapsed, duration) : elapsed;
    }

    return 0;
  }

  /**
   * 获取音频总时长
   * @returns {number} 总时长（秒）
   */
  getDuration() {
    // 优先使用 audioBuffer 的时长（完整音频）
    if (this.audioBuffer) {
      return this.audioBuffer.duration;
    }

    // 如果正在流式播放，返回 StreamBuffer 的当前时长
    if (this.streamBuffer) {
      return this.streamBuffer.getDuration();
    }

    return 0;
  }

  /**
   * 获取播放状态
   * @returns {object} 状态对象
   */
  getState() {
    return {
      isPlaying: this.isPlaying,
      isPaused: this.isPaused,
      currentTime: this.getCurrentTime(),
      duration: this.getDuration(),
      playbackRate: this.playbackRate,
      volume: this.gainNode ? this.gainNode.gain.value : 1.0
    };
  }

  /**
   * 停止 source node
   * @private
   */
  _stopSource() {
    if (this.sourceNode) {
      try {
        this.sourceNode.stop();
      } catch (e) {
        // 忽略已经停止的错误
      }
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
  }

  /**
   * 开始进度更新定时器
   * @private
   */
  _startProgressTimer() {
    this._stopProgressTimer();

    const updateProgress = () => {
      if (this.isPlaying) {
        this._emit('timeupdate', this.getCurrentTime());
        this.progressTimer = requestAnimationFrame(updateProgress);
      }
    };

    this.progressTimer = requestAnimationFrame(updateProgress);
  }

  /**
   * 停止进度更新定时器
   * @private
   */
  _stopProgressTimer() {
    if (this.progressTimer) {
      cancelAnimationFrame(this.progressTimer);
      this.progressTimer = null;
    }
  }

  /**
   * 添加事件监听器
   * @param {string} event - 事件名称
   * @param {function} callback - 回调函数
   */
  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  /**
   * 移除事件监听器
   * @param {string} event - 事件名称
   * @param {function} callback - 回调函数
   */
  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  /**
   * 触发事件
   * @private
   * @param {string} event - 事件名称
   * @param {*} data - 事件数据
   */
  _emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`事件处理器错误 (${event}):`, error);
        }
      });
    }
  }

  /**
   * 清理资源
   */
  destroy() {
    console.log('🗑️ 清理 AudioPlayer 资源');

    this.stop();
    this._stopProgressTimer();

    if (this.gainNode) {
      this.gainNode.disconnect();
      this.gainNode = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.audioBuffer = null;
    this.listeners = {};
  }
}

export default AudioPlayer;
