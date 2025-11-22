# Design Document: True Streaming TTS

## Overview

本设计文档描述了如何修复当前 TTS 系统的阻塞问题，实现真正的流式音频播放。当前实现虽然调用了 Gemini TTS 的流式 API，但在后端使用了阻塞式的音频块收集逻辑，导致必须等待所有音频生成完成（可能长达数百秒）才开始发送数据给前端。

本设计将重构后端的流式处理逻辑，使用 Python 的异步生成器（async generator）来实现真正的流式处理，让音频块一旦从 API 接收到就立即发送给前端，从而实现 2-5 秒内开始播放的目标。

### Key Features

- **真正的流式处理**: 音频块一旦生成就立即发送，不等待所有块生成完成
- **异步生成器模式**: 使用 Python async generator 实现零阻塞的流式处理
- **首字节延迟优化**: 从点击播放到听到声音控制在 2-5 秒内
- **恒定内存使用**: 不收集所有音频块到内存，内存使用与音频长度无关
- **实时进度反馈**: 每个音频块发送时都报告进度
- **优雅的错误处理**: 网络中断时继续播放已缓冲的音频

## Architecture

### Current Architecture (Problematic)

```
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Python/FastAPI)                  │
├─────────────────────────────────────────────────────────────┤
│  generate_tts_stream():                                      │
│    ┌──────────────────────────────────────────────────┐    │
│    │  1. Call Gemini API (streaming)                  │    │
│    │  2. ❌ Collect ALL chunks into list              │    │
│    │     audio_chunks = []                            │    │
│    │     for chunk in stream:                         │    │
│    │         audio_chunks.append(chunk)               │    │
│    │  3. ❌ Wait for ALL chunks (454 seconds!)        │    │
│    │  4. Then yield chunks one by one                 │    │
│    └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ After 454 seconds...
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Browser)                      │
│  Finally receives first chunk after 454 seconds              │
└─────────────────────────────────────────────────────────────┘
```

**Problem**: The `run_in_executor` wraps a synchronous function that collects all chunks before returning, blocking the entire async flow.

### New Architecture (True Streaming)

```
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Python/FastAPI)                  │
├─────────────────────────────────────────────────────────────┤
│  generate_tts_stream():                                      │
│    ┌──────────────────────────────────────────────────┐    │
│    │  1. Call Gemini API (streaming)                  │    │
│    │  2. ✅ Async iterate over stream                 │    │
│    │     async for chunk in async_stream:             │    │
│    │  3. ✅ Yield immediately (< 100ms)               │    │
│    │         yield chunk                              │    │
│    │  4. ✅ No collection, no waiting                 │    │
│    └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ 2-5 seconds
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Browser)                      │
│  Receives first chunk in 2-5 seconds, starts playing        │
│  Continues receiving chunks as they're generated            │
└─────────────────────────────────────────────────────────────┘
```

**Solution**: Use async generator pattern with `async for` to yield chunks immediately as they arrive from the API.

## Components and Interfaces

### Modified Backend Components

#### 1. GeminiClient.generate_tts_stream() - Core Fix

**Current Implementation (Problematic)**:
```python
async def generate_tts_stream(self, text: str, voice: str, language: str):
    def _call_tts_stream():
        # Synchronous function that collects ALL chunks
        client = genai.Client(api_key=self.config.api_key)
        response_stream = client.models.generate_content_stream(...)
        
        audio_chunks = []  # ❌ Blocking collection
        for chunk in response_stream:
            if chunk.candidates:
                for part in chunk.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        audio_chunks.append(part.inline_data.data)
        
        return audio_chunks  # ❌ Returns only after ALL chunks collected
    
    # ❌ Blocks until _call_tts_stream completes
    audio_chunks = await loop.run_in_executor(None, _call_tts_stream)
    
    # ❌ Only now starts yielding
    for i, audio_data in enumerate(audio_chunks):
        yield audio_data
```

