"""Authentication routes"""

import logging
import uuid
import base64
import hashlib
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Header, Depends

from reinvent_insight.core import config
from reinvent_insight.api.schemas.auth import LoginRequest, LoginResponse
from reinvent_insight.api.schemas.user import (
    RegisterRequest, UserResponse, UserListResponse, DeleteUserResponse
)
from reinvent_insight.services.user_service import user_service
from reinvent_insight.domain.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["auth"])

# Session management: token -> username
session_tokens: Dict[str, str] = {}


def verify_token(authorization: str = None):
    """Dependency: Validate Bearer Token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或令牌缺失")
    token = authorization.split(" ", 1)[1]
    if token not in session_tokens:
        raise HTTPException(status_code=401, detail="令牌无效，请重新登录")
    return True


def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """依赖注入: 验证并返回当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或令牌缺失")
    token = authorization.split(" ", 1)[1]
    if token not in session_tokens:
        raise HTTPException(status_code=401, detail="令牌无效,请重新登录")
    
    username = session_tokens[token]
    user = user_service.get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def verify_admin(current_user: User = Depends(get_current_user)) -> User:
    """依赖注入: 验证是否为管理员"""
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """验证用户名密码,返回 Bearer Token"""
    user = user_service.verify_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 生成 token
    raw = f"{req.username}:{req.password}:{uuid.uuid4()}".encode()
    token = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode()[:48]
    session_tokens[token] = req.username
    
    return LoginResponse(
        token=token,
        username=user.username,
        role=user.role
    )


@router.get("/api/auth/check-admin")
def check_admin(authorization: Optional[str] = Header(None)):
    """检查当前用户是否为管理员"""
    try:
        user = get_current_user(authorization)
        return {"is_admin": user.is_admin()}
    except HTTPException:
        return {"is_admin": False}


@router.get("/api/auth/verify")
def verify_token_endpoint(authorization: Optional[str] = Header(None)):
    """验证 token 是否有效（用于前端启动时检查）"""
    if not authorization or not authorization.startswith("Bearer "):
        return {"valid": False, "reason": "missing_token"}
    
    token = authorization.split(" ", 1)[1]
    if token not in session_tokens:
        return {"valid": False, "reason": "invalid_token"}
    
    # Token 有效，返回用户信息
    username = session_tokens[token]
    user = user_service.get_user(username)
    if not user:
        return {"valid": False, "reason": "user_not_found"}
    
    return {
        "valid": True,
        "username": user.username,
        "role": user.role
    }


# ==================== 用户管理 API ====================

@router.post("/api/auth/register", response_model=UserResponse)
def register_user(
    req: RegisterRequest,
    admin: User = Depends(verify_admin)
):
    """注册新用户(仅管理员可调用)"""
    try:
        user = user_service.create_user(
            username=req.username,
            password=req.password,
            role=req.role
        )
        return UserResponse(
            username=user.username,
            role=user.role,
            created_at=user.created_at.isoformat(),
            is_active=user.is_active
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/auth/users", response_model=UserListResponse)
def get_users(admin: User = Depends(verify_admin)):
    """获取所有用户列表(仅管理员可调用)"""
    users = user_service.get_all_users()
    return UserListResponse(
        users=[
            UserResponse(
                username=u.username,
                role=u.role,
                created_at=u.created_at.isoformat(),
                is_active=u.is_active
            )
            for u in users
        ],
        total=len(users)
    )


@router.delete("/api/auth/users/{username}", response_model=DeleteUserResponse)
def delete_user(
    username: str,
    admin: User = Depends(verify_admin)
):
    """删除指定用户(仅管理员可调用)"""
    try:
        user_service.delete_user(username)
        
        # 删除该用户的所有 session token
        tokens_to_remove = [token for token, user in session_tokens.items() if user == username]
        for token in tokens_to_remove:
            del session_tokens[token]
        
        return DeleteUserResponse(
            success=True,
            message=f"用户 {username} 已删除"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
