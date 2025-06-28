/**
 * LoginModal 组件
 * 用户登录模态框
 */
export default {
  props: {
    // 是否显示模态框
    visible: {
      type: Boolean,
      required: true
    },
    // 模态框标题
    title: {
      type: String,
      default: '用户登录'
    },
    // 用户名占位符
    usernamePlaceholder: {
      type: String,
      default: '请输入用户名'
    },
    // 密码占位符
    passwordPlaceholder: {
      type: String,
      default: '请输入密码'
    },
    // 提交按钮文本
    submitText: {
      type: String,
      default: '登录'
    },
    // 加载状态
    loading: {
      type: Boolean,
      default: false
    },
    // 用户名（v-model）
    modelValue: {
      type: Object,
      default: () => ({ username: '', password: '' })
    }
  },
  
  emits: ['update:modelValue', 'submit', 'close'],
  
  setup(props, { emit }) {
    const { computed } = Vue;
    
    // 双向绑定用户名
    const username = computed({
      get: () => props.modelValue.username,
      set: (value) => {
        emit('update:modelValue', {
          ...props.modelValue,
          username: value
        });
      }
    });
    
    // 双向绑定密码
    const password = computed({
      get: () => props.modelValue.password,
      set: (value) => {
        emit('update:modelValue', {
          ...props.modelValue,
          password: value
        });
      }
    });
    
    // 处理表单提交
    const handleSubmit = () => {
      emit('submit', {
        username: username.value,
        password: password.value
      });
    };
    
    // 关闭模态框
    const close = () => {
      emit('close');
    };
    
    // 点击背景关闭（可选）
    const handleBackdropClick = (event) => {
      if (event.target === event.currentTarget) {
        close();
      }
    };
    
    return {
      username,
      password,
      handleSubmit,
      close,
      handleBackdropClick
    };
  }
}; 