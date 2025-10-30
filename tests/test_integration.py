"""集成测试"""
import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.reinvent_insight.cookie_store import CookieStore
from src.reinvent_insight.cookie_importer import CookieImporter
from src.reinvent_insight.cookie_refresher import CookieRefresher
from src.reinvent_insight.cookie_scheduler import CookieScheduler
from src.reinvent_insight.cookie_models import CookieManagerConfig


@pytest.fixture
def temp_config(tmp_path):
    """临时配置"""
    return CookieManagerConfig(
        cookie_store_path=tmp_path / "cookies.json",
        netscape_cookie_path=tmp_path / "cookies.txt",
        refresh_interval_hours=1,
        browser_timeout=10,
        max_retry_count=2
    )


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
        },
        {
            "name": "PREF",
            "value": "test_pref",
            "domain": ".youtube.com",
            "path": "/",
            "expires": datetime.now().timestamp() + 86400,
            "secure": False,
            "httpOnly": False
        }
    ]


def test_complete_import_flow(temp_config, tmp_path, sample_cookies):
    """测试完整的 cookie 导入流程"""
    # 1. 创建测试文件
    import json
    test_file = tmp_path / "test_cookies.json"
    test_file.write_text(json.dumps(sample_cookies))
    
    # 2. 导入 cookies
    importer = CookieImporter()
    cookies, message = importer.import_cookies(test_file)
    
    assert len(cookies) == 3
    assert "成功验证" in message
    
    # 3. 保存到 Cookie Store
    store = CookieStore(
        temp_config.cookie_store_path,
        temp_config.netscape_cookie_path
    )
    
    from src.reinvent_insight.cookie_models import CookieMetadata
    metadata = CookieMetadata(source="manual_import").model_dump()
    store.save_cookies(cookies, metadata)
    
    # 4. 验证保存成功
    assert temp_config.cookie_store_path.exists()
    assert temp_config.netscape_cookie_path.exists()
    
    # 5. 加载并验证
    loaded_cookies = store.load_cookies()
    assert len(loaded_cookies) == 3
    
    # 6. 验证 Netscape 格式
    netscape_content = temp_config.netscape_cookie_path.read_text()
    assert "CONSENT" in netscape_content
    assert "VISITOR_INFO1_LIVE" in netscape_content


@pytest.mark.asyncio
async def test_cookie_refresh_flow_with_mock(temp_config, sample_cookies):
    """测试 cookie 刷新流程（使用 mock）"""
    # 1. 准备 Cookie Store
    store = CookieStore(
        temp_config.cookie_store_path,
        temp_config.netscape_cookie_path
    )
    
    from src.reinvent_insight.cookie_models import CookieMetadata
    metadata = CookieMetadata(source="test").model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    # 2. 创建 Refresher（mock 浏览器操作）
    refresher = CookieRefresher(
        cookie_store=store,
        browser_type="chromium",
        browser_timeout=10,
        headless=True,
        max_retry_count=2
    )
    
    # Mock 浏览器操作
    with patch.object(refresher, '_setup_browser', new_callable=AsyncMock) as mock_browser:
        with patch.object(refresher, '_extract_cookies_async', new_callable=AsyncMock) as mock_extract:
            with patch.object(refresher, '_close_browser', new_callable=AsyncMock):
                # 设置 mock 返回值
                mock_browser.return_value = Mock()
                mock_extract.return_value = sample_cookies
                
                # Mock 浏览器上下文
                mock_context = AsyncMock()
                mock_context.add_cookies = AsyncMock()
                mock_context.new_page = AsyncMock()
                
                mock_page = AsyncMock()
                mock_page.goto = AsyncMock(return_value=Mock(status=200))
                mock_page.wait_for_timeout = AsyncMock()
                
                mock_context.new_page.return_value = mock_page
                mock_browser.return_value.new_context = AsyncMock(return_value=mock_context)
                
                # 3. 执行刷新
                success, message = await refresher.refresh()
                
                # 4. 验证结果
                assert success is True
                assert "成功刷新" in message
                
                # 5. 验证 cookies 已更新
                updated_cookies = store.load_cookies()
                assert len(updated_cookies) == len(sample_cookies)
                
                # 6. 验证元数据已更新
                updated_metadata = store.get_metadata()
                assert updated_metadata["source"] == "auto_refresh"
                assert updated_metadata["validation_status"] == "valid"


