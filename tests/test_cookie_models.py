"""测试 Cookie Models"""
import pytest
from datetime import datetime
from pathlib import Path

from src.reinvent_insight.cookie_models import Cookie, CookieMetadata, CookieManagerConfig


def test_cookie_creation():
    """测试创建 Cookie"""
    cookie = Cookie(
        name="TEST",
        value="test_value",
        domain=".youtube.com",
        path="/",
        expires=1735689600.0,
        secure=True,
        httpOnly=False,
        sameSite="None"
    )
    
    assert cookie.name == "TEST"
    assert cookie.value == "test_value"
    assert cookie.domain == ".youtube.com"
    assert cookie.secure is True


def test_cookie_is_expired():
    """测试 Cookie 过期检查"""
    # 未过期的 cookie
    future_cookie = Cookie(
        name="TEST",
        value="test",
        domain=".youtube.com",
        expires=datetime.now().timestamp() + 86400  # 明天
    )
    assert future_cookie.is_expired() is False
    
    # 已过期的 cookie
    past_cookie = Cookie(
        name="TEST",
        value="test",
        domain=".youtube.com",
        expires=datetime.now().timestamp() - 86400  # 昨天
    )
    assert past_cookie.is_expired() is True
    
    # 没有过期时间的 cookie
    no_expiry_cookie = Cookie(
        name="TEST",
        value="test",
        domain=".youtube.com",
        expires=None
    )
    assert no_expiry_cookie.is_expired() is False


def test_cookie_to_netscape_line():
    """测试转换为 Netscape 格式"""
    cookie = Cookie(
        name="TEST",
        value="test_value",
        domain=".youtube.com",
        path="/",
        expires=1735689600.0,
        secure=True
    )
    
    line = cookie.to_netscape_line()
    parts = line.split("\t")
    
    assert len(parts) == 7
    assert parts[0] == ".youtube.com"
    assert parts[5] == "TEST"
    assert parts[6] == "test_value"


def test_cookie_metadata_creation():
    """测试创建 CookieMetadata"""
    metadata = CookieMetadata(
        source="test",
        refresh_count=5,
        validation_status="valid"
    )
    
    assert metadata.source == "test"
    assert metadata.refresh_count == 5
    assert metadata.validation_status == "valid"
    assert metadata.last_updated is not None


def test_cookie_metadata_mark_refreshed():
    """测试标记为已刷新"""
    metadata = CookieMetadata(refresh_count=0)
    
    metadata.mark_refreshed()
    
    assert metadata.refresh_count == 1
    assert metadata.validation_status == "valid"
    assert metadata.last_validated is not None


def test_cookie_metadata_mark_validated():
    """测试标记验证结果"""
    metadata = CookieMetadata()
    
    # 标记为有效
    metadata.mark_validated(True)
    assert metadata.validation_status == "valid"
    assert metadata.last_validated is not None
    
    # 标记为无效
    metadata.mark_validated(False)
    assert metadata.validation_status == "invalid"


def test_cookie_manager_config_defaults():
    """测试 CookieManagerConfig 默认值"""
    config = CookieManagerConfig()
    
    assert config.refresh_interval_hours == 6
    assert config.browser_type == "chromium"
    assert config.browser_timeout == 30
    assert config.max_retry_count == 3
    assert config.retry_delay_minutes == 5


def test_cookie_manager_config_custom_values():
    """测试自定义配置值"""
    config = CookieManagerConfig(
        refresh_interval_hours=12,
        browser_type="firefox",
        browser_timeout=60,
        max_retry_count=5
    )
    
    assert config.refresh_interval_hours == 12
    assert config.browser_type == "firefox"
    assert config.browser_timeout == 60
    assert config.max_retry_count == 5


def test_cookie_manager_config_validation():
    """测试配置验证"""
    # 刷新间隔必须在 1-24 小时之间
    with pytest.raises(Exception):
        CookieManagerConfig(refresh_interval_hours=0)
    
    with pytest.raises(Exception):
        CookieManagerConfig(refresh_interval_hours=25)
