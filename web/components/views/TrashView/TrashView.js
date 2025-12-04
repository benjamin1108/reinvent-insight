export default {
  name: 'TrashView',
  
  props: {
    items: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  
  emits: ['restore', 'delete', 'empty', 'load'],
  
  data() {
    return {
      confirmDeleteHash: null,
      confirmEmptyAll: false
    };
  },
  
  mounted() {
    // 加载回收站数据
    this.$emit('load');
  },
  
  computed: {
    isEmpty() {
      return this.items.length === 0;
    },
    
    totalSize() {
      return this.items.reduce((sum, item) => sum + (item.size || 0), 0);
    },
    
    formattedTotalSize() {
      return this.formatSize(this.totalSize);
    }
  },
  
  methods: {
    formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },
    
    formatDate(dateStr) {
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
    
    handleRestore(item) {
      this.$emit('restore', item.doc_hash, item.title_cn || item.title_en);
    },
    
    showDeleteConfirm(hash) {
      this.confirmDeleteHash = hash;
    },
    
    cancelDelete() {
      this.confirmDeleteHash = null;
    },
    
    handleDelete(item) {
      this.$emit('delete', item.doc_hash, item.title_cn || item.title_en);
      this.confirmDeleteHash = null;
    },
    
    showEmptyConfirm() {
      this.confirmEmptyAll = true;
    },
    
    cancelEmpty() {
      this.confirmEmptyAll = false;
    },
    
    handleEmpty() {
      this.$emit('empty');
      this.confirmEmptyAll = false;
    }
  }
};
