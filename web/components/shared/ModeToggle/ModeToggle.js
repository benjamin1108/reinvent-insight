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
        },
        // 紧凑模式（用于 AppHeader 等小空间场景）
        compact: {
            type: Boolean,
            default: false
        }
    },
    
    emits: ['mode-change'],
    
    computed: {
        isDisabled() {
            return !this.visualAvailable || this.visualStatus !== 'completed';
        },
        
        isQuickMode() {
            return this.currentMode === 'quick';
        },
        
        switchTooltip() {
            if (this.isDisabled) {
                if (this.visualStatus === 'processing') {
                    return '可视化解读生成中...';
                }
                return '可视化解读尚未生成';
            }
            return this.isQuickMode ? '切换到 Deep Insight' : '切换到 Visual Insight';
        }
    },
    
    methods: {
        handleToggle() {
            if (this.isDisabled) return;
            const newMode = this.isQuickMode ? 'deep' : 'quick';
            this.$emit('mode-change', newMode);
        },
        
        handleLabelClick(mode) {
            if (this.isDisabled && mode === 'quick') return;
            if (this.currentMode !== mode) {
                this.$emit('mode-change', mode);
            }
        }
    }
};
