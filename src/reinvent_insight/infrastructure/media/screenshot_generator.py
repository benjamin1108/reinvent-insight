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
                    device_scale_factor=1.5  # 1.5倍分辨率，平衡清晰度和稳定性
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
                
                logger.info("页面加载完成，开始触发懒加载内容渲染...")
                
                # 滚动页面触发所有懒加载内容
                await self._scroll_to_trigger_lazy_load(page)
                
                # 等待图表和动画渲染
                await self._wait_for_charts(page)
                
                # 滚动回顶部
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(0.5)  # 短暂等待滚动完成
                
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
    
    async def _scroll_to_trigger_lazy_load(self, page: Page) -> None:
        """
        滚动页面触发所有懒加载内容（Intersection Observer）
        
        Args:
            page: Playwright Page 对象
        """
        logger.info("滚动页面触发懒加载内容...")
        
        try:
            # 获取页面总高度
            total_height = await page.evaluate("document.documentElement.scrollHeight")
            viewport_height = 1080  # 视口高度
            
            # 分段滚动，确保所有内容进入视口触发 Intersection Observer
            scroll_step = viewport_height * 0.8  # 每次滚动80%视口高度，确保有重叠
            current_position = 0
            
            while current_position < total_height:
                await page.evaluate(f"window.scrollTo(0, {current_position})")
                await asyncio.sleep(0.3)  # 每次滚动后等待300ms，让动画和图表有时间渲染
                current_position += scroll_step
            
            # 滚动到底部，确保最后一屏内容也被触发
            await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            await asyncio.sleep(0.5)
            
            logger.info(f"页面滚动完成，总高度: {total_height}px")
            
        except Exception as e:
            logger.warning(f"页面滚动失败（可能影响截图完整性）: {e}")
    
    async def _wait_for_charts(self, page: Page) -> None:
        """
        等待 Chart.js 图表渲染完成
        
        Args:
            page: Playwright Page 对象
        """
        # 固定延迟，等待图表和动画渲染
        logger.info(f"等待 {self.wait_time} 秒以确保图表和动画渲染完成...")
        await asyncio.sleep(self.wait_time)
        
        # 可选：检测 Chart.js 是否加载完成
        try:
            # 执行 JavaScript 检测图表是否存在
            has_charts = await page.evaluate("""
                () => {
                    return typeof Chart !== 'undefined' && 
                           document.querySelectorAll('canvas').length > 0;
                }
            """)
            
            if has_charts:
                logger.info("检测到 Chart.js 图表，已等待渲染完成")
            else:
                logger.info("未检测到图表，页面已准备就绪")
                
        except Exception as e:
            logger.warning(f"图表检测失败（可忽略）: {e}")
    
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
