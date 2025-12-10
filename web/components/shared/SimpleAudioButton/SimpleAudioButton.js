/**
 * SimpleAudioButton - 极简音频播放按钮
 * 支持预生成音频和移动端熄屏播放
 */
export default {
    name: 'SimpleAudioButton',

    props: {
        articleHash: {
            type: String,
            required: true
        },
        articleTitle: {
            type: String,
            default: '文章音频'
        },
        articleText: {
            type: String,
            default: ''
        },
        autoCheck: {
            type: Boolean,
            default: true
        },
        showIfReady: {
            type: Boolean,
            default: false  // 默认总是显示按钮
        }
    },

    data() {
        return {
            isPlaying: false,
            isPaused: false,
            isLoading: false,
            audioElement: null,
            error: null,
            audioUrl: null,
            hasAudio: false,
            audioStatus: 'none', // 'none', 'pending', 'processing', 'ready'
            isVisible: true,  // 总是显示按钮
            isGenerating: false,  // 是否正在生成中
            generationProgress: 0,  // 生成进度 (0-100)
            pollInterval: null,  // 轮询定时器
            taskId: null,  // 生成任务 ID
            waitingForPartial: false  // 是否正在等待部分音频
        };
    },

    computed: {
        buttonIcon() {
            if (this.isLoading) return '⏳';  // 加载中
            if (this.isPlaying) return '⏸';  // 暂停
            // 生成中也显示播放图标，表明可以点击
            return '▶';  // 播放
        },

        buttonTooltip() {
            if (this.waitingForPartial) {
                return '正在准备音频，马上开始...';
            }
            if (this.isGenerating) {
                return `音频生成中 ${this.generationProgress}%，点击播放已生成部分`;
            }
            if (this.audioStatus === 'processing') return '音频生成中...（点击播放）';
            if (this.isLoading) return '加载中...';
            if (this.isPlaying) return '暂停';
            if (this.isPaused) return '继续播放';
            if (this.audioStatus === 'ready') return '播放音频';
            return '播放音频（首次需生成）';
        },

        buttonText() {
            if (this.isGenerating) {
                return `${this.generationProgress}%`;
            }
            return '';
        }
    },

    async mounted() {
        // 自动检查音频状态
        if (this.autoCheck) {
            await this.checkAudioStatus();
        }

        // 初始化 MediaSession API
        this.setupMediaSession();
    },

    beforeUnmount() {
        this.cleanup();
        // 清理轮询定时器
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        // 清理等待状态
        this.waitingForPartial = false;
    },

    methods: {
        async checkAudioStatus() {
            try {
                const response = await fetch(`/api/tts/status/${this.articleHash}`);
                if (!response.ok) {
                    this.audioStatus = 'none';
                    this.isVisible = true;
                    return;
                }

                const data = await response.json();
                this.hasAudio = data.has_audio;
                this.audioStatus = data.status;
                this.audioUrl = data.audio_url;

                // 总是显示按钮
                this.isVisible = true;


                // 如果正在生成中，启动轮询
                if (data.status === 'processing' || data.status === 'pending') {
                    this.isGenerating = true;
                    this.startPolling();
                }
            } catch (error) {
                console.error('查询音频状态失败:', error);
                this.audioStatus = 'none';
                this.isVisible = true;
            }
        },

        async togglePlay() {
            // 如果正在播放，暂停
            if (this.isPlaying) {
                this.pause();
                return;
            }

            // 其他情况都尝试播放
            await this.play();
        },

        async play() {
            try {
                this.error = null;

                // 如果音频已准备好，直接播放
                if (this.audioUrl && this.audioStatus === 'ready') {
                    this.isLoading = true;

                    // 初始化音频元素
                    if (!this.audioElement) {
                        this.audioElement = new Audio();
                        this.setupAudioEvents();
                    }

                    // 如果是暂停状态，恢复播放
                    if (this.isPaused) {
                        this.audioElement.play();
                        this.isPlaying = true;
                        this.isPaused = false;
                        this.isLoading = false;
                        return;
                    }

                    // 加载音频
                    this.audioElement.src = this.audioUrl;
                    await this.audioElement.play();

                    this.isPlaying = true;
                    this.isPaused = false;

                    // 更新 MediaSession 元数据
                    this.updateMediaSessionMetadata();
                    this.isLoading = false;
                    return;
                }

                // 如果正在生成中，检查是否有部分音频
                if (this.isGenerating) {
                    // 先查询最新状态
                    const status = await this.fetchAudioStatus();
                    
                    if (status && status.has_partial && status.partial_url) {
                        // 有部分音频，播放它
                        await this.playPartialAudio(status.partial_url);
                        return;
                    } else {
                        // 没有部分音频，启动等待模式
                        const chunksGenerated = status?.chunks_generated || 0;
                        this.showInfo(`准备中... ${chunksGenerated}/10 片段`);
                        
                        // 启动快速轮询，等待部分音频
                        this.waitingForPartial = true;
                        this.startWaitingForPartial();
                        return;
                    }
                }

                // 否则触发生成
                await this.triggerGeneration();

            } catch (error) {
                console.error('[TTS] Play error:', error);
                this.showError('播放失败：' + error.message);
                this.isLoading = false;
            }
        },

        pause() {
            if (this.audioElement && this.isPlaying) {
                this.audioElement.pause();
                this.isPlaying = false;
                this.isPaused = true;
            }
            // 注意：不停止后台缓存生成
        },

        async fetchAudioStatus() {
            try {
                const response = await fetch(`/api/tts/status/${this.articleHash}`);
                if (!response.ok) return null;
                return await response.json();
            } catch (error) {
                console.error('查询音频状态失败:', error);
                return null;
            }
        },

        async playPartialAudio(partialUrl) {
            try {
                this.isLoading = true;

                // 初始化音频元素
                if (!this.audioElement) {
                    this.audioElement = new Audio();
                    this.setupAudioEvents();
                }

                // 加载部分音频
                this.audioElement.src = partialUrl;
                await this.audioElement.play();

                this.isPlaying = true;
                this.isPaused = false;

                // 更新 MediaSession 元数据
                this.updateMediaSessionMetadata();


            } catch (error) {
                console.error('播放部分音频失败:', error);
                this.showError('播放失败：' + error.message);
            } finally {
                this.isLoading = false;
            }
        },

        async triggerGeneration() {
            try {
                this.isGenerating = true;
                this.generationProgress = 0;

                const response = await fetch('/api/tts/pregenerate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        article_hash: this.articleHash,
                        text: this.articleText || ''
                    })
                });

                if (!response.ok) {
                    throw new Error('触发生成失败');
                }

                const data = await response.json();
                this.taskId = data.task_id;


                // 开始轮询进度
                this.startPolling();

            } catch (error) {
                console.error('触发音频生成失败:', error);
                this.showError('生成失败：' + error.message);
                this.isGenerating = false;
            }
        },

        startPolling() {
            // 清除旧的轮询
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
            }

            // 每 2 秒轮询一次
            this.pollInterval = setInterval(async () => {
                await this.checkGenerationProgress();
            }, 2000);

            // 立即执行一次
            this.checkGenerationProgress();
        },

        startWaitingForPartial() {
            
            // 清除旧的轮询
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
            }

            // 快速轮询：每 1 秒检查一次
            this.pollInterval = setInterval(async () => {
                await this.checkPartialAudio();
            }, 1000);

            // 立即执行一次
            this.checkPartialAudio();
        },

        async checkPartialAudio() {
            try {
                const status = await this.fetchAudioStatus();
                
                if (!status) return;

                const chunksGenerated = status.chunks_generated || 0;

                // 更新提示信息
                this.showInfo(`准备中... ${chunksGenerated}/10 片段`);

                // 检查是否有部分音频
                if (status.has_partial && status.partial_url) {
                    // 找到部分音频！
                    
                    // 停止快速轮询
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }
                    
                    this.waitingForPartial = false;
                    
                    // 播放部分音频
                    await this.playPartialAudio(status.partial_url);
                    
                    // 恢复正常轮询，继续监控进度
                    this.startPolling();
                } else if (status.status === 'ready') {
                    // 已经完成了！直接播放完整音频
                    
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }
                    
                    this.waitingForPartial = false;
                    this.audioStatus = 'ready';
                    this.audioUrl = status.audio_url;
                    this.isGenerating = false;
                    
                    // 播放完整音频
                    await this.play();
                }
            } catch (error) {
                console.error('检查部分音频失败:', error);
            }
        },

        async checkGenerationProgress() {
            try {
                const response = await fetch(`/api/tts/status/${this.articleHash}`);
                if (!response.ok) {
                    return;
                }

                const data = await response.json();
                

                // 使用后端计算的进度
                if (data.progress_percent > 0) {
                    this.generationProgress = data.progress_percent;
                } else if (data.status === 'pending') {
                    this.generationProgress = 10;
                } else if (data.status === 'processing') {
                    // 根据时间估算进度，最多 90%
                    this.generationProgress = Math.min(90, this.generationProgress + 5);
                } else if (data.status === 'ready') {
                    this.generationProgress = 100;
                    this.audioStatus = 'ready';
                    this.audioUrl = data.audio_url;
                    this.isGenerating = false;
                    
                    // 停止轮询
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }

                    
                    // 如果正在播放部分音频，替换为完整音频
                    if (this.isPlaying && this.audioElement) {
                        const currentTime = this.audioElement.currentTime;
                        this.audioElement.src = data.audio_url;
                        this.audioElement.currentTime = currentTime;
                        await this.audioElement.play();
                    } else {
                        // 自动开始播放
                        setTimeout(() => {
                            this.play();
                        }, 500);
                    }
                }
            } catch (error) {
                console.error('检查生成进度失败:', error);
            }
        },

        stop() {
            if (this.audioElement) {
                this.audioElement.pause();
                this.audioElement.currentTime = 0;
                this.isPlaying = false;
                this.isPaused = false;
            }
        },

        setupAudioEvents() {
            if (!this.audioElement) return;

            this.audioElement.addEventListener('ended', () => {
                this.isPlaying = false;
                this.isPaused = false;
            });

            this.audioElement.addEventListener('error', (error) => {
                this.showError('播放出错：' + error.message);
                this.isPlaying = false;
                this.isLoading = false;
            });

            this.audioElement.addEventListener('pause', () => {
            });

            this.audioElement.addEventListener('play', () => {
            });
        },

        setupMediaSession() {
            if (!('mediaSession' in navigator)) {
                return;
            }


            // 设置控制器
            navigator.mediaSession.setActionHandler('play', () => {
                this.play();
            });

            navigator.mediaSession.setActionHandler('pause', () => {
                this.pause();
            });

            navigator.mediaSession.setActionHandler('stop', () => {
                this.stop();
            });

            // 快进/快退
            navigator.mediaSession.setActionHandler('seekbackward', () => {
                if (this.audioElement) {
                    this.audioElement.currentTime = Math.max(0, this.audioElement.currentTime - 10);
                }
            });

            navigator.mediaSession.setActionHandler('seekforward', () => {
                if (this.audioElement) {
                    this.audioElement.currentTime = Math.min(
                        this.audioElement.duration,
                        this.audioElement.currentTime + 10
                    );
                }
            });
        },

        updateMediaSessionMetadata() {
            if (!('mediaSession' in navigator)) return;

            navigator.mediaSession.metadata = new MediaMetadata({
                title: this.articleTitle,
                artist: 'ReInvent Insight',
                album: '深度解读',
                // artwork: [
                //     { src: '/path/to/cover.png', sizes: '512x512', type: 'image/png' }
                // ]
            });

        },

        cleanup() {
            if (this.audioElement) {
                this.audioElement.pause();
                this.audioElement.src = '';
                this.audioElement = null;
            }

            // 清理 MediaSession
            if ('mediaSession' in navigator) {
                navigator.mediaSession.metadata = null;
                navigator.mediaSession.setActionHandler('play', null);
                navigator.mediaSession.setActionHandler('pause', null);
                navigator.mediaSession.setActionHandler('stop', null);
                navigator.mediaSession.setActionHandler('seekbackward', null);
                navigator.mediaSession.setActionHandler('seekforward', null);
            }
        },

        showError(message) {
            this.error = message;
            setTimeout(() => {
                this.error = null;
            }, 3000);
        },

        showInfo(message) {
            console.log('ℹ️', message);
            // 可以在这里添加 toast 提示
        }
    }
};
