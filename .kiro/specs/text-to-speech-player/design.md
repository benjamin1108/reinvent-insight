# Design Document: Text-to-Speech Player

## Overview

本设计文档描述了一个集成到 ReadingView 的文本转语音（TTS）播放系统。该系统使用阿里云通义千问 Qwen3-TTS API，通过流式音频生成和播放技术，为用户提供高质量的文章朗读体验。系统采用前后端分离架构，后端负责与 TTS API 交互和音频缓存管理，前端提供精致的播放控制界面。

### Key Features

- **流式音频播放**: 边生成边播放，减少用户等待时间
- **智能缓存机制**: 缓存已生成的音频，避免重复 API 调用
- **精致的 UI 控件**: 现代化的播放控制条，与 ReadingView 无缝集成
- **多音色支持**: 支持 17 种 Qwen3-TTS 音色选择
- **播放速度控制**: 0.5x 到 2x 的灵活速度调整
- **统一模型配置**: 使用现有的 model_config.yaml 配置框架
- **智能文本处理**: 自动清理 Markdown、HTML 和代码块

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Browser)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ReadingView Component                    │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │        AudioControlBar Component               │  │  │
│  │  │  - Play/Pause/Stop buttons                     │  │  │
│  │  │  - Progress slider                             │  │  │
│  │  │  - Voice selector                              │  │  │
│  │  │  - Speed control                               │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │        AudioPlayer (Web Audio API)             │  │  │
│  │  │  - Stream buffer management                    │  │  │
│  │  │  - Playback control                            │  │  │
│  │  │  - Speed adjustment                            │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/SSE
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Python/FastAPI)                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │              TTS API Endpoint                         │  │
│  │  - /api/tts/generate (POST)                          │  │
│  │  - /api/tts/stream (GET, SSE)                        │  │
│  │  - /api/tts/cache/{hash} (GET)                       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              TTSService                               │  │
│  │  - Text preprocessing                                 │  │
│  │  - API client management                             │  │
│  │  - Stream handling                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AudioCache                               │  │
│  │  - File storage                                       │  │
│  │  - LRU eviction                                       │  │
│  │  - Hash-based lookup                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         ModelConfigManager (Existing)                 │  │
│  │  - Load config from model_config.yaml                │  │
│  │  - Task type: "text_to_speech"                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Qwen3-TTS API (DashScope)                       │
│  - Model: qwen3-tts-flash                                   │
│  - Streaming: SSE                                            │
│  - Audio format: PCM (Base64)                                │
└─────────────────────────────────────────────────────────────┘
```


### Component Interaction Flow

1. **User initiates playback**:
   - User clicks play button in AudioControlBar
   - Frontend sends article hash and preferences to backend

2. **Backend checks cache**:
   - AudioCache checks if audio exists for article hash + voice + speed
   - If cached, return audio file URL
   - If not cached, proceed to generation

3. **Audio generation (streaming)**:
   - TTSService preprocesses article text
   - Sends request to Qwen3-TTS API with SSE enabled
   - Receives Base64-encoded PCM chunks via SSE
   - Forwards chunks to frontend via SSE

4. **Frontend playback**:
   - AudioPlayer receives chunks and decodes Base64
   - Appends PCM data to Web Audio API buffer
   - Begins playback when sufficient buffer accumulated
   - Continues receiving and appending chunks seamlessly

5. **Cache storage**:
   - When stream completes, backend assembles complete WAV file
   - AudioCache stores file with hash-based filename
   - Future requests use cached file directly

## Components and Interfaces

### Backend Components

#### 1. TTS API Endpoints

**POST /api/tts/generate**
- Purpose: Generate audio for article (non-streaming, returns URL when complete)
- Request:
  ```json
  {
    "article_hash": "string",
    "text": "string",
    "voice": "Cherry",
    "language": "Chinese",
    "use_cache": true
  }
  ```
- Response:
  ```json
  {
    "audio_url": "/api/tts/cache/{hash}",
    "duration": 120.5,
    "cached": false
  }
  ```

**GET /api/tts/stream**
- Purpose: Stream audio generation in real-time (SSE)
- Query params: article_hash, voice, language, use_cache
- Response: Server-Sent Events stream
  ```
  event: chunk
  data: {"audio": "base64_pcm_data", "index": 0}

  event: chunk
  data: {"audio": "base64_pcm_data", "index": 1}

  event: complete
  data: {"audio_url": "/api/tts/cache/{hash}", "duration": 120.5}
  ```

**GET /api/tts/cache/{hash}**
- Purpose: Retrieve cached audio file
- Response: WAV audio file (audio/wav)


#### 2. TTSService Class

```python
class TTSService:
    """Text-to-Speech service using Qwen3-TTS API"""
    
    def __init__(self, model_client: BaseModelClient, cache: AudioCache):
        self.client = model_client
        self.cache = cache
    
    async def generate_audio_stream(
        self,
        text: str,
        voice: str = "Cherry",
        language: str = "Chinese"
    ) -> AsyncGenerator[bytes, None]:
        """Generate audio stream from text"""
        
    async def generate_audio(
        self,
        text: str,
        voice: str = "Cherry",
        language: str = "Chinese"
    ) -> str:
        """Generate complete audio file and return URL"""
        
    def preprocess_text(self, text: str, skip_code: bool = True) -> str:
        """Clean and prepare text for TTS"""
        
    def calculate_text_hash(
        self,
        text: str,
        voice: str,
        language: str
    ) -> str:
        """Calculate unique hash for caching"""
