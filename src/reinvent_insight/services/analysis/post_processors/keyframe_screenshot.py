"""YouTube 关键帧截图后处理器

通过 Gemini API 分析视频内容，推荐关键时间点进行截图
"""

import asyncio
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from reinvent_insight.core import config
from reinvent_insight.infrastructure.ai.model_config import get_model_client
from reinvent_insight.infrastructure.ai.config_models import APIError
from reinvent_insight.infrastructure.media.screenshot_generator import ScreenshotGenerator
from reinvent_insight.services.analysis.post_processors.base import (
    PostProcessor,
    PostProcessorContext,
    PostProcessorResult,
    ProcessorPriority
)

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


logger = logger.bind(name=__name__)


@dataclass
class KeyframePoint:
    """关键帧截图点"""
    timestamp: int  # 秒数
    description: str  # 描述
    target_chapter: str = ""  # 要插入的章节标题
    relevance_score: float = 0.0  # 关联度评分


class KeyframeScreenshotProcessor(PostProcessor):
    """关键帧截图后处理器
    
    异步处理器：文章生成完成后，触发视频关键帧截图任务
    """
    
    name = "keyframe_screenshot"
    description = "生成YouTube视频关键帧截图"
    priority = ProcessorPriority.LOW  # 在 Visual 生成之前
    is_async = True  # 异步执行，只触发不等待
    
    def __init__(self, enabled: bool = None, min_chapter_count: int = None):
        """初始化关键帧截图处理器
        
        Args:
            enabled: 是否启用（None=使用配置）
            min_chapter_count: 最小章节数（None=使用配置）
        """
        self.enabled = enabled if enabled is not None else config.ENABLE_KEYFRAME_SCREENSHOT
        self.min_chapter_count = min_chapter_count if min_chapter_count is not None else config.KEYFRAME_MIN_CHAPTER_COUNT
        self.max_count = config.KEYFRAME_MAX_COUNT
        
        logger.info(
            f"初始化关键帧截图处理器 - "
            f"启用: {self.enabled}, 最小章节数: {self.min_chapter_count}, "
            f"最大截图数: {self.max_count}"
        )
    
    async def should_run(self, context: PostProcessorContext) -> bool:
        """判断是否应该运行"""
        if not self.enabled:
            logger.debug("关键帧截图处理器未启用 (ENABLE_KEYFRAME_SCREENSHOT=false)")
            return False
        
        # 必须是 YouTube 来源
        if context.content_type != "youtube":
            logger.debug(f"内容类型为 '{context.content_type}'，非 YouTube，跳过关键帧截图")
            return False
        
        # 必须有 video_url
        if not context.video_url:
            logger.warning("缺少 video_url，跳过关键帧截图")
            return False
        
        # 章节数要求
        if context.chapter_count < self.min_chapter_count:
            logger.info(
                f"章节数 {context.chapter_count} < {self.min_chapter_count}，"
                f"跳过关键帧截图"
            )
            return False
        
        return True
    
    async def process(self, context: PostProcessorContext) -> PostProcessorResult:
        """执行后处理（异步触发）"""
        try:
            logger.info(f"触发关键帧截图任务 - video_url: {context.video_url}")
            
            # 异步触发截图任务，不等待完成
            task = asyncio.create_task(self._generate_keyframes(
                video_url=context.video_url,
                report_content=context.report_content,
                doc_hash=context.doc_hash,
                title=context.title,
                article_path=context.get('article_path')
            ))
            
            # 添加异常回调，确保后台任务的异常能被记录
            def handle_exception(t):
                if t.exception():
                    logger.error(f"关键帧截图后台任务异常: {t.exception()}", exc_info=True)
            
            task.add_done_callback(handle_exception)
            
            return PostProcessorResult.ok(
                context.report_content,
                f"已触发关键帧截图任务"
            )
            
        except Exception as e:
            logger.error(f"触发关键帧截图任务失败: {e}", exc_info=True)
            return PostProcessorResult.error(
                context.report_content,
                f"触发失败: {e}"
            )
    
    async def _generate_keyframes(
        self,
        video_url: str,
        report_content: str,
        doc_hash: str,
        title: str,
        article_path: Optional[str] = None
    ):
        """生成关键帧截图（后台任务）"""
        try:
            logger.info(f"开始生成关键帧截图 - doc_hash: {doc_hash}")
            
            # 1. AI 分析获取推荐时间点
            keyframes = await self._analyze_keyframes(video_url, report_content)
            
            if not keyframes:
                logger.warning("AI 未返回有效的截图建议，跳过截图")
                return
            
            logger.info(f"AI 推荐了 {len(keyframes)} 个截图点")
            
            # 2. 执行截图
            successful_screenshots = await self._capture_keyframes(
                video_url=video_url,
                keyframes=keyframes,
                doc_hash=doc_hash
            )
            
            logger.info(f"成功截图 {len(successful_screenshots)} 张")
            
            # 3. 更新文章元数据
            if successful_screenshots and article_path:
                await self._update_article_metadata(
                    article_path=article_path,
                    screenshots=successful_screenshots
                )
            
            logger.info(f"关键帧截图任务完成 - doc_hash: {doc_hash}")
            
        except Exception as e:
            logger.error(f"生成关键帧截图失败: {e}", exc_info=True)
    
    async def _analyze_keyframes(
        self,
        video_url: str,
        report_content: str
    ) -> List[KeyframePoint]:
        """使用 Gemini API 分析带时间轴的字幕，推荐截图时间点"""
        try:
            # 1. 获取带时间戳的字幕
            timed_transcript = await self._get_timed_transcript(video_url)
            if not timed_transcript:
                logger.warning("无法获取字幕，跳过关键帧分析")
                return []
            
            # 2. 提取章节标题摘要
            chapter_summary = self._extract_chapter_summary(report_content)
            
            # 3. 构建分析提示词
            prompt = f"""你是一个视频内容分析专家。请根据以下带时间轴的字幕，分析视频内容并推荐截图时间点。

## 视频字幕（带时间轴）
{timed_transcript[:15000]}  # 限制长度避免超出 token 限制

## 文章章节
{chapter_summary}

## 任务
请推荐 3-{self.max_count} 个最值得截图的关键时间点：

1. 根据字幕内容，识别演讲者可能在展示图表、架构图、代码或演示的时刻
2. 优先选择字幕中提到 "as you can see"、"this diagram"、"here we have"、"let me show you" 等表达的时间点
3. 避免纯口播片段，选择有视觉内容的时刻
4. 时间点应均匀分布在视频各部分
5. target_chapter 必须是上面列出的章节标题之一

## 输出格式
请以 JSON 格式返回，描述使用中文：
{{
  "keyframes": [
    {{
      "timestamp": 秒数(整数),
      "description": "该时间点字幕内容的中文描述，以及为什么这个时间点值得截图",
      "target_chapter": "对应的章节标题",
      "relevance_score": 0-1之间的分数
    }}
  ]
}}
"""
            
            # 4. 调用 Gemini API
            client = get_model_client("keyframe_analysis")
            
            logger.info("调用 Gemini API 分析字幕推荐截图点...")
            response = await asyncio.wait_for(
                client.generate_content(
                    prompt=prompt,
                    is_json=True
                ),
                timeout=120
            )
            
            # 5. 解析结果
            data = json.loads(response)
            keyframes_data = data.get("keyframes", [])
            
            keyframes = []
            for item in keyframes_data:
                try:
                    keyframe = KeyframePoint(
                        timestamp=int(item["timestamp"]),
                        description=item.get("description", ""),
                        target_chapter=item.get("target_chapter", ""),
                        relevance_score=float(item.get("relevance_score", 0.5))
                    )
                    keyframes.append(keyframe)
                except (KeyError, ValueError) as e:
                    logger.warning(f"解析关键帧数据失败: {item}, 错误: {e}")
            
            logger.info(f"成功解析 {len(keyframes)} 个关键帧")
            return keyframes
            
        except asyncio.TimeoutError:
            logger.error("Gemini API 调用超时")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"解析 JSON 响应失败: {e}")
            return []
        except APIError as e:
            logger.error(f"Gemini API 调用失败: {e}")
            return []
        except Exception as e:
            logger.error(f"分析关键帧失败: {e}", exc_info=True)
            return []
    
    async def _get_timed_transcript(self, video_url: str) -> Optional[str]:
        """获取带时间戳的字幕"""
        try:
            from reinvent_insight.infrastructure.media.youtube_downloader import (
                SubtitleDownloader, normalize_youtube_url
            )
            
            # 标准化 URL 并获取视频信息
            normalized_url, _ = normalize_youtube_url(video_url)
            dl = SubtitleDownloader(normalized_url)
            
            # 获取元数据
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(None, dl._fetch_metadata)
            if not success or not dl.metadata:
                logger.warning("无法获取视频元数据")
                return None
            
            # 查找已存在的 VTT 字幕文件
            possible_langs = ['en', 'en-US', 'en-GB', 'zh-Hans', 'zh-CN', 'zh']
            vtt_path = None
            
            for lang in possible_langs:
                path = config.SUBTITLE_DIR / f"{dl.metadata.sanitized_title}.{lang}.vtt"
                if path.exists():
                    vtt_path = path
                    break
            
            if not vtt_path:
                # 尝试下载字幕
                logger.info("字幕文件不存在，尝试下载...")
                _, _, error = await loop.run_in_executor(None, dl.download)
                if error:
                    logger.warning(f"下载字幕失败: {error.message}")
                    return None
                
                # 再次查找
                for lang in possible_langs:
                    path = config.SUBTITLE_DIR / f"{dl.metadata.sanitized_title}.{lang}.vtt"
                    if path.exists():
                        vtt_path = path
                        break
            
            if not vtt_path or not vtt_path.exists():
                logger.warning("找不到字幕文件")
                return None
            
            # 读取并简化 VTT 内容（保留时间戳）
            vtt_content = vtt_path.read_text(encoding='utf-8')
            timed_transcript = self._parse_vtt_with_timestamps(vtt_content)
            
            logger.info(f"成功获取带时间轴字幕，长度: {len(timed_transcript)} 字符")
            return timed_transcript
            
        except Exception as e:
            logger.error(f"获取字幕失败: {e}", exc_info=True)
            return None
    
    def _parse_vtt_with_timestamps(self, vtt_content: str) -> str:
        """解析 VTT 字幕，保留时间戳但简化格式"""
        lines = vtt_content.splitlines()
        result = []
        current_time = None
        current_text = []
        seen_texts = set()  # 去重
        
        for line in lines:
            line = line.strip()
            
            # 跳过 VTT 头部
            if 'WEBVTT' in line or 'Kind:' in line or 'Language:' in line or not line:
                continue
            
            # 解析时间行（如 "00:00:05.000 --> 00:00:10.000"）
            if '-->' in line:
                # 保存之前的内容
                if current_time and current_text:
                    text = ' '.join(current_text)
                    text = re.sub(r'<[^>]+>', '', text)  # 移除 HTML 标签
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        result.append(f"[{current_time}] {text}")
                
                # 提取开始时间（只保留分:秒）
                time_match = re.match(r'(\d+):(\d+):(\d+)', line)
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    seconds = int(time_match.group(3))
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    current_time = f"{total_seconds}s"
                else:
                    time_match = re.match(r'(\d+):(\d+)', line)
                    if time_match:
                        minutes = int(time_match.group(1))
                        seconds = int(time_match.group(2))
                        total_seconds = minutes * 60 + seconds
                        current_time = f"{total_seconds}s"
                
                current_text = []
            else:
                # 字幕文本
                if line and not line.isdigit():  # 跳过序号行
                    current_text.append(line)
        
        # 保存最后一条
        if current_time and current_text:
            text = ' '.join(current_text)
            text = re.sub(r'<[^>]+>', '', text)
            if text and text not in seen_texts:
                result.append(f"[{current_time}] {text}")
        
        return '\n'.join(result)
    
    def _extract_chapter_summary(self, report_content: str) -> str:
        """提取文章章节摘要"""
        # 提取所有二级和三级标题
        lines = report_content.split('\n')
        chapters = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('## ') or line.startswith('### '):
                # 移除 Markdown 标记
                chapter = line.lstrip('#').strip()
                chapters.append(chapter)
        
        if chapters:
            return '\n'.join(f"- {ch}" for ch in chapters[:30])  # 最多30个章节
        else:
            # 如果没有章节，返回前500字符
            return report_content[:500]
    
    async def _capture_keyframes(
        self,
        video_url: str,
        keyframes: List[KeyframePoint],
        doc_hash: str
    ) -> List[Dict]:
        """捕获关键帧截图（复用浏览器实例）"""
        successful_screenshots = []
        
        # 确保输出目录存在
        output_dir = config.KEYFRAME_OUTPUT_DIR / doc_hash
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            async with async_playwright() as p:
                # 启动浏览器（只启动一次）
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-gpu',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                    ],
                    timeout=config.KEYFRAME_TIMEOUT * 1000
                )
                
                # 创建页面
                page = await browser.new_page(
                    viewport={
                        'width': config.KEYFRAME_SCREENSHOT_WIDTH,
                        'height': config.KEYFRAME_SCREENSHOT_HEIGHT
                    },
                    device_scale_factor=2  # 2倍分辨率
                )
                page.set_default_timeout(config.KEYFRAME_TIMEOUT * 1000)
                
                # 加载 Cookie（只加载一次）
                try:
                    from reinvent_insight.services.cookie.cookie_store import CookieStore
                    store = CookieStore()
                    cookies = store.load_cookies()
                    if cookies:
                        playwright_cookies = []
                        for c in cookies:
                            pc = {
                                'name': c.get('name', ''),
                                'value': c.get('value', ''),
                                'domain': c.get('domain', ''),
                                'path': c.get('path', '/'),
                            }
                            if c.get('expires'):
                                pc['expires'] = c['expires']
                            if c.get('httpOnly') is not None:
                                pc['httpOnly'] = c['httpOnly']
                            if c.get('secure') is not None:
                                pc['secure'] = c['secure']
                            if c.get('sameSite'):
                                pc['sameSite'] = c['sameSite']
                            playwright_cookies.append(pc)
                        
                        await page.context.add_cookies(playwright_cookies)
                        logger.info(f"成功加载 {len(playwright_cookies)} 个 Cookie")
                except Exception as e:
                    logger.warning(f"加载 Cookie 失败: {e}")
                
                # 串行处理每个截图点
                for i, keyframe in enumerate(keyframes, 1):
                    try:
                        logger.info(
                            f"截图 {i}/{len(keyframes)} - "
                            f"时间: {keyframe.timestamp}s, 描述: {keyframe.description}"
                        )
                        
                        # 构造时间戳 URL
                        if '?' in video_url:
                            timestamp_url = f"{video_url}&t={keyframe.timestamp}s"
                        else:
                            timestamp_url = f"{video_url}?t={keyframe.timestamp}s"
                        
                        # 输出路径
                        output_path = output_dir / f"frame_{keyframe.timestamp}.png"
                        
                        # 访问视频页面
                        logger.info(f"访问 YouTube: {timestamp_url}")
                        await page.goto(timestamp_url, wait_until='domcontentloaded', timeout=config.KEYFRAME_TIMEOUT * 1000)
                        
                        # 等待视频元素加载
                        await page.wait_for_selector('video', timeout=10000)
                        
                        # 等待视频缓冲
                        await asyncio.sleep(config.KEYFRAME_WAIT_TIME)
                        
                        # 尝试暂停视频并进入影院模式
                        try:
                            await page.evaluate("""
                                () => {
                                    const video = document.querySelector('video');
                                    if (video && !video.paused) {
                                        video.pause();
                                    }
                                    // 点击影院模式按钮
                                    const theaterBtn = document.querySelector('.ytp-size-button');
                                    if (theaterBtn) {
                                        theaterBtn.click();
                                    }
                                }
                            """)
                            await asyncio.sleep(0.5)
                        except Exception:
                            pass
                        
                        # 截取视频元素（而不是整个页面）
                        video_element = await page.query_selector('video')
                        if video_element:
                            await video_element.screenshot(
                                path=str(output_path),
                                type='png'
                            )
                        else:
                            # 回退到页面截图
                            await page.screenshot(
                                path=str(output_path),
                                type='png',
                                full_page=False
                            )
                        
                        successful_screenshots.append({
                            "timestamp": keyframe.timestamp,
                            "file": str(output_path.relative_to(config.OUTPUT_DIR)),
                            "description": keyframe.description,
                            "target_chapter": keyframe.target_chapter,
                            "relevance_score": keyframe.relevance_score
                        })
                        logger.info(f"截图成功: {output_path}")
                        
                    except Exception as e:
                        logger.warning(f"截图失败 (时间: {keyframe.timestamp}s): {e}")
                        continue
                
                # 关闭浏览器
                await browser.close()
                
        except PlaywrightTimeoutError:
            logger.error("浏览器超时")
        except Exception as e:
            logger.error(f"截图流程失败: {e}", exc_info=True)
        
        return successful_screenshots
    
    async def _capture_youtube_screenshot(
        self,
        url: str,
        output_path: Path,
        wait_time: int = 3
    ) -> bool:
        """使用 Playwright 截取 YouTube 视频截图（单次调用，保留以兼容旧代码）"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage'],
                    timeout=config.KEYFRAME_TIMEOUT * 1000
                )
                
                page = await browser.new_page(
                    viewport={
                        'width': config.KEYFRAME_SCREENSHOT_WIDTH,
                        'height': config.KEYFRAME_SCREENSHOT_HEIGHT
                    },
                    device_scale_factor=2
                )
                page.set_default_timeout(config.KEYFRAME_TIMEOUT * 1000)
                
                # 加载 Cookie
                try:
                    from reinvent_insight.services.cookie.cookie_store import CookieStore
                    store = CookieStore()
                    cookies = store.load_cookies()
                    if cookies:
                        playwright_cookies = [{
                            'name': c.get('name', ''),
                            'value': c.get('value', ''),
                            'domain': c.get('domain', ''),
                            'path': c.get('path', '/'),
                            **({k: c[k] for k in ['expires', 'httpOnly', 'secure', 'sameSite'] if c.get(k) is not None})
                        } for c in cookies]
                        await page.context.add_cookies(playwright_cookies)
                except Exception as e:
                    logger.warning(f"加载 Cookie 失败: {e}")
                
                await page.goto(url, wait_until='domcontentloaded', timeout=config.KEYFRAME_TIMEOUT * 1000)
                await page.wait_for_selector('video', timeout=10000)
                await asyncio.sleep(wait_time)
                
                try:
                    await page.evaluate("document.querySelector('video')?.pause()")
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
                
                await page.screenshot(path=str(output_path), type='png', full_page=False)
                await browser.close()
                return True
                
        except PlaywrightTimeoutError:
            logger.error(f"截图超时: {url}")
            return False
        except Exception as e:
            logger.error(f"截图失败: {e}", exc_info=True)
            return False
    
    async def _load_cookies(self) -> List[Dict]:
        """加载 Netscape 格式的 Cookie 文件"""
        cookies = []
        try:
            with open(config.COOKIES_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        cookies.append({
                            'name': parts[5],
                            'value': parts[6],
                            'domain': parts[0],
                            'path': parts[2],
                        })
        except Exception as e:
            logger.warning(f"解析 Cookie 文件失败: {e}")
        
        return cookies
    
    async def _update_article_metadata(
        self,
        article_path: str,
        screenshots: List[Dict]
    ):
        """更新文章元数据并在章节后插入截图"""
        try:
            import yaml
            
            article_file = Path(article_path)
            if not article_file.exists():
                logger.warning(f"文章文件不存在: {article_path}")
                return
            
            content = article_file.read_text(encoding='utf-8')
            
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1]) or {}
                    article_body = parts[2]
                    
                    # 更新元数据
                    metadata['keyframe_screenshots'] = {
                        'status': 'completed',
                        'generated_at': datetime.now().isoformat(),
                        'screenshots': screenshots,
                        'total_count': len(screenshots)
                    }
                    
                    # 在对应章节后插入截图
                    article_body = self._insert_screenshots_to_chapters(article_body, screenshots)
                    
                    # 重新组装
                    new_content = f"---\n{yaml.dump(metadata, allow_unicode=True)}---{article_body}"
                    article_file.write_text(new_content, encoding='utf-8')
                    
                    logger.info(f"元数据已更新，截图已插入到章节: {article_path}")
        
        except Exception as e:
            logger.error(f"更新文章失败: {e}", exc_info=True)
    
    def _insert_screenshots_to_chapters(self, article_body: str, screenshots: List[Dict]) -> str:
        """在对应章节后插入截图"""
        if not screenshots:
            return article_body
        
        # 按章节分组截图
        chapter_screenshots = {}
        unmatched = []
        
        for shot in screenshots:
            target = shot.get('target_chapter', '')
            if target:
                if target not in chapter_screenshots:
                    chapter_screenshots[target] = []
                chapter_screenshots[target].append(shot)
            else:
                unmatched.append(shot)
        
        # 在每个章节后插入图片
        lines = article_body.split('\n')
        new_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            new_lines.append(line)
            
            # 检查是否是章节标题
            if line.strip().startswith('## ') or line.strip().startswith('### '):
                chapter_title = line.strip().lstrip('#').strip()
                
                # 查找匹配的截图
                matched_shots = None
                for target_chapter, shots in chapter_screenshots.items():
                    # 模糊匹配：章节标题包含目标关键词或反过来
                    if target_chapter in chapter_title or chapter_title in target_chapter:
                        matched_shots = shots
                        del chapter_screenshots[target_chapter]
                        break
                
                if matched_shots:
                    # 找到章节结束位置（下一个同级或更高级标题之前）
                    current_level = len(line) - len(line.lstrip('#'))
                    insert_pos = i + 1
                    
                    # 找章节内容结束位置
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j].strip()
                        if next_line.startswith('#'):
                            next_level = len(lines[j]) - len(lines[j].lstrip('#'))
                            if next_level <= current_level:
                                insert_pos = j
                                break
                    else:
                        insert_pos = len(lines)
                    
                    # 在章节标题后立即插入图片
                    for shot in matched_shots:
                        img_md = self._format_screenshot_markdown(shot)
                        new_lines.append('')
                        new_lines.append(img_md)
            
            i += 1
        
        # 存在未匹配的截图，追加到文末
        remaining = list(chapter_screenshots.values())
        all_unmatched = unmatched + [s for shots in remaining for s in shots]
        
        if all_unmatched:
            new_lines.append('')
            new_lines.append('---')
            new_lines.append('')
            new_lines.append('## 🎬 其他视频关键帧')
            new_lines.append('')
            for shot in all_unmatched:
                img_md = self._format_screenshot_markdown(shot)
                new_lines.append(img_md)
                new_lines.append('')
        
        return '\n'.join(new_lines)
    
    def _format_screenshot_markdown(self, shot: Dict) -> str:
        """格式化单个截图为 Markdown"""
        timestamp = shot.get('timestamp', 0)
        description = shot.get('description', '')
        file_path = shot.get('file', '')
        
        minutes = timestamp // 60
        seconds = timestamp % 60
        time_str = f"{minutes}:{seconds:02d}"
        
        # 使用 HTML 标签控制图片宽度
        return f'<img src="/d/{file_path}" alt="{time_str}" style="max-width: 100%; width: 720px; border-radius: 8px; margin: 12px 0;">\n\n*[{time_str}] {description}*'
