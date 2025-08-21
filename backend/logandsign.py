# logandsign.py
"""
用户登录注册模块
提供用户认证、注册、登录等功能
"""

import hashlib
import secrets
import jwt
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path


class UserAuthManager:
    """用户认证管理器"""
    
    def __init__(self, db_path: str = "chat_history.db", secret_key: str = None):
        self.db_path = db_path
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        
    async def initialize(self) -> bool:
        """初始化用户表"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 创建用户表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        last_login TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        profile_data TEXT DEFAULT '{}'
                    )
                """)
                
                # 创建用户会话表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # 创建索引
                await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
                
                await db.commit()
                print("✅ 用户认证数据库初始化成功")
                return True
                
        except Exception as e:
            print(f"❌ 用户认证数据库初始化失败: {e}")
            return False
    
    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """密码加密"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        ).hex()
        
        return password_hash, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == password_hash
    
    def _generate_jwt_token(self, user_id: int, username: str) -> str:
        """生成JWT令牌"""
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(days=7),  # 7天过期
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def _verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """用户注册"""
        try:
            # 验证输入
            if not username or len(username) < 3:
                return {"success": False, "message": "用户名至少需要3个字符"}
            
            if not email or '@' not in email:
                return {"success": False, "message": "请输入有效的邮箱地址"}
            
            if not password or len(password) < 6:
                return {"success": False, "message": "密码至少需要6个字符"}
            
            async with aiosqlite.connect(self.db_path) as db:
                # 检查用户名是否已存在
                cursor = await db.execute(
                    "SELECT id FROM users WHERE username = ? OR email = ?",
                    (username, email)
                )
                existing_user = await cursor.fetchone()
                
                if existing_user:
                    return {"success": False, "message": "用户名或邮箱已存在"}
                
                # 加密密码
                password_hash, salt = self._hash_password(password)
                
                # 插入新用户
                cursor = await db.execute("""
                    INSERT INTO users (username, email, password_hash, salt, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    username, email, password_hash, salt, datetime.now().isoformat()
                ))
                
                user_id = cursor.lastrowid
                await db.commit()
                
                print(f"✅ 用户注册成功: {username} (ID: {user_id})")
                return {
                    "success": True,
                    "message": "注册成功",
                    "user_id": user_id,
                    "username": username
                }
                
        except Exception as e:
            print(f"❌ 用户注册失败: {e}")
            return {"success": False, "message": f"注册失败: {str(e)}"}
    
    async def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 查找用户
                cursor = await db.execute("""
                    SELECT id, username, email, password_hash, salt, is_active
                    FROM users WHERE username = ? OR email = ?
                """, (username, username))
                
                user = await cursor.fetchone()
                
                if not user:
                    return {"success": False, "message": "用户名或密码错误"}
                
                user_id, db_username, email, password_hash, salt, is_active = user
                
                if not is_active:
                    return {"success": False, "message": "账户已被禁用"}
                
                # 验证密码
                if not self._verify_password(password, password_hash, salt):
                    return {"success": False, "message": "用户名或密码错误"}
                
                # 生成JWT令牌
                token = self._generate_jwt_token(user_id, db_username)
                
                # 更新最后登录时间
                await db.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                
                # 创建会话记录
                await db.execute("""
                    INSERT INTO user_sessions (user_id, session_token, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    user_id, token,
                    datetime.now().isoformat(),
                    (datetime.now() + timedelta(days=7)).isoformat()
                ))
                
                await db.commit()
                
                print(f"✅ 用户登录成功: {db_username} (ID: {user_id})")
                return {
                    "success": True,
                    "message": "登录成功",
                    "token": token,
                    "user": {
                        "id": user_id,
                        "username": db_username,
                        "email": email
                    }
                }
                
        except Exception as e:
            print(f"❌ 用户登录失败: {e}")
            return {"success": False, "message": f"登录失败: {str(e)}"}
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证用户令牌"""
        try:
            # 验证JWT令牌
            payload = self._verify_jwt_token(token)
            if not payload:
                return None
            
            async with aiosqlite.connect(self.db_path) as db:
                # 检查会话是否存在且有效
                cursor = await db.execute("""
                    SELECT us.id, us.user_id, u.username, u.email, u.is_active
                    FROM user_sessions us
                    JOIN users u ON us.user_id = u.id
                    WHERE us.session_token = ? AND us.is_active = 1 AND us.expires_at > ?
                """, (token, datetime.now().isoformat()))
                
                session = await cursor.fetchone()
                
                if not session:
                    return None
                
                session_id, user_id, username, email, is_active = session
                
                if not is_active:
                    return None
                
                return {
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                    "session_id": session_id
                }
                
        except Exception as e:
            print(f"❌ 令牌验证失败: {e}")
            return None
    
    async def logout_user(self, token: str) -> bool:
        """用户登出"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 禁用会话
                await db.execute(
                    "UPDATE user_sessions SET is_active = 0 WHERE session_token = ?",
                    (token,)
                )
                await db.commit()
                
                print(f"✅ 用户登出成功")
                return True
                
        except Exception as e:
            print(f"❌ 用户登出失败: {e}")
            return False
    
    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT id, username, email, created_at, last_login, profile_data
                    FROM users WHERE id = ? AND is_active = 1
                """, (user_id,))
                
                user = await cursor.fetchone()
                
                if not user:
                    return None
                
                user_id, username, email, created_at, last_login, profile_data = user
                
                return {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "created_at": created_at,
                    "last_login": last_login,
                    "profile_data": profile_data
                }
                
        except Exception as e:
            print(f"❌ 获取用户信息失败: {e}")
            return None
    
    async def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM user_sessions WHERE expires_at < ?",
                    (datetime.now().isoformat(),)
                )
                
                deleted_count = cursor.rowcount
                await db.commit()
                
                if deleted_count > 0:
                    print(f"🧹 清理了 {deleted_count} 个过期会话")
                
                return deleted_count
                
        except Exception as e:
            print(f"❌ 清理过期会话失败: {e}")
            return 0