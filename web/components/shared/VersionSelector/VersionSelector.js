/**
 * VersionSelector 组件
 * 文档版本选择器
 */
export default {
  props: {
    // 所有可用的版本列表
    versions: {
      type: Array,
      required: true,
      validator: (value) => {
        // 只支持包含version字段的对象数组，version必须是数字
        return value.every(v => 
          typeof v === 'object' && v !== null && 'version' in v && 
          (typeof v.version === 'number' || !isNaN(Number(v.version)))
        );
      }
    },
    
    // 当前选中的版本
    currentVersion: {
      type: Number, // 强制要求为数字
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
        // 统一处理为数字类型，不再支持字符串格式
        if (typeof v === 'object' && v !== null && 'version' in v) {
          const numVersion = Number(v.version);
          if (isNaN(numVersion) || !isFinite(numVersion)) {
            console.error('版本号必须是有效数字:', v.version);
            return { ...v, version: 0 };
          }
          return { ...v, version: numVersion };
        } else {
          console.error('版本数据格式错误，必须是包含version字段的对象:', v);
          return { version: 0, title: '无效版本' };
        }
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
      
      const versionNumber = Number(version); // 确保是数字
      if (versionNumber !== internalVersion.value) {
        internalVersion.value = versionNumber;
        emit('change', versionNumber);
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
