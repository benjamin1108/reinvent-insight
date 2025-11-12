export default {
    name: 'ModeToggle',
    
    props: {
        currentMode: {
            type: String,
            default: 'deep',
            validator: (value) => ['deep', 'quick'].includes(value)
        },
        visualAvailable: {
            type: Boolean,
            default: false
        },
        visualStatus: {
            type: String,
            default: 'pending',  // 'pending' | 'processing' | 'completed' | 'failed'
        }
    },
    
    emits: ['mode-change'],
    
    data() {
        return {
            modes: [
                {
                    id: 'deep',
                    label: 'Deep Insight',
                    icon: '📖',
                    description: '完整深度解读'
                },
                {
                    id: 'quick',
                    label: 'Quick Insight',
                    icon: '⚡',
                    description: '可视化解读'
                }
            ]
        };
    },
    
    computed: {
        isQuickModeDisabled() {
            return !this.visualAvailable || this.visualStatus !== 'completed';
        },
        
        quickModeTooltip() {
            if (!this.visualAvailable) {
                return '可视化解读尚未生成';
            }
            if (this.visualStatus === 'processing') {
                return '正在生成可视化解读...';
            }
            if (this.visualStatus === 'failed') {
                return '可视化解读生成失败';
            }
            return '切换到可视化解读';
        }
    },
    
    methods: {
        handleModeChange(modeId) {
            if (modeId === 'quick' && this.isQuickModeDisabled) {
                return;
            }
            this.$emit('mode-change', modeId);
        }
    }
};