```

#### 3. AudioCache Class

```python
class AudioCache:
    """LRU cache for generated audio files"""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 500):
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        self.metadata = {}  # {hash: {size, last_access, path}}
    
    def get(self, audio_hash: str) -> Optional[Path]:
        """Retrieve cached audio file"""
        
    def put(self, audio_hash: str, audio_data: bytes) -> Path:
        """Store audio file in cache"""
        
    def invalidate(self, audio_hash: str) -> bool:
        """Remove audio from cache"""
        
    def evict_lru(self) -> None:
        """Remove least recently used files to free space"""
        
    def get_cache_size(self) -> int:
        """Get total cache size in bytes"""
```

#### 4. DashScope TTS Client Extension

Extend existing `DashScopeClient` to support TTS:

```python
class DashScopeClient(BaseModelClient):
    # ... existing methods ...
    
    async def generate_tts_stream(
        self,
        text: str,
        voice: str = "Cherry",
        language: str = "Chinese"
    ) -> AsyncGenerator[bytes, None]:
        """Generate TTS audio stream using Qwen3-TTS"""
        
    async def generate_tts(
        self,
        text: str,
        voice: str = "Cherry",
        language: str = "Chinese"
    ) -> bytes:
        """Generate complete TTS audio"""
```


### Frontend Components

#### 1. AudioControlBar Component

Vue 3 component providing playback controls:

```javascript
export default {
  name: 'AudioControlBar',
  
  props: {
    articleHash: String,
    articleText: String
  },
  
  data() {
    return {
      isPlaying: false,
      isLoading: false,
      currentTime: 0,
      duration: 0,
      volume: 1.0,
      playbackRate: 1.0,
      selectedVoice: 'Cherry',
      availableVoices: [...],
      error: null
    }
  },
  
  methods: {
    async play() {},
    pause() {},
    stop() {},
    seek(time) {},
    setVolume(volume) {},
    setPlaybackRate(rate) {},
    setVoice(voice) {}
  }
}
```

**UI Layout**:
```
┌────────────────────────────────────────────────────────────┐
│  🔊  ▶️  ⏸️  ⏹️   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│      Play Pause Stop    Progress Slider                    │
│                                                             │
│  00:45 / 03:20    🎤 Cherry ▼    🏃 1.0x ▼    🔊 ━━━━━━━  │
│  Current/Total    Voice Select   Speed        Volume       │
└────────────────────────────────────────────────────────────┘
```

#### 2. AudioPlayer Class

JavaScript class managing Web Audio API:

```javascript
class AudioPlayer {
  constructor() {
    this.audioContext = new AudioContext();
    this.sourceNode = null;
    this.gainNode = null;
    this.audioBuffer = null;
    this.startTime = 0;
    this.pauseTime = 0;
    this.isPlaying = false;
  }
  
  async loadFromStream(streamUrl) {
    // Connect to SSE stream and build audio buffer
  }
  
  async loadFromUrl(audioUrl) {
    // Load complete audio file
  }
  
  play() {
    // Start or resume playback
  }
  
  pause() {
    // Pause playback
  }
  
  stop() {
    // Stop and reset
  }
  
  seek(time) {
    // Seek to position
  }
  
  setPlaybackRate(rate) {
    // Adjust speed
  }
  
  setVolume(volume) {
    // Adjust volume
  }
  
  getCurrentTime() {
    // Get current position
  }
  
  getDuration() {
    // Get total duration
  }
}
```

#### 3. StreamBuffer Class

Manages streaming audio data:

```javascript
class StreamBuffer {
  constructor(audioContext) {
    this.audioContext = audioContext;
    this.chunks = [];
    this.sampleRate = 24000;
    this.channels = 1;
  }
  
  appendChunk(base64Data) {
    // Decode Base64 PCM and append to buffer
  }
  
  getAudioBuffer() {
    // Convert accumulated chunks to AudioBuffer
  }
  
  clear() {
    // Clear buffer
  }
}
```


## Data Models

### Backend Data Models

#### AudioMetadata

```python
@dataclass
class AudioMetadata:
    """Metadata for cached audio"""
    hash: str
    text_hash: str
    voice: str
    language: str
    duration: float
    file_size: int
    file_path: Path
    created_at: datetime
    last_accessed: datetime
    access_count: int
```

#### TTSRequest

```python
@dataclass
class TTSRequest:
    """TTS generation request"""
    article_hash: str
    text: str
    voice: str = "Cherry"
    language: str = "Chinese"
    use_cache: bool = True
    skip_code_blocks: bool = True
```

#### TTSResponse

```python
@dataclass
class TTSResponse:
    """TTS generation response"""
    audio_url: str
    duration: float
    cached: bool
    voice: str
    language: str
```

### Frontend Data Models

#### AudioState

```typescript
interface AudioState {
  isPlaying: boolean;
  isLoading: boolean;
  isPaused: boolean;
  currentTime: number;
  duration: number;
  buffered: number;
  error: string | null;
}
```

#### AudioPreferences

```typescript
interface AudioPreferences {
  voice: string;
  playbackRate: number;
  volume: number;
  skipCodeBlocks: boolean;
  autoPlay: boolean;
}
```

### Configuration Model

#### TTS Task Configuration (model_config.yaml)

```yaml
tasks:
  text_to_speech:
    provider: dashscope
    model_name: qwen3-tts-flash
    api_key_env: DASHSCOPE_API_KEY
    
    generation:
      temperature: 0.7  # Not used for TTS, but kept for consistency
      top_p: 0.9
      top_k: 40
      max_output_tokens: 600  # Max characters per request
    
    rate_limit:
      interval: 0.5
      max_retries: 3
      retry_backoff_base: 2.0
    
    # TTS-specific settings
    tts:
      default_voice: Cherry
      default_language: Chinese
      sample_rate: 24000
      audio_format: wav
      cache_enabled: true
      cache_max_size_mb: 500
      cache_dir: downloads/tts_cache
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Playback initiation responsiveness
*For any* article text and user play request, the audio player should begin playback within 2 seconds of the request.
**Validates: Requirements 1.2**

