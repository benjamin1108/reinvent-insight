/**
 * AdminView 组件
 * 系统管理页面，整合文章管理和回收站功能
 */
export default {
  name: 'AdminView',
  
  dependencies: [
    ['trash-view', '/components/views/TrashView', 'TrashView']
  ],
  
  data() {
    return {
      // 当前标签页
      activeTab: 'articles', // 'articles' | 'trash' | 'users'
      
      // 文章列表数据
      articles: [],
      loading: false,
      
      // 选中的文章
      selectedArticles: [],
      
      // 删除确认
      deleteConfirmVisible: false,
      deleteTarget: 'single', // 'single' | 'batch'
      articleToDelete: null,
      deleting: false,
      
      // 回收站数据
      trashItems: [],
      trashLoading: false,
      
      // 用户管理数据
      users: [],
      usersLoading: false,
      userFormVisible: false,
      addUserDialogVisible: false,
      addingUser: false,
      newUser: {
        username: '',
        password: '',
        role: 'user'
      },
      newUserErrors: {},
      userFormErrors: { username: '', password: '' },
      userFormSubmitting: false,
      userDeleteConfirmVisible: false,
      deleteUserConfirmVisible: false,
      userToDelete: null,
      userDeleting: false,
      deletingUser: false,
      
      // Ultra Deep 轮询定时器
      ultraPollingTimer: null
    };
  },

  watch: {
    activeTab(newTab) {
      // 切换到回收站标签页时加载回收站数据
      if (newTab === 'trash' && this.trashItems.length === 0) {
        this.loadTrash();
      }
      // 切换到用户管理标签页时加载用户列表
      if (newTab === 'users' && this.users.length === 0) {
        this.loadUsers();
      }
    }
  },
  
  computed: {
    // 是否全选
    isAllSelected() {
      return this.articles.length > 0 && 
             this.selectedArticles.length === this.articles.length;
    }
  },
  
  mounted() {
    // 加载文章列表
    this.loadArticles();
  },
  
  beforeUnmount() {
    // 清理轮询定时器
    if (this.ultraPollingTimer) {
      clearInterval(this.ultraPollingTimer);
    }
  },
  
  methods: {
    // ========== 文章列表加载 ==========
    
    async loadArticles() {
      this.loading = true;
      
      try {
        // 获取所有文档列表
        const response = await fetch('/api/public/summaries');
        if (!response.ok) {
          throw new Error('获取文章列表失败');
        }
        
        const data = await response.json();
        const summaries = data.summaries || [];
        
        // 组装文章数据
        const articles = [];
        for (const summary of summaries) {
          const article = {
            hash: summary.hash,
            title_cn: summary.title_cn,
            title_en: summary.title_en,
            source_type: summary.source_type || 'document',
            word_count: summary.word_count || 0,
            version: summary.version || 0,
            created_at: summary.created_at || summary.upload_date,
            chapter_count: summary.chapter_count || 0,
            ultraExists: false,
            ultraGenerating: false,
            ultraDisabledReason: ''
          };
          
          // 查询 Ultra Deep 状态
          await this.checkUltraStatus(article);
          
          articles.push(article);
        }
        
        // 按创建时间倒序排序
        articles.sort((a, b) => {
          const dateA = new Date(a.created_at || 0);
          const dateB = new Date(b.created_at || 0);
          return dateB - dateA;
        });
        
        this.articles = articles;
        
        // 启动轮询检查生成中的 Ultra 任务
        this.startUltraPolling();
        
      } catch (error) {
        console.error('加载文章列表失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: '加载文章列表失败',
            type: 'error'
          });
        }
      } finally {
        this.loading = false;
      }
    },
    
    // 检查 Ultra Deep 状态
    async checkUltraStatus(article) {
      try {
        const response = await fetch(`/api/article/${article.hash}/ultra-deep/status`);
        if (!response.ok) return;
        
        const data = await response.json();
        
        if (data.status === 'completed' && data.exists) {
          article.ultraExists = true;
          article.ultraGenerating = false;
        } else if (data.status === 'generating') {
          article.ultraExists = false;
          article.ultraGenerating = true;
        } else {
          article.ultraExists = false;
          article.ultraGenerating = false;
          
          // 检查是否可以生成
          if (data.reason) {
            article.ultraDisabledReason = data.reason;
          } else if (article.chapter_count > 15) {
            article.ultraDisabledReason = '章节数超过15章，已是深度内容';
          }
        }
      } catch (error) {
        console.error('检查Ultra状态失败:', error);
      }
    },
    
    // 启动 Ultra 轮询
    startUltraPolling() {
      if (this.ultraPollingTimer) {
        clearInterval(this.ultraPollingTimer);
      }
      
      this.ultraPollingTimer = setInterval(async () => {
        // 只检查生成中的文章
        const generatingArticles = this.articles.filter(a => a.ultraGenerating);
        
        if (generatingArticles.length === 0) {
          return;
        }
        
        for (const article of generatingArticles) {
          await this.checkUltraStatus(article);
        }
      }, 5000); // 每5秒检查一次
    },
    
    // ========== 文章操作 ==========
    
    // 点击文章标题跳转阅读
    handleArticleClick(article) {
      if (window.eventBus) {
        window.eventBus.emit('navigate-to-reading', {
          hash: article.hash
        });
      }
    },
    
    // 判断是否可以触发 Ultra
    canTriggerUltra(article) {
      return !article.ultraExists && 
             !article.ultraGenerating && 
             article.chapter_count <= 15;
    },
    
    // 获取 Ultra 按钮标题
    getUltraButtonTitle(article) {
      if (article.ultraGenerating) {
        return 'Ultra DeepInsight 生成中...';
      }
      if (article.ultraExists) {
        return '已有 Ultra DeepInsight 版本';
      }
      if (article.chapter_count > 15) {
        return '章节数超过15章，已是深度内容';
      }
      return '生成 Ultra DeepInsight 版本';
    },
    
    // 触发 Ultra Deep 生成
    async handleTriggerUltra(article) {
      if (!this.canTriggerUltra(article)) {
        return;
      }
      
      try {
        const token = localStorage.getItem('authToken');
        if (!token) {
          if (window.eventBus) {
            window.eventBus.emit('show-login-modal');
          }
          return;
        }
        
        article.ultraGenerating = true;
        
        const response = await fetch(`/api/article/${article.hash}/ultra-deep`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || '触发 Ultra Deep 失败');
        }
        
        const data = await response.json();
        
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: 'Ultra DeepInsight 任务已启动',
            type: 'success'
          });
        }
        
        // 启动轮询
        this.startUltraPolling();
        
      } catch (error) {
        console.error('触发Ultra失败:', error);
        article.ultraGenerating = false;
        
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: error.message || '触发 Ultra Deep 失败',
            type: 'error'
          });
        }
      }
    },
    
    // 点击删除按钮
    handleDeleteClick(article) {
      this.deleteTarget = 'single';
      this.articleToDelete = article;
      this.deleteConfirmVisible = true;
    },
    
    // 批量删除
    handleBatchDelete() {
      if (this.selectedArticles.length === 0) return;
      
      this.deleteTarget = 'batch';
      this.deleteConfirmVisible = true;
    },
    
    // 取消删除
    cancelDelete() {
      this.deleteConfirmVisible = false;
      this.articleToDelete = null;
    },
    
    // 确认删除
    async confirmDelete() {
      this.deleting = true;
      
      try {
        const token = localStorage.getItem('authToken');
        if (!token) {
          throw new Error('请先登录');
        }
        
        const hashesToDelete = this.deleteTarget === 'single' 
          ? [this.articleToDelete.hash]
          : this.selectedArticles;
        
        let successCount = 0;
        let failCount = 0;
        
        for (const hash of hashesToDelete) {
          try {
            const response = await fetch(`/api/summaries/${hash}`, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            
            if (response.ok) {
              successCount++;
            } else {
              failCount++;
            }
          } catch (error) {
            failCount++;
            console.error(`删除文章 ${hash} 失败:`, error);
          }
        }
        
        // 显示结果
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: `成功删除 ${successCount} 篇文章${failCount > 0 ? `，${failCount} 篇失败` : ''}`,
            type: successCount > 0 ? 'success' : 'error'
          });
        }
        
        // 刷新列表
        this.selectedArticles = [];
        await this.loadArticles();
        
      } catch (error) {
        console.error('删除失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: error.message || '删除失败',
            type: 'error'
          });
        }
      } finally {
        this.deleting = false;
        this.deleteConfirmVisible = false;
        this.articleToDelete = null;
      }
    },
    
    // ========== 选择操作 ==========
    
    // 切换全选
    toggleSelectAll() {
      if (this.isAllSelected) {
        this.selectedArticles = [];
      } else {
        this.selectedArticles = this.articles.map(a => a.hash);
      }
    },
    
    // 切换单篇文章选择
    toggleArticleSelection(hash) {
      const index = this.selectedArticles.indexOf(hash);
      if (index > -1) {
        this.selectedArticles.splice(index, 1);
      } else {
        this.selectedArticles.push(hash);
      }
    },
    
    // 判断文章是否被选中
    isArticleSelected(hash) {
      return this.selectedArticles.includes(hash);
    },
    
    // ========== 回收站操作 ==========
    
    // 加载回收站
    async loadTrash() {
      this.trashLoading = true;
      
      try {
        const token = localStorage.getItem('authToken');
        if (!token) {
          console.warn('未登录，跳过加载回收站');
          this.trashLoading = false;
          return;
        }
        
        const response = await fetch('/api/admin/trash', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('获取回收站失败');
        }
        
        const data = await response.json();
        this.trashItems = data.items || [];
        
      } catch (error) {
        console.error('加载回收站失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: '加载回收站失败',
            type: 'error'
          });
        }
      } finally {
        this.trashLoading = false;
      }
    },
    
    // 恢复文章
    async handleRestore(docHash, title) {
      try {
        const token = localStorage.getItem('authToken');
        if (!token) {
          if (window.eventBus) {
            window.eventBus.emit('show-login-modal');
          }
          return;
        }
        
        const response = await fetch(`/api/admin/trash/${docHash}/restore`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('恢复失败');
        }
        
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: `已恢复: ${title}`,
            type: 'success'
          });
        }
        
        // 刷新两个列表
        await Promise.all([
          this.loadTrash(),
          this.loadArticles()
        ]);
        
      } catch (error) {
        console.error('恢复失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: '恢复失败',
            type: 'error'
          });
        }
      }
    },
    
    // 永久删除
    async handlePermanentDelete(docHash, title) {
      try {
        const token = localStorage.getItem('authToken');
        if (!token) {
          if (window.eventBus) {
            window.eventBus.emit('show-login-modal');
          }
          return;
        }
        
        const response = await fetch(`/api/admin/trash/${docHash}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('永久删除失败');
        }
        
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: `已永久删除: ${title}`,
            type: 'success'
          });
        }
        
        await this.loadTrash();
        
      } catch (error) {
        console.error('永久删除失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: '永久删除失败',
            type: 'error'
          });
        }
      }
    },
    
    // 清空回收站
    async handleEmptyTrash() {
      try {
        const token = localStorage.getItem('authToken');
        if (!token) {
          if (window.eventBus) {
            window.eventBus.emit('show-login-modal');
          }
          return;
        }
        
        const response = await fetch('/api/admin/trash', {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('清空回收站失败');
        }
        
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: '回收站已清空',
            type: 'success'
          });
        }
        
        await this.loadTrash();
        
      } catch (error) {
        console.error('清空回收站失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: '清空回收站失败',
            type: 'error'
          });
        }
      }
    },
    
    // ========== 工具方法 ==========
    
    // 格式化字数
    formatWordCount(count) {
      if (!count || count === 0) return '—';
      if (count >= 10000) {
        return `${(count / 10000).toFixed(1)}万字`;
      }
      if (count >= 1000) {
        return `${(count / 1000).toFixed(1)}k字`;
      }
      return `${count}字`;
    },
    
    // 格式化日期
    formatDate(dateStr) {
      if (!dateStr) return '—';
      try {
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        });
      } catch {
        return dateStr;
      }
    },
    
    // 获取类型文本
    getTypeText(sourceType) {
      const typeMap = {
        'youtube': 'YouTube',
        'document': '文档',
        'pdf': 'PDF',
        'url': '网页'
      };
      return typeMap[sourceType] || '其他';
    },
    
    // 获取类型徽章样式
    getTypeBadgeClass(sourceType) {
      return `admin-view__badge--${sourceType || 'default'}`;
    },
    
    // ========== 用户管理 ==========
    
    // 加载用户列表
    async loadUsers() {
      this.usersLoading = true;
      
      try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/auth/users', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('获取用户列表失败');
        }
        
        const data = await response.json();
        this.users = data.users || [];
        
      } catch (error) {
        console.error('加载用户列表失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: '加载用户列表失败',
            type: 'error'
          });
        }
      } finally {
        this.usersLoading = false;
      }
    },
    
    // 显示添加用户对话框
    showAddUserDialog() {
      this.newUser = {
        username: '',
        password: '',
        role: 'user'
      };
      this.newUserErrors = {};
      this.addUserDialogVisible = true;
    },
    
    // 取消添加用户
    cancelAddUser() {
      if (this.addingUser) return;
      this.addUserDialogVisible = false;
    },
    
    // 验证用户输入
    validateUserInput() {
      this.newUserErrors = {};
      
      if (!this.newUser.username || this.newUser.username.trim().length < 3) {
        this.newUserErrors.username = '用户名至少 3 个字符';
      }
      if (this.newUser.username && this.newUser.username.length > 50) {
        this.newUserErrors.username = '用户名最多 50 个字符';
      }
      if (!this.newUser.password || this.newUser.password.length < 6) {
        this.newUserErrors.password = '密码至少 6 个字符';
      }
      
      return Object.keys(this.newUserErrors).length === 0;
    },
    
    // 确认添加用户
    async confirmAddUser() {
      if (!this.validateUserInput()) {
        return;
      }
      
      this.addingUser = true;
      
      try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/auth/register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            username: this.newUser.username.trim(),
            password: this.newUser.password,
            role: this.newUser.role
          })
        });
        
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || '添加用户失败');
        }
        
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: `用户 ${this.newUser.username} 添加成功`,
            type: 'success'
          });
        }
        
        this.addUserDialogVisible = false;
        await this.loadUsers();
        
      } catch (error) {
        console.error('添加用户失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: error.message || '添加用户失败',
            type: 'error'
          });
        }
      } finally {
        this.addingUser = false;
      }
    },
    
    // 处理删除用户
    handleDeleteUser(user) {
      this.userToDelete = user;
      this.deleteUserConfirmVisible = true;
    },
    
    // 取消删除用户
    cancelDeleteUser() {
      if (this.deletingUser) return;
      this.deleteUserConfirmVisible = false;
      this.userToDelete = null;
    },
    
    // 确认删除用户
    async confirmDeleteUser() {
      if (!this.userToDelete) return;
      
      this.deletingUser = true;
      
      try {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`/api/auth/users/${this.userToDelete.username}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || '删除用户失败');
        }
        
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: `用户 ${this.userToDelete.username} 已删除`,
            type: 'success'
          });
        }
        
        this.deleteUserConfirmVisible = false;
        this.userToDelete = null;
        await this.loadUsers();
        
      } catch (error) {
        console.error('删除用户失败:', error);
        if (window.eventBus) {
          window.eventBus.emit('show-toast', {
            message: error.message || '删除用户失败',
            type: 'error'
          });
        }
      } finally {
        this.deletingUser = false;
      }
    }
  }
};
