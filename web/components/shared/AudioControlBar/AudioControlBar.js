export default {
    name: 'AudioControlBar',

    props: {
        articleHash: {
            type: String,
            required: true
        },
        articleText: {
            type: String,
            required: true
        }
    },

    data() {
        return {
            // Playback state
            isPlaying: false,
            isPaused: false,
            isLoading: false,
            isDownloading: false,

            // Time tracking
            currentTime: 0,
            duration: 0,
            buffered: 0,

            // Audio controls (simplified - voice hidden, volume removed)
            playbackRate: 1.0,
            selectedVoice: 'Cherry',  // Default voice, not shown in UI

            playbackRates: [
                { value: 0.5, label: '0.5x' },
                { value: 0.75, label: '0.75x' },
                { value: 1.0, label: '1.0x' },
                { value: 1.25, label: '1.25x' },
                { value: 1.5, label: '1.5x' },
                { value: 2.0, label: '2.0x' }
            ],

            // Error handling
            error: null,

            // Audio player instance
            audioPlayer: null,

            // Progress update interval
            progressInterval: null
        };
    },

    computed: {
        formattedCurrentTime() {
            return this.formatTime(this.currentTime);
        },

        formattedDuration() {
            return this.formatTime(this.duration);
        },

        progressPercentage() {
            if (this.duration === 0) return 0;
            return (this.currentTime / this.duration) * 100;
        },

        bufferedPercentage() {
            if (this.duration === 0) return 0;
            return (this.buffered / this.duration) * 100;
        },

        playButtonIcon() {
            if (this.isLoading) return '⏳';
            if (this.isPlaying) return '⏸️';
            return '▶️';
        },

        playButtonTooltip() {
            if (this.isLoading) return '加载中...';
            if (this.isPlaying) return '暂停';
            if (this.isPaused) return '继续播放';
            return '播放';
        },

        currentSpeedLabel() {
            return this.playbackRate === 1.0 ? '1.0x' : `${this.playbackRate}x`;
        }
    },

    watch: {
        // 监听文章切换
        articleHash(newHash, oldHash) {
            if (newHash !== oldHash) {
                console.log('📄 文章切换:', oldHash, '→', newHash);
                this.handleArticleChange();
            }
        }
    },

    mounted() {
        // Load user preferences from localStorage
        this.loadPreferences();
    },

    beforeUnmount() {
        // Clean up
        this.stopProgressTracking();
        if (this.audioPlayer) {
            this.audioPlayer.stop();
            this.audioPlayer = null;
        }
    },

    methods: {
        handleArticleChange() {
            // 停止当前播放
            if (this.audioPlayer) {
                console.log('🛑 停止当前文章的播放');
                this.audioPlayer.stop();
            }

            // 重置状态
            this.isPlaying = false;
            this.isPaused = false;
            this.isLoading = false;
            this.currentTime = 0;
            this.duration = 0;
            this.buffered = 0;
            this.error = null;

            // 停止进度跟踪
            this.stopProgressTracking();

            console.log('✅ 已重置播放器状态，准备播放新文章');
        },

        async togglePlayPause() {
            // 如果正在播放，暂停
            if (this.isPlaying) {
                this.pause();
                return;
            }

            // 如果已暂停，恢复播放
            if (this.isPaused) {
                this.resume();
                return;
            }

            // 否则开始新的播放
            await this.play();
        },

        async play() {
            try {
                this.error = null;

                // Validate article text
                if (!this.articleText || this.articleText.trim().length === 0) {
                    this.error = '无法播放:文章内容为空';
                    return;
                }

                this.isLoading = true;

                // Initialize audio player if not already done
                if (!this.audioPlayer) {
                    // Import AudioPlayer dynamically
                    const AudioPlayerModule = await import('/utils/AudioPlayer.js');
                    const AudioPlayer = AudioPlayerModule.AudioPlayer || AudioPlayerModule.default;
                    this.audioPlayer = new AudioPlayer();

                    // Set up event listeners
                    this.setupAudioPlayerEvents();
                }

                // Load audio from stream
                const requestData = {
                    article_hash: this.articleHash,
                    text: this.articleText,
                    voice: this.selectedVoice,
                    language: 'Chinese',
                    use_cache: true,
                    skip_code_blocks: true
                };

                await this.audioPlayer.loadFromStream(requestData);

                // Apply user preferences
                this.audioPlayer.setPlaybackRate(this.playbackRate);

                // 流式播放会自动开始，不需要手动调用 play()
                // 状态会通过事件监听器更新

            } catch (error) {
                console.error('[TTS] Play error:', error);
                this.error = '播放失败：' + error.message;
            } finally {
                this.isLoading = false;
            }
        },

        pause() {
            if (this.audioPlayer && this.isPlaying) {
                this.audioPlayer.pause();
                this.isPlaying = false;
                this.isPaused = true;
                this.stopProgressTracking();
            }
        },

        resume() {
            if (this.audioPlayer && this.isPaused) {
                this.audioPlayer.resume();
                this.isPlaying = true;
                this.isPaused = false;
                this.startProgressTracking();
            }
        },

        seek(event) {
            if (!this.audioPlayer || this.duration === 0) return;

            const progressBar = event.currentTarget;
            const rect = progressBar.getBoundingClientRect();
            const clickX = event.clientX - rect.left;
            const percentage = clickX / rect.width;
            const newTime = percentage * this.duration;

            this.audioPlayer.seek(newTime);
            this.currentTime = newTime;
        },

        async setPlaybackRate(event) {
            const newRate = parseFloat(event.target.value);
            this.playbackRate = newRate;

            if (this.audioPlayer) {
                this.audioPlayer.setPlaybackRate(newRate);
            }

            // Save preference
            this.savePreferences();
        },

        async downloadAudio() {
            if (this.isDownloading) return;

            try {
                this.isDownloading = true;
                this.error = null;

                // Use the generate endpoint to get the cache URL
                const response = await fetch('/api/tts/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        article_hash: this.articleHash,
                        text: this.articleText,
                        voice: this.selectedVoice,
                        language: 'Chinese',
                        use_cache: true,
                        skip_code_blocks: true
                    })
                });

                if (!response.ok) {
                    throw new Error('获取下载链接失败');
                }

                const data = await response.json();
                const downloadUrl = data.audio_url;

                // Trigger download
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = `audio_${this.articleHash}.wav`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

            } catch (error) {
                console.error('[TTS] Download error:', error);
                this.error = '下载失败：' + error.message;
            } finally {
                this.isDownloading = false;
            }
        },

        setupAudioPlayerEvents() {
            if (!this.audioPlayer) return;

            // Listen for audio player events
            this.audioPlayer.on('play', () => {
                this.isPlaying = true;
                this.isPaused = false;
                this.startProgressTracking();
            });

            this.audioPlayer.on('pause', () => {
                this.isPlaying = false;
                this.isPaused = true;
                this.stopProgressTracking();
            });

            this.audioPlayer.on('timeupdate', (time) => {
                this.currentTime = time;
            });

            this.audioPlayer.on('durationchange', (duration) => {
                this.duration = duration;
            });

            this.audioPlayer.on('ended', () => {
                this.isPlaying = false;
                this.isPaused = false;
                this.currentTime = 0;
                this.stopProgressTracking();
            });

            this.audioPlayer.on('error', (error) => {
                this.error = '播放出错：' + error.message;
                this.isPlaying = false;
                this.isLoading = false;
                this.stopProgressTracking();
            });

            this.audioPlayer.on('buffered', (bufferedTime) => {
                this.buffered = bufferedTime;
            });
        },

        startProgressTracking() {
            if (this.progressInterval) return;

            this.progressInterval = setInterval(() => {
                if (this.audioPlayer && this.isPlaying) {
                    this.currentTime = this.audioPlayer.getCurrentTime();
                }
            }, 100); // Update every 100ms
        },

        stopProgressTracking() {
            if (this.progressInterval) {
                clearInterval(this.progressInterval);
                this.progressInterval = null;
            }
        },

        formatTime(seconds) {
            if (!seconds || isNaN(seconds)) return '00:00';

            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        },

        loadPreferences() {
            try {
                const savedRate = localStorage.getItem('tts_playback_rate');
                if (savedRate) {
                    this.playbackRate = parseFloat(savedRate);
                }
            } catch (error) {
                console.warn('[TTS] Failed to load preferences:', error);
            }
        },

        savePreferences() {
            try {
                localStorage.setItem('tts_playback_rate', this.playbackRate.toString());
            } catch (error) {
                console.warn('[TTS] Failed to save preferences:', error);
            }
        }
    }
};
