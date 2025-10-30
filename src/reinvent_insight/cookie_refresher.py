"""Cookie Refresher - 使用 headless 浏览器刷新 cookies"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .cookie_store import CookieStore
from .cookie_models import Cookie, CookieMetadata
from .error_recovery import ErrorRecovery

logger = logging.getLogger(__name__)


class CookieRefresher:
    """Cookie 刷新器，使用 Playwright 访问 YouTube 刷新 cookies"""
    
    def __init__(
        self,
        cookie_store: CookieStore,
        browser_type: str = "chromium",
        browser_timeout: int = 30,
        headless: bool = True,
        max_retry_count: int = 3
    ):
        """
        初始化 Cookie Refresher
        
        Args:
            cookie_store: Cookie 存储管理器
            browser_type: 浏览器类型 (chromium, firefox, webkit)
            browser_timeout: 浏览器操作超时时间（秒）
            headless: 是否使用 headless 模式
            max_retry_count: 最大重试次数
        """
        self.cookie_store = cookie_store
        self.browser_type = browser_type
        self.browser_timeout = browser_timeout * 1000  # 转换为毫秒
        self.headless = headless
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        
        # 错误恢复机制
        self.error_recovery = ErrorRecovery(max_failures=max_retry_count)
    
    async def _setup_browser(self) -> Browser:
        """
        启动 Playwright 浏览器
        
        Returns:
            Browser 实例
        """
        try:
            logger.info(f"启动 {self.browser_type} 浏览器 (headless={self.headless})")
            
            self.playwright = await async_playwright().start()
            
            # 根据类型选择浏览器
            if self.browser_type == "chromium":
                browser_launcher = self.playwright.chromium
            elif self.browser_type == "firefox":
                browser_launcher = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_launcher = self.playwright.webkit
            else:
                raise ValueError(f"不支持的浏览器类型: {self.browser_type}")
            
            # 启动浏览器
            self.browser = await browser_launcher.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            logger.info("浏览器启动成功")
            return self.browser
        
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            raise
    
    async def _close_browser(self):
        """关闭浏览器"""
        try:
            if self.browser:
                await self.browser.close()
                logger.info("浏览器已关闭")
            
            if self.playwright:
                await self.playwright.stop()
        
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
    
    def _extract_cookies(self, context: BrowserContext) -> list[dict]:
        """
        从浏览器上下文提取 cookies
        
        Args:
            context: 浏览器上下文
            
        Returns:
            Cookie 列表（字典格式）
        """
        # 注意：这是一个同步方法，但 context.cookies() 是异步的
        # 所以我们需要在异步方法中调用它
        raise NotImplementedError("This method should not be called directly")
    
    async def _extract_cookies_async(self, context: BrowserContext) -> list[dict]:
        """
        从浏览器上下文提取 cookies（异步版本）
        
        Args:
            context: 浏览器上下文
            
        Returns:
            Cookie 列表（字典格式）
        """
        try:
            cookies = await context.cookies()
            
            # 只保留 YouTube 相关的 cookies
            youtube_cookies = [
                c for c in cookies
                if 'youtube.com' in c.get('domain', '') or 'google.com' in c.get('domain', '')
            ]
            
            logger.info(f"提取了 {len(youtube_cookies)} 个 YouTube/Google cookies")
            return youtube_cookies
        
        except Exception as e:
            logger.error(f"提取 cookies 失败: {e}")
            raise
    
    def _normalize_cookies(self, cookies: list[dict]) -> list[dict]:
        """
        规范化 cookies，确保符合 Playwright 要求
        
        Args:
            cookies: 原始 cookie 列表
            
        Returns:
            规范化后的 cookie 列表
        """
        normalized = []
        for cookie in cookies:
            # 复制 cookie
            normalized_cookie = cookie.copy()
            
            # 规范化 sameSite 值
            same_site = normalized_cookie.get('sameSite')
            
            # 处理 None 或空字符串
            if same_site is None or same_site == '':
                normalized_cookie['sameSite'] = 'Lax'
            else:
                # 转换为小写字符串进行比较
                same_site_lower = str(same_site).lower()
                if same_site_lower in ['strict', 'lax', 'none']:
                    # 首字母大写
                    normalized_cookie['sameSite'] = same_site_lower.capitalize()
                else:
                    # 无效值，使用默认值
                    normalized_cookie['sameSite'] = 'Lax'
            
            # 规范化 expires 字段 - 必须是 float 或 -1
            if 'expires' in normalized_cookie:
                expires_value = normalized_cookie['expires']
                if expires_value is None or expires_value == '':
                    # None 或空字符串表示会话 cookie，使用 -1
                    normalized_cookie['expires'] = -1
                else:
                    try:
                        # 尝试转换为 float
                        normalized_cookie['expires'] = float(expires_value)
                    except (ValueError, TypeError):
                        # 无法转换，使用 -1（会话 cookie）
                        logger.warning(f"Cookie {normalized_cookie.get('name')} 的 expires 字段无效: {expires_value}，设置为会话 cookie")
                        normalized_cookie['expires'] = -1
            
            normalized.append(normalized_cookie)
        
        return normalized
    
    async def validate_cookies_online(self, cookies: list[dict]) -> bool:
        """
        在线验证 cookies 是否有效
        
        通过访问 YouTube 并检查响应来验证 cookies
        
        Args:
            cookies: Cookie 列表
            
        Returns:
            True 如果 cookies 有效
        """
        browser = None
        try:
            # 启动浏览器
            browser = await self._setup_browser()
            
            # 规范化 cookies
            normalized_cookies = self._normalize_cookies(cookies)
            
            # 创建浏览器上下文并添加 cookies
            context = await browser.new_context()
            await context.add_cookies(normalized_cookies)
            
            # 访问 YouTube
            page = await context.new_page()
            response = await page.goto(
                'https://www.youtube.com',
                timeout=self.browser_timeout,
                wait_until='domcontentloaded'
            )
            
            # 检查响应状态
            if response and response.status == 200:
                # 检查是否需要登录
                # 如果页面包含登录按钮，说明 cookies 可能无效
                try:
                    # 等待一小段时间让页面加载
                    await page.wait_for_timeout(2000)
                    
                    # 检查是否有登录按钮
                    sign_in_button = await page.query_selector('a[href*="accounts.google.com"]')
                    
                    if sign_in_button:
                        logger.warning("检测到登录按钮，cookies 可能无效")
                        return False
                    
                    logger.info("Cookies 验证成功")
                    return True
                
                except Exception as e:
                    logger.warning(f"检查登录状态时出错: {e}")
                    # 如果检查失败，但页面加载成功，我们认为 cookies 可能有效
                    return True
            else:
                logger.warning(f"YouTube 响应状态码: {response.status if response else 'None'}")
                return False
        
        except Exception as e:
            logger.error(f"验证 cookies 失败: {e}")
            return False
        
        finally:
            if browser:
                await self._close_browser()
    
    async def refresh(self) -> tuple[bool, str]:
        """
        刷新 cookies（带重试机制）
        
        工作流程：
        1. 加载现有 cookies
        2. 启动浏览器并添加 cookies
        3. 访问 YouTube
        4. 提取更新后的 cookies
        5. 保存到 Cookie Store
        
        Returns:
            (是否成功, 消息)
        """
        try:
            logger.info("开始刷新 cookies")
            
            # 加载现有 cookies
            existing_cookies = self.cookie_store.load_cookies()
            
            if not existing_cookies:
                error_msg = "没有找到现有的 cookies，请先导入 cookies"
                self.error_recovery.record_failure(error_msg)
                return False, error_msg
            
            logger.info(f"加载了 {len(existing_cookies)} 个现有 cookies")
            
            # 启动浏览器（带重试）
            browser = None
            for attempt in range(3):
                try:
                    browser = await self._setup_browser()
                    break
                except Exception as e:
                    logger.warning(f"浏览器启动失败 (尝试 {attempt + 1}/3): {e}")
                    if attempt < 2:
                        await asyncio.sleep(5)
                    else:
                        error_msg = f"浏览器启动失败（已重试3次）: {str(e)}"
                        self.error_recovery.record_failure(error_msg)
                        return False, error_msg
            
            try:
                # 创建浏览器上下文
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                # 规范化并添加现有 cookies
                normalized_cookies = self._normalize_cookies(existing_cookies)
                await context.add_cookies(normalized_cookies)
                logger.info("已添加现有 cookies 到浏览器")
                
                # 访问 YouTube
                page = await context.new_page()
                logger.info("正在访问 YouTube...")
                
                response = await page.goto(
                    'https://www.youtube.com',
                    timeout=self.browser_timeout,
                    wait_until='domcontentloaded'
                )
                
                if not response or response.status != 200:
                    error_msg = f"访问 YouTube 失败，状态码: {response.status if response else 'None'}"
                    self.error_recovery.record_failure(error_msg)
                    return False, error_msg
                
                logger.info("成功访问 YouTube")
                
                # 等待页面加载
                await page.wait_for_timeout(3000)
                
                # 提取更新后的 cookies
                updated_cookies = await self._extract_cookies_async(context)
                
                if not updated_cookies:
                    error_msg = "未能提取到 cookies"
                    self.error_recovery.record_failure(error_msg)
                    # 保留旧 cookies
                    logger.warning("保留现有 cookies")
                    return False, error_msg
                
                # 更新元数据
                metadata = CookieMetadata(
                    source="auto_refresh",
                    validation_status="valid"
                )
                metadata.mark_refreshed()
                
                # 保存 cookies
                self.cookie_store.save_cookies(updated_cookies, metadata.model_dump())
                
                # 记录成功
                self.error_recovery.record_success()
                
                logger.info(f"成功刷新并保存 {len(updated_cookies)} 个 cookies")
                return True, f"成功刷新 {len(updated_cookies)} 个 cookies"
            
            finally:
                await self._close_browser()
        
        except Exception as e:
            error_msg = f"刷新 cookies 失败: {str(e)}"
            logger.error(error_msg)
            self.error_recovery.record_failure(error_msg)
            return False, error_msg
    
    def get_error_status(self) -> dict:
        """获取错误恢复状态"""
        return self.error_recovery.get_status()
