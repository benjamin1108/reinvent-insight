"""测试 Cookie Store"""
import json
import pytest
from pathlib import Path
from datetime import datetime

from src.reinvent_insight.cookie_store import CookieStore
from src.reinvent_insight.cookie_models import Cookie, CookieMetadata


@pytest.fixture
def temp_store_path(tmp_path):
    """临时存储路径"""
    return tmp_path / "test_cookies.json"


@pytest.fixture
def temp_netscape_path(tmp_path):
    """临时 Netscape 路径"""
    return tmp_path / "test_cookies.txt"


@pytest.fixture
def sample_cookies():
    """示例 cookies"""
    return [
        {
            "name": "CONSENT",
            "value": "YES+test",
            "domain": ".youtube.com",
            "path": "/",
            "expires": datetime.now().timestamp() + 86400,
            "secure": True,
            "httpOnly": False,
            "sameSite": "None"
        },
        {
            "name": "VISITOR_INFO1_LIVE",
            "value": "test_value",
            "domain": ".youtube.com",
            "path": "/",
            "expires": datetime.now().timestamp() + 86400,
            "secure": True,
            "httpOnly": True,
            "sameSite": "None"
        }
    ]


def test_cookie_store_init(temp_store_path, temp_netscape_path):
    """测试 CookieStore 初始化"""
    store = CookieStore(temp_store_path, temp_netscape_path)
    
    assert store.store_path == temp_store_path
    assert store.netscape_path == temp_netscape_path


def test_save_and_load_cookies(temp_store_path, temp_netscape_path, sample_cookies):
    """测试保存和加载 cookies"""
    store = CookieStore(temp_store_path, temp_netscape_path)
    
    metadata = CookieMetadata(source="test").model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    # 验证 JSON 文件存在
    assert temp_store_path.exists()
    
    # 加载 cookies
    loaded_cookies = store.load_cookies()
    
    assert len(loaded_cookies) == len(sample_cookies)
    assert loaded_cookies[0]["name"] == "CONSENT"
    assert loaded_cookies[1]["name"] == "VISITOR_INFO1_LIVE"


def test_get_metadata(temp_store_path, temp_netscape_path, sample_cookies):
    """测试获取元数据"""
    store = CookieStore(temp_store_path, temp_netscape_path)
    
    metadata = CookieMetadata(source="test", refresh_count=5).model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    loaded_metadata = store.get_metadata()
    
    assert loaded_metadata["source"] == "test"
    assert loaded_metadata["refresh_count"] == 5


def test_export_to_netscape(temp_store_path, temp_netscape_path, sample_cookies):
    """测试导出为 Netscape 格式"""
    store = CookieStore(temp_store_path, temp_netscape_path)
    
    metadata = CookieMetadata().model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    # 验证 Netscape 文件存在
    assert temp_netscape_path.exists()
    
    # 读取并验证内容
    content = temp_netscape_path.read_text()
    
    assert "# Netscape HTTP Cookie File" in content
    assert "CONSENT" in content
    assert "VISITOR_INFO1_LIVE" in content
    assert ".youtube.com" in content


def test_is_valid_with_valid_cookies(temp_store_path, temp_netscape_path, sample_cookies):
    """测试有效 cookies 的验证"""
    store = CookieStore(temp_store_path, temp_netscape_path)
    
    metadata = CookieMetadata(validation_status="valid").model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    assert store.is_valid() is True


def test_is_valid_with_no_cookies(temp_store_path, temp_netscape_path):
    """测试没有 cookies 的验证"""
    store = CookieStore(temp_store_path, temp_netscape_path)
    
    assert store.is_valid() is False


def test_is_valid_with_invalid_status(temp_store_path, temp_netscape_path, sample_cookies):
    """测试无效状态的验证"""
    store = CookieStore(temp_store_path, temp_netscape_path)
    
    metadata = CookieMetadata(validation_status="invalid").model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    assert store.is_valid() is False


def test_update_metadata(temp_store_path, temp_netscape_path, sample_cookies):
    """测试更新元数据"""
    store = CookieStore(temp_store_path, temp_netscape_path)
    
    metadata = CookieMetadata(refresh_count=0).model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    # 更新元数据
    store.update_metadata(refresh_count=5, validation_status="valid")
    
    updated_metadata = store.get_metadata()
    assert updated_metadata["refresh_count"] == 5
    assert updated_metadata["validation_status"] == "valid"


def test_cookie_to_netscape_line():
    """测试 Cookie 转换为 Netscape 格式"""
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
    
    line = cookie.to_netscape_line()
    parts = line.split("\t")
    
    assert parts[0] == ".youtube.com"
    assert parts[1] == "TRUE"  # domain starts with .
    assert parts[2] == "/"
    assert parts[3] == "TRUE"  # secure
    assert parts[4] == "1735689600"
    assert parts[5] == "TEST"
    assert parts[6] == "test_value"
