/**
 * VersionSelector 组件
 * 文档版本选择器
 */
const VersionSelector = {
  props: {
    // 所有可用的版本列表
    versions: {
      type: Array,
      required: true,
      validator: (value) => {
        return value.every(v => 
          typeof v === 'object' && 
          typeof v.version === 'number'
        );
      }
    },
    
    // 当前选中的版本
    modelValue: {
      type: Number,
      required: true
    },
    
    // 自定义CSS类
    customClass: {
      type: String,
      default: ''
    },
    
    // 是否禁用
    disabled: {
      type: Boolean,
      default: false
    }
  },
  
  emits: ['update:modelValue', 'change'],
  
  setup(props, { emit }) {
    const { ref, computed } = Vue;
    
    // 下拉菜单显示状态
    const isOpen = ref(false);
    
    // 当前版本
    const currentVersion = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    });
    
    // 切换下拉菜单
    const toggleDropdown = () => {
      if (props.disabled) return;
      isOpen.value = !isOpen.value;
    };
    
    // 选择版本
    const selectVersion = (version) => {
      if (props.disabled) return;
      if (version !== currentVersion.value) {
        currentVersion.value = version;
        emit('change', version);
      }
      isOpen.value = false;
    };
    
    // 点击外部关闭下拉菜单
    const handleClickOutside = (event) => {
      const versionSelector = event.target.closest('.version-selector');
      // 如果点击的不是版本选择器内部，则关闭下拉菜单
      if (!versionSelector) {
        isOpen.value = false;
      }
    };
    
    // 监听全局点击事件
    Vue.onMounted(() => {
      document.addEventListener('click', handleClickOutside);
    });
    
    Vue.onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside);
    });
    
    return {
      isOpen,
      currentVersion,
      toggleDropdown,
      selectVersion
    };
  }
};

export default VersionSelector;
