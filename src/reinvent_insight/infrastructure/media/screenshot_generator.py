"""
Screenshot Generator - Visual Insight 长图生成器

使用 Playwright 将 HTML 文件转换为全页面截图
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

import logging
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from reinvent_insight.core import config


logger = logging.getLogger(__name__)


class ScreenshotGenerator:
    """截图生成器，基于 Playwright"""
    
    def __init__(self, viewport_width: Optional[int] = None, wait_time: Optional[int] = None):
        """
        初始化截图生成器
        
        Args:
            viewport_width: 视口宽度（像素），默认使用配置值
            wait_time: 等待时间（秒），默认使用配置值
        """
        self.viewport_width = viewport_width or config.VISUAL_SCREENSHOT_VIEWPORT_WIDTH
        self.wait_time = wait_time or config.VISUAL_SCREENSHOT_WAIT_TIME
        self.browser_timeout = config.VISUAL_SCREENSHOT_BROWSER_TIMEOUT * 1000  # 转换为毫秒
        
        # 并发控制：最多同时 2 个截图任务
        self._semaphore = asyncio.Semaphore(2)
        
        logger.info(
            f"初始化截图生成器 - 视口宽度: {self.viewport_width}px, "
            f"等待时间: {self.wait_time}s, 浏览器超时: {self.browser_timeout}ms"
        )
    
    async def capture_full_page(
        self, 
        html_path: Path, 
        output_path: Path,
        viewport_width: Optional[int] = None
    ) -> Dict:
        """
        执行全页面截图
        
        Args:
            html_path: HTML 文件路径
            output_path: 输出图片路径
            viewport_width: 视口宽度（可选，覆盖默认值）
            
        Returns:
            包含截图信息的字典（路径、尺寸、文件大小等）
            
        Raises:
            FileNotFoundError: HTML 文件不存在
            PlaywrightTimeoutError: 浏览器操作超时
            Exception: 其他截图错误
        """
        async with self._semaphore:  # 并发控制
            return await self._capture_full_page_internal(html_path, output_path, viewport_width)
    
    async def _capture_full_page_internal(
        self, 
        html_path: Path, 
        output_path: Path,
        viewport_width: Optional[int] = None
    ) -> Dict:
        """内部截图实现"""
        if not html_path.exists():
            raise FileNotFoundError(f"HTML 文件不存在: {html_path}")
        
        width = viewport_width or self.viewport_width
        
        logger.info(f"开始截图 - HTML: {html_path}, 输出: {output_path}, 视口宽度: {width}px")
        start_time = datetime.now()
        
        browser: Optional[Browser] = None
        page: Optional[Page] = None
        
        try:
            # 启动 Playwright
            async with async_playwright() as p:
                logger.info("启动 Chromium 浏览器（无头模式）")
                
                # 启动浏览器（无头模式）
                # 注意：移除 --disable-gpu，使用 GPU 加速渲染避免长页面色块/撕裂问题
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',  # 允许加载本地资源
                        '--disable-software-rasterizer',  # 禁用软件光栅化
                        '--enable-gpu-rasterization',  # 启用 GPU 光栅化
                        '--enable-zero-copy',  # 零拷贝优化
                        '--ignore-gpu-blocklist',  # 忽略 GPU 黑名单
                    ],
                    timeout=self.browser_timeout
                )
                
                # 创建页面并设置视口
                # 使用 1.5x deviceScaleFactor 平衡清晰度和渲染稳定性
                # 注意：2x 在超长页面下可能导致渲染问题
                page = await browser.new_page(
                    viewport={'width': width, 'height': 1080},
                    device_scale_factor=3.0  # 2倍分辨率，高清输出
                )
                
                # 设置超时
                page.set_default_timeout(self.browser_timeout)
                
                # 加载 HTML 文件（使用 file:// 协议）
                file_url = html_path.absolute().as_uri()
                logger.info(f"加载 HTML 文件: {file_url}")
                
                await page.goto(
                    file_url,
                    wait_until='networkidle',  # 等待网络空闲
                    timeout=self.browser_timeout
                )
                
                logger.info("页面加载完成，触发动画和渲染...")
                
                # 优化：直接通过 JS 触发所有动画元素，绕过 Intersection Observer
                await self._trigger_all_animations(page)
                
                # 等待动画和图表渲染完成
                await self._wait_for_render(page)
                
                # 获取页面实际尺寸
                dimensions = await self._get_page_dimensions(page)
                logger.info(f"页面尺寸: {dimensions['width']}x{dimensions['height']}px")
                
                # 确保输出目录存在
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 执行全页面截图
                logger.info("执行全页面截图...")
                await page.screenshot(
                    path=str(output_path),
                    full_page=True,
                    type='png'
                )
                
                # 关闭浏览器
                await browser.close()
                
                # 获取文件大小
                file_size = output_path.stat().st_size
                
                # 计算耗时
                duration = (datetime.now() - start_time).total_seconds()
                
                logger.info(
                    f"截图完成 - 文件: {output_path}, "
                    f"尺寸: {dimensions['width']}x{dimensions['height']}px, "
                    f"大小: {file_size / 1024 / 1024:.2f}MB, "
                    f"耗时: {duration:.2f}s"
                )
                
                return {
                    "path": str(output_path),
                    "dimensions": dimensions,
                    "file_size": file_size,
                    "duration": duration,
                    "generated_at": datetime.now().isoformat()
                }
                
        except PlaywrightTimeoutError as e:
            logger.error(f"截图超时: {e}")
            raise
        except Exception as e:
            logger.error(f"截图失败: {e}", exc_info=True)
            raise
        finally:
            # 确保浏览器关闭
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
    
    async def _trigger_all_animations(self, page: Page) -> None:
        """
        通过 JS 直接触发所有动画元素，绕过 Intersection Observer 的滚动触发机制
        
        Args:
            page: Playwright Page 对象
        """
        try:
            # 一次性触发所有 fade-in-up 动画元素
            triggered_count = await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('.fade-in-up');
                    elements.forEach(el => el.classList.add('visible'));
                    return elements.length;
                }
            """)
            
            logger.info(f"已触发 {triggered_count} 个动画元素")
            
        except Exception as e:
            logger.warning(f"触发动画失败，回退到滚动模式: {e}")
            await self._scroll_fallback(page)
    
    async def _scroll_fallback(self, page: Page) -> None:
        """
        回退方案：快速滚动触发懒加载（优化版）
        """
        try:
            total_height = await page.evaluate("document.documentElement.scrollHeight")
            
            # 快速滚动：只触发 3 个关键位置（顶部、中部、底部）
            positions = [0, total_height // 2, total_height]
            for pos in positions:
                await page.evaluate(f"window.scrollTo(0, {pos})")
                await asyncio.sleep(0.1)
            
            # 回到顶部
            await page.evaluate("window.scrollTo(0, 0)")
            
        except Exception as e:
            logger.warning(f"滚动回退失败: {e}")
    
    async def _wait_for_render(self, page: Page) -> None:
        """
        等待动画和图表渲染完成（优化版）
        
        Args:
            page: Playwright Page 对象
        """
        # 检测是否有图表需要额外等待
        try:
            has_charts = await page.evaluate("""
                () => typeof Chart !== 'undefined' && document.querySelectorAll('canvas').length > 0
            """)
            
            if has_charts:
                # 有图表：等待图表渲染
                wait_time = min(self.wait_time, 2)  # 最多等 2 秒
                logger.info(f"检测到图表，等待 {wait_time}s 渲染")
                await asyncio.sleep(wait_time)
            else:
                # 无图表：只等待动画完成（0.8s 是 fade-in-up 动画时长）
                logger.info("无图表，等待动画完成")
                await asyncio.sleep(1.0)
                
        except Exception as e:
            logger.warning(f"渲染检测失败，使用默认等待: {e}")
            await asyncio.sleep(1.0)
    
    async def _get_page_dimensions(self, page: Page) -> Dict[str, int]:
        """
        获取页面实际尺寸
        
        Args:
            page: Playwright Page 对象
            
        Returns:
            包含 width 和 height 的字典
        """
        try:
            dimensions = await page.evaluate("""
                () => {
                    return {
                        width: document.documentElement.scrollWidth,
                        height: document.documentElement.scrollHeight
                    };
                }
            """)
            
            return {
                "width": int(dimensions['width']),
                "height": int(dimensions['height'])
            }
            
        except Exception as e:
            logger.warning(f"获取页面尺寸失败，使用默认值: {e}")
            return {
                "width": self.viewport_width,
                "height": 8000  # 默认高度
            }
