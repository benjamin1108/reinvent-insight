# Requirements Document

## Introduction

本文档定义了一个集成到 ReadingView 的文本转语音（TTS）播放功能。该功能使用阿里云通义千问 Qwen3-TTS API，支持流式音频生成和播放，并提供音频缓存机制以优化用户体验。播放控件设计精致美观，自然嵌入到阅读界面中。

## Glossary

- **TTS System**: 文本转语音系统，负责将文本内容转换为语音音频
- **Audio Player**: 音频播放器组件，提供播放、暂停、进度控制等功能
- **Stream Buffer**: 流式缓冲区，用于接收和处理流式音频数据
- **Audio Cache**: 音频缓存系统，用于存储已生成的音频文件
- **PCM Audio**: 脉冲编码调制音频格式，原始音频数据格式
- **WAV Audio**: 波形音频文件格式，包含 PCM 数据和文件头
- **Base64 Encoding**: Base64 编码，用于在 HTTP 传输中编码二进制音频数据
- **Reading View**: 文章阅读视图组件，显示文章内容的主界面
- **Audio Control Bar**: 音频控制条，包含播放控制按钮和进度条的 UI 组件
- **Qwen3-TTS API**: 阿里云通义千问语音合成 API
- **SSE (Server-Sent Events)**: 服务器推送事件，用于实现流式数据传输

## Requirements

### Requirement 1

**User Story:** 作为用户，我希望能够朗读当前文章的内容，以便在不方便阅读时通过听觉获取信息。

#### Acceptance Criteria

1. WHEN a user clicks the play button THEN the TTS System SHALL begin converting the article text to speech and start playback
2. WHEN the TTS System generates audio data THEN the Audio Player SHALL begin playing audio within 2 seconds of the user's request
3. WHEN the article content is empty or invalid THEN the TTS System SHALL display an error message and prevent playback
4. WHEN the TTS System is processing THEN the Audio Control Bar SHALL display a loading indicator
5. WHEN audio playback starts THEN the Audio Control Bar SHALL update to show the playing state with a pause button

### Requirement 2

**User Story:** 作为用户，我希望能够控制音频播放（播放、暂停、停止、调整进度），以便根据需要管理播放状态。

#### Acceptance Criteria

1. WHEN a user clicks the pause button during playback THEN the Audio Player SHALL pause the audio immediately
2. WHEN a user clicks the play button while paused THEN the Audio Player SHALL resume playback from the paused position
3. WHEN a user drags the progress slider THEN the Audio Player SHALL seek to the corresponding position in the audio
4. WHEN a user clicks the stop button THEN the Audio Player SHALL stop playback and reset the progress to the beginning
5. WHEN audio playback completes naturally THEN the Audio Player SHALL reset to the initial state with the play button visible

### Requirement 3

**User Story:** 作为用户，我希望系统能够流式播放音频，以便在音频生成的同时就能开始收听，减少等待时间。

#### Acceptance Criteria

1. WHEN the TTS System receives audio chunks from the API THEN the Stream Buffer SHALL append the chunks to the playback queue
2. WHEN the Stream Buffer accumulates sufficient audio data THEN the Audio Player SHALL begin playback before the entire audio is generated
3. WHEN the Audio Player is playing and new chunks arrive THEN the Stream Buffer SHALL seamlessly append them to the current playback
4. WHEN the stream ends THEN the Stream Buffer SHALL signal completion to the Audio Player
5. WHEN a network error occurs during streaming THEN the TTS System SHALL handle the error gracefully and notify the user

### Requirement 4

**User Story:** 作为用户，我希望系统能够缓存已生成的音频，以便下次播放同一文章时无需重新生成，节省时间和成本。

#### Acceptance Criteria

1. WHEN audio generation completes successfully THEN the Audio Cache SHALL store the complete audio file with a unique identifier
2. WHEN a user requests playback for an article THEN the TTS System SHALL check the Audio Cache for existing audio before generating new audio
3. WHEN cached audio exists for an article THEN the Audio Player SHALL load and play the cached audio directly
4. WHEN the article content is updated THEN the TTS System SHALL invalidate the old cached audio and generate new audio on next playback
5. WHEN the Audio Cache exceeds storage limits THEN the system SHALL remove the least recently used cached audio files

### Requirement 5

**User Story:** 作为用户，我希望音频播放控件设计精致美观且易于使用，以便获得良好的用户体验。

#### Acceptance Criteria

