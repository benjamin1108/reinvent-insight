"""测试 Cookie Importer"""
import json
import pytest
from pathlib import Path
from datetime import datetime

from src.reinvent_insight.cookie_importer import CookieImporter


@pytest.fixture
def importer():
    """创建 CookieImporter 实例"""
    return CookieImporter()


@pytest.fixture
def netscape_file(tmp_path):
    """创建 Netscape 格式的测试文件"""
    file_path = tmp_path / "cookies.txt"
    content = """# Netscape HTTP Cookie File
# This is a test file
.youtube.com	TRUE	/	TRUE	1735689600	CONSENT	YES+test
.youtube.com	TRUE	/	TRUE	1735689600	VISITOR_INFO1_LIVE	test_value
.youtube.com	TRUE	/	FALSE	0	PREF	test_pref
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def json_file(tmp_path):
    """创建 JSON 格式的测试文件"""
    file_path = tmp_path / "cookies.json"
    cookies = [
        {
            "name": "CONSENT",
            "value": "YES+test",
            "domain": ".youtube.com",
            "path": "/",
            "expires": 1735689600.0,
            "secure": True,
            "httpOnly": False,
            "sameSite": "None"
        },
        {
            "name": "VISITOR_INFO1_LIVE",
            "value": "test_value",
            "domain": ".youtube.com",
            "path": "/",
            "expires": 1735689600.0,
            "secure": True,
            "httpOnly": True,
            "sameSite": "None"
        }
    ]
    file_path.write_text(json.dumps(cookies, indent=2))
    return file_path


def test_import_from_netscape(importer, netscape_file):
    """测试从 Netscape 格式导入"""
    cookies = importer.import_from_netscape(netscape_file)
    
    assert len(cookies) == 3
    assert cookies[0]["name"] == "CONSENT"
    assert cookies[0]["domain"] == ".youtube.com"
    assert cookies[0]["secure"] is True
    
    assert cookies[1]["name"] == "VISITOR_INFO1_LIVE"
    assert cookies[2]["name"] == "PREF"


def test_import_from_json(importer, json_file):
    """测试从 JSON 格式导入"""
    cookies = importer.import_from_json(json_file)
    
    assert len(cookies) == 2
    assert cookies[0]["name"] == "CONSENT"
    assert cookies[1]["name"] == "VISITOR_INFO1_LIVE"


def test_detect_format_netscape(importer, netscape_file):
    """测试检测 Netscape 格式"""
    format = importer.detect_format(netscape_file)
    assert format == "netscape"


def test_detect_format_json(importer, json_file):
    """测试检测 JSON 格式"""
    format = importer.detect_format(json_file)
    assert format == "json"


def test_validate_cookies_success(importer):
    """测试验证有效的 cookies"""
    cookies = [
        {
            "name": "CONSENT",
            "value": "YES+test",
            "domain": ".youtube.com",
            "path": "/",
            "expires": datetime.now().timestamp() + 86400,
            "secure": True,
            "httpOnly": False
        },
        {
            "name": "VISITOR_INFO1_LIVE",
            "value": "test_value",
            "domain": ".youtube.com",
            "path": "/",
            "expires": datetime.now().timestamp() + 86400,
            "secure": True,
            "httpOnly": True
        }
    ]
    
    is_valid, message = importer.validate_cookies(cookies)
    
    assert is_valid is True
    assert "成功验证" in message


def test_validate_cookies_no_youtube_domain(importer):
    """测试验证没有 YouTube 域名的 cookies"""
    cookies = [
        {
            "name": "TEST",
            "value": "test",
            "domain": ".example.com",
            "path": "/"
        }
    ]
    
    is_valid, message = importer.validate_cookies(cookies)
    
    assert is_valid is False
    assert "YouTube" in message


def test_validate_cookies_empty(importer):
    """测试验证空 cookies"""
    is_valid, message = importer.validate_cookies([])
    
    assert is_valid is False
    assert "没有找到任何 cookies" in message


def test_import_cookies_auto_detect(importer, netscape_file):
    """测试自动检测格式导入"""
    cookies, message = importer.import_cookies(netscape_file)
    
    assert len(cookies) > 0
    assert "成功验证" in message


def test_import_cookies_invalid_format(importer, tmp_path):
    """测试导入不支持的格式"""
    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_text("invalid content")
    
    with pytest.raises(ValueError):
        importer.import_cookies(invalid_file)


def test_standardize_cookie_fields(importer):
    """测试标准化 cookie 字段"""
    # Selenium 格式（使用 expiry）
    selenium_cookie = {
        "name": "TEST",
        "value": "test",
        "domain": ".youtube.com",
        "path": "/",
        "expiry": 1735689600,
        "httpOnly": True,
        "secure": True
    }
    
    standardized = importer._standardize_cookie_fields(selenium_cookie)
    
    assert standardized["name"] == "TEST"
    assert standardized["expires"] == 1735689600.0
    assert standardized["httpOnly"] is True
    
    # Playwright 格式（使用 expires）
    playwright_cookie = {
        "name": "TEST2",
        "value": "test2",
        "domain": ".youtube.com",
        "path": "/",
        "expires": 1735689600.0,
        "httpOnly": False,
        "secure": False
    }
    
    standardized = importer._standardize_cookie_fields(playwright_cookie)
    
    assert standardized["name"] == "TEST2"
    assert standardized["expires"] == 1735689600.0
    assert standardized["httpOnly"] is False