**New Implementation (True Streaming)**:
```python
async def generate_tts_stream(
    self,
    text: str,
    voice: str = "Kore",
    language: str = "zh-CN"
) -> AsyncGenerator[bytes, None]:
    """
    Generate TTS audio stream with true streaming (no blocking collection).
    
    Yields audio chunks immediately as they arrive from the Gemini API,
    without waiting for all chunks to be generated.
    """
    try:
        from google import genai
        from google.genai import types
        import asyncio
        import base64
        
        logger.info(f"🎤 开始真正的流式 TTS: voice={voice}, text_length={len(text)}")
        start_time = asyncio.get_event_loop().time()
        
        # Create client (can be done synchronously, it's just initialization)
        client = genai.Client(api_key=self.config.api_key)
        
        # Helper to wrap sync iterator for async iteration
        async def async_stream_wrapper():
            """Wrap synchronous stream for async iteration"""
            def _get_stream():
                return client.models.generate_content_stream(
                    model=self.config.model_name,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice
                                )
                            )
                        )
                    )
                )
            
            # Get the stream
            stream = await asyncio.to_thread(_get_stream)
            
            # Iterate over stream chunks asynchronously
            chunk_index = 0
            while True:
                try:
                    # Get next chunk in thread pool to avoid blocking
                    chunk = await asyncio.to_thread(lambda: next(stream, None))
                    if chunk is None:
                        break
                    
                    chunk_index += 1
                    yield chunk, chunk_index
                    
                except StopIteration:
                    break
                except Exception as e:
                    logger.error(f"Error reading chunk {chunk_index}: {e}")
                    raise
        
        # Process stream and yield audio chunks immediately
        chunk_count = 0
        total_bytes = 0
        first_chunk_time = None
        
        async for chunk, chunk_index in async_stream_wrapper():
            # Record first chunk latency
            if chunk_count == 0:
                first_chunk_time = asyncio.get_event_loop().time()
                first_chunk_latency = first_chunk_time - start_time
                logger.info(f"⚡ 首块延迟: {first_chunk_latency:.2f}s")
            
            # Extract audio data from chunk
            if chunk.candidates:
                for part in chunk.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        audio_data = part.inline_data.data
                        
                        # Encode as Base64 for frontend
                        if isinstance(audio_data, str):
                            pcm_data = base64.b64decode(audio_data)
                        else:
                            pcm_data = audio_data
                        
                        b64_data = base64.b64encode(pcm_data).decode('utf-8')
                        
                        chunk_count += 1
                        total_bytes += len(pcm_data)
                        
                        logger.info(
                            f"📦 立即发送音频块 {chunk_count}: "
                            f"{len(pcm_data)} bytes, "
                            f"累计 {total_bytes / 1024:.1f}KB"
                        )
                        
                        # ✅ Yield immediately, no collection!
                        yield b64_data.encode('utf-8')
        
        # Log completion
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        logger.info(
            f"🎉 流式 TTS 完成: "
            f"{chunk_count} 块, "
            f"{total_bytes / 1024:.1f}KB, "
            f"总时长 {total_time:.2f}s"
        )
        
    except Exception as e:
        logger.error(f"流式 TTS 失败: {e}", exc_info=True)
        raise APIError(f"Gemini TTS 流式生成失败: {e}") from e
```

**Key Changes**:
1. ✅ Removed `audio_chunks = []` collection list
2. ✅ Removed blocking `for chunk in response_stream` loop
3. ✅ Added `async_stream_wrapper()` to properly wrap sync iterator
4. ✅ Use `asyncio.to_thread()` for each iteration step (non-blocking)
5. ✅ Yield chunks immediately with `yield` (not after collection)
6. ✅ Added first chunk latency tracking
7. ✅ Added detailed logging for each chunk

#### 2. API Endpoint - No Changes Needed

The `/api/tts/stream` endpoint already correctly handles async generators:

```python
@app.get("/api/tts/stream")
async def stream_tts(...):
    async for chunk in tts_service.generate_audio_stream(...):
        # This will now receive chunks immediately!
        yield f"event: chunk\n"
        yield f"data: {json.dumps({'index': chunk_index, 'data': chunk})}\n\n"
```

The endpoint code doesn't need changes because it already uses `async for` correctly. The problem was in the `generate_tts_stream()` method that it calls.

### Frontend Components - No Changes Needed

The frontend `AudioPlayer.js` and `StreamBuffer.js` already handle streaming correctly. They will automatically benefit from the backend fix:

- `AudioPlayer.loadFromStream()` already connects to SSE and processes chunks
- `StreamBuffer.appendChunk()` already decodes and buffers chunks
- `AudioPlayer.scheduleChunk()` already plays chunks as they arrive

## Data Models

### StreamChunk

```python
@dataclass
class StreamChunk:
    """Represents a single audio chunk in the stream"""
    index: int
    data: bytes  # Base64-encoded PCM data
    size: int  # Size in bytes
    timestamp: float  # When chunk was generated
```

### StreamMetrics

