"""Cookie Importer - 从多种格式导入 cookies"""
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from .models import Cookie

logger = logging.getLogger(__name__)


class CookieImporter:
    """Cookie 导入器，支持多种格式"""
    
    # YouTube 必需的认证字段
    REQUIRED_YOUTUBE_FIELDS = ['CONSENT', 'VISITOR_INFO1_LIVE', 'PREF']
    
    def import_from_netscape(self, file_path: Path) -> list[dict]:
        """
        从 Netscape cookies.txt 格式导入 cookies
        
        格式示例：
        # Netscape HTTP Cookie File
        .youtube.com    TRUE    /    TRUE    1735689600    CONSENT    YES+...
        
        Args:
            file_path: cookies.txt 文件路径
            
        Returns:
            Cookie 列表（字典格式）
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Cookie 文件不存在: {file_path}")
        
        cookies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # 跳过空行和注释行
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析 Netscape 格式
                    parts = line.split('\t')
                    
                    if len(parts) < 7:
                        logger.warning(f"第 {line_num} 行格式不正确，跳过: {line}")
                        continue
                    
                    try:
                        domain = parts[0]
                        # parts[1] 是 flag (TRUE/FALSE)
                        path = parts[2]
                        secure = parts[3].upper() == 'TRUE'
                        expires_str = parts[4]
                        name = parts[5]
                        value = parts[6]
                        
                        # 转换过期时间
                        expires = None
                        if expires_str and expires_str != '0':
                            try:
                                expires = float(expires_str)
                            except ValueError:
                                logger.warning(f"无效的过期时间: {expires_str}")
                        
                        cookie_dict = {
                            'name': name,
                            'value': value,
                            'domain': domain,
                            'path': path,
                            'expires': expires,
                            'secure': secure,
                            'httpOnly': False,  # Netscape 格式不包含此字段
                            'sameSite': None
                        }
                        
                        cookies.append(cookie_dict)
                    
                    except Exception as e:
                        logger.warning(f"解析第 {line_num} 行失败: {e}")
                        continue
            
            logger.info(f"从 Netscape 格式导入了 {len(cookies)} 个 cookies")
            return cookies
        
        except Exception as e:
            logger.error(f"读取 Netscape 格式文件失败: {e}")
            raise
    
    def import_from_json(self, file_path: Path) -> list[dict]:
        """
        从 JSON 格式导入 cookies
        
        支持两种格式：
        1. Playwright/Selenium 格式：直接是 cookie 数组
        2. 自定义格式：包含 cookies 和 metadata 的对象
        
        Args:
            file_path: JSON 文件路径
            
        Returns:
            Cookie 列表（字典格式）
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Cookie 文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 判断格式
            if isinstance(data, list):
                # Playwright/Selenium 格式：直接是数组
                cookies = data
            elif isinstance(data, dict) and 'cookies' in data:
                # 自定义格式：包含 cookies 字段
                cookies = data['cookies']
            else:
                raise ValueError("不支持的 JSON 格式")
            
            # 标准化字段名称
            standardized_cookies = []
            for cookie in cookies:
                standardized = self._standardize_cookie_fields(cookie)
                standardized_cookies.append(standardized)
            
            logger.info(f"从 JSON 格式导入了 {len(standardized_cookies)} 个 cookies")
            return standardized_cookies
        
        except json.JSONDecodeError as e:
            logger.error(f"解析 JSON 文件失败: {e}")
            raise
        except Exception as e:
            logger.error(f"读取 JSON 文件失败: {e}")
            raise
    
    def _standardize_cookie_fields(self, cookie: dict) -> dict:
        """
        标准化 cookie 字段名称
        
        不同工具导出的 JSON 可能使用不同的字段名：
        - Playwright: name, value, domain, path, expires, httpOnly, secure, sameSite
        - Selenium: name, value, domain, path, expiry, httpOnly, secure
        
        Args:
            cookie: 原始 cookie 字典
            
        Returns:
            标准化后的 cookie 字典
        """
        standardized = {
            'name': cookie.get('name', ''),
            'value': cookie.get('value', ''),
            'domain': cookie.get('domain', ''),
            'path': cookie.get('path', '/'),
            'httpOnly': cookie.get('httpOnly', False),
            'secure': cookie.get('secure', False),
            'sameSite': cookie.get('sameSite', None)
        }
        
        # 处理过期时间的不同字段名
        expires = cookie.get('expires') or cookie.get('expiry') or cookie.get('expirationDate')
        if expires:
            # 确保是浮点数
            try:
                standardized['expires'] = float(expires)
            except (ValueError, TypeError):
                standardized['expires'] = None
        else:
            standardized['expires'] = None
        
        return standardized
    
    def detect_format(self, file_path: Path) -> str:
        """
        自动检测文件格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            'netscape' 或 'json'
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            # 尝试读取第一行
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            
            # 检查是否是 JSON
            if first_line.startswith('{') or first_line.startswith('['):
                return 'json'
            
            # 检查是否是 Netscape 格式
            if first_line.startswith('#') or '\t' in first_line:
                return 'netscape'
            
            # 默认尝试 JSON
            return 'json'
        
        except Exception as e:
            logger.warning(f"检测文件格式失败: {e}，默认使用 JSON")
            return 'json'
    
    def validate_cookies(self, cookies: list[dict]) -> tuple[bool, str]:
        """
        验证导入的 cookies 是否有效
        
        检查：
        1. 是否包含 YouTube 域名的 cookies
        2. 是否包含必需的认证字段
        3. Cookie 格式是否正确
        
        Args:
            cookies: Cookie 列表
            
        Returns:
            (是否有效, 错误信息)
        """
        if not cookies:
            return False, "没有找到任何 cookies"
        
        # 检查是否有 YouTube 域名的 cookies
        youtube_cookies = [c for c in cookies if 'youtube.com' in c.get('domain', '')]
        
        if not youtube_cookies:
            return False, "没有找到 YouTube 域名的 cookies。请确保从已登录 YouTube 的浏览器导出 cookies。"
        
        # 检查必需的认证字段
        cookie_names = {c.get('name', '') for c in youtube_cookies}
        missing_fields = []
        
        for required_field in self.REQUIRED_YOUTUBE_FIELDS:
            if required_field not in cookie_names:
                missing_fields.append(required_field)
        
        if missing_fields:
            logger.warning(f"缺少推荐的认证字段: {', '.join(missing_fields)}")
            # 注意：这里只是警告，不阻止导入
            # 因为有些 cookies 可能仍然有效
        
        # 验证 cookie 格式
        invalid_cookies = []
        for i, cookie in enumerate(youtube_cookies):
            try:
                # 尝试创建 Cookie 对象验证格式
                Cookie(**cookie)
            except Exception as e:
                invalid_cookies.append(f"Cookie {i}: {str(e)}")
        
        if invalid_cookies:
            error_msg = "以下 cookies 格式不正确:\n" + "\n".join(invalid_cookies[:5])
            if len(invalid_cookies) > 5:
                error_msg += f"\n... 还有 {len(invalid_cookies) - 5} 个错误"
            return False, error_msg
        
        # 检查是否有过期的 cookies
        expired_count = 0
        for cookie_dict in youtube_cookies:
            try:
                cookie = Cookie(**cookie_dict)
                if cookie.is_expired():
                    expired_count += 1
            except Exception:
                pass
        
        if expired_count > 0:
            logger.warning(f"发现 {expired_count} 个已过期的 cookies")
        
        # 所有检查通过
        success_msg = f"成功验证 {len(youtube_cookies)} 个 YouTube cookies"
        if missing_fields:
            success_msg += f"（警告：缺少推荐字段 {', '.join(missing_fields)}）"
        
        return True, success_msg
    
    def import_cookies(self, file_path: Path, format: Optional[str] = None) -> tuple[list[dict], str]:
        """
        导入 cookies（自动检测格式或使用指定格式）
        
        Args:
            file_path: Cookie 文件路径
            format: 格式类型 ('netscape', 'json', None=自动检测)
            
        Returns:
            (Cookie 列表, 成功消息)
            
        Raises:
            ValueError: 如果 cookies 验证失败
        """
        # 检测格式
        if format is None:
            format = self.detect_format(file_path)
            logger.info(f"检测到文件格式: {format}")
        
        # 导入 cookies
        if format == 'netscape':
            cookies = self.import_from_netscape(file_path)
        elif format == 'json':
            cookies = self.import_from_json(file_path)
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        # 验证 cookies
        is_valid, message = self.validate_cookies(cookies)
        
        if not is_valid:
            raise ValueError(f"Cookie 验证失败: {message}")
        
        return cookies, message
