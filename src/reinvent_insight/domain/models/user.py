"""用户数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class User:
    """用户模型"""
    username: str
    password_hash: str
    role: Literal["admin", "user"]
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def to_dict(self):
        """转换为字典"""
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建用户"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            role=data.get("role", "user"),
            created_at=created_at,
            is_active=data.get("is_active", True)
        )
    
    def is_admin(self) -> bool:
        """判断是否为管理员"""
        return self.role == "admin"
