/**
 * LevelFilter 组件
 * 课程级别筛选器
 */

const LevelFilter = {
  // 不在这里声明components，因为CustomDropdown是通过ComponentLoader全局注册的
  
  props: {
    // 当前选中的级别
    modelValue: {
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
    const { computed } = Vue;
    
    // 级别选项
    const levelOptions = computed(() => [
      { value: '', label: '全部级别' },
      { value: '100', label: '100-基础' },
      { value: '200', label: '200-中级' },
      { value: '300', label: '300-高级' },
      { value: '400', label: '400-专家' },
      { value: 'Keynote', label: 'Keynote演讲' }
    ]);
    
    // 占位文本
    const placeholder = computed(() => {
      if (!props.modelValue) return '全部级别';
      const selected = levelOptions.value.find(opt => opt.value === props.modelValue);
      if (selected && selected.value === 'Keynote') {
        return 'Keynote';
      }
      return selected ? `${selected.value} 级` : '全部级别';
    });
    
    // 处理值变化
    const handleChange = (value) => {
      emit('update:modelValue', value);
      emit('change', value);
    };
    
    return {
      levelOptions,
      placeholder,
      handleChange
    };
  }
}; 

// 暴露到window对象以支持旧代码
if (typeof window !== 'undefined') {
  window.LevelFilter = LevelFilter;
}

export default LevelFilter;