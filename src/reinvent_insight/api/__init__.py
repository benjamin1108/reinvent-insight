"""API模块 - 重构后的模块化API

该模块提供重构后的模块化API架构:
- api/schemas: Pydantic模型定义
- api/routes: 按功能拆分的路由模块
- api/app: 主FastAPI应用
"""

from reinvent_insight.api.app import app, serve

__all__ = ['app', 'serve']