```python
@dataclass
class StreamMetrics:
    """Metrics for stream performance monitoring"""
    first_chunk_latency: float  # Time to first chunk (seconds)
    total_chunks: int
    total_bytes: int
    total_duration: float  # Total streaming time (seconds)
    average_chunk_size: int
    chunks_per_second: float
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Immediate chunk yielding
*For any* audio chunk received from the Gemini API, the time between receiving the chunk and yielding it to the caller should be less than 100 milliseconds.
**Validates: Requirements 1.2, 1.3, 2.2, 7.2**

### Property 2: First byte latency
*For any* text input, the time from starting the stream to yielding the first audio chunk should be less than 5 seconds.
**Validates: Requirements 1.1, 1.5**

### Property 3: No blocking collection
*For any* stream processing, the implementation should not create a list or collection to store all chunks before yielding.
**Validates: Requirements 2.1, 7.1**

### Property 4: Async generator pattern
*For any* call to `generate_tts_stream()`, the function should be an async generator using `async for` and `yield`, not a regular function with `run_in_executor`.
**Validates: Requirements 2.3, 2.4, 7.3, 9.3, 9.4**

### Property 5: Incremental yielding
*For any* stream with multiple chunks, chunks should be yielded incrementally with measurable time gaps between yields, not all at once.
**Validates: Requirements 7.4**

### Property 6: Constant memory usage
*For any* audio length, the memory used by the streaming function should remain constant and not grow with the number of chunks.
**Validates: Requirements 7.5**

### Property 7: Completion event after all chunks
*For any* completed stream, a completion event should be sent after all audio chunks have been sent.
**Validates: Requirements 1.4**

### Property 8: Progress event with chunk index
*For any* chunk sent, the event data should include the chunk index.
**Validates: Requirements 3.1, 3.2**

### Property 9: Completion event with duration
*For any* completed stream, the completion event should include the final audio duration.
**Validates: Requirements 3.5**

### Property 10: Candidate presence check
*For any* API response chunk, the system should check for the presence of `candidates` before accessing content.
**Validates: Requirements 4.1**

### Property 11: Part iteration for audio extraction
*For any* candidate with content parts, the system should iterate through all parts to find audio data.
**Validates: Requirements 4.2**

### Property 12: Inline data extraction
*For any* part containing `inline_data`, the system should extract audio data from `inline_data.data`.
**Validates: Requirements 4.3**

### Property 13: Empty chunk handling
*For any* chunk containing no audio data, the system should skip it without errors and continue processing.
**Validates: Requirements 4.4**

### Property 14: Base64 encoding
*For any* audio data extracted, it should be encoded as Base64 before being yielded.
**Validates: Requirements 4.5**

### Property 15: Chunk logging
*For any* chunk received, the system should log the chunk index and size.
**Validates: Requirements 5.2, 5.3**

### Property 16: Error logging with context
*For any* error during streaming, the system should log the error with full context including the chunk index where it occurred.
**Validates: Requirements 5.5**

### Property 17: Graceful error handling
*For any* error during streaming, the system should handle it gracefully without crashing and notify the user.
**Validates: Requirements 2.5**

### Property 18: Resource cleanup on cancellation
*For any* cancelled stream, the system should clean up resources and close the API connection.
**Validates: Requirements 8.4**

### Property 19: Buffered duration calculation
*For any* sequence of received chunks, the system should correctly calculate the cumulative buffered duration.
**Validates: Requirements 10.1**

### Property 20: Duration update events
*For any* change in buffered duration, the system should send an update event to the frontend.
**Validates: Requirements 10.2**

## Error Handling

### Error Categories

#### 1. API Stream Errors
- **Stream Initialization Error**: Cannot create Gemini client or start stream
  - Action: Log error, raise APIError with clear message
  - Message: "无法初始化 Gemini TTS 流式服务"

- **Chunk Read Error**: Error reading next chunk from stream
  - Action: Log error with chunk index, attempt to continue if possible
  - Message: "读取音频块 {index} 时出错"

- **Stream Interruption**: Stream ends unexpectedly
  - Action: Send what was received, log warning
  - Message: "音频流意外中断，已发送部分音频"

#### 2. Data Processing Errors
- **Base64 Decode Error**: Cannot decode audio data
  - Action: Skip corrupted chunk, log error, continue
  - Log: "音频块 {index} Base64 解码失败"

- **Invalid Chunk Format**: Chunk doesn't have expected structure
  - Action: Skip chunk, log warning, continue
  - Log: "音频块 {index} 格式无效"

#### 3. Network Errors
- **Connection Timeout**: API connection times out
  - Action: Retry with exponential backoff (up to 3 times)
  - Message: "连接超时，正在重试..."

- **Connection Lost**: Network drops during streaming
  - Action: Frontend continues playing buffered audio, backend attempts reconnect
  - Message: "网络连接中断，正在尝试重新连接..."

#### 4. Resource Errors
- **Memory Pressure**: System running low on memory
  - Action: Log warning, continue (constant memory usage should prevent this)
  - Log: "系统内存压力较大"

- **Thread Pool Exhaustion**: Too many concurrent streams
  - Action: Queue request, log warning
  - Message: "服务繁忙，请稍候..."

### Error Recovery Strategies

#### Exponential Backoff for Retries
```python
async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed")
                raise
