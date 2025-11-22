# Implementation Plan

- [x] 1. Refactor GeminiClient.generate_tts_stream() for true streaming
  - Modify `src/reinvent_insight/model_config.py` to implement async generator pattern
  - Remove blocking collection logic (`audio_chunks = []` and collection loop)
  - Add `async_stream_wrapper()` helper function to wrap sync iterator
  - Use `asyncio.to_thread()` for non-blocking iteration
  - Yield chunks immediately with `yield` instead of collecting first
  - Add first chunk latency tracking
  - Add detailed logging for each chunk (index, size, cumulative total)
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 7.1, 7.2, 7.3, 7.4, 9.1, 9.2, 9.3, 9.4_

- [ ]* 1.1 Write property test for immediate chunk yielding
  - **Property 1: Immediate chunk yielding**
  - **Validates: Requirements 1.2, 1.3, 2.2, 7.2**

- [ ]* 1.2 Write property test for first byte latency
  - **Property 2: First byte latency**
  - **Validates: Requirements 1.1, 1.5**

- [ ]* 1.3 Write property test for incremental yielding
  - **Property 5: Incremental yielding**
  - **Validates: Requirements 7.4**

- [ ]* 1.4 Write property test for constant memory usage
  - **Property 6: Constant memory usage**
  - **Validates: Requirements 7.5**

- [ ]* 1.5 Write unit test for async generator pattern
  - Verify `generate_tts_stream()` is an async generator function
  - Verify it uses `async for` and `yield`
  - Verify it does NOT use `run_in_executor` with collection function
  - _Requirements: 2.3, 2.4, 7.3, 9.3, 9.4_

- [ ]* 1.6 Write unit test for no blocking collection
  - Inspect code to ensure no `audio_chunks = []` pattern
  - Verify chunks are yielded immediately, not collected first
  - _Requirements: 2.1, 7.1_

- [x] 2. Add progress reporting and metrics
  - Add chunk index to each SSE event in `src/reinvent_insight/api.py`
  - Add cumulative data size tracking
  - Send progress events with chunk count and buffered duration
  - Add completion event with final duration
  - _Requirements: 3.1, 3.2, 3.4, 3.5_

- [ ]* 2.1 Write property test for chunk index in events
  - **Property 8: Progress event with chunk index**
  - **Validates: Requirements 3.1, 3.2**

- [ ]* 2.2 Write property test for completion event with duration
  - **Property 9: Completion event with duration**
  - **Validates: Requirements 3.5**

- [ ]* 2.3 Write unit test for completion event
  - Test that completion event is sent after all chunks
  - Verify completion event includes duration
  - _Requirements: 1.4, 3.5_

- [x] 3. Improve API response parsing
  - Add robust checking for `candidates` presence in chunks
  - Iterate through all content parts to find audio data
  - Extract audio data from `inline_data.data`
  - Skip chunks with no audio data gracefully
  - Ensure all audio data is Base64 encoded before yielding
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 3.1 Write property test for Base64 encoding
  - **Property 14: Base64 encoding**
  - **Validates: Requirements 4.5**

- [ ]* 3.2 Write property test for empty chunk handling
  - **Property 13: Empty chunk handling**
  - **Validates: Requirements 4.4**

- [ ]* 3.3 Write unit test for candidate presence check
  - Test with chunks that have no candidates
  - Verify no errors and processing continues
  - _Requirements: 4.1_

- [ ]* 3.4 Write unit test for part iteration
  - Test with chunks containing multiple parts
  - Verify all parts are checked for audio data
  - _Requirements: 4.2_

- [x] 4. Enhance logging and error handling
  - Log stream start with timestamp and parameters
  - Log each chunk with index, size, and cumulative total
  - Log first chunk latency
  - Log stream completion with metrics (total chunks, size, duration)
  - Add error logging with full context including chunk index
  - Add graceful error handling for stream interruptions
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 2.5_

- [ ]* 4.1 Write property test for chunk logging
  - **Property 15: Chunk logging**
  - **Validates: Requirements 5.2, 5.3**

- [ ]* 4.2 Write property test for error logging with context
  - **Property 16: Error logging with context**
  - **Validates: Requirements 5.5**

- [ ]* 4.3 Write property test for graceful error handling
  - **Property 17: Graceful error handling**
  - **Validates: Requirements 2.5**

- [ ] 5. Add resource cleanup and cancellation handling
  - Implement proper cleanup when stream is cancelled
  - Close API connection on cancellation
  - Release resources (memory, threads) properly
  - Add cancellation tests
  - _Requirements: 8.3, 8.4_

- [ ]* 5.1 Write property test for resource cleanup
  - **Property 18: Resource cleanup on cancellation**
  - **Validates: Requirements 8.4**

- [ ]* 5.2 Write unit test for resource cleanup
  - Test stream cancellation
  - Verify resources are properly released
  - _Requirements: 8.4_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Add buffered duration calculation
  - Calculate cumulative buffered duration from received chunks
  - Send duration update events to frontend
  - Update progress indicators with buffered vs played portions
  - _Requirements: 10.1, 10.2_

- [ ]* 7.1 Write property test for buffered duration calculation
  - **Property 19: Buffered duration calculation**
  - **Validates: Requirements 10.1**

- [ ]* 7.2 Write property test for duration update events
  - **Property 20: Duration update events**
  - **Validates: Requirements 10.2**

- [ ] 8. Integration testing and validation
  - Create end-to-end streaming test
  - Test with short, medium, and long text inputs
  - Measure first chunk latency for each
  - Verify chunks arrive incrementally
  - Validate audio data integrity
  - Test memory usage remains constant
  - _Requirements: All_

- [ ]* 8.1 Write integration test for end-to-end streaming
  - Start stream and measure first chunk time
  - Verify chunks arrive incrementally
  - Check completion event
  - Validate audio data

- [ ]* 8.2 Write performance test
  - Test short text (< 100 chars): first chunk < 2s
  - Test medium text (100-500 chars): first chunk < 3s
  - Test long text (> 500 chars): first chunk < 5s
  - Verify memory usage is constant

- [ ] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
