"""
测试重试策略功能
"""
import pytest
from src.reinvent_insight.downloader import (
    RetryStrategy,
    RetryConfig,
    DownloadError,
    DownloadErrorType
)


class TestRetryStrategy:
    """测试重试策略"""
    
    def test_default_config(self):
        """测试默认配置"""
        strategy = RetryStrategy()
        
        assert strategy.config.max_attempts == 3
        assert strategy.config.base_delay == 5.0
        assert strategy.config.max_delay == 30.0
        assert strategy.config.exponential_base == 2.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=10.0,
            max_delay=60.0,
            exponential_base=3.0
        )
        strategy = RetryStrategy(config)
        
        assert strategy.config.max_attempts == 5
        assert strategy.config.base_delay == 10.0
    
    def test_should_retry_network_timeout(self):
        """测试网络超时应该重试"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.NETWORK_TIMEOUT,
            message="Timeout"
        )
        
        assert strategy.should_retry(error, 0) is True
        assert strategy.should_retry(error, 1) is True
        assert strategy.should_retry(error, 2) is True
        assert strategy.should_retry(error, 3) is False  # 超过最大次数
    
    def test_should_not_retry_no_subtitles(self):
        """测试无字幕不应该重试"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.NO_SUBTITLES,
            message="No subtitles"
        )
        
        assert strategy.should_retry(error, 0) is False
    
    def test_should_not_retry_video_not_found(self):
        """测试视频不存在不应该重试"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.VIDEO_NOT_FOUND,
            message="Not found"
        )
        
        assert strategy.should_retry(error, 0) is False
    
    def test_should_not_retry_tool_missing(self):
        """测试工具缺失不应该重试"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.TOOL_MISSING,
            message="Tool missing"
        )
        
        assert strategy.should_retry(error, 0) is False
    
    def test_should_not_retry_invalid_url(self):
        """测试无效 URL 不应该重试"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.INVALID_URL,
            message="Invalid URL"
        )
        
        assert strategy.should_retry(error, 0) is False
    
    def test_exponential_backoff_delay(self):
        """测试指数退避延迟"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.NETWORK_TIMEOUT,
            message="Timeout"
        )
        
        # 第 1 次重试: 5 * 2^0 = 5
        assert strategy.get_delay(error, 0) == 5.0
        
        # 第 2 次重试: 5 * 2^1 = 10
        assert strategy.get_delay(error, 1) == 10.0
        
        # 第 3 次重试: 5 * 2^2 = 20
        assert strategy.get_delay(error, 2) == 20.0
        
        # 第 4 次重试: 5 * 2^3 = 40，但不超过 max_delay 30
        assert strategy.get_delay(error, 3) == 30.0
    
    def test_incremental_delay_for_forbidden(self):
        """测试 403 错误的递增延迟"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.ACCESS_FORBIDDEN,
            message="Forbidden"
        )
        
        # 第 1 次重试: 5 * 1 = 5
        assert strategy.get_delay(error, 0) == 5.0
        
        # 第 2 次重试: 5 * 2 = 10
        assert strategy.get_delay(error, 1) == 10.0
        
        # 第 3 次重试: 5 * 3 = 15
        assert strategy.get_delay(error, 2) == 15.0
    
    def test_fixed_delay_for_rate_limit(self):
        """测试限流错误的固定延迟"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.RATE_LIMITED,
            message="Rate limited"
        )
        
        # 所有重试都使用固定的 30 秒延迟
        assert strategy.get_delay(error, 0) == 30.0
        assert strategy.get_delay(error, 1) == 30.0
        assert strategy.get_delay(error, 2) == 30.0
    
    def test_custom_retry_after(self):
        """测试自定义重试延迟"""
        strategy = RetryStrategy()
        error = DownloadError(
            error_type=DownloadErrorType.UNKNOWN,
            message="Unknown",
            retry_after=15
        )
        
        # 使用错误对象指定的延迟
        assert strategy.get_delay(error, 0) == 15.0
        assert strategy.get_delay(error, 1) == 15.0
    
    def test_max_delay_cap(self):
        """测试最大延迟限制"""
        config = RetryConfig(
            base_delay=20.0,
            max_delay=50.0,
            exponential_base=3.0
        )
        strategy = RetryStrategy(config)
        error = DownloadError(
            error_type=DownloadErrorType.NETWORK_TIMEOUT,
            message="Timeout"
        )
        
        # 20 * 3^0 = 20
        assert strategy.get_delay(error, 0) == 20.0
        
        # 20 * 3^1 = 60，但不超过 max_delay 50
        assert strategy.get_delay(error, 1) == 50.0
        
        # 20 * 3^2 = 180，但不超过 max_delay 50
        assert strategy.get_delay(error, 2) == 50.0
    
    def test_non_retryable_errors_set(self):
        """测试不可重试的错误集合"""
        strategy = RetryStrategy()
        
        assert DownloadErrorType.NO_SUBTITLES in strategy.non_retryable_errors
        assert DownloadErrorType.VIDEO_NOT_FOUND in strategy.non_retryable_errors
        assert DownloadErrorType.TOOL_MISSING in strategy.non_retryable_errors
        assert DownloadErrorType.INVALID_URL in strategy.non_retryable_errors
        
        # 可重试的错误不在集合中
        assert DownloadErrorType.NETWORK_TIMEOUT not in strategy.non_retryable_errors
        assert DownloadErrorType.ACCESS_FORBIDDEN not in strategy.non_retryable_errors
