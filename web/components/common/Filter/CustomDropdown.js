/**
 * CustomDropdown 组件
 * 通用的自定义下拉菜单组件，可被LevelFilter和YearFilter使用
 */
const CustomDropdown = {
  props: {
    // 选中的值
    modelValue: {
      type: String,
      default: ''
    },
    
    // 选项列表
    options: {
      type: Array,
      required: true,
      validator: (options) => {
        return options.every(opt => 
          typeof opt === 'object' &&
          'value' in opt &&
          'label' in opt
        );
      }
    },
    
    // 占位文本
    placeholder: {
      type: String,
      default: '请选择'
    },
    
    // 是否禁用
    disabled: {
      type: Boolean,
      default: false
    },
    
    // 自定义类名
    customClass: {
      type: String,
      default: ''
    }
  },
  
  emits: ['update:modelValue', 'change'],
  
  setup(props, { emit }) {
    const { ref, computed, onMounted, onUnmounted } = Vue;
    
    // 下拉菜单显示状态
    const showDropdown = ref(false);
    
    // 当前显示的文本
    const displayText = computed(() => {
      if (!props.modelValue) return props.placeholder;
      
      const selectedOption = props.options.find(opt => opt.value === props.modelValue);
      return selectedOption ? selectedOption.label : props.placeholder;
    });
    
    // 切换下拉菜单
    const toggleDropdown = () => {
      if (props.disabled) return;
      showDropdown.value = !showDropdown.value;
    };
    
    // 选择选项
    const selectOption = (value) => {
      if (props.disabled) return;
      
      emit('update:modelValue', value);
      emit('change', value);
      showDropdown.value = false;
    };
    
    // 点击外部关闭下拉菜单
    const handleClickOutside = (event) => {
      const dropdown = event.target.closest('.custom-dropdown');
      if (!dropdown || !dropdown.contains(event.target)) {
        showDropdown.value = false;
      }
    };
    
    onMounted(() => {
      document.addEventListener('click', handleClickOutside);
    });
    
    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside);
    });
    
    return {
      showDropdown,
      displayText,
      toggleDropdown,
      selectOption
    };
  }
}; 

// 暴露到window对象以支持旧代码
if (typeof window !== 'undefined') {
  window.CustomDropdown = CustomDropdown;
}

export default CustomDropdown;