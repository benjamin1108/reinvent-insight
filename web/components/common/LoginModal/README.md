# LoginModal 组件

用户登录模态框组件，支持灵活的登录方式和验证规则。

## 功能特性

- 支持邮箱、用户名或两者同时登录
- 可配置密码长度要求
- 实时表单验证
- 防跳变布局设计
- 响应式设计（移动端全屏）
- 支持 ESC 键关闭
- 内置错误/成功提示系统

## Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| visible | Boolean | required | 控制模态框显示/隐藏 |
| title | String | '用户登录' | 模态框标题 |
| submitText | String | '登录' | 提交按钮文本 |
| loading | Boolean | false | 加载状态 |
| loginType | String | 'email' | 登录类型：'email'、'username'、'both' |
| minPasswordLength | Number | 6 | 最小密码长度 |
| usernameLabel | String | '用户名' | 用户名字段的标签 |
| usernamePlaceholder | String | '请输入用户名' | 用户名输入框占位符 |

## 登录类型说明

- **email**: 仅显示邮箱输入框，必须输入有效邮箱
- **username**: 仅显示用户名输入框，用户名至少3个字符
- **both**: 同时显示邮箱和用户名，至少填写一个

## 事件

- `@update:visible`: 模态框关闭时触发
- `@submit`: 表单提交时触发，参数根据登录类型不同：
  - email 模式：`{ email, password }`
  - username 模式：`{ username, password }`
  - both 模式：`{ email?, username?, password }`
- `@close`: 模态框关闭时触发

## 方法

- `setError(message)`: 显示错误提示
- `setSuccess(message)`: 显示成功提示

## 使用示例

```vue
<!-- 仅邮箱登录（默认） -->
<login-modal 
  v-model:visible="modalVisible"
  @submit="handleLogin"
/>

<!-- 仅用户名登录 -->
<login-modal 
  v-model:visible="modalVisible"
  login-type="username"
  :min-password-length="8"
  @submit="handleLogin"
/>

<!-- 邮箱或用户名登录 -->
<login-modal 
  v-model:visible="modalVisible"
  login-type="both"
  username-label="用户名/手机号"
  @submit="handleLogin"
/>
```

## 样式特性

- 使用固定高度容器防止提示信息导致的跳变
- 错误信息使用绝对定位，不影响表单高度
- 支持科技感渐变边框和发光效果 