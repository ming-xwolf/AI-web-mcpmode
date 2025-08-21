# database.py
"""
SQLite数据库管理
存储聊天记录：用户问题、MCP工具返回内容、AI回复
"""

import os
import json
import aiosqlite
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import hashlib
import secrets
import jwt
from datetime import timedelta


class ChatDatabase:
    """聊天记录数据库管理类"""
    
    def __init__(self, db_path: str = "chat_history.db", secret_key: str = None):
        """初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认为当前目录下的chat_history.db
            secret_key: JWT密钥，用于用户认证
        """
        # 确保使用绝对路径
        if not os.path.isabs(db_path):
            db_path = Path(__file__).parent / db_path
        
        self.db_path = str(db_path)
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        print(f"📁 数据库路径: {self.db_path}")
    
    async def initialize(self):
        """初始化数据库表结构"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 创建聊天会话表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建聊天记录表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS chat_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT DEFAULT 'default',
                        conversation_id INTEGER,
                        msid INTEGER,
                        
                        -- 用户输入
                        user_input TEXT,
                        user_timestamp TIMESTAMP,
                        
                        -- MCP工具相关
                        mcp_tools_called TEXT,  -- JSON格式存储调用的工具信息
                        mcp_results TEXT,       -- JSON格式存储工具返回结果
                        
                        -- AI回复
                        ai_response TEXT,
                        ai_timestamp TIMESTAMP,
                        
                        -- 元数据
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                    )
                """)
                # 兼容旧库：尝试补充 msid 列
                try:
                    await db.execute("ALTER TABLE chat_records ADD COLUMN msid INTEGER")
                except Exception:
                    pass
                
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
                
                # 创建索引以提高查询性能
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_records_session 
                    ON chat_records(session_id)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_records_msid 
                    ON chat_records(msid)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_records_conversation 
                    ON chat_records(conversation_id)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_records_created 
                    ON chat_records(created_at)
                """)
                
                # 用户表索引
                await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
                
                await db.commit()
                print("✅ 数据库表结构初始化完成")
                return True
                
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            return False
    
    async def start_conversation(self, session_id: str = "default") -> int:
        """开始新的对话，返回conversation_id"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 确保session存在
                await db.execute("""
                    INSERT OR IGNORE INTO chat_sessions (session_id) VALUES (?)
                """, (session_id,))
                
                # 获取下一个conversation_id
                cursor = await db.execute("""
                    SELECT COALESCE(MAX(conversation_id), 0) + 1 
                    FROM chat_records WHERE session_id = ?
                """, (session_id,))
                conversation_id = (await cursor.fetchone())[0]
                
                await db.commit()
                return conversation_id
                
        except Exception as e:
            print(f"❌ 开始对话失败: {e}")
            return 1  # 默认返回1
    
    async def save_conversation(
        self, 
        user_input: str,
        mcp_tools_called: List[Dict[str, Any]] = None,
        mcp_results: List[Dict[str, Any]] = None,
        ai_response: str = "",
        session_id: str = "default",
        conversation_id: int = None,
        msid: int = None,
    ) -> bool:
        """保存完整的对话记录
        
        Args:
            user_input: 用户输入的问题
            mcp_tools_called: 调用的MCP工具列表
            mcp_results: MCP工具返回的结果列表
            ai_response: AI的回复内容
            session_id: 会话ID
            conversation_id: 对话ID，如果为None则自动生成
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if conversation_id is None:
                    conversation_id = await self.start_conversation(session_id)
                
                # 将工具调用和结果转换为JSON
                mcp_tools_json = json.dumps(mcp_tools_called or [], ensure_ascii=False)
                mcp_results_json = json.dumps(mcp_results or [], ensure_ascii=False)
                
                await db.execute("""
                    INSERT INTO chat_records (
                        session_id, conversation_id, msid,
                        user_input, user_timestamp,
                        mcp_tools_called, mcp_results,
                        ai_response, ai_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, conversation_id, msid,
                    user_input, datetime.now().isoformat(),
                    mcp_tools_json, mcp_results_json,
                    ai_response, datetime.now().isoformat()
                ))
                
                await db.commit()
                print(f"💾 对话记录已保存 (session={session_id}, conversation={conversation_id})")
                return True
                
        except Exception as e:
            print(f"❌ 保存对话记录失败: {e}")
            return False

    async def get_threads_by_msid(self, msid: int, limit: int = 100) -> List[Dict[str, Any]]:
        """按 msid 返回线程列表（每个线程对应一组 session_id+conversation_id）。"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT session_id, conversation_id,
                           MIN(created_at) AS first_time,
                           MAX(created_at) AS last_time,
                           COUNT(*) AS message_count,
                           COALESCE(
                               (SELECT user_input FROM chat_records cr2 
                                WHERE cr2.session_id = cr.session_id AND cr2.conversation_id = cr.conversation_id 
                                ORDER BY cr2.created_at ASC LIMIT 1),
                               ''
                           ) AS first_user_input
                    FROM chat_records cr
                    WHERE msid = ?
                    GROUP BY session_id, conversation_id
                    ORDER BY last_time DESC
                    LIMIT ?
                    """,
                    (msid, limit),
                )
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ 获取线程列表失败: {e}")
            return []
    
    async def get_chat_history(
        self, 
        session_id: str = "default", 
        limit: int = 50,
        conversation_id: int = None
    ) -> List[Dict[str, Any]]:
        """获取聊天历史记录
        
        Args:
            session_id: 会话ID
            limit: 返回记录数量限制
            conversation_id: 特定对话ID，如果指定则只返回该对话
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if conversation_id is not None:
                    # 获取特定对话
                    cursor = await db.execute("""
                        SELECT * FROM chat_records 
                        WHERE session_id = ? AND conversation_id = ?
                        ORDER BY created_at ASC
                    """, (session_id, conversation_id))
                else:
                    # 获取最近的对话记录
                    cursor = await db.execute("""
                        SELECT * FROM (
                            SELECT * FROM chat_records 
                            WHERE session_id = ?
                            ORDER BY created_at DESC 
                            LIMIT ?
                        ) ORDER BY created_at ASC
                    """, (session_id, limit))
                
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                records = []
                for row in rows:
                    record = dict(zip(columns, row))
                    
                    # 解析JSON字段
                    try:
                        record['mcp_tools_called'] = json.loads(record['mcp_tools_called'] or '[]')
                        record['mcp_results'] = json.loads(record['mcp_results'] or '[]')
                    except json.JSONDecodeError:
                        record['mcp_tools_called'] = []
                        record['mcp_results'] = []
                    
                    records.append(record)
                
                # 如果不是特定对话，需要反转顺序（最新的在前面）
                if conversation_id is None:
                    records.reverse()
                
                return records
                
        except Exception as e:
            print(f"❌ 获取聊天历史失败: {e}")
            return []
    
    async def clear_history(self, session_id: str = "default") -> bool:
        """清空指定会话的聊天历史"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM chat_records WHERE session_id = ?
                """, (session_id,))
                
                await db.execute("""
                    DELETE FROM chat_sessions WHERE session_id = ?
                """, (session_id,))
                
                await db.commit()
                print(f"🗑️ 已清空会话 {session_id} 的聊天历史")
                return True
                
        except Exception as e:
            print(f"❌ 清空聊天历史失败: {e}")
            return False

    async def delete_conversation(self, session_id: str, conversation_id: int) -> bool:
        """删除指定会话中的某个对话线程"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM chat_records WHERE session_id = ? AND conversation_id = ?",
                    (session_id, conversation_id),
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"❌ 删除对话线程失败: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 总记录数
                cursor = await db.execute("SELECT COUNT(*) FROM chat_records")
                total_records = (await cursor.fetchone())[0]
                
                # 会话数
                cursor = await db.execute("SELECT COUNT(DISTINCT session_id) FROM chat_records")
                total_sessions = (await cursor.fetchone())[0]
                
                # 对话数
                cursor = await db.execute("SELECT COUNT(DISTINCT conversation_id) FROM chat_records")
                total_conversations = (await cursor.fetchone())[0]
                
                # 最近记录时间
                cursor = await db.execute("SELECT MAX(created_at) FROM chat_records")
                latest_record = (await cursor.fetchone())[0]
                
                return {
                    "total_records": total_records,
                    "total_sessions": total_sessions,
                    "total_conversations": total_conversations,
                    "latest_record": latest_record,
                    "database_path": self.db_path
                }
                
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {}
    
    async def close(self):
        """关闭数据库连接（在aiosqlite中不需要显式关闭）"""
        pass
    
    # 用户认证相关方法
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