"""Authentication routes"""

import logging
import uuid
import base64
import hashlib
from typing import Set, Optional
from fastapi import APIRouter, HTTPException, Header

from reinvent_insight.core import config
from reinvent_insight.api.schemas.auth import LoginRequest, LoginResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["auth"])

# Session management
session_tokens: Set[str] = set()


def verify_token(authorization: str = None):
    """Dependency: Validate Bearer Token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或令牌缺失")
    token = authorization.split(" ", 1)[1]
    if token not in session_tokens:
        raise HTTPException(status_code=401, detail="令牌无效，请重新登录")
    return True


def get_current_user(authorization: Optional[str] = Header(None)):
    """依赖注入: 验证并返回当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或令牌缺失")
    token = authorization.split(" ", 1)[1]
    if token not in session_tokens:
        raise HTTPException(status_code=401, detail="令牌无效，请重新登录")
    return {"username": config.ADMIN_USERNAME}


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """验证用户名密码，返回简易 Bearer Token。"""
    if req.username == config.ADMIN_USERNAME and req.password == config.ADMIN_PASSWORD:
        raw = f"{req.username}:{req.password}:{uuid.uuid4()}".encode()
        token = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode()[:48]
        session_tokens.add(token)
        return LoginResponse(token=token)
    raise HTTPException(status_code=401, detail="用户名或密码错误")