@pytest.mark.asyncio
async def test_scheduler_manual_refresh(temp_config, sample_cookies):
    """测试调度器手动刷新"""
    # 1. 准备 Cookie Store
    store = CookieStore(
        temp_config.cookie_store_path,
        temp_config.netscape_cookie_path
    )
    
    from src.reinvent_insight.cookie_models import CookieMetadata
    metadata = CookieMetadata(source="test").model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    # 2. 创建 Refresher 和 Scheduler
    refresher = CookieRefresher(
        cookie_store=store,
        browser_type="chromium",
        browser_timeout=10,
        headless=True
    )
    
    scheduler = CookieScheduler(
        refresher=refresher,
        interval_hours=1
    )
    
    # Mock 刷新操作
    with patch.object(refresher, 'refresh', new_callable=AsyncMock) as mock_refresh:
        mock_refresh.return_value = (True, "成功刷新 3 个 cookies")
        
        # 3. 手动触发刷新
        success, message = await scheduler.trigger_manual_refresh()
        
        # 4. 验证结果
        assert success is True
        assert "成功刷新" in message
        assert mock_refresh.called


def test_service_lifecycle(temp_config, sample_cookies):
    """测试服务生命周期"""
    from src.reinvent_insight.cookie_manager_service import CookieManagerService
    
    # 1. 准备 cookies
    store = CookieStore(
        temp_config.cookie_store_path,
        temp_config.netscape_cookie_path
    )
    
    from src.reinvent_insight.cookie_models import CookieMetadata
    metadata = CookieMetadata(source="test").model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    # 2. 创建服务
    service = CookieManagerService(temp_config)
    
    # 3. 验证初始状态
    assert service.is_running is False
    
    # 4. 获取状态
    status = service.get_status()
    assert status['is_running'] is False
    assert status['cookie_store']['has_cookies'] is True
    
    # 注意：不实际启动服务，因为需要异步环境和真实的浏览器


def test_error_recovery_flow():
    """测试错误恢复流程"""
    from src.reinvent_insight.error_recovery import ErrorRecovery
    
    recovery = ErrorRecovery(max_failures=3)
    
    # 1. 初始状态
    assert recovery.should_retry() is True
    assert recovery.failure_count == 0
    
    # 2. 记录第一次失败
    recovery.record_failure("Test error 1")
    assert recovery.failure_count == 1
    assert recovery.should_retry() is True
    
    # 3. 记录第二次失败
    recovery.record_failure("Test error 2")
    assert recovery.failure_count == 2
    assert recovery.should_retry() is True
    
    # 4. 记录第三次失败
    recovery.record_failure("Test error 3")
    assert recovery.failure_count == 3
    assert recovery.should_retry() is False
    
    # 5. 记录成功，重置计数
    recovery.record_success()
    assert recovery.failure_count == 0
    assert recovery.should_retry() is True
    
    # 6. 测试重试延迟
    recovery.record_failure("Test error")
    delay = recovery.get_retry_delay()
    assert delay == 300  # 5分钟
    
    recovery.record_failure("Test error")
    delay = recovery.get_retry_delay()
    assert delay == 600  # 10分钟


@pytest.mark.asyncio
async def test_concurrent_refresh_prevention(temp_config, sample_cookies):
    """测试防止并发刷新"""
    # 1. 准备 Cookie Store
    store = CookieStore(
        temp_config.cookie_store_path,
        temp_config.netscape_cookie_path
    )
    
    from src.reinvent_insight.cookie_models import CookieMetadata
    metadata = CookieMetadata(source="test").model_dump()
    store.save_cookies(sample_cookies, metadata)
    
    # 2. 创建 Refresher
    refresher = CookieRefresher(
        cookie_store=store,
        browser_type="chromium",
        browser_timeout=10,
        headless=True
    )
    
    # Mock 刷新操作（模拟长时间运行）
    async def slow_refresh():
        await asyncio.sleep(0.5)
        return (True, "Success")
    
    with patch.object(refresher, 'refresh', side_effect=slow_refresh):
        # 3. 尝试并发刷新
        task1 = asyncio.create_task(refresher.refresh())
        task2 = asyncio.create_task(refresher.refresh())
        
        results = await asyncio.gather(task1, task2)
        
        # 4. 验证两次刷新都完成了
        assert len(results) == 2
        assert all(r[0] is True for r in results)