```

#### Graceful Degradation
- If streaming fails completely, fall back to non-streaming generation
- If some chunks fail, continue with successfully received chunks
- If network is unstable, increase buffer size before starting playback

## Testing Strategy

### Dual Testing Approach

We will use both unit tests and property-based tests:

- **Unit tests** verify specific scenarios and edge cases
- **Property-based tests** verify universal properties across all inputs
- Together they provide comprehensive coverage

### Property-Based Testing

We will use **pytest with Hypothesis** for Python backend tests. Each property-based test should run a minimum of 100 iterations.

#### Property Test 1: Immediate chunk yielding
- **Feature: true-streaming-tts, Property 1: Immediate chunk yielding**
- **Validates: Requirements 1.2, 1.3, 2.2, 7.2**
- Generate: Random text inputs
- Property: Time between receiving chunk and yielding < 100ms
- Verify: Measure time delta for each chunk

#### Property Test 2: First byte latency
- **Feature: true-streaming-tts, Property 2: First byte latency**
- **Validates: Requirements 1.1, 1.5**
- Generate: Random text inputs
- Property: Time to first chunk < 5 seconds
- Verify: Measure time from start to first yield

#### Property Test 3: Incremental yielding
- **Feature: true-streaming-tts, Property 5: Incremental yielding**
- **Validates: Requirements 7.4**
- Generate: Random text inputs producing multiple chunks
- Property: Chunks yielded with time gaps, not all at once
- Verify: Measure time between consecutive yields

#### Property Test 4: Constant memory usage
- **Feature: true-streaming-tts, Property 6: Constant memory usage**
- **Validates: Requirements 7.5**
- Generate: Text inputs of varying lengths (short, medium, long)
- Property: Memory usage remains constant regardless of length
- Verify: Measure memory before, during, and after streaming

#### Property Test 5: Chunk index in events
- **Feature: true-streaming-tts, Property 8: Progress event with chunk index**
- **Validates: Requirements 3.1, 3.2**
- Generate: Random text inputs
- Property: All chunk events contain index field
- Verify: Parse event data and check for index

#### Property Test 6: Base64 encoding
- **Feature: true-streaming-tts, Property 14: Base64 encoding**
- **Validates: Requirements 4.5**
- Generate: Random audio data
- Property: All yielded data is valid Base64
- Verify: Attempt to decode all yielded chunks

#### Property Test 7: Empty chunk handling
- **Feature: true-streaming-tts, Property 13: Empty chunk handling**
- **Validates: Requirements 4.4**
- Generate: Streams with some empty chunks
- Property: Empty chunks skipped without errors
- Verify: No exceptions raised, processing continues

#### Property Test 8: Error logging with context
- **Feature: true-streaming-tts, Property 16: Error logging with context**
- **Validates: Requirements 5.5**
- Generate: Errors at random chunk indices
- Property: Error logs include chunk index
- Verify: Parse logs and check for chunk index in error messages

### Unit Testing

#### Backend Unit Tests

**Test 1: Async generator pattern**
- Verify `generate_tts_stream()` is an async generator function
- Verify it uses `async for` and `yield`
- Verify it does NOT use `run_in_executor` with collection function

**Test 2: No blocking collection**
- Inspect code to ensure no `audio_chunks = []` pattern
- Verify chunks are yielded immediately, not collected first

**Test 3: Completion event**
- Test that completion event is sent after all chunks
- Verify completion event includes duration

**Test 4: Candidate presence check**
- Test with chunks that have no candidates
- Verify no errors and processing continues

**Test 5: Part iteration**
- Test with chunks containing multiple parts
- Verify all parts are checked for audio data

**Test 6: Resource cleanup**
- Test stream cancellation
- Verify resources are properly released

### Integration Testing

#### End-to-End Streaming Test

1. **Start stream**: Send request to `/api/tts/stream`
2. **Measure first chunk**: Record time to first SSE event
3. **Verify streaming**: Confirm chunks arrive incrementally
4. **Check completion**: Verify completion event received
5. **Validate audio**: Decode and verify audio data is valid

**Expected Results**:
- First chunk arrives in < 5 seconds
- Chunks arrive incrementally (not all at once)
- Total time < (audio duration + 10 seconds)
- All chunks are valid Base64-encoded PCM data

#### Performance Test

1. **Short text** (< 100 chars): First chunk < 2 seconds
2. **Medium text** (100-500 chars): First chunk < 3 seconds
3. **Long text** (> 500 chars): First chunk < 5 seconds
4. **Memory usage**: Constant regardless of text length

### Test Configuration

```python
# pytest configuration
@pytest.fixture
async def gemini_client():
    """Fixture for Gemini client with test configuration"""
    config = ModelConfig(
        model_name="gemini-2.5-flash-preview-tts",
        api_key=os.getenv("GEMINI_API_KEY"),
        provider="gemini"
    )
    return GeminiClient(config)

