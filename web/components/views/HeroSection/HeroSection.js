/**
 * HeroSection组件
 * 首页英雄区域，包含欢迎信息和登录引导
 */
export default {
  dependencies: [
    ['tech-button', '/components/shared/TechButton', 'TechButton']
  ],
  
  props: {
    // 用户认证状态
    isAuthenticated: {
      type: Boolean,
      required: true
    }
  },
  
  emits: ['login-click'],
  
  setup(props, { emit }) {
    // 处理登录按钮点击
    const handleLoginClick = () => {
      emit('login-click');
    };
    
    return {
      handleLoginClick
    };
  }
}; 