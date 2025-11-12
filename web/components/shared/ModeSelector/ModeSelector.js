/**
 * ModeSelector 组件
 * 提供显示模式切换的UI控件
 */
export default {
  props: {
    // 当前激活的模式
    currentMode: {
      type: String,
      default: 'full-analysis',
      validator: (value) => ['core-summary', 'simplified-text', 'full-analysis'].includes(value)
    },
    
    // 可用的模式列表
    modes: {
      type: Array,
      default: () => [
        { id: 'core-summary', label: '核心要点', icon: '📌', shortLabel: '要点' },
        { id: 'simplified-text', label: '精简摘要', icon: '📝', shortLabel: '摘要' },
        { id: 'full-analysis', label: '完整解读', icon: '📖', shortLabel: '全文' }
      ]
    }
  },
  
  emits: ['mode-change'],
  
  setup(props, { emit }) {
    const { ref } = Vue;
    
    // 处理模式切换
    const handleModeClick = (modeId) => {
      if (modeId !== props.currentMode) {
        emit('mode-change', modeId);
      }
    };
    
    // 判断是否为激活模式
    const isActive = (modeId) => {
      return modeId === props.currentMode;
    };
    
    return {
      handleModeClick,
      isActive
    };
  }
};
