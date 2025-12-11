"""Authentication schemas"""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response schema"""
    token: str
    username: str
    role: str


class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户信息响应"""
    username: str
    role: str
