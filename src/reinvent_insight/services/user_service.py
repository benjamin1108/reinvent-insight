"""用户管理服务 - 基于 JSON 文件存储"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from reinvent_insight.core import config
from reinvent_insight.domain.models.user import User

logger = logging.getLogger(__name__)

# 用户数据存储路径
USERS_FILE = config.PROJECT_ROOT / "config" / "users.json"


class UserService:
    """用户管理服务"""
    
    def __init__(self):
        """初始化用户服务"""
        self._users: dict[str, User] = {}
        self._load_users()
        self._init_admin_user()
    
    def _load_users(self):
        """从文件加载用户数据"""
        if not USERS_FILE.exists():
            logger.info("用户数据文件不存在，将创建新文件")
            self._users = {}
            return
        
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._users = {
                    username: User.from_dict(user_data)
                    for username, user_data in data.items()
                }
            logger.info(f"成功加载 {len(self._users)} 个用户")
        except Exception as e:
            logger.error(f"加载用户数据失败: {e}")
            self._users = {}
    
    def _save_users(self):
        """保存用户数据到文件"""
        try:
            # 确保目录存在
            USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                username: user.to_dict()
                for username, user in self._users.items()
            }
            
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(self._users)} 个用户")
        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")
            raise
    
    def _init_admin_user(self):
        """初始化管理员用户（如果不存在）"""
        admin_username = config.ADMIN_USERNAME
        
        # 优先使用 ADMIN_PASSWORD_HASH，更安全
        if config.ADMIN_PASSWORD_HASH:
            admin_password_hash = config.ADMIN_PASSWORD_HASH
        else:
            # 回退到明文密码的哈希
            admin_password_hash = self._hash_password(config.ADMIN_PASSWORD)
        
        if admin_username not in self._users:
            admin_user = User(
                username=admin_username,
                password_hash=admin_password_hash,
                role="admin"
            )
            self._users[admin_username] = admin_user
            self._save_users()
            logger.info(f"初始化管理员用户: {admin_username}")
        else:
            # 如果 admin 已存在，检查是否需要更新密码哈希（当 .env 中的哈希变化时）
            existing_user = self._users[admin_username]
            if existing_user.password_hash != admin_password_hash:
                existing_user.password_hash = admin_password_hash
                self._save_users()
                logger.info(f"更新管理员密码: {admin_username}")
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, password: str, role: str = "user") -> User:
        """创建新用户"""
        if username in self._users:
            raise ValueError(f"用户已存在: {username}")
        
        if role not in ["admin", "user"]:
            raise ValueError(f"无效的角色: {role}")
        
        password_hash = self._hash_password(password)
        user = User(username=username, password_hash=password_hash, role=role)
        self._users[username] = user
        self._save_users()
        
        logger.info(f"创建用户成功: {username} (角色: {role})")
        return user
    
    def verify_user(self, username: str, password: str) -> Optional[User]:
        """验证用户名和密码"""
        user = self._users.get(username)
        if not user:
            return None
        
        password_hash = self._hash_password(password)
        if password_hash == user.password_hash:
            return user
        
        return None
    
    def get_user(self, username: str) -> Optional[User]:
        """获取用户信息"""
        return self._users.get(username)
    
    def list_users(self) -> List[dict]:
        """获取所有用户列表（不包含密码哈希）"""
        return [
            {
                "username": user.username,
                "role": user.role
            }
            for user in self._users.values()
        ]
    
    def get_all_users(self) -> List[User]:
        """获取所有用户对象列表"""
        return list(self._users.values())
    
    def delete_user(self, username: str) -> bool:
        """删除用户"""
        # 不允许删除管理员账户
        if username == config.ADMIN_USERNAME:
            raise ValueError(f"不允许删除管理员账户")
        
        if username not in self._users:
            raise ValueError(f"用户不存在: {username}")
        
        del self._users[username]
        self._save_users()
        logger.info(f"删除用户成功: {username}")
        return True
    
    def update_password(self, username: str, new_password: str) -> bool:
        """更新用户密码"""
        user = self._users.get(username)
        if not user:
            logger.warning(f"用户不存在: {username}")
            return False
        
        user.password_hash = self._hash_password(new_password)
        self._save_users()
        logger.info(f"更新密码成功: {username}")
        return True


# 全局单例
user_service = UserService()
