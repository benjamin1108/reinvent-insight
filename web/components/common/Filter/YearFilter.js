/**
 * YearFilter 组件
 * 年份筛选器
 */

const YearFilter = {
  dependencies: [
    ['custom-dropdown', '/components/common/Filter', 'CustomDropdown']
  ],
  
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
      const options = [{ value: '', label: '年份' }];
      
      // 添加可用年份（按降序排列）
      const sortedYears = [...props.availableYears].sort((a, b) => b - a);
      sortedYears.forEach(year => {
        options.push({ value: year, label: year });
      });
      
      return options;
    });
    
    // 占位文本
    const placeholder = computed(() => {
      return props.modelValue || '年份';
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

export default YearFilter;