### Property 2: Empty content error handling
*For any* empty or whitespace-only article text, the TTS system should display an error message and prevent playback without making API calls.
**Validates: Requirements 1.3**

### Property 3: Pause and resume position preservation
*For any* audio playback position, pausing and then resuming should continue from the exact same position.
**Validates: Requirements 2.2**

### Property 4: Seek position accuracy
*For any* valid seek position in the audio, seeking to that position should result in playback continuing from that position with less than 100ms deviation.
**Validates: Requirements 2.3**

### Property 5: Stop resets playback
*For any* audio playback state, stopping should reset the current position to 0 and change the UI to the initial state.
**Validates: Requirements 2.4**

### Property 6: Stream buffer append order
*For any* sequence of audio chunks received from the API, the stream buffer should append them in the exact order received.
**Validates: Requirements 3.1**

### Property 7: Streaming playback threshold
*For any* audio stream, playback should begin when the buffer contains at least 2 seconds of audio data, before the complete audio is generated.
**Validates: Requirements 3.2**

### Property 8: Seamless chunk appending
*For any* audio chunk received during playback, appending it to the buffer should not cause audible gaps or glitches in playback.
**Validates: Requirements 3.3**

### Property 9: Network error graceful handling
*For any* network error during streaming, the system should handle it gracefully without crashing and notify the user with a clear error message.
**Validates: Requirements 3.5**

### Property 10: Cache storage completeness
*For any* successfully generated audio, the cache should store the complete audio file with a unique hash identifier that can be retrieved later.
**Validates: Requirements 4.1**

### Property 11: Cache-first lookup
*For any* audio generation request, the system should check the cache before making API calls, and use cached audio if available.
**Validates: Requirements 4.2, 4.3, 9.1**

### Property 12: Cache invalidation on content change
*For any* article with cached audio, if the article content changes, the old cache entry should be invalidated and new audio generated on next playback.
**Validates: Requirements 4.4**

### Property 13: LRU cache eviction
*For any* cache that exceeds the maximum size limit, the system should remove the least recently used audio files until the cache size is below the limit.
**Validates: Requirements 4.5**

### Property 14: UI responsiveness
*For any* user interaction with the audio control bar, the system should provide visual feedback within 100 milliseconds.
**Validates: Requirements 5.2**

### Property 15: Progress indicator accuracy
*For any* playing audio, the progress indicator should display the current position and total duration with updates at least every 100 milliseconds.
**Validates: Requirements 5.3**

### Property 16: Responsive layout adaptation
*For any* viewport resize to mobile dimensions (≤768px), the audio control bar should adapt its layout to remain fully usable.
**Validates: Requirements 5.5**


### Property 17: Voice selection persistence
*For any* voice selected by the user, subsequent audio generation should use that voice, and the preference should persist across sessions.
**Validates: Requirements 6.2, 6.4**

### Property 18: Voice change regeneration
*For any* audio currently playing, changing the voice should stop playback and regenerate the audio with the new voice.
**Validates: Requirements 6.3**

### Property 19: Language-based voice recommendation
*For any* detected article language, the system should recommend voices appropriate for that language.
**Validates: Requirements 6.5**

### Property 20: Markdown stripping completeness
*For any* article text containing Markdown formatting, the preprocessed text should contain no Markdown syntax characters (*, #, [], etc.).
**Validates: Requirements 7.1**

### Property 21: HTML tag removal
*For any* article text containing HTML tags, the preprocessed text should contain only the text content with all tags removed.
**Validates: Requirements 7.2**

### Property 22: Code block handling
*For any* article text containing code blocks, the preprocessed text should either skip them entirely or include them as plain text based on user preference.
**Validates: Requirements 7.3**

### Property 23: Special character safety
*For any* article text containing special characters or emojis, the TTS system should process them without throwing errors.
**Validates: Requirements 7.4**

### Property 24: Text chunking for long content
*For any* article text exceeding the API's maximum character limit (600 characters), the system should split it into chunks and process them sequentially.
**Validates: Requirements 7.5**

### Property 25: API error user notification
*For any* API error that occurs, the system should display a user-friendly error message that explains the issue without exposing technical details.
**Validates: Requirements 8.1**

### Property 26: Network reconnection attempts
*For any* network connection loss during streaming, the system should attempt to reconnect with exponential backoff up to 3 times.
**Validates: Requirements 8.3**

### Property 27: Cache reuse for duplicate requests
*For any* two requests for the same article with the same voice and language, the system should reuse the cached audio and make only one API call.
**Validates: Requirements 9.2**

### Property 28: Exponential backoff retry
*For any* API error response, the system should retry with exponential backoff (2^attempt seconds) up to a maximum of 3 attempts.
**Validates: Requirements 9.3**

### Property 29: Playback speed application
*For any* playback speed selection (0.5x to 2x), the audio player should immediately apply the new speed while maintaining the current playback position.
**Validates: Requirements 10.2, 10.3**

### Property 30: Speed preference persistence
*For any* playback speed set by the user, the preference should persist and be applied to future playback sessions.
**Validates: Requirements 10.4**

### Property 31: Speed indicator display
*For any* playback speed other than 1x, the audio control bar should display the current speed value.
**Validates: Requirements 10.5**

### Property 32: Environment variable override
*For any* configuration parameter with an environment variable set (MODEL_TEXT_TO_SPEECH_{PARAMETER}), the environment variable value should override the YAML configuration value.
**Validates: Requirements 11.3**

### Property 33: Configuration hot-reload
*For any* configuration file update, calling the reload method should apply the new configuration without requiring application restart.
**Validates: Requirements 11.5**


## Error Handling

### Error Categories

#### 1. User Input Errors
- **Empty Content**: Article text is empty or contains only whitespace
  - Action: Display error message, disable play button
  - Message: "无法播放：文章内容为空"

- **Invalid Voice Selection**: Selected voice not available
  - Action: Fall back to default voice (Cherry), log warning
  - Message: "所选音色不可用，已切换到默认音色"

#### 2. API Errors
- **Authentication Error**: Invalid API key
  - Action: Display error, disable TTS feature
  - Message: "语音服务配置错误，请联系管理员"

- **Rate Limit Exceeded**: Too many requests
  - Action: Implement exponential backoff, notify user
  - Message: "请求过于频繁，请稍后再试"

- **Quota Exhausted**: Daily quota exceeded
  - Action: Disable TTS feature, log alert
  - Message: "今日语音配额已用完，请明天再试"

- **Service Unavailable**: API service down
  - Action: Retry with backoff, notify user
  - Message: "语音服务暂时不可用，正在重试..."

#### 3. Network Errors
- **Connection Timeout**: Request timeout
  - Action: Retry up to 3 times, show error if all fail
  - Message: "网络连接超时，请检查网络后重试"

- **Connection Lost During Streaming**: Network interrupted
  - Action: Attempt reconnection, buffer existing audio
  - Message: "网络连接中断，正在尝试重新连接..."

#### 4. Cache Errors
- **Cache Read Error**: Cannot read cached file
  - Action: Invalidate cache entry, regenerate audio
  - Log: "Cache read failed for {hash}, regenerating"

- **Cache Write Error**: Cannot write to cache
  - Action: Continue without caching, log error
  - Log: "Cache write failed, continuing without cache"

- **Cache Full**: Cache size limit exceeded
  - Action: Evict LRU entries, retry write
  - Log: "Cache full, evicting LRU entries"

#### 5. Audio Processing Errors
- **Decode Error**: Cannot decode Base64 audio data
  - Action: Skip corrupted chunk, log error
  - Log: "Failed to decode audio chunk {index}"

- **Buffer Overflow**: Audio buffer too large
  - Action: Clear old buffer data, continue streaming
  - Log: "Audio buffer overflow, clearing old data"

- **Playback Error**: Web Audio API error
  - Action: Reset audio context, notify user
  - Message: "播放出错，请重试"

### Error Recovery Strategies

#### Retry with Exponential Backoff
```python
async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
            else:
                raise
```

#### Graceful Degradation
- If streaming fails, fall back to non-streaming generation
- If cache fails, continue without caching
- If preferred voice unavailable, use default voice

#### User Notification
- Show clear, actionable error messages
- Provide retry buttons where appropriate
- Log technical details for debugging


## Testing Strategy

### Dual Testing Approach

The TTS player will be tested using both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit tests** verify specific examples, edge cases, and integration points
- **Property-based tests** verify universal properties across all inputs
- Together they provide complete coverage: unit tests catch concrete bugs, property tests verify general correctness

### Unit Testing

#### Backend Unit Tests

**TTSService Tests**:
- Test text preprocessing with various Markdown formats
- Test HTML tag stripping
- Test code block handling (skip vs. include)
- Test text chunking for long content
- Test hash calculation consistency
- Test cache lookup before API calls

**AudioCache Tests**:
- Test file storage and retrieval
- Test LRU eviction when cache is full
- Test cache invalidation
- Test concurrent access handling
- Test cache size calculation

**API Endpoint Tests**:
- Test /api/tts/generate with valid input
- Test /api/tts/stream SSE connection
- Test /api/tts/cache/{hash} file serving
- Test error responses for invalid input
- Test authentication and authorization

#### Frontend Unit Tests

**AudioControlBar Tests**:
- Test play button click triggers playback
- Test pause button click pauses audio
- Test stop button resets state
- Test progress slider updates current time
- Test voice selector changes voice
- Test speed selector changes playback rate
- Test volume slider changes volume

**AudioPlayer Tests**:
- Test loading audio from URL
- Test loading audio from stream
- Test play/pause/stop functionality
- Test seek to specific position
- Test playback rate adjustment
- Test volume adjustment
- Test event emission (timeupdate, ended, error)

**StreamBuffer Tests**:
- Test Base64 decoding
- Test chunk appending
- Test AudioBuffer creation
- Test buffer clearing

### Property-Based Testing

We will use **pytest with Hypothesis** for Python backend tests and **fast-check** for JavaScript frontend tests. Each property-based test should run a minimum of 100 iterations.

#### Backend Property Tests

**Property Test 1: Cache-first lookup**
- **Feature: text-to-speech-player, Property 11: Cache-first lookup**
- **Validates: Requirements 4.2, 4.3, 9.1**
- Generate: Random article text, voice, language
- Property: For any request, cache should be checked before API calls
- Verify: Cache lookup is called before API client

**Property Test 2: LRU cache eviction**
- **Feature: text-to-speech-player, Property 13: LRU cache eviction**
- **Validates: Requirements 4.5**
- Generate: Random audio files exceeding cache limit
- Property: When cache is full, least recently used files are removed
- Verify: Oldest accessed files are evicted first

**Property Test 3: Markdown stripping completeness**
- **Feature: text-to-speech-player, Property 20: Markdown stripping completeness**
- **Validates: Requirements 7.1**
- Generate: Random text with Markdown syntax
- Property: Preprocessed text contains no Markdown characters
- Verify: No *, #, [], (), etc. in output

**Property Test 4: HTML tag removal**
- **Feature: text-to-speech-player, Property 21: HTML tag removal**
- **Validates: Requirements 7.2**
- Generate: Random text with HTML tags
- Property: Preprocessed text contains no HTML tags
- Verify: No <, >, tag names in output

**Property Test 5: Text chunking for long content**
- **Feature: text-to-speech-player, Property 24: Text chunking for long content**
- **Validates: Requirements 7.5**
- Generate: Random text exceeding max length
- Property: Text is split into chunks ≤ max length
- Verify: All chunks ≤ 600 characters, concatenation equals original

**Property Test 6: Exponential backoff retry**
- **Feature: text-to-speech-player, Property 28: Exponential backoff retry**
- **Validates: Requirements 9.3**
- Generate: Random API errors
- Property: Retry delays follow exponential pattern (2^attempt)
- Verify: Delays are approximately 1s, 2s, 4s

**Property Test 7: Environment variable override**
- **Feature: text-to-speech-player, Property 32: Environment variable override**
- **Validates: Requirements 11.3**
- Generate: Random config values and env var values
- Property: Env var value overrides YAML value
- Verify: Loaded config uses env var value


#### Frontend Property Tests

**Property Test 8: Pause and resume position preservation**
- **Feature: text-to-speech-player, Property 3: Pause and resume position preservation**
- **Validates: Requirements 2.2**
- Generate: Random pause positions in audio
- Property: Pausing then resuming continues from same position
- Verify: Position difference < 100ms

**Property Test 9: Seek position accuracy**
- **Feature: text-to-speech-player, Property 4: Seek position accuracy**
- **Validates: Requirements 2.3**
- Generate: Random seek positions
- Property: Seeking to position results in playback from that position
- Verify: Actual position within 100ms of target

**Property Test 10: Stream buffer append order**
- **Feature: text-to-speech-player, Property 6: Stream buffer append order**
- **Validates: Requirements 3.1**
- Generate: Random sequence of audio chunks
- Property: Chunks are appended in order received
- Verify: Buffer contains chunks in exact order

**Property Test 11: Playback speed application**
- **Feature: text-to-speech-player, Property 29: Playback speed application**
- **Validates: Requirements 10.2, 10.3**
- Generate: Random playback speeds (0.5x to 2x)
- Property: Speed change applies immediately, position preserved
- Verify: New speed active, position unchanged

**Property Test 12: Speed preference persistence**
- **Feature: text-to-speech-player, Property 30: Speed preference persistence**
- **Validates: Requirements 10.4**
- Generate: Random speed preferences
- Property: Speed preference persists across sessions
- Verify: Saved speed loaded on next session

### Integration Testing

#### End-to-End Tests

1. **Complete playback flow**:
   - User clicks play → audio generates → playback starts → audio completes
   - Verify: Audio plays completely without errors

2. **Cache hit flow**:
   - Generate audio → play again → verify cache used
   - Verify: Second playback uses cache, no API call

3. **Streaming flow**:
   - Start streaming → receive chunks → playback begins → stream completes
   - Verify: Playback starts before stream completes

4. **Error recovery flow**:
   - Simulate API error → verify retry → verify success or error message
   - Verify: Proper error handling and user notification

5. **Voice change flow**:
   - Start playback → change voice → verify regeneration
   - Verify: Audio regenerates with new voice

### Test Configuration

#### Property-Based Test Settings

**Python (Hypothesis)**:
```python
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(max_examples=100, deadline=None)
@given(
    text=st.text(min_size=1, max_size=10000),
    voice=st.sampled_from(['Cherry', 'Ethan', 'Jennifer']),
    language=st.sampled_from(['Chinese', 'English'])
)
async def test_cache_lookup_property(text, voice, language):
    # Test implementation
    pass
```

**JavaScript (fast-check)**:
```javascript
import fc from 'fast-check';

test('pause and resume preserves position', () => {
  fc.assert(
    fc.asyncProperty(
      fc.float({ min: 0, max: 100 }), // pause position
      async (pausePosition) => {
        // Test implementation
      }
    ),
    { numRuns: 100 }
  );
});
```

### Test Coverage Goals

- **Backend**: 80% code coverage minimum
- **Frontend**: 75% code coverage minimum
- **Property tests**: All 33 correctness properties covered
- **Integration tests**: All major user flows covered


## Implementation Details

### Text Preprocessing Pipeline

```python
def preprocess_text(text: str, skip_code: bool = True) -> str:
    """
    Clean and prepare text for TTS
    
    Steps:
    1. Strip HTML tags
    2. Remove Markdown formatting
    3. Handle code blocks (skip or convert to plain text)
    4. Normalize whitespace
    5. Remove special characters that cause TTS issues
    6. Validate length and chunk if necessary
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove Markdown code blocks
    if skip_code:
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)
    
    # Remove Markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
    text = re.sub(r'#+\s', '', text)                 # Headers
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text
```

### Audio Streaming Implementation

#### Backend SSE Stream

```python
async def stream_audio(request: TTSRequest):
    """Stream audio generation via SSE"""
    
    async def event_generator():
        try:
            # Check cache first
            audio_hash = calculate_hash(request)
            cached_path = cache.get(audio_hash)
            
            if cached_path and request.use_cache:
                # Serve cached audio
                yield {
                    "event": "cached",
                    "data": json.dumps({
                        "audio_url": f"/api/tts/cache/{audio_hash}",
                        "duration": get_audio_duration(cached_path)
                    })
                }
                return
            
            # Generate audio stream
            chunks = []
            async for chunk_data in tts_client.generate_tts_stream(
                text=request.text,
                voice=request.voice,
                language=request.language
            ):
                # Send chunk to client
                yield {
                    "event": "chunk",
                    "data": json.dumps({
                        "audio": chunk_data,
                        "index": len(chunks)
                    })
                }
                chunks.append(chunk_data)
            
            # Save complete audio to cache
            complete_audio = assemble_wav(chunks)
            cache_path = cache.put(audio_hash, complete_audio)
            
            # Send completion event
            yield {
                "event": "complete",
                "data": json.dumps({
                    "audio_url": f"/api/tts/cache/{audio_hash}",
                    "duration": get_audio_duration(cache_path)
                })
            }
            
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "message": "音频生成失败"
                })
            }
    
    return EventSourceResponse(event_generator())
```

#### Frontend SSE Consumer

```javascript
async loadFromStream(streamUrl) {
  const eventSource = new EventSource(streamUrl);
  const streamBuffer = new StreamBuffer(this.audioContext);
  
  eventSource.addEventListener('chunk', (event) => {
    const data = JSON.parse(event.data);
    streamBuffer.appendChunk(data.audio);
    
    // Start playback when buffer has enough data
    if (!this.isPlaying && streamBuffer.getDuration() >= 2.0) {
      this.audioBuffer = streamBuffer.getAudioBuffer();
      this.play();
    }
  });
  
  eventSource.addEventListener('complete', (event) => {
    const data = JSON.parse(event.data);
    this.audioBuffer = streamBuffer.getAudioBuffer();
    this.duration = data.duration;
    eventSource.close();
  });
  
  eventSource.addEventListener('cached', (event) => {
    const data = JSON.parse(event.data);
    // Load from cache URL instead
    this.loadFromUrl(data.audio_url);
    eventSource.close();
  });
  
  eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    this.handleError(data.message);
    eventSource.close();
  });
}
```

### WAV File Assembly

```python
def assemble_wav(pcm_chunks: List[bytes], sample_rate: int = 24000) -> bytes:
    """
    Assemble PCM chunks into WAV file
    
    WAV format:
    - RIFF header
    - fmt chunk (format info)
    - data chunk (PCM data)
    """
    import struct
    
    # Concatenate all PCM data
    pcm_data = b''.join(pcm_chunks)
    pcm_size = len(pcm_data)
    
    # WAV header
    wav_header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + pcm_size,  # File size - 8
        b'WAVE',
        b'fmt ',
        16,  # fmt chunk size
        1,   # PCM format
        1,   # Mono
        sample_rate,
        sample_rate * 2,  # Byte rate
        2,   # Block align
        16,  # Bits per sample
        b'data',
        pcm_size
    )
    
    return wav_header + pcm_data
```


### Cache Management

#### Hash Calculation

```python
def calculate_hash(text: str, voice: str, language: str) -> str:
    """
    Calculate unique hash for caching
    
    Hash includes:
    - Preprocessed text content
    - Voice selection
    - Language setting
    """
    import hashlib
    
    content = f"{text}|{voice}|{language}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

#### LRU Eviction

```python
def evict_lru(self) -> None:
    """Remove least recently used files"""
    while self.get_cache_size() > self.max_size_mb * 1024 * 1024:
        # Sort by last access time
        sorted_items = sorted(
            self.metadata.items(),
            key=lambda x: x[1]['last_accessed']
        )
        
        if not sorted_items:
            break
        
        # Remove oldest
        oldest_hash, oldest_meta = sorted_items[0]
        self.invalidate(oldest_hash)
        
        logger.info(f"Evicted LRU cache entry: {oldest_hash}")
```

### UI Component Styling

#### AudioControlBar CSS

```css
.audio-control-bar {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.9));
  backdrop-filter: blur(10px);
  border-top: 1px solid #374151;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 100;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
}

