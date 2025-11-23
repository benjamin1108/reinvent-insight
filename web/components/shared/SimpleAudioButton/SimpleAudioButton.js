/**
 * SimpleAudioButton - 极简音频播放按钮
 * 只有播放/暂停功能，集成到AppHeader中
 */
export default {
    name: 'SimpleAudioButton',

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
            isPlaying: false,
            isPaused: false,
            isLoading: false,
            audioPlayer: null,
            error: null,
            selectedVoice: 'Cherry',
            playbackRate: 1.0
        };
    },

    computed: {
        buttonIcon() {
            if (this.isLoading) return '⏳';
            if (this.isPlaying) return '⏸';
            return '▶';
        },

        buttonTooltip() {
            if (this.isLoading) return '加载中...';
            if (this.isPlaying) return '暂停';
            if (this.isPaused) return '继续播放';
            return '播放音频';
        }
    },

    mounted() {
        console.log('🎵 [SimpleAudioButton] 组件已挂载:', {
            articleHash: this.articleHash,
            articleTextLength: this.articleText?.length || 0
        });
    },

    beforeUnmount() {
        console.log('🎵 [SimpleAudioButton] 组件卸载');
        if (this.audioPlayer) {
            this.audioPlayer.stop();
            this.audioPlayer = null;
        }
    },

    methods: {
        async togglePlay() {
            if (this.isPlaying) {
                this.pause();
            } else {
                await this.play();
            }
        },

        async play() {
            try {
                this.error = null;

                if (!this.articleText || this.articleText.trim().length === 0) {
                    this.showError('无法播放：文章内容为空');
                    return;
                }

                this.isLoading = true;

                // 初始化音频播放器
                if (!this.audioPlayer) {
                    const AudioPlayerModule = await import('/utils/AudioPlayer.js');
                    const AudioPlayer = AudioPlayerModule.AudioPlayer || AudioPlayerModule.default;
                    this.audioPlayer = new AudioPlayer();
                    this.setupAudioPlayerEvents();
                }

                // 如果是暂停状态，恢复播放
                if (this.isPaused) {
                    this.audioPlayer.resume();  // 使用 resume() 而不是 play()
                    this.isPlaying = true;
                    this.isPaused = false;
                    this.isLoading = false;
                    return;
                }

                // 加载音频
                const requestData = {
                    article_hash: this.articleHash,
                    text: this.articleText,
                    voice: this.selectedVoice,
                    language: 'Chinese',
                    use_cache: true,
                    skip_code_blocks: true
                };

                await this.audioPlayer.loadFromStream(requestData);
                this.audioPlayer.setPlaybackRate(this.playbackRate);

                // 只在非流式模式或未播放时调用 play()
                // 流式模式会在接收第一个块时自动开始播放
                if (!this.audioPlayer.isStreamMode || !this.audioPlayer.isPlaying) {
                    this.audioPlayer.play();
                }


                this.isPlaying = true;
                this.isPaused = false;

            } catch (error) {
                console.error('[TTS] Play error:', error);
                this.showError('播放失败：' + error.message);
            } finally {
                this.isLoading = false;
            }
        },

        pause() {
            if (this.audioPlayer && this.isPlaying) {
                this.audioPlayer.pause();
                this.isPlaying = false;
                this.isPaused = true;
            }
        },

        setupAudioPlayerEvents() {
            if (!this.audioPlayer) return;

            this.audioPlayer.on('ended', () => {
                this.isPlaying = false;
                this.isPaused = false;
            });

            this.audioPlayer.on('error', (error) => {
                this.showError('播放出错：' + error.message);
                this.isPlaying = false;
                this.isLoading = false;
            });
        },

        showError(message) {
            this.error = message;
            setTimeout(() => {
                this.error = null;
            }, 3000);
        }
    }
};