@pytest.mark.asyncio
async def test_true_streaming(gemini_client):
    """Test that streaming yields chunks immediately"""
    text = "这是一个测试文本，用于验证流式播放功能。"
    
    start_time = time.time()
    first_chunk_time = None
    chunk_times = []
    
    async for chunk in gemini_client.generate_tts_stream(text, "Kore", "zh-CN"):
        current_time = time.time()
        
        if first_chunk_time is None:
            first_chunk_time = current_time
            first_chunk_latency = first_chunk_time - start_time
            assert first_chunk_latency < 5.0, f"First chunk took {first_chunk_latency}s"
        
        chunk_times.append(current_time)
    
    # Verify chunks arrived incrementally
    if len(chunk_times) > 1:
        time_diffs = [chunk_times[i+1] - chunk_times[i] for i in range(len(chunk_times)-1)]
        # At least some gaps should be > 0.1s (not all at once)
        assert any(diff > 0.1 for diff in time_diffs), "Chunks arrived all at once"
```

## Implementation Plan

### Phase 1: Core Streaming Fix
1. Modify `GeminiClient.generate_tts_stream()` to use async generator pattern
2. Remove blocking collection logic
3. Add `async_stream_wrapper()` helper
4. Add first chunk latency tracking

### Phase 2: Logging and Monitoring
1. Add detailed logging for each chunk
2. Add stream metrics collection
3. Add performance monitoring

### Phase 3: Error Handling
1. Add graceful error handling for stream interruptions
2. Add retry logic with exponential backoff
3. Add resource cleanup on cancellation

### Phase 4: Testing
1. Write property-based tests
2. Write unit tests
3. Write integration tests
4. Performance testing

### Phase 5: Documentation
1. Update API documentation
2. Add performance benchmarks
3. Create troubleshooting guide

## Performance Considerations

### Memory Usage
- **Before**: O(n) where n is total audio size (all chunks collected)
- **After**: O(1) constant memory (chunks yielded immediately)

### Latency
- **Before**: 454 seconds to first byte (wait for all chunks)
- **After**: 2-5 seconds to first byte (immediate streaming)

### Throughput
- **Before**: Limited by collection phase
- **After**: Limited only by API and network speed

## Migration Notes

### Breaking Changes
None. This is a pure performance fix with no API changes.

### Backward Compatibility
Fully backward compatible. Frontend code requires no changes.

### Deployment
Can be deployed as a hot-fix without downtime.

## Monitoring and Metrics

### Key Metrics to Track

1. **First Chunk Latency**: Time from request to first chunk
   - Target: < 5 seconds
   - Alert if: > 10 seconds

2. **Chunk Throughput**: Chunks per second
   - Target: > 1 chunk/second
   - Alert if: < 0.5 chunks/second

3. **Stream Completion Rate**: % of streams that complete successfully
   - Target: > 95%
   - Alert if: < 90%

4. **Memory Usage**: Memory per active stream
   - Target: < 10MB per stream
   - Alert if: > 50MB per stream

### Logging Format

```python
# Start
logger.info(f"🎤 开始流式 TTS: voice={voice}, text_length={len(text)}")

# First chunk
logger.info(f"⚡ 首块延迟: {latency:.2f}s")

# Each chunk
logger.info(f"📦 发送音频块 {index}: {size} bytes, 累计 {total}KB")

# Completion
logger.info(f"🎉 流式完成: {chunks} 块, {size}KB, {duration}s")

# Errors
logger.error(f"❌ 流式失败 at chunk {index}: {error}")
```

## Future Enhancements

1. **Adaptive Buffering**: Adjust buffer size based on network conditions
2. **Chunk Compression**: Compress chunks before sending to reduce bandwidth
3. **Parallel Streaming**: Support multiple concurrent streams efficiently
4. **Stream Resumption**: Resume interrupted streams from last chunk
5. **Quality Selection**: Allow users to choose audio quality vs. speed tradeoff