.audio-control-bar__buttons {
  display: flex;
  gap: 0.5rem;
}

.audio-control-bar__button {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #22d3ee, #3b82f6);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.audio-control-bar__button:hover {
  transform: scale(1.1);
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.5);
}

.audio-control-bar__button:active {
  transform: scale(0.95);
}

.audio-control-bar__button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.audio-control-bar__progress {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.audio-control-bar__slider {
  width: 100%;
  height: 4px;
  background: #374151;
  border-radius: 2px;
  position: relative;
  cursor: pointer;
}

.audio-control-bar__slider-fill {
  height: 100%;
  background: linear-gradient(to right, #22d3ee, #3b82f6);
  border-radius: 2px;
  transition: width 0.1s linear;
}

.audio-control-bar__slider-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.8);
  cursor: grab;
}

.audio-control-bar__slider-thumb:active {
  cursor: grabbing;
  transform: translate(-50%, -50%) scale(1.2);
}

.audio-control-bar__time {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: #9ca3af;
  font-family: 'SF Mono', 'JetBrains Mono', monospace;
}

.audio-control-bar__controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.audio-control-bar__select {
  background: rgba(55, 65, 81, 0.5);
  border: 1px solid #374151;
  border-radius: 0.5rem;
  padding: 0.5rem 1rem;
  color: #e5e7eb;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.audio-control-bar__select:hover {
  border-color: #22d3ee;
  background: rgba(34, 211, 238, 0.1);
}

