#!/usr/bin/env python3
"""设置 admin 密码的 CLI 工具

将密码哈希后保存到 .env 文件，更安全地存储密码
"""

import hashlib
import sys
import getpass
from pathlib import Path


def hash_password(password: str) -> str:
    """计算密码的 SHA-256 哈希值"""
    return hashlib.sha256(password.encode()).hexdigest()


def update_env_file(env_path: Path, key: str, value: str) -> bool:
    """更新 .env 文件中的指定键值"""
    lines = []
    key_found = False
    
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找并更新已有的键
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(f'{key}=') or stripped.startswith(f'{key} ='):
                lines[i] = f'{key}={value}\n'
                key_found = True
                break
    
    # 如果键不存在，添加新行
    if not key_found:
        # 确保最后一行有换行符
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines.append(f'{key}={value}\n')
    
    # 写入文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True


def main():
    # 查找项目根目录
    # 从当前目录向上查找包含 .env 或 .env.example 的目录
    current = Path.cwd()
    project_root = None
    
    for parent in [current] + list(current.parents):
        if (parent / '.env').exists() or (parent / '.env.example').exists():
            project_root = parent
            break
    
    if not project_root:
        # 尝试从脚本位置推断
        script_path = Path(__file__).resolve()
        project_root = script_path.parent.parent.parent.parent.parent
    
    env_path = project_root / '.env'
    
    print("=" * 50)
    print("Admin 密码配置工具")
    print("=" * 50)
    print(f"\n.env 文件路径: {env_path}")
    
    # 获取密码输入
    print("\n请输入新的 admin 密码:")
    password = getpass.getpass("密码: ")
    
    if not password:
        print("\n❌ 密码不能为空")
        sys.exit(1)
    
    if len(password) < 6:
        print("\n❌ 密码至少需要 6 个字符")
        sys.exit(1)
    
    # 确认密码
    confirm = getpass.getpass("确认密码: ")
    
    if password != confirm:
        print("\n❌ 两次输入的密码不一致")
        sys.exit(1)
    
    # 计算哈希
    password_hash = hash_password(password)
    
    # 更新 .env 文件
    try:
        update_env_file(env_path, 'ADMIN_PASSWORD_HASH', password_hash)
        print(f"\n✅ 密码哈希已保存到 .env 文件")
        print(f"   ADMIN_PASSWORD_HASH={password_hash[:16]}...")
        print("\n⚠️  请重启服务以使新密码生效")
    except Exception as e:
        print(f"\n❌ 保存失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
