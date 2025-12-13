/**
 * VideoPlayer 组件
 * 浮动视频播放器，支持拖动、调整大小、最小化、字幕叠加
 */

// 全局 YouTube API 状态
let ytApiLoaded = false;
let ytApiLoading = false;
const ytApiCallbacks = [];

// 加载 YouTube IFrame API
function loadYouTubeAPI() {
  return new Promise((resolve) => {
    if (ytApiLoaded) {
      resolve();
      return;
    }
    
    ytApiCallbacks.push(resolve);
    
    if (ytApiLoading) return;
    ytApiLoading = true;
    
    window.onYouTubeIframeAPIReady = () => {
      ytApiLoaded = true;
      ytApiCallbacks.forEach(cb => cb());
      ytApiCallbacks.length = 0;
    };
    
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
  });
}

// 解析 VTT 字幕为时间轴数组
function parseVTT(vttContent) {
  const cues = [];
  const lines = vttContent.split('\n');
  let i = 0;
  
  // 跳过 WEBVTT 头部
  while (i < lines.length && !lines[i].includes('-->')) {
    i++;
  }
  
  while (i < lines.length) {
    const line = lines[i].trim();
    
    if (line.includes('-->')) {
      // 解析时间轴: 00:00:01.000 --> 00:00:04.000
      const match = line.match(/(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})/);
      if (match) {
        const start = parseTime(match[1]);
        const end = parseTime(match[2]);
        
        // 收集字幕文本（可能多行）
        i++;
        const textLines = [];
        while (i < lines.length && lines[i].trim() !== '') {
          // 移除 HTML 标签
          const cleanLine = lines[i].replace(/<[^>]+>/g, '').trim();
          if (cleanLine) textLines.push(cleanLine);
          i++;
        }
        
        if (textLines.length > 0) {
          cues.push({
            start,
            end,
            text: textLines.join(' ')
          });
        }
      } else {
        i++;
      }
    } else {
      i++;
    }
  }
  
  return cues;
}

// 解析时间字符串为秒数
function parseTime(timeStr) {
  // 格式: 00:00:01.000 或 00:00:01,000
  const parts = timeStr.replace(',', '.').split(':');
  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  const seconds = parseFloat(parts[2]);
  return hours * 3600 + minutes * 60 + seconds;
}

