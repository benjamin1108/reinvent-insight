"""
测试下载错误分类功能
"""
import pytest
from src.reinvent_insight.downloader import (
    classify_download_error,
    DownloadErrorType,
    DownloadError
)


class TestErrorClassification:
    """测试错误分类功能"""
    
    def test_classify_403_error(self):
        """测试 403 错误分类"""
        stderr = "ERROR: HTTP Error 403: Forbidden"
        error = classify_download_error(stderr=stderr, returncode=1)
        
        assert error.error_type == DownloadErrorType.ACCESS_FORBIDDEN
        assert "拒绝了访问请求" in error.message
        assert "Cookie" in error.suggestions[0]
    
    def test_classify_timeout_error(self):
        """测试超时错误分类"""
        stderr = "ERROR: Connection timed out after 30 seconds"
        error = classify_download_error(stderr=stderr, returncode=1)
        
        assert error.error_type == DownloadErrorType.NETWORK_TIMEOUT
        assert "超时" in error.message
        assert "网络连接" in error.suggestions[0]
    
    def test_classify_rate_limit_error(self):
        """测试限流错误分类"""
        stderr = "ERROR: HTTP Error 429: Too Many Requests"
        error = classify_download_error(stderr=stderr, returncode=1)
        
        assert error.error_type == DownloadErrorType.RATE_LIMITED
        assert "限流" in error.message
        assert error.retry_after == 30
    
    def test_classify_video_not_found(self):
        """测试视频不存在错误"""
        stderr = "ERROR: Video unavailable. This video is not available"
        error = classify_download_error(stderr=stderr, returncode=1)
        
        assert error.error_type == DownloadErrorType.VIDEO_NOT_FOUND
        assert "不存在" in error.message
    
    def test_classify_no_subtitles(self):
        """测试无字幕错误"""
        stderr = "WARNING: video doesn't have subtitles"
        error = classify_download_error(stderr=stderr, returncode=0)
        
        assert error.error_type == DownloadErrorType.NO_SUBTITLES
        assert "字幕" in error.message
    
    def test_classify_tool_missing(self):
        """测试工具缺失错误"""
        exception = FileNotFoundError("yt-dlp not found")
        error = classify_download_error(exception=exception)
        
        assert error.error_type == DownloadErrorType.TOOL_MISSING
        assert "yt-dlp" in error.message
        assert "安装" in error.suggestions[0]
    
    def test_classify_unknown_error(self):
        """测试未知错误"""
        stderr = "Some random error message"
        error = classify_download_error(stderr=stderr, returncode=1)
        
        assert error.error_type == DownloadErrorType.UNKNOWN
        assert "未知错误" in error.message
    
    def test_error_to_dict(self):
        """测试错误对象转换为字典"""
        error = DownloadError(
            error_type=DownloadErrorType.ACCESS_FORBIDDEN,
            message="Test error",
            technical_details="Details here",
            suggestions=["Suggestion 1", "Suggestion 2"],
            retry_after=10
        )
        
        error_dict = error.to_dict()
        
        assert error_dict['error_type'] == "access_forbidden"
        assert error_dict['message'] == "Test error"
        assert error_dict['technical_details'] == "Details here"
        assert len(error_dict['suggestions']) == 2
        assert error_dict['retry_after'] == 10
    
    def test_classify_connection_reset(self):
        """测试连接重置错误"""
        stderr = "ERROR: Connection reset by peer"
        error = classify_download_error(stderr=stderr, returncode=1)
        
        assert error.error_type == DownloadErrorType.NETWORK_TIMEOUT
        assert "超时" in error.message
    
    def test_classify_private_video(self):
        """测试私密视频错误"""
        stderr = "ERROR: This video is private"
        error = classify_download_error(stderr=stderr, returncode=1)
        
        assert error.error_type == DownloadErrorType.VIDEO_NOT_FOUND
        assert "不存在或无法访问" in error.message
    
    def test_technical_details_truncation(self):
        """测试技术细节截断"""
        long_stderr = "ERROR: " + "x" * 1000
        error = classify_download_error(stderr=long_stderr, returncode=1)
        
        assert error.technical_details is not None
        assert len(error.technical_details) <= 500
    
    def test_case_insensitive_matching(self):
        """测试大小写不敏感的匹配"""
        stderr = "ERROR: FORBIDDEN ACCESS"
        error = classify_download_error(stderr=stderr, returncode=1)
        
        assert error.error_type == DownloadErrorType.ACCESS_FORBIDDEN