1. WHEN the Reading View loads THEN the Audio Control Bar SHALL be positioned in a non-intrusive location that does not obstruct article content
2. WHEN the user interacts with the Audio Control Bar THEN the system SHALL provide visual feedback within 100 milliseconds
3. WHEN the audio is playing THEN the Audio Control Bar SHALL display a real-time progress indicator showing current position and total duration
4. WHEN the user hovers over control buttons THEN the system SHALL display tooltips explaining the button function
5. WHEN the viewport is resized to mobile dimensions THEN the Audio Control Bar SHALL adapt its layout to remain usable and accessible

### Requirement 6

**User Story:** 作为用户，我希望能够选择不同的语音音色，以便根据个人喜好定制听觉体验。

#### Acceptance Criteria

1. WHEN the Audio Control Bar is displayed THEN the system SHALL provide a voice selection dropdown with available voices
2. WHEN a user selects a different voice THEN the TTS System SHALL use the selected voice for subsequent audio generation
3. WHEN a user changes the voice during playback THEN the system SHALL stop current playback and regenerate audio with the new voice
4. WHEN the user's voice preference is set THEN the system SHALL persist the preference for future sessions
5. WHERE the article language is detected THEN the system SHALL recommend appropriate voices for that language

### Requirement 7

**User Story:** 作为开发者，我希望 TTS 系统能够正确处理各种文本格式和特殊字符，以便提供准确的语音输出。

#### Acceptance Criteria

1. WHEN the article contains Markdown formatting THEN the TTS System SHALL convert it to plain text before sending to the API
2. WHEN the article contains HTML tags THEN the TTS System SHALL strip the tags and extract only the text content
3. WHEN the article contains code blocks THEN the TTS System SHALL either skip them or read them as plain text based on user preference
4. WHEN the article contains special characters or emojis THEN the TTS System SHALL handle them appropriately without causing errors
5. WHEN the article exceeds the API's maximum character limit THEN the TTS System SHALL split the text into chunks and process them sequentially

### Requirement 8

**User Story:** 作为用户，我希望系统能够显示清晰的错误信息和状态提示，以便了解当前的播放状态和可能的问题。

#### Acceptance Criteria

1. WHEN an API error occurs THEN the TTS System SHALL display a user-friendly error message explaining the issue
2. WHEN the API rate limit is exceeded THEN the system SHALL inform the user and suggest waiting before retrying
3. WHEN the network connection is lost during streaming THEN the system SHALL attempt to reconnect and notify the user of the connection status
4. WHEN audio generation is in progress THEN the Audio Control Bar SHALL display the current status (e.g., "Generating audio...")
5. WHEN the cached audio is being loaded THEN the system SHALL display a brief loading indicator

### Requirement 9

**User Story:** 作为系统管理员，我希望 TTS 功能能够高效使用 API 配额，以便控制成本并确保服务可用性。

#### Acceptance Criteria

1. WHEN audio is requested THEN the TTS System SHALL check the Audio Cache before making API calls
2. WHEN multiple users request the same article THEN the system SHALL reuse cached audio to avoid duplicate API calls
3. WHEN the API returns an error THEN the TTS System SHALL implement exponential backoff retry logic with a maximum of 3 attempts
4. WHEN the daily API quota is approaching the limit THEN the system SHALL log a warning for monitoring purposes
5. WHEN the API quota is exhausted THEN the system SHALL disable the TTS feature and display an appropriate message to users

### Requirement 10

**User Story:** 作为用户，我希望能够调整播放速度，以便根据个人习惯加快或减慢语音播放。

#### Acceptance Criteria

1. WHEN the Audio Control Bar is displayed THEN the system SHALL provide a playback speed control with options (0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x)
2. WHEN a user selects a different playback speed THEN the Audio Player SHALL immediately apply the new speed to the current playback
3. WHEN the playback speed is changed THEN the Audio Player SHALL maintain the current playback position
4. WHEN the user's speed preference is set THEN the system SHALL persist the preference for future playback sessions
5. WHEN the playback speed is not 1x THEN the Audio Control Bar SHALL display the current speed indicator

### Requirement 11

**User Story:** 作为开发者，我希望 TTS 系统使用统一的模型配置框架，以便与现有系统保持一致并便于维护。

#### Acceptance Criteria

1. WHEN the TTS System initializes THEN the system SHALL load configuration from the unified model_config.yaml file
2. WHEN a TTS task is created THEN the system SHALL use the task type "text_to_speech" to retrieve model configuration
3. WHEN the model configuration is loaded THEN the system SHALL support environment variable overrides following the pattern MODEL_TEXT_TO_SPEECH_{PARAMETER}
4. WHEN the TTS API is called THEN the system SHALL use the DashScope provider with the configured model name and parameters
5. WHEN the configuration is updated THEN the system SHALL support hot-reloading without requiring application restart
