/**
 * YearFilter 组件
 * 年份筛选器
 */

const YearFilter = {
  // 不在这里声明components，因为CustomDropdown是通过ComponentLoader全局注册的
  
  props: {
    // 当前选中的年份
    modelValue: {
      type: String,
      default: ''
    },
    
    // 可用的年份列表
    availableYears: {
      type: Array,
      default: () => []
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
    
    // 年份选项
    const yearOptions = computed(() => {
      const options = [{ value: '', label: '全部年份' }];
      
      // 添加可用年份（按降序排列）
      const sortedYears = [...props.availableYears].sort((a, b) => b - a);
      sortedYears.forEach(year => {
        options.push({ value: year, label: year });
      });
      
      return options;
    });
    
    // 占位文本
    const placeholder = computed(() => {
      return props.modelValue || '全部年份';
    });
    
    // 处理值变化
    const handleChange = (value) => {
      emit('update:modelValue', value);
      emit('change', value);
    };
    
    return {
      yearOptions,
      placeholder,
      handleChange
    };
  }
}; 

// 暴露到window对象以支持旧代码
if (typeof window !== 'undefined') {
  window.YearFilter = YearFilter;
}

export default YearFilter;