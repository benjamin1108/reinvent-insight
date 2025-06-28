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
        // 支持字符串数组或对象数组
        return value.every(v => 
          typeof v === 'string' || 
          (typeof v === 'object' && v !== null && 'version' in v)
        );
      }
    },
    
    // 当前选中的版本
    currentVersion: {
      type: [String, Number],
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
  
  emits: ['change'],
  
  setup(props, { emit }) {
    const { ref, computed, watch } = Vue;
    
    // 下拉菜单显示状态
    const isOpen = ref(false);
    
    // 内部版本状态
    const internalVersion = ref(props.currentVersion);
    
    // 监听外部版本变化
    watch(() => props.currentVersion, (newVersion) => {
      internalVersion.value = newVersion;
    });
    
    // 规范化版本列表，确保统一格式
    const normalizedVersions = computed(() => {
      return props.versions.map(v => {
        if (typeof v === 'string') {
          // 如果是字符串，转换为对象格式
          return { version: v };
        }
        return v;
      });
    });
    
    // 切换下拉菜单
    const toggleDropdown = () => {
      if (props.disabled) return;
      isOpen.value = !isOpen.value;
    };
    
    // 选择版本
    const selectVersion = (version) => {
      if (props.disabled) return;
      if (version !== internalVersion.value) {
        internalVersion.value = version;
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
      currentVersion: internalVersion,
      toggleDropdown,
      selectVersion,
      normalizedVersions
    };
  }
};

export default VersionSelector;
