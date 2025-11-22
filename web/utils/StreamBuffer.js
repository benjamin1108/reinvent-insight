/**
 * StreamBuffer - 流式音频缓冲管理器
 * 
 * 管理流式接收的音频数据块，并转换为可播放的 AudioBuffer
 */

export class StreamBuffer {
  constructor(audioContext) {
    this.audioContext = audioContext;
    this.chunks = [];
    this.sampleRate = 24000;  // Qwen3-TTS 采样率
    this.channels = 1;         // 单声道
    this.totalSamples = 0;

    console.log('🎵 StreamBuffer 初始化:', {
      sampleRate: this.sampleRate,
      channels: this.channels
    });
  }

  /**
   * 追加音频块
   * @param {string} base64Data - Base64 编码的 PCM 数据
   * @returns {Float32Array} 解码后的音频数据
   */
  appendChunk(base64Data) {
    try {
      // Base64 解码
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // 转换为 Int16Array (16-bit PCM)
      const pcmData = new Int16Array(bytes.buffer);

      // 转换为 Float32Array (-1.0 到 1.0)
      const floatData = new Float32Array(pcmData.length);
      for (let i = 0; i < pcmData.length; i++) {
        floatData[i] = pcmData[i] / 32768.0;  // 16-bit PCM 归一化
      }

      this.chunks.push(floatData);
      this.totalSamples += floatData.length;

      console.log('📦 追加音频块:', {
        chunkIndex: this.chunks.length - 1,
        samples: floatData.length,
        totalSamples: this.totalSamples,
        duration: this.getDuration()
      });

      return floatData;

    } catch (error) {
      console.error('❌ 追加音频块失败:', error);
      throw error;
    }
  }

  /**
   * 从单个数据块创建 AudioBuffer
   * @param {Float32Array} floatData - 音频数据
   * @returns {AudioBuffer}
   */
  createChunkAudioBuffer(floatData) {
    const audioBuffer = this.audioContext.createBuffer(
      this.channels,
      floatData.length,
      this.sampleRate
    );
    audioBuffer.getChannelData(0).set(floatData);
    return audioBuffer;
  }

  /**
   * 获取完整的 AudioBuffer
   * @returns {AudioBuffer} 可播放的音频缓冲区
   */
  getAudioBuffer() {
    if (this.chunks.length === 0) {
      console.warn('⚠️ 没有音频数据');
      return null;
    }

    try {
      // 创建 AudioBuffer
      const audioBuffer = this.audioContext.createBuffer(
        this.channels,
        this.totalSamples,
        this.sampleRate
      );

      // 获取通道数据
      const channelData = audioBuffer.getChannelData(0);

      // 拷贝所有块到 AudioBuffer
      let offset = 0;
      for (const chunk of this.chunks) {
        channelData.set(chunk, offset);
        offset += chunk.length;
      }

      console.log('✅ AudioBuffer 创建完成:', {
        duration: audioBuffer.duration,
        sampleRate: audioBuffer.sampleRate,
        channels: audioBuffer.numberOfChannels,
        length: audioBuffer.length
      });

      return audioBuffer;

    } catch (error) {
      console.error('❌ 创建 AudioBuffer 失败:', error);
      throw error;
    }
  }

  /**
   * 获取当前缓冲的音频时长
   * @returns {number} 时长（秒）
   */
  getDuration() {
    return this.totalSamples / this.sampleRate;
  }

  /**
   * 获取已缓冲的数据量
   * @returns {number} 样本数
   */
  getBufferedAmount() {
    return this.totalSamples;
  }

  /**
   * 检查是否有足够的数据开始播放
   * @param {number} minSeconds - 最小缓冲时长（秒）
   * @returns {boolean} 是否可以开始播放
   */
  hasEnoughData(minSeconds = 2.0) {
    return this.getDuration() >= minSeconds;
  }

  /**
   * 清空缓冲区
   */
  clear() {
    this.chunks = [];
    this.totalSamples = 0;
    console.log('🗑️ StreamBuffer 已清空');
  }

  /**
   * 获取缓冲区状态
   * @returns {object} 状态对象
   */
  getState() {
    return {
      chunks: this.chunks.length,
      totalSamples: this.totalSamples,
      duration: this.getDuration(),
      sampleRate: this.sampleRate,
      channels: this.channels
    };
  }
}

export default StreamBuffer;