.audio-control-bar__select:focus {
  outline: none;
  border-color: #22d3ee;
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.2);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .audio-control-bar {
    padding: 0.75rem 1rem;
    flex-wrap: wrap;
  }
  
  .audio-control-bar__progress {
    order: -1;
    width: 100%;
    margin-bottom: 0.5rem;
  }
  
  .audio-control-bar__controls {
    gap: 0.5rem;
  }
  
  .audio-control-bar__select {
    font-size: 0.75rem;
    padding: 0.375rem 0.75rem;
  }
}
```


### Performance Considerations

#### Backend Optimizations

1. **Async I/O**: Use asyncio for all I/O operations
   - API calls are non-blocking
   - File operations use aiofiles
   - Database queries use async drivers

2. **Connection Pooling**: Reuse HTTP connections
   - Use aiohttp ClientSession
   - Configure connection limits
   - Implement connection timeout

3. **Caching Strategy**:
   - Check cache before API calls (saves cost and time)
   - Use memory-mapped files for large audio
   - Implement cache warming for popular articles

4. **Rate Limiting**:
   - Respect API rate limits (0.5s interval)
   - Use token bucket algorithm
   - Queue requests during high load

5. **Text Chunking**:
   - Split long text at sentence boundaries
   - Process chunks in parallel when possible
   - Merge audio chunks efficiently

#### Frontend Optimizations

1. **Lazy Loading**: Load audio player only when needed
   - Don't initialize Web Audio API until play clicked
   - Defer loading of audio control bar component

2. **Buffer Management**:
   - Use circular buffer for streaming
   - Limit buffer size to prevent memory issues
   - Clear old buffer data during long playback

3. **UI Responsiveness**:
   - Use requestAnimationFrame for progress updates
   - Debounce slider drag events
   - Throttle volume/speed changes

4. **Resource Cleanup**:
   - Disconnect audio nodes when not playing
   - Close EventSource connections properly
   - Cancel pending requests on component unmount

5. **Progressive Enhancement**:
   - Check Web Audio API support
   - Fall back to HTML5 audio if needed
   - Provide clear error messages for unsupported browsers

### Security Considerations

#### Backend Security

1. **API Key Protection**:
   - Store API keys in environment variables
   - Never expose keys in client-side code
   - Rotate keys regularly

2. **Input Validation**:
   - Sanitize article text input
   - Validate voice and language parameters
   - Limit text length to prevent abuse

3. **Rate Limiting**:
   - Implement per-user rate limits
   - Prevent API quota exhaustion
   - Log suspicious activity

4. **Cache Security**:
   - Use secure hash algorithms (SHA-256)
   - Prevent directory traversal attacks
   - Validate file paths before access

5. **Error Handling**:
   - Don't expose internal errors to users
   - Log errors securely
   - Sanitize error messages

#### Frontend Security

1. **XSS Prevention**:
   - Sanitize article content before display
   - Use Vue's built-in XSS protection
   - Validate all user inputs

2. **CSRF Protection**:
   - Use CSRF tokens for API requests
   - Validate origin headers
   - Implement SameSite cookies

3. **Content Security Policy**:
   - Restrict script sources
   - Allow only trusted audio sources
   - Prevent inline script execution

### Monitoring and Logging

#### Metrics to Track

1. **Performance Metrics**:
   - Time to first audio (TTFA)
   - Audio generation time
   - Cache hit rate
   - API response time

2. **Usage Metrics**:
   - Number of audio generations
   - Most popular voices
   - Average playback duration
   - Cache size and eviction rate

3. **Error Metrics**:
   - API error rate
   - Network error rate
   - Cache error rate
   - Client-side errors

#### Logging Strategy

```python
# Backend logging
logger.info("TTS generation started", extra={
    "article_hash": article_hash,
    "voice": voice,
    "language": language,
    "text_length": len(text),
    "cached": cached
})