export default {
  props: {
    // 是否显示播放器
    visible: {
      type: Boolean,
      required: true
    },
    // 视频ID（YouTube）
    videoId: {
      type: String,
      required: true
    },
    // 视频标题
    title: {
      type: String,
      default: '视频播放器'
    },
    // 初始位置
    initialPosition: {
      type: Object,
      default: () => ({ x: null, y: null })
    },
    // 初始大小
    initialSize: {
      type: Object,
      default: () => ({ width: 480, height: 320 })
    },
    // 是否默认最小化
    defaultMinimized: {
      type: Boolean,
      default: false
    }
  },
  
  emits: ['update:visible', 'close', 'positionChange', 'sizeChange', 'minimizeChange'],
  
  setup(props, { emit }) {
    const { ref, computed, reactive, watch, onMounted, onUnmounted, nextTick } = Vue;
    
    // 生成唯一的容器 ID
    const iframeContainerId = ref(`yt-player-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
    
    // 状态
    const minimized = ref(props.defaultMinimized);
    const position = reactive({
      x: props.initialPosition.x,
      y: props.initialPosition.y
    });
    const size = reactive({
      width: props.initialSize.width,
      height: props.initialSize.height
    });
    
    // 拖动相关
    const isDragging = ref(false);
    const dragStartPos = reactive({ x: 0, y: 0 });
    const playerStartPos = reactive({ x: 0, y: 0 });
    
    // 调整大小相关
    const isResizing = ref(false);
    const resizeStartPos = reactive({ x: 0, y: 0 });
    const playerStartSize = reactive({ width: 0, height: 0 });
    
    // YouTube 播放器实例
    let ytPlayer = null;
    let subtitleInterval = null;
    
    // 字幕相关状态
    const subtitleEnabled = ref(false);
    const subtitleLoading = ref(false);
    const subtitleCues = ref([]);
    const currentSubtitle = ref('');
    const subtitleError = ref(null);
    const subtitleLang = ref('zh'); // 'zh' 或 'en'
    
    // 字幕位置拖动相关
    const subtitleBottom = ref(24); // 默认距底部 24px
    const isSubtitleDragging = ref(false);
    let subtitleDragStartY = 0;
    let subtitleStartBottom = 0;
    
    // 字幕样式控制
    const subtitleFontSize = ref(18); // 默认 18px
    const subtitleColor = ref('#ffffff'); // 默认白色
    const showSubtitleSettings = ref(false); // 是否显示设置面板
    
    // 可选颜色列表
    const colorOptions = [
      { name: '白色', value: '#ffffff' },
      { name: '黄色', value: '#ffff00' },
      { name: '青色', value: '#00ffff' },
      { name: '绿色', value: '#00ff00' },
      { name: '粉色', value: '#ff69b4' },
      { name: '橙色', value: '#ffa500' }
    ];
    
    // 字幕按钮提示
    const subtitleButtonTitle = computed(() => {
      if (subtitleLoading.value) return '加载字幕中...';
      if (subtitleError.value) return `字幕加载失败: ${subtitleError.value}`;
      return subtitleEnabled.value ? '关闭字幕' : '开启字幕';
    });
    
    // 方法
    const close = () => {
      emit('close');
      emit('update:visible', false);
    };
    
    const toggleMinimize = () => {
      minimized.value = !minimized.value;
      emit('minimizeChange', minimized.value);
    };
    
    // 拖动功能
    const startDrag = (e) => {
      if (e.target.closest('.video-control-btn')) return;
      
      isDragging.value = true;
      const event = e.type.includes('touch') ? e.touches[0] : e;
      
      dragStartPos.x = event.clientX;
      dragStartPos.y = event.clientY;
      
      // 如果当前使用的是默认位置（右下角），需要计算实际位置
      if (position.x === null || position.y === null) {
        const playerEl = e.target.closest('.floating-video-player');
        if (playerEl) {
          const rect = playerEl.getBoundingClientRect();
          position.x = rect.left;
          position.y = rect.top;
        }
      }
      
      playerStartPos.x = position.x || 0;
      playerStartPos.y = position.y || 0;
      
      e.preventDefault();
    };
    
    const handleDrag = (e) => {
      if (!isDragging.value) return;
      
      const event = e.type.includes('touch') ? e.touches[0] : e;
      const deltaX = event.clientX - dragStartPos.x;
      const deltaY = event.clientY - dragStartPos.y;
      
      let newX = playerStartPos.x + deltaX;
      let newY = playerStartPos.y + deltaY;
      
      // 限制在视口内
      const maxX = window.innerWidth - (minimized.value ? 300 : size.width);
      const maxY = window.innerHeight - 41; // 标题栏高度
      
      newX = Math.max(0, Math.min(newX, maxX));
      newY = Math.max(0, Math.min(newY, maxY));
      
      position.x = newX;
      position.y = newY;
      
      emit('positionChange', { x: newX, y: newY });
    };
    
    const endDrag = () => {
      isDragging.value = false;
    };
    
    // 调整大小功能
    const startResize = (e) => {
      if (minimized.value) return;
      
      isResizing.value = true;
      const event = e.type.includes('touch') ? e.touches[0] : e;
      
      resizeStartPos.x = event.clientX;
      resizeStartPos.y = event.clientY;
      playerStartSize.width = size.width;
      playerStartSize.height = size.height;
      
      e.preventDefault();
    };
    
    const handleResize = (e) => {
      if (!isResizing.value) return;
      
      const event = e.type.includes('touch') ? e.touches[0] : e;
      const deltaX = event.clientX - resizeStartPos.x;
      const deltaY = event.clientY - resizeStartPos.y;
      
      let newWidth = playerStartSize.width + deltaX;
      let newHeight = playerStartSize.height + deltaY;
      
      // 限制最小/最大尺寸
      newWidth = Math.max(320, Math.min(newWidth, window.innerWidth - (position.x || 0)));
      newHeight = Math.max(240, Math.min(newHeight, window.innerHeight - (position.y || 0)));
      
      // 保持16:9比例（可选）
      // newHeight = newWidth / (16/9);
      
      size.width = newWidth;
      size.height = newHeight;
      
      emit('sizeChange', { width: newWidth, height: newHeight });
    };
    
    const endResize = () => {
      isResizing.value = false;
    };
    
    // 字幕垂直拖动功能
    const startSubtitleDrag = (e) => {
      isSubtitleDragging.value = true;
      const event = e.type.includes('touch') ? e.touches[0] : e;
      subtitleDragStartY = event.clientY;
      subtitleStartBottom = subtitleBottom.value;
      e.preventDefault();
      e.stopPropagation();
    };
    
    const handleSubtitleDrag = (e) => {
      if (!isSubtitleDragging.value) return;
      
      const event = e.type.includes('touch') ? e.touches[0] : e;
      const deltaY = subtitleDragStartY - event.clientY; // 向上拖动增加 bottom
      
      let newBottom = subtitleStartBottom + deltaY;
      
      // 限制范围：10px ~ (height - 60)px
      const maxBottom = size.height - 60;
      newBottom = Math.max(10, Math.min(newBottom, maxBottom));
      
      subtitleBottom.value = newBottom;
    };
    
    const endSubtitleDrag = () => {
      isSubtitleDragging.value = false;
    };
    
    // 自动调整位置（防止超出视口）
    const adjustPosition = () => {
      if (position.x === null || position.y === null) return;
      
      const maxX = window.innerWidth - (minimized.value ? 300 : size.width);
      const maxY = window.innerHeight - 41;
      
      let adjusted = false;
      
      if (position.x > maxX) {
        position.x = maxX;
        adjusted = true;
      }
      
      if (position.y > maxY) {
        position.y = maxY;
        adjusted = true;
      }
      
      if (adjusted) {
        emit('positionChange', { x: position.x, y: position.y });
      }
    };
    
    // 初始化 YouTube 播放器
    const initYouTubePlayer = async () => {
      if (!props.videoId) return;
      
      try {
        await loadYouTubeAPI();
        
        // 等待容器元素存在
        await nextTick();
        
        const container = document.getElementById(iframeContainerId.value);
        if (!container) {
          console.warn('YouTube player container not found');
          return;
        }
        
        // 销毁旧的播放器
        if (ytPlayer) {
          try {
            ytPlayer.destroy();
          } catch (e) {
            // 忽略销毁错误
          }
          ytPlayer = null;
        }
        
        // 创建新的播放器
        ytPlayer = new YT.Player(iframeContainerId.value, {
          videoId: props.videoId,
          playerVars: {
            enablejsapi: 1,
            modestbranding: 1,
            rel: 0,
            fs: 1,
            autoplay: 0,
            origin: window.location.origin
          },
          events: {
            onReady: onPlayerReady,
            onStateChange: onPlayerStateChange
          }
        });
      } catch (e) {
        console.error('Failed to init YouTube player:', e);
      }
    };
    
    const onPlayerReady = async (event) => {
      console.log('YouTube player ready');
      
      // 自动尝试加载中文字幕
      if (!subtitleEnabled.value && subtitleCues.value.length === 0) {
        try {
          // 先检查是否有中文字幕
          const response = await fetch(`/api/public/subtitle/${props.videoId}/translated`);
          if (response.ok) {
            const data = await response.json();
            if (data.vtt && !data.generating) {
              // 有中文字幕，自动加载并启用
              subtitleCues.value = parseVTT(data.vtt);
              subtitleEnabled.value = true;
              subtitleLang.value = 'zh';
              console.log(`自动加载中文字幕: ${subtitleCues.value.length} 条`);
            }
          }
        } catch (e) {
          // 静默失败，不影响播放
          console.log('自动加载字幕失败，用户可手动开启');
        }
      }
    };
    
    const onPlayerStateChange = (event) => {
      // YT.PlayerState: PLAYING=1, PAUSED=2, ENDED=0
      if (event.data === YT.PlayerState.PLAYING) {
        startSubtitleSync();
      } else {
        stopSubtitleSync();
      }
    };
    
    // 字幕同步
    const startSubtitleSync = () => {
      if (subtitleInterval) return;
      if (!subtitleEnabled.value || subtitleCues.value.length === 0) return;
      
      subtitleInterval = setInterval(() => {
        if (!ytPlayer || typeof ytPlayer.getCurrentTime !== 'function') return;
        
        try {
          const currentTime = ytPlayer.getCurrentTime();
          const cue = subtitleCues.value.find(c => currentTime >= c.start && currentTime <= c.end);
          currentSubtitle.value = cue ? cue.text : '';
        } catch (e) {
          // 忽略错误
        }
      }, 50);
    };
    
    const stopSubtitleSync = () => {
      if (subtitleInterval) {
        clearInterval(subtitleInterval);
        subtitleInterval = null;
      }
    };
    
    // 字幕轮询定时器
    let subtitlePollTimer = null;
    
    // 加载字幕
    const loadSubtitles = async (lang = null) => {
      if (!props.videoId) return;
      
      const targetLang = lang || subtitleLang.value;
      subtitleLoading.value = true;
      subtitleError.value = null;
      
      try {
        // 根据语言选择 API
        const apiUrl = targetLang === 'en' 
          ? `/api/public/subtitle/${props.videoId}`
          : `/api/public/subtitle/${props.videoId}/translated`;
        
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || '字幕加载失败');
        }
        
        const data = await response.json();
        
        // 检查是否正在翻译中（仅中文字幕）
        if (targetLang === 'zh' && data.generating) {
          subtitleError.value = data.message || '字幕正在翻译中...';
          subtitleLoading.value = false;
          
          // 启动轮询，5秒后重试
          if (!subtitlePollTimer) {
            subtitlePollTimer = setInterval(async () => {
              try {
                const pollResponse = await fetch(`/api/public/subtitle/${props.videoId}/translated`);
                const pollData = await pollResponse.json();
                
                if (pollData.vtt && !pollData.generating) {
                  // 翻译完成，停止轮询并加载字幕
                  clearInterval(subtitlePollTimer);
                  subtitlePollTimer = null;
                  subtitleCues.value = parseVTT(pollData.vtt);
                  subtitleError.value = null;
                  console.log(`Loaded ${subtitleCues.value.length} subtitle cues`);
                  
                  // 如果正在播放，开始同步
                  if (ytPlayer && typeof ytPlayer.getPlayerState === 'function') {
                    if (ytPlayer.getPlayerState() === YT.PlayerState.PLAYING) {
                      startSubtitleSync();
                    }
                  }
                }
              } catch (e) {
                console.error('Poll subtitles failed:', e);
              }
            }, 5000);
          }
          return;
        }
        
        if (data.vtt) {
          subtitleCues.value = parseVTT(data.vtt);
          console.log(`Loaded ${subtitleCues.value.length} subtitle cues`);
          
          // 如果正在播放，开始同步
          if (ytPlayer && typeof ytPlayer.getPlayerState === 'function') {
            if (ytPlayer.getPlayerState() === YT.PlayerState.PLAYING) {
              startSubtitleSync();
            }
          }
        } else {
          throw new Error('字幕内容为空');
        }
      } catch (e) {
        console.error('Failed to load subtitles:', e);
        subtitleError.value = e.message;
        subtitleEnabled.value = false;
      } finally {
        subtitleLoading.value = false;
      }
    };
    
    // 切换字幕语言
    const toggleSubtitleLang = async () => {
      if (subtitleLoading.value) return;
      
      const newLang = subtitleLang.value === 'zh' ? 'en' : 'zh';
      subtitleLang.value = newLang;
      
      // 重新加载字幕
      subtitleCues.value = [];
      currentSubtitle.value = '';
      
      if (subtitleEnabled.value) {
        await loadSubtitles(newLang);
      }
    };
    
    // 切换字幕
    const toggleSubtitle = async () => {
      if (subtitleLoading.value) return;
      
      if (subtitleEnabled.value) {
        // 关闭字幕
        subtitleEnabled.value = false;
        stopSubtitleSync();
        currentSubtitle.value = '';
        showSubtitleSettings.value = false;
      } else {
        // 开启字幕
        subtitleEnabled.value = true;
        
        // 如果还没加载字幕，先加载
        if (subtitleCues.value.length === 0) {
          await loadSubtitles();
        } else {
          // 已有字幕，直接开始同步
          if (ytPlayer && typeof ytPlayer.getPlayerState === 'function') {
            if (ytPlayer.getPlayerState() === YT.PlayerState.PLAYING) {
              startSubtitleSync();
            }
          }
        }
      }
    };
    
    // 字幕字体调大
    const increaseSubtitleSize = () => {
      if (subtitleFontSize.value < 32) {
        subtitleFontSize.value += 2;
      }
    };
    
    // 字幕字体调小
    const decreaseSubtitleSize = () => {
      if (subtitleFontSize.value > 12) {
        subtitleFontSize.value -= 2;
      }
    };
    
    // 设置字幕颜色
    const setSubtitleColor = (color) => {
      subtitleColor.value = color;
    };
    
    // 切换设置面板
    const toggleSubtitleSettings = () => {
      showSubtitleSettings.value = !showSubtitleSettings.value;
    };
    
    // 监听props变化
    watch(() => props.videoId, (newId, oldId) => {
      if (newId && newId !== oldId) {
        // 视频变化时重置字幕状态
        subtitleCues.value = [];
        currentSubtitle.value = '';
        subtitleError.value = null;
        stopSubtitleSync();
        
        // 重新初始化播放器
        nextTick(() => {
          initYouTubePlayer();
        });
      }
    });
    
    watch(() => props.visible, (newVal) => {
      if (newVal) {
        // 显示时调整初始位置并初始化播放器
        nextTick(() => {
          adjustPosition();
          initYouTubePlayer();
        });
      } else {
        // 隐藏时停止字幕同步
        stopSubtitleSync();
      }
    });
    
    // 生命周期
    onMounted(() => {
      // 添加全局事件监听
      document.addEventListener('mousemove', handleDrag);
      document.addEventListener('mouseup', endDrag);
      document.addEventListener('touchmove', handleDrag, { passive: false });
      document.addEventListener('touchend', endDrag);
      
      document.addEventListener('mousemove', handleResize);
      document.addEventListener('mouseup', endResize);
      document.addEventListener('touchmove', handleResize, { passive: false });
      document.addEventListener('touchend', endResize);
      
      // 字幕拖动事件
      document.addEventListener('mousemove', handleSubtitleDrag);
      document.addEventListener('mouseup', endSubtitleDrag);
      document.addEventListener('touchmove', handleSubtitleDrag, { passive: false });
      document.addEventListener('touchend', endSubtitleDrag);
      
      // 窗口大小变化时调整位置
      window.addEventListener('resize', adjustPosition);
      
      // 如果已经可见，初始化播放器
      if (props.visible && props.videoId) {
        nextTick(() => {
          initYouTubePlayer();
        });
      }
    });
    
    onUnmounted(() => {
      // 移除全局事件监听
      document.removeEventListener('mousemove', handleDrag);
      document.removeEventListener('mouseup', endDrag);
      document.removeEventListener('touchmove', handleDrag);
      document.removeEventListener('touchend', endDrag);
      
      document.removeEventListener('mousemove', handleResize);
      document.removeEventListener('mouseup', endResize);
      document.removeEventListener('touchmove', handleResize);
      document.removeEventListener('touchend', endResize);
      
      // 字幕拖动事件
      document.removeEventListener('mousemove', handleSubtitleDrag);
      document.removeEventListener('mouseup', endSubtitleDrag);
      document.removeEventListener('touchmove', handleSubtitleDrag);
      document.removeEventListener('touchend', endSubtitleDrag);
      
      window.removeEventListener('resize', adjustPosition);
      
      // 清理字幕同步
      stopSubtitleSync();
      
      // 清理字幕轮询定时器
      if (subtitlePollTimer) {
        clearInterval(subtitlePollTimer);
        subtitlePollTimer = null;
      }
      
      // 销毁播放器
      if (ytPlayer) {
        try {
          ytPlayer.destroy();
        } catch (e) {
          // 忽略
        }
        ytPlayer = null;
      }
    });
    
    return {
      // 状态
      minimized,
      position,
      size,
      isDragging,
      isResizing,
      iframeContainerId,
      
      // 字幕状态
      subtitleEnabled,
      subtitleLoading,
      currentSubtitle,
      subtitleButtonTitle,
      subtitleLang,
      subtitleBottom,
      isSubtitleDragging,
      subtitleFontSize,
      subtitleColor,
      showSubtitleSettings,
      colorOptions,
      
      // 方法
      close,
      toggleMinimize,
      startDrag,
      startResize,
      toggleSubtitle,
      toggleSubtitleLang,
      startSubtitleDrag,
      increaseSubtitleSize,
      decreaseSubtitleSize,
      setSubtitleColor,
      toggleSubtitleSettings
    };
  }
}; 