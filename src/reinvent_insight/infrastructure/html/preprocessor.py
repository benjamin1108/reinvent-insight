"""
HTML预处理器

负责清理HTML，去除JavaScript、CSS、注释等冗余内容。
"""

import logging
from bs4 import BeautifulSoup, Comment
from typing import Optional

from .exceptions import HTMLParseError

logger = logging.getLogger(__name__)


class HTMLPreprocessor:
    """HTML预处理器，去除冗余内容
    
    使用BeautifulSoup解析HTML并移除不必要的元素：
    - JavaScript代码（script标签）
    - CSS样式（style标签和style属性）
    - HTML注释
    - SVG和Canvas元素
    
    使用示例:
        >>> preprocessor = HTMLPreprocessor()
        >>> cleaned_html = preprocessor.preprocess(raw_html)
    """
    
    def __init__(self, parser: str = "lxml"):
        """初始化预处理器
        
        Args:
            parser: HTML解析器（默认使用lxml以获得更好的性能）
        """
        self.parser = parser
        logger.info(f"HTMLPreprocessor initialized with parser={parser}")
    
    def preprocess(self, html: str) -> str:
        """预处理HTML内容
        
        Args:
            html: 原始HTML字符串
            
        Returns:
            清理后的HTML字符串
            
        Raises:
            HTMLParseError: HTML解析失败
        """
        if not html or not html.strip():
            raise HTMLParseError("HTML content is empty")
        
        logger.info("Starting HTML preprocessing")
        
        try:
            # 解析HTML
            soup = BeautifulSoup(html, self.parser)
            
            # 执行各种清理操作
            self._remove_scripts(soup)
            self._remove_styles(soup)
            self._remove_comments(soup)
            self._remove_svg_canvas(soup)
            self._remove_navigation_elements(soup)
            self._remove_metadata_elements(soup)
            self._remove_unnecessary_attributes(soup)
            self._extract_main_content(soup)
            self._simplify_structure(soup)
            self._extract_text_content(soup)
            
            # 转换回字符串
            cleaned_html = str(soup)
            
            logger.info("HTML preprocessing completed")
            return cleaned_html
            
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}", exc_info=True)
            
            # 尝试使用宽松模式重新解析
            try:
                logger.info("Retrying with html.parser (lenient mode)")
                soup = BeautifulSoup(html, "html.parser")
                
                self._remove_scripts(soup)
                self._remove_styles(soup)
                self._remove_comments(soup)
                self._remove_svg_canvas(soup)
                self._remove_navigation_elements(soup)
                self._remove_metadata_elements(soup)
                self._remove_unnecessary_attributes(soup)
                self._extract_main_content(soup)
                
                cleaned_html = str(soup)
                logger.info("HTML preprocessing completed (lenient mode)")
                return cleaned_html
                
            except Exception as e2:
                logger.error(f"HTML parsing failed even in lenient mode: {e2}")
                raise HTMLParseError(f"Failed to parse HTML: {e2}") from e2
    
    def _remove_scripts(self, soup: BeautifulSoup) -> None:
        """移除所有script标签
        
        Args:
            soup: BeautifulSoup对象
        """
        scripts = soup.find_all('script')
        count = len(scripts)
        
        for script in scripts:
            script.decompose()
        
        if count > 0:
            logger.debug(f"Removed {count} script tags")
    
    def _remove_styles(self, soup: BeautifulSoup) -> None:
        """移除所有style标签和style属性
        
        Args:
            soup: BeautifulSoup对象
        """
        # 移除style标签
        styles = soup.find_all('style')
        style_count = len(styles)
        
        for style in styles:
            style.decompose()
        
        # 移除所有元素的style属性
        attr_count = 0
        for tag in soup.find_all(True):  # True匹配所有标签
            if tag.has_attr('style'):
                del tag['style']
                attr_count += 1
        
        if style_count > 0 or attr_count > 0:
            logger.debug(f"Removed {style_count} style tags and {attr_count} style attributes")
    
    def _remove_comments(self, soup: BeautifulSoup) -> None:
        """移除HTML注释
        
        Args:
            soup: BeautifulSoup对象
        """
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        count = len(comments)
        
        for comment in comments:
            comment.extract()
        
        if count > 0:
            logger.debug(f"Removed {count} HTML comments")
    
    def _remove_svg_canvas(self, soup: BeautifulSoup) -> None:
        """移除SVG和Canvas元素
        
        Args:
            soup: BeautifulSoup对象
        """
        # 移除SVG元素
        svgs = soup.find_all('svg')
        svg_count = len(svgs)
        
        for svg in svgs:
            svg.decompose()
        
        # 移除Canvas元素
        canvases = soup.find_all('canvas')
        canvas_count = len(canvases)
        
        for canvas in canvases:
            canvas.decompose()
        
        if svg_count > 0 or canvas_count > 0:
            logger.debug(f"Removed {svg_count} SVG elements and {canvas_count} Canvas elements")
    
    def _remove_navigation_elements(self, soup: BeautifulSoup) -> None:
        """移除导航、页脚、侧边栏等非内容元素
        
        Args:
            soup: BeautifulSoup对象
        """
        # 要移除的标签
        tags_to_remove = ['nav', 'header', 'footer', 'aside']
        
        # 要移除的class/id关键词
        keywords_to_remove = [
            'nav', 'navigation', 'menu', 'sidebar', 'side-bar',
            'header', 'footer', 'advertisement', 'ad-', 'ads',
            'social', 'share', 'comment', 'related', 'recommend',
            'popup', 'modal', 'overlay', 'cookie', 'banner',
            'subscription', 'subscribe', 'newsletter-signup',
            'paywall', 'login', 'signup', 'toolbar', 'breadcrumb'
        ]
        
        count = 0
        
        # 移除特定标签
        for tag_name in tags_to_remove:
            for tag in soup.find_all(tag_name):
                tag.decompose()
                count += 1
        
        # 移除包含特定关键词的元素（先收集再删除，避免遍历时修改）
        tags_to_delete = []
        
        for tag in soup.find_all(True):
            try:
                # 检查class属性
                if tag.has_attr('class') and tag.get('class'):
                    classes = ' '.join(tag['class']).lower()
                    if any(keyword in classes for keyword in keywords_to_remove):
                        tags_to_delete.append(tag)
                        continue
                
                # 检查id属性
                if tag.has_attr('id') and tag.get('id'):
                    tag_id = tag['id'].lower()
                    if any(keyword in tag_id for keyword in keywords_to_remove):
                        tags_to_delete.append(tag)
                        continue
                
                # 检查role属性
                if tag.has_attr('role') and tag.get('role'):
                    role = tag['role'].lower()
                    if role in ['navigation', 'banner', 'complementary', 'contentinfo']:
                        tags_to_delete.append(tag)
            except (AttributeError, TypeError):
                # 跳过有问题的标签
                continue
        
        # 删除收集到的标签
        for tag in tags_to_delete:
            try:
                tag.decompose()
                count += 1
            except:
                pass
        
        if count > 0:
            logger.debug(f"Removed {count} navigation/footer/sidebar elements")
    
    def _remove_metadata_elements(self, soup: BeautifulSoup) -> None:
        """移除head中的元数据和其他不需要的元素
        
        Args:
            soup: BeautifulSoup对象
        """
        count = 0
        
        # 移除head标签（保留title）
        head = soup.find('head')
        if head:
            # 保存title
            title = head.find('title')
            title_text = title.get_text() if title else None
            
            # 移除整个head
            head.decompose()
            count += 1
            
            # 如果有title，添加回去
            if title_text:
                new_head = soup.new_tag('head')
                new_title = soup.new_tag('title')
                new_title.string = title_text
                new_head.append(new_title)
                if soup.html:
                    soup.html.insert(0, new_head)
        
        # 移除noscript标签
        for tag in soup.find_all('noscript'):
            tag.decompose()
            count += 1
        
        # 移除iframe（通常是广告或嵌入内容）
        for tag in soup.find_all('iframe'):
            tag.decompose()
            count += 1
        
        # 移除form表单（通常是搜索框、订阅表单等）
        for tag in soup.find_all('form'):
            tag.decompose()
            count += 1
        
        # 移除button（通常是交互按钮）
        for tag in soup.find_all('button'):
            tag.decompose()
            count += 1
        
        if count > 0:
            logger.debug(f"Removed {count} metadata/form/iframe elements")
    
    def _remove_unnecessary_attributes(self, soup: BeautifulSoup) -> None:
        """移除不必要的HTML属性以减少token消耗
        
        Args:
            soup: BeautifulSoup对象
        """
        # 要保留的属性（白名单）
        keep_attributes = {'href', 'src', 'alt', 'title'}
        
        count = 0
        for tag in soup.find_all(True):
            # 获取所有属性
            attrs_to_remove = [attr for attr in tag.attrs if attr not in keep_attributes]
            
            # 移除不需要的属性
            for attr in attrs_to_remove:
                del tag[attr]
                count += 1
        
        if count > 0:
            logger.debug(f"Removed {count} unnecessary attributes")
    
    def _extract_main_content(self, soup: BeautifulSoup) -> None:
        """尝试提取主要内容区域
        
        Args:
            soup: BeautifulSoup对象
        """
        # 尝试找到主要内容区域
        main_content = None
        
        # 优先级1: <main>标签
        main_content = soup.find('main')
        
        # 优先级2: <article>标签
        if not main_content:
            main_content = soup.find('article')
        
        # 优先级3: role="main"
        if not main_content:
            main_content = soup.find(attrs={'role': 'main'})
        
        # 优先级4: 包含"content"、"article"、"post"等关键词的div
        if not main_content:
            for keyword in ['content', 'article', 'post', 'entry', 'main']:
                # 尝试通过class查找
                main_content = soup.find('div', class_=lambda x: x and keyword in x.lower())
                if main_content:
                    break
                
                # 尝试通过id查找
                main_content = soup.find('div', id=lambda x: x and keyword in x.lower())
                if main_content:
                    break
        
        # 如果找到主要内容区域，只保留这部分
        if main_content:
            logger.debug(f"Found main content area: {main_content.name}")
            
            # 创建新的body，只包含主要内容
            new_body = soup.new_tag('body')
            new_body.append(main_content.extract())
            
            # 替换原来的body
            if soup.body:
                soup.body.replace_with(new_body)
            else:
                if soup.html:
                    soup.html.append(new_body)
                else:
                    soup.append(new_body)
            
            logger.debug("Extracted main content area")
        else:
            logger.debug("No specific main content area found, keeping all body content")
    
    def _simplify_structure(self, soup: BeautifulSoup) -> None:
        """简化HTML结构，移除冗余的嵌套标签
        
        Args:
            soup: BeautifulSoup对象
        """
        # 移除picture标签，只保留img
        for picture in soup.find_all('picture'):
            img = picture.find('img')
            if img:
                picture.replace_with(img)
            else:
                picture.decompose()
        
        # 移除source标签
        for source in soup.find_all('source'):
            source.decompose()
        
        # 移除figure标签，保留内容
        for figure in soup.find_all('figure'):
            # 提取img和figcaption
            img = figure.find('img')
            figcaption = figure.find('figcaption')
            
            if img:
                # 如果有caption，将其作为img的title
                if figcaption and figcaption.get_text(strip=True):
                    img['title'] = figcaption.get_text(strip=True)
                figure.replace_with(img)
            else:
                figure.decompose()
        
        # 移除空的div和span
        for tag_name in ['div', 'span']:
            for tag in soup.find_all(tag_name):
                # 如果标签没有文本内容且没有img子元素，删除它
                if not tag.get_text(strip=True) and not tag.find('img'):
                    tag.decompose()
        
        logger.debug("Simplified HTML structure")
    
    def _extract_text_content(self, soup: BeautifulSoup) -> None:
        """提取纯文本内容，构建简化的HTML
        
        Args:
            soup: BeautifulSoup对象
        """
        # 只保留这些有意义的标签
        meaningful_tags = {
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',  # 标题
            'p', 'br',  # 段落
            'ul', 'ol', 'li',  # 列表
            'a',  # 链接
            'img',  # 图片
            'strong', 'em', 'b', 'i',  # 强调
            'code', 'pre',  # 代码
            'blockquote',  # 引用
            'table', 'tr', 'td', 'th', 'thead', 'tbody',  # 表格
        }
        
        # 遍历所有标签，将不在白名单中的标签替换为其内容
        for tag in soup.find_all(True):
            if tag.name not in meaningful_tags:
                # 如果是body或article，保留
                if tag.name in ['body', 'article', 'main', 'section']:
                    continue
                
                # 其他标签：提取内容并替换
                try:
                    tag.unwrap()
                except:
                    pass
        
        logger.debug("Extracted text content with meaningful tags only")
