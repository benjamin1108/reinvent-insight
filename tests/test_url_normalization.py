"""
测试 YouTube URL 标准化功能
"""
import pytest
from src.reinvent_insight.downloader import normalize_youtube_url


class TestURLNormalization:
    """测试 URL 标准化功能"""
    
    def test_standard_format(self):
        """测试标准格式 URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
    
    def test_url_with_timestamp(self):
        """测试带时间戳的 URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=2209s"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
        assert metadata['timestamp'] == "2209s"
    
    def test_url_with_playlist(self):
        """测试带播放列表的 URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
        assert metadata['playlist_id'] == "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
    
    def test_short_url_format(self):
        """测试短链接格式"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
    
    def test_short_url_with_share_id(self):
        """测试带分享参数的短链接"""
        url = "https://youtu.be/dQw4w9WgXcQ?si=abc123xyz"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
        assert metadata['share_id'] == "abc123xyz"
    
    def test_embed_format(self):
        """测试嵌入式格式"""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
    
    def test_mobile_format(self):
        """测试移动端格式"""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
    
    def test_url_without_protocol(self):
        """测试不带协议的 URL"""
        url = "www.youtube.com/watch?v=dQw4w9WgXcQ"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
    
    def test_url_with_multiple_parameters(self):
        """测试带多个参数的 URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=100s&list=PLtest&index=5"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
        assert metadata['timestamp'] == "100s"
        assert metadata['playlist_id'] == "PLtest"
        assert metadata['playlist_index'] == "5"
    
    def test_invalid_url_empty(self):
        """测试空 URL"""
        with pytest.raises(ValueError, match="URL 必须是非空字符串"):
            normalize_youtube_url("")
    
    def test_invalid_url_none(self):
        """测试 None URL"""
        with pytest.raises(ValueError, match="URL 必须是非空字符串"):
            normalize_youtube_url(None)
    
    def test_invalid_url_no_video_id(self):
        """测试无法提取视频 ID 的 URL"""
        with pytest.raises(ValueError, match="无法从 URL 中提取有效的视频 ID"):
            normalize_youtube_url("https://www.youtube.com/")
    
    def test_invalid_url_wrong_domain(self):
        """测试错误的域名"""
        with pytest.raises(ValueError, match="无法从 URL 中提取有效的视频 ID"):
            normalize_youtube_url("https://www.notyoutube.com/watch?v=dQw4w9WgXcQ")
    
    def test_video_id_format_validation(self):
        """测试视频 ID 格式验证"""
        # 有效的 11 位视频 ID
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        normalized, metadata = normalize_youtube_url(url)
        assert len(metadata['video_id']) == 11
    
    def test_case_insensitive_domain(self):
        """测试域名大小写不敏感"""
        url = "https://WWW.YOUTUBE.COM/watch?v=dQw4w9WgXcQ"
        normalized, metadata = normalize_youtube_url(url)
        
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata['video_id'] == "dQw4w9WgXcQ"
