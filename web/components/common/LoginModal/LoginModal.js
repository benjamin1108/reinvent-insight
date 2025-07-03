/**
 * LoginModal 组件
 * 用户登录模态框
 */
export default {
  props: {
    // 模态框标题
    title: {
      type: String,
      default: '用户登录'
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
    // 登录类型：'email' | 'username' | 'both'
    loginType: {
      type: String,
      default: 'email',
      validator: (value) => ['email', 'username', 'both'].includes(value)
    },
    // 最小密码长度
    minPasswordLength: {
      type: Number,
      default: 6
    },
    // 用户名字段的标签
    usernameLabel: {
      type: String,
      default: '用户名'
    },
    // 用户名字段的占位符
    usernamePlaceholder: {
      type: String,
      default: '请输入用户名'
    }
  },
  
  emits: ['submit', 'close'],
  
  setup(props, { emit }) {
    const { ref, computed, watch } = Vue;
    
    // 表单数据
    const form = ref({
      username: '',
      email: '',
      password: ''
    });
    
    // 字段错误
    const errors = ref({
      username: '',
      email: '',
      password: ''
    });
    
    // 提示信息
    const alert = ref({
      type: '', // 'error' 或 'success'
      message: ''
    });
    
    // 提交状态
    const isSubmitting = ref(false);
    
    // 计算当前使用的登录字段
    const loginField = computed(() => {
      if (props.loginType === 'email') return 'email';
      if (props.loginType === 'username') return 'username';
      // 'both' 类型时，根据输入内容判断
      return form.value.email ? 'email' : 'username';
    });
    
    // 验证用户名
    const validateUsername = () => {
      const username = form.value.username;
      if (!username && (props.loginType === 'username' || (props.loginType === 'both' && !form.value.email))) {
        errors.value.username = `请输入${props.usernameLabel}`;
        return false;
      }
      if (username && username.length < 3) {
        errors.value.username = `${props.usernameLabel}长度至少3位`;
        return false;
      }
      errors.value.username = '';
      return true;
    };
    
    // 验证邮箱
    const validateEmail = () => {
      const email = form.value.email;
      if (!email && (props.loginType === 'email' || (props.loginType === 'both' && !form.value.username))) {
        errors.value.email = '请输入邮箱地址';
        return false;
      }
      if (email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
          errors.value.email = '请输入有效的邮箱地址';
          return false;
        }
      }
      errors.value.email = '';
      return true;
    };
    
    // 验证密码
    const validatePassword = () => {
      const password = form.value.password;
      if (!password) {
        errors.value.password = '请输入密码';
        return false;
      }
      if (password.length < props.minPasswordLength) {
        errors.value.password = `密码长度至少${props.minPasswordLength}位`;
        return false;
      }
      errors.value.password = '';
      return true;
    };
    
    // 清除特定字段错误
    const clearError = (field) => {
      errors.value[field] = '';
    };
    
    // 验证整个表单
    const validateForm = () => {
      let isValid = true;
      
      if (props.loginType === 'email') {
        isValid = validateEmail() && isValid;
      } else if (props.loginType === 'username') {
        isValid = validateUsername() && isValid;
      } else { // 'both'
        // 至少需要一个登录标识
        const usernameValid = validateUsername();
        const emailValid = validateEmail();
        if (!form.value.username && !form.value.email) {
          errors.value.username = `请输入${props.usernameLabel}或邮箱`;
          isValid = false;
        } else {
          isValid = (form.value.username ? usernameValid : true) && 
                   (form.value.email ? emailValid : true);
        }
      }
      
      isValid = validatePassword() && isValid;
      return isValid;
    };
    
    // 处理表单提交
    const handleSubmit = async () => {
      // 清除之前的提示
      alert.value = { type: '', message: '' };
      
      // 验证表单
      if (!validateForm()) {
        return;
      }
      
      // 设置提交状态
      isSubmitting.value = true;
      
      try {
        // 构建提交数据
        const submitData = {
          password: form.value.password
        };
        
        // 根据登录类型添加相应字段
        if (props.loginType === 'email') {
          submitData.email = form.value.email;
        } else if (props.loginType === 'username') {
          submitData.username = form.value.username;
        } else { // 'both'
          if (form.value.email) submitData.email = form.value.email;
          if (form.value.username) submitData.username = form.value.username;
        }
        
        // 触发提交事件
        emit('submit', submitData);
      } finally {
        // 这里不重置提交状态，让父组件控制
        // isSubmitting.value = false;
      }
    };
    
    // 关闭模态框
    const close = () => {
      // 清除所有状态
      form.value = { username: '', email: '', password: '' };
      errors.value = { username: '', email: '', password: '' };
      alert.value = { type: '', message: '' };
      isSubmitting.value = false;
      
      emit('close');
    };
    
    // 点击背景关闭
    const handleBackdropClick = (event) => {
      if (event.target === event.currentTarget) {
        close();
      }
    };
    
    // 组件挂载时重置状态
    Vue.onMounted(() => {
      form.value = { username: '', email: '', password: '' };
      errors.value = { username: '', email: '', password: '' };
      alert.value = { type: '', message: '' };
      isSubmitting.value = false;
    });
    
    // ESC键关闭模态框
    const handleEscKey = (event) => {
      if (event.key === 'Escape') {
        close();
      }
    };
    
    // 生命周期钩子 - 添加ESC键监听
    Vue.onMounted(() => {
      document.addEventListener('keydown', handleEscKey);
    });
    
    Vue.onUnmounted(() => {
      document.removeEventListener('keydown', handleEscKey);
    });
    
    // 暴露方法供父组件调用
    const setError = (message) => {
      alert.value = { type: 'error', message };
      isSubmitting.value = false;
    };
    
    const setSuccess = (message) => {
      alert.value = { type: 'success', message };
      isSubmitting.value = false;
    };
    
    // 监听全局登录错误事件
    let unsubscribeLoginError;
    Vue.onMounted(() => {
      if (window.eventBus && window.eventBus.on) {
        unsubscribeLoginError = window.eventBus.on('login-error', (msg) => {
          setError(msg || '登录失败');
        });
      }
    });
    
    Vue.onUnmounted(() => {
      if (unsubscribeLoginError) {
        unsubscribeLoginError();
      }
    });
    
    return {
      form,
      errors,
      alert,
      isSubmitting,
      loginField,
      validateUsername,
      validateEmail,
      validatePassword,
      clearError,
      handleSubmit,
      close,
      handleBackdropClick,
      setError,
      setSuccess
    };
  }
}; 