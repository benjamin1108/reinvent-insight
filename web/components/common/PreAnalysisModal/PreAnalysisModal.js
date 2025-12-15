/**
 * PreAnalysisModal 组件
 * 用于展示和确认AI的Pre分析结果
 */
export default {
  props: {
    // 任务ID
    taskId: {
      type: String,
      required: true
    },
    // Pre分析数据
    analysisData: {
      type: Object,
      required: true
    }
  },
  
  emits: ['confirm', 'close'],
  
  setup(props, { emit }) {
    const { ref, watch, onMounted, onUnmounted } = Vue;
    
    // 表单数据（从props初始化）
    const form = ref({
      content_type: '',
      content_style: '',
      target_audience: '',
      depth_level: '',
      core_value: '',
      interpretation_style: '',
      tone_guidance: ''
    });
    
    // 提交状态
    const isSubmitting = ref(false);
    
    // 初始化表单数据
    const initForm = () => {
      if (props.analysisData) {
        form.value = {
          content_type: props.analysisData.content_type || '技术演讲',
          content_style: props.analysisData.content_style || '深度理论型',
          target_audience: props.analysisData.target_audience || '技术专家',
          depth_level: props.analysisData.depth_level || '进阶理解',
          core_value: props.analysisData.core_value || '',
          interpretation_style: props.analysisData.interpretation_style || '',
          tone_guidance: props.analysisData.tone_guidance || ''
        };
      }
    };
    
    // 监听props变化
    watch(() => props.analysisData, () => {
      initForm();
    }, { immediate: true, deep: true });
    
    // 确认并提交
    const handleConfirm = async () => {
      if (isSubmitting.value) return;
      
      isSubmitting.value = true;
      
      try {
        // 调用API确认Pre分析结果
        const token = localStorage.getItem('authToken');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        
        await axios.post(`/api/tasks/${props.taskId}/confirm-pre-analysis`, form.value, { headers });
        
        // 触发确认事件
        emit('confirm', form.value);
      } catch (error) {
        console.error('确认Pre分析失败:', error);
        // 显示错误提示
        if (window.showToast) {
          window.showToast('确认失败，请重试', 'danger');
        }
      } finally {
        isSubmitting.value = false;
      }
    };
    
    // 关闭模态框（不会真正关闭，只是隐藏，因为必须确认才能继续）
    const close = () => {
      emit('close');
    };
    
    // 点击背景不关闭（必须确认）
    const handleBackdropClick = (event) => {
      // 不做任何操作，用户必须确认
    };
    
    // ESC键处理（不关闭，显示提示）
    const handleEscKey = (event) => {
      if (event.key === 'Escape') {
        if (window.showToast) {
          window.showToast('请确认解读风格后继续', 'warning', 2000);
        }
      }
    };
    
    onMounted(() => {
      document.addEventListener('keydown', handleEscKey);
      initForm();
    });
    
    onUnmounted(() => {
      document.removeEventListener('keydown', handleEscKey);
    });
    
    return {
      form,
      isSubmitting,
      handleConfirm,
      close,
      handleBackdropClick
    };
  }
};
