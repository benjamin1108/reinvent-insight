"""请求日志中间件 - 添加请求追踪"""

import uuid
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from reinvent_insight.core.logger import request_id_var

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 - 添加请求追踪"""
    
    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        
        # 设置上下文
        token = request_id_var.set(request_id)
        
        # 记录请求开始
        start_time = time.perf_counter()
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算耗时
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # 记录请求完成（跳过静态资源）
            if not self._is_static_path(request.url.path):
                # 添加状态码语义
                status_names = {
                    200: "OK", 201: "Created", 204: "No Content",
                    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
                    500: "Internal Error", 502: "Bad Gateway", 503: "Service Unavailable"
                }
                status_name = status_names.get(response.status_code, "")
                
                logger.info(
                    f"{request.method} {request.url.path} → "
                    f"{response.status_code} {status_name} | {duration_ms:.0f}ms"
                )
            
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"{request.method} {request.url.path} → ERROR | {duration_ms:.0f}ms: {str(e)[:100]}"
            )
            raise
        finally:
            request_id_var.reset(token)
    
    @staticmethod
    def _is_static_path(path: str) -> bool:
        """判断是否为静态资源路径"""
        static_prefixes = ('/js/', '/css/', '/fonts/', '/components/', '/utils/')
        static_suffixes = ('.js', '.css', '.png', '.jpg', '.ico', '.woff', '.woff2')
        return (
            any(path.startswith(p) for p in static_prefixes) or
            any(path.endswith(s) for s in static_suffixes)
        )
