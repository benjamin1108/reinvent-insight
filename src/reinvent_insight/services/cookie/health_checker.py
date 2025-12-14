"""Cookie Health Check - 检查 Cookie Manager 服务和 cookies 状态"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import os

from reinvent_insight.core import config

logger = logging.getLogger(__name__)


class CookieHealthCheck:
    """Cookie 健康检查器"""
    
    def __init__(self, cookie_file: Optional[Path] = None):
        """
        初始化健康检查器
        
        Args:
            cookie_file: Cookie 文件路径，默认使用配置中的路径
        """
        self.cookie_file = cookie_file or config.COOKIES_FILE
        self.warning_threshold_hours = 12  # 超过12小时发出警告
        self.critical_threshold_hours = 24  # 超过24小时视为严重
    
    def check_service_status(self) -> Dict[str, Any]:
        """
        检查 Cookie Manager 服务状态
        
        Returns:
            服务状态字典
        """
        try:
            from .manager_service import get_service_status
            status = get_service_status()
            
            return {
                'available': True,
                'running': status.get('is_running', False),
                'details': status
            }
        except ImportError as e:
            # 导入失败通常意味着依赖问题，记录 warning
            logger.warning(f"无法导入 Cookie Manager 服务模块: {e}")
            return {
                'available': False,
                'running': False,
                'error': f"ImportError: {e}"
            }
        except Exception as e:
            logger.warning(f"检查 Cookie Manager 服务状态时出错: {e}")
            return {
                'available': False,
                'running': False,
                'error': str(e)
            }
    
    def check_cookie_file(self) -> Dict[str, Any]:
        """
        检查 cookie 文件状态
        
        Returns:
            文件状态字典
        """
        if not self.cookie_file.exists():
            return {
                'exists': False,
                'status': 'missing',
                'message': 'Cookie 文件不存在'
            }
        
        try:
            # 检查文件大小
            file_size = os.path.getsize(self.cookie_file)
            if file_size == 0:
                return {
                    'exists': True,
                    'status': 'empty',
                    'message': 'Cookie 文件为空'
                }
            
            # 检查文件修改时间
            mtime = datetime.fromtimestamp(os.path.getmtime(self.cookie_file))
            age = datetime.now() - mtime
            age_hours = age.total_seconds() / 3600
            
            # 判断新鲜度
            if age_hours > self.critical_threshold_hours:
                status = 'critical'
                message = f'Cookie 文件已严重过期 ({age_hours:.1f} 小时)'
            elif age_hours > self.warning_threshold_hours:
                status = 'warning'
                message = f'Cookie 文件接近过期 ({age_hours:.1f} 小时)'
            else:
                status = 'fresh'
                message = f'Cookie 文件新鲜 ({age_hours:.1f} 小时)'
            
            return {
                'exists': True,
                'status': status,
                'message': message,
                'size': file_size,
                'age_hours': age_hours,
                'last_modified': mtime.isoformat()
            }
        
        except Exception as e:
            return {
                'exists': True,
                'status': 'error',
                'message': f'检查文件时出错: {str(e)}'
            }
    
    def check_cookie_content(self) -> Dict[str, Any]:
        """
        检查 cookie 文件内容
        
        Returns:
            内容检查结果
        """
        if not self.cookie_file.exists():
            return {
                'valid': False,
                'message': 'Cookie 文件不存在'
            }
        
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含 YouTube cookies
            has_youtube = 'youtube.com' in content
            has_google = 'google.com' in content
            
            # 统计 cookie 行数（排除注释和空行）
            cookie_lines = [
                line for line in content.split('\n')
                if line.strip() and not line.startswith('#')
            ]
            cookie_count = len(cookie_lines)
            
            if not has_youtube and not has_google:
                return {
                    'valid': False,
                    'message': 'Cookie 文件不包含 YouTube/Google cookies',
                    'cookie_count': cookie_count
                }
            
            if cookie_count < 5:
                return {
                    'valid': False,
                    'message': f'Cookie 数量过少 ({cookie_count} 个)',
                    'cookie_count': cookie_count
                }
            
            return {
                'valid': True,
                'message': f'Cookie 文件有效 ({cookie_count} 个 cookies)',
                'cookie_count': cookie_count,
                'has_youtube': has_youtube,
                'has_google': has_google
            }
        
        except Exception as e:
            return {
                'valid': False,
                'message': f'读取文件时出错: {str(e)}'
            }
    
    def perform_full_check(self) -> Dict[str, Any]:
        """
        执行完整的健康检查
        
        Returns:
            完整的健康检查结果
        """
        service_status = self.check_service_status()
        file_status = self.check_cookie_file()
        content_status = self.check_cookie_content()
        
        # 判断整体健康状态
        overall_status = 'healthy'
        issues = []
        warnings = []
        
        # 检查服务状态
        if not service_status['running']:
            warnings.append('Cookie Manager 服务未运行')
            overall_status = 'degraded'
        
        # 检查文件状态
        if file_status['status'] == 'missing':
            issues.append('Cookie 文件不存在')
            overall_status = 'unhealthy'
        elif file_status['status'] == 'empty':
            issues.append('Cookie 文件为空')
            overall_status = 'unhealthy'
        elif file_status['status'] == 'critical':
            issues.append(file_status['message'])
            overall_status = 'unhealthy'
        elif file_status['status'] == 'warning':
            warnings.append(file_status['message'])
            if overall_status == 'healthy':
                overall_status = 'degraded'
        
        # 检查内容状态
        if not content_status['valid']:
            issues.append(content_status['message'])
            overall_status = 'unhealthy'
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'service': service_status,
            'file': file_status,
            'content': content_status,
            'issues': issues,
            'warnings': warnings
        }
    
    def get_recommendations(self, check_result: Dict[str, Any]) -> list[str]:
        """
        根据检查结果提供建议
        
        Args:
            check_result: 健康检查结果
            
        Returns:
            建议列表
        """
        recommendations = []
        
        # 服务未运行
        if not check_result['service']['running']:
            recommendations.append(
                "启动 Cookie Manager 服务: "
                "reinvent-insight cookie-manager start --daemon"
            )
        
        # Cookie 文件不存在
        if check_result['file']['status'] == 'missing':
            recommendations.append(
                "导入 cookies: "
                "reinvent-insight cookie-manager import-cookies cookies.txt"
            )
        
        # Cookie 文件过期
        if check_result['file']['status'] in ['warning', 'critical']:
            recommendations.append(
                "手动刷新 cookies: "
                "reinvent-insight cookie-manager refresh"
            )
        
        # Cookie 内容无效
        if not check_result['content']['valid']:
            recommendations.append(
                "重新导入有效的 cookies 文件"
            )
        
        return recommendations
    
    def print_status_report(self, check_result: Optional[Dict[str, Any]] = None):
        """
        打印状态报告
        
        Args:
            check_result: 健康检查结果，如果为 None 则执行新的检查
        """
        if check_result is None:
            check_result = self.perform_full_check()
        
        # 状态图标
        status_icons = {
            'healthy': '✅',
            'degraded': '⚠️',
            'unhealthy': '❌'
        }
        
        overall_status = check_result['overall_status']
        icon = status_icons.get(overall_status, '❓')
        
        print(f"\n{icon} Cookie 健康状态: {overall_status.upper()}")
        print("=" * 60)
        
        # 服务状态
        service = check_result['service']
        service_icon = '✅' if service['running'] else '❌'
        print(f"\n{service_icon} Cookie Manager 服务: {'运行中' if service['running'] else '未运行'}")
        
        # 文件状态
        file_status = check_result['file']
        if file_status['exists']:
            file_icon = '✅' if file_status['status'] == 'fresh' else '⚠️' if file_status['status'] == 'warning' else '❌'
            print(f"{file_icon} Cookie 文件: {file_status['message']}")
        else:
            print(f"❌ Cookie 文件: 不存在")
        
        # 内容状态
        content = check_result['content']
        content_icon = '✅' if content['valid'] else '❌'
        print(f"{content_icon} Cookie 内容: {content['message']}")
        
        # 问题和警告
        if check_result['issues']:
            print("\n❌ 问题:")
            for issue in check_result['issues']:
                print(f"  - {issue}")
        
        if check_result['warnings']:
            print("\n⚠️  警告:")
            for warning in check_result['warnings']:
                print(f"  - {warning}")
        
        # 建议
        recommendations = self.get_recommendations(check_result)
        if recommendations:
            print("\n💡 建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("=" * 60)


def ensure_fresh_cookies() -> bool:
    """
    确保 cookies 是新鲜的（便捷函数）
    
    Returns:
        True 如果 cookies 可用且新鲜
    """
    checker = CookieHealthCheck()
    result = checker.perform_full_check()
    
    if result['overall_status'] == 'unhealthy':
        logger.error("Cookie 状态不健康，可能影响下载功能")
        checker.print_status_report(result)
        return False
    
    if result['overall_status'] == 'degraded':
        logger.warning("Cookie 状态降级，建议检查")
        # 不阻止操作，只是警告
    
    return True


def check_and_warn() -> None:
    """
    检查并在需要时发出警告（用于主程序启动时）
    """
    checker = CookieHealthCheck()
    result = checker.perform_full_check()
    
    if result['overall_status'] != 'healthy':
        logger.warning("Cookie 健康检查发现问题")
        
        # 在日志中记录详细信息
        for issue in result['issues']:
            logger.error(f"Cookie 问题: {issue}")
        
        for warning in result['warnings']:
            logger.warning(f"Cookie 警告: {warning}")
        
        # 提供建议
        recommendations = checker.get_recommendations(result)
        if recommendations:
            logger.info("建议采取以下措施:")
            for rec in recommendations:
                logger.info(f"  - {rec}")
