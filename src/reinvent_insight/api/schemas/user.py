"""用户相关 API Schema"""

from pydantic import BaseModel, Field
from typing import Literal, Optional


class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    role: Literal["admin", "user"] = Field(default="user", description="角色")


class UserResponse(BaseModel):
    """用户信息响应"""
    username: str
    role: str
    created_at: str
    is_active: bool


class UserListResponse(BaseModel):
    """用户列表响应"""
    users: list[UserResponse]
    total: int


class DeleteUserResponse(BaseModel):
    """删除用户响应"""
    success: bool
    message: str