logger.info("TTS generation completed", extra={
    "article_hash": article_hash,
    "duration": duration,
    "generation_time": generation_time,
    "cache_hit": cache_hit
})

logger.error("TTS generation failed", extra={
    "article_hash": article_hash,
    "error": str(error),
    "retry_count": retry_count
})
```

```javascript
// Frontend logging
console.log('[TTS] Playback started', {
  articleHash,
  voice,
  playbackRate,
  cached: isCached
});

console.log('[TTS] Playback completed', {
  articleHash,
  duration,
  playbackTime
});

console.error('[TTS] Playback error', {
  articleHash,
  error: error.message,
  stack: error.stack
});
```


## Deployment Considerations

### Configuration Management

#### Environment Variables

```bash
# Required
DASHSCOPE_API_KEY=sk-xxx

# Optional (with defaults)
MODEL_TEXT_TO_SPEECH_MODEL_NAME=qwen3-tts-flash
MODEL_TEXT_TO_SPEECH_DEFAULT_VOICE=Cherry
MODEL_TEXT_TO_SPEECH_CACHE_MAX_SIZE_MB=500
MODEL_TEXT_TO_SPEECH_CACHE_DIR=downloads/tts_cache
```

#### model_config.yaml Updates

Add TTS task configuration:

```yaml
tasks:
  text_to_speech:
    provider: dashscope
    model_name: qwen3-tts-flash
    api_key_env: DASHSCOPE_API_KEY
    
    generation:
      temperature: 0.7
      top_p: 0.9
      top_k: 40
      max_output_tokens: 600
    
    rate_limit:
      interval: 0.5
      max_retries: 3
      retry_backoff_base: 2.0
    
    tts:
      default_voice: Cherry
      default_language: Chinese
      sample_rate: 24000
      audio_format: wav
      cache_enabled: true
      cache_max_size_mb: 500
      cache_dir: downloads/tts_cache
```

### Database Schema (Optional)

If tracking TTS usage in database:

```sql
CREATE TABLE tts_usage (
    id SERIAL PRIMARY KEY,
    article_hash VARCHAR(64) NOT NULL,
    voice VARCHAR(50) NOT NULL,
    language VARCHAR(50) NOT NULL,
    text_length INTEGER NOT NULL,
    audio_duration FLOAT NOT NULL,
    cached BOOLEAN NOT NULL,
    generation_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_article_hash (article_hash),
    INDEX idx_created_at (created_at)
);

CREATE TABLE tts_cache_metadata (
    audio_hash VARCHAR(64) PRIMARY KEY,
    article_hash VARCHAR(64) NOT NULL,
    voice VARCHAR(50) NOT NULL,
    language VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    duration FLOAT NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    INDEX idx_article_hash (article_hash),
    INDEX idx_last_accessed (last_accessed)
);
```

### Deployment Checklist

#### Backend Deployment

- [ ] Install required Python packages (dashscope, aiofiles, etc.)
- [ ] Set DASHSCOPE_API_KEY environment variable
- [ ] Create TTS cache directory with proper permissions
- [ ] Update model_config.yaml with TTS configuration
- [ ] Run database migrations (if using database tracking)
- [ ] Test API endpoints with curl/Postman
- [ ] Verify cache read/write permissions
- [ ] Configure log rotation for TTS logs
- [ ] Set up monitoring alerts for API errors
- [ ] Test rate limiting and retry logic

#### Frontend Deployment

- [ ] Build frontend assets with TTS components
- [ ] Test Web Audio API support in target browsers
- [ ] Verify SSE connection handling
- [ ] Test responsive layout on mobile devices
- [ ] Verify audio control bar positioning
- [ ] Test keyboard shortcuts
- [ ] Verify accessibility features (ARIA labels, keyboard navigation)
- [ ] Test error handling and user notifications
- [ ] Verify preference persistence (localStorage)
- [ ] Test with various article lengths and formats

#### Integration Testing

- [ ] Test complete flow: play → stream → cache → replay
- [ ] Test voice selection and switching
- [ ] Test playback speed adjustment
- [ ] Test pause/resume/stop functionality
- [ ] Test seek functionality
- [ ] Test error scenarios (network errors, API errors)
- [ ] Test cache eviction when full
- [ ] Test concurrent requests
- [ ] Test mobile responsiveness
- [ ] Load test with multiple users

### Rollback Plan

If issues arise after deployment:

1. **Disable TTS Feature**:
   - Set feature flag to disable TTS UI
   - Return 503 from TTS API endpoints
   - Display maintenance message to users

2. **Revert Code Changes**:
   - Rollback to previous deployment
   - Restore previous model_config.yaml
   - Clear TTS cache if corrupted

3. **Database Rollback** (if applicable):
   - Revert database migrations
   - Restore from backup if needed

4. **Monitor and Debug**:
   - Check logs for errors
   - Verify API key validity
   - Test cache read/write
   - Check network connectivity to DashScope API


## Future Enhancements

### Phase 2 Features

1. **Offline Support**:
   - Download audio for offline playback
   - Service worker for caching
   - Background sync for downloads

2. **Advanced Voice Customization**:
   - Pitch adjustment
   - Speaking rate fine-tuning
   - Emotion/tone selection

3. **Multi-language Auto-detection**:
   - Detect article language automatically
   - Switch voices based on language
   - Support mixed-language articles

4. **Playlist Mode**:
   - Queue multiple articles
   - Auto-play next article
   - Shuffle and repeat options

5. **Bookmarks and Highlights**:
   - Bookmark specific positions
   - Highlight text while playing
   - Jump to bookmarked positions

6. **Social Features**:
   - Share audio with timestamp
   - Collaborative playlists
   - Comments at specific timestamps

7. **Analytics Dashboard**:
   - Listening statistics
   - Popular articles
   - Voice preferences
   - Usage patterns

8. **Accessibility Enhancements**:
   - Screen reader optimization
   - High contrast mode
   - Keyboard-only navigation
   - Voice commands

### Technical Debt and Improvements

1. **Performance**:
   - Implement audio compression
   - Use WebAssembly for audio processing
   - Optimize cache lookup with bloom filters
   - Implement predictive caching

2. **Reliability**:
   - Add circuit breaker pattern
   - Implement request deduplication
   - Add health check endpoints
   - Improve error recovery

3. **Scalability**:
   - Distribute cache across multiple servers
   - Implement CDN for audio files
   - Add load balancing
   - Optimize database queries

4. **Maintainability**:
   - Add comprehensive documentation
   - Improve test coverage
   - Refactor complex components
   - Add performance benchmarks

## Conclusion

This design document provides a comprehensive blueprint for implementing a text-to-speech player integrated into the ReadingView component. The system leverages Qwen3-TTS API for high-quality audio generation, implements intelligent caching to optimize costs, and provides a polished user interface with modern playback controls.

Key design decisions:

- **Streaming architecture** for responsive user experience
- **LRU caching** to balance performance and storage
- **Unified model configuration** for consistency with existing systems
- **Property-based testing** for comprehensive correctness verification
- **Progressive enhancement** for broad browser support

The implementation follows best practices for security, performance, and maintainability, ensuring a robust and scalable solution that enhances the reading experience for users.
