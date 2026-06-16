import os
import json
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "companion.db")

_engine = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    url = os.environ.get("DATABASE_URL")
    if url:
        # Render 提供的 postgres:// 需要改成 postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _engine = create_async_engine(url, pool_pre_ping=True)
    else:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")
    return _engine


def _is_pg(engine):
    return engine.url.drivername.startswith("postgresql")


async def init_db():
    engine = get_engine()
    pg = _is_pg(engine)

    if pg:
        id_col = "id SERIAL PRIMARY KEY"
        insert_ignore = "INSERT INTO companion_profile (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
        insert_ignore_user = "INSERT INTO user_profile (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
    else:
        id_col = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        insert_ignore = "INSERT OR IGNORE INTO companion_profile (id) VALUES (1)"
        insert_ignore_user = "INSERT OR IGNORE INTO user_profile (id) VALUES (1)"

    async with engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS messages (
                {id_col},
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS memories (
                {id_col},
                session_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                mood_keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                nickname TEXT,
                preferences TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS companion_profile (
                id INTEGER PRIMARY KEY,
                nickname TEXT DEFAULT '小伴',
                personality_type TEXT DEFAULT 'warm',
                personality_desc TEXT,
                avatar_path TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text(insert_ignore))
        await conn.execute(text(insert_ignore_user))

        # 索引
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_session_role ON messages(session_id, role)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id)"))


# ========== 消息操作 ==========

async def create_session(session_id: str):
    engine = get_engine()
    pg = _is_pg(engine)
    sql = ("INSERT INTO sessions (id) VALUES (:sid) ON CONFLICT (id) DO NOTHING"
           if pg else
           "INSERT OR IGNORE INTO sessions (id) VALUES (:sid)")
    async with engine.begin() as conn:
        await conn.execute(text(sql), {"sid": session_id})


async def save_message(session_id: str, role: str, content: str):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO messages (session_id, role, content) VALUES (:sid, :role, :content)"),
            {"sid": session_id, "role": role, "content": content},
        )


async def get_recent_messages(session_id: str, limit: int = 20) -> list:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT role, content, created_at FROM messages WHERE session_id = :sid ORDER BY id DESC LIMIT :lim"),
            {"sid": session_id, "lim": limit},
        )
        rows = result.fetchall()
        return [{"role": r[0], "content": r[1], "created_at": str(r[2])} for r in reversed(rows)]


async def get_session_message_count(session_id: str) -> int:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM messages WHERE session_id = :sid"),
            {"sid": session_id},
        )
        return result.scalar()


async def get_session_messages(session_id: str) -> list:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT role, content, created_at FROM messages WHERE session_id = :sid ORDER BY id"),
            {"sid": session_id},
        )
        return [{"role": r[0], "content": r[1], "created_at": str(r[2])} for r in result.fetchall()]


async def delete_session(session_id: str):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM messages WHERE session_id = :sid"), {"sid": session_id})
        await conn.execute(text("DELETE FROM memories WHERE session_id = :sid"), {"sid": session_id})
        await conn.execute(text("DELETE FROM sessions WHERE id = :sid"), {"sid": session_id})


async def clear_all_messages():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM messages"))
        await conn.execute(text("DELETE FROM memories"))


async def get_sessions_list() -> list:
    """获取最近会话列表（含消息数、预览、最后消息时间）。"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT s.id, s.created_at,
              COUNT(m.id) as msg_count,
              MIN(CASE WHEN m.role = 'user' THEN m.content END) as preview,
              MAX(m.created_at) as last_message_at
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id, s.created_at
            HAVING COUNT(m.id) > 0
            ORDER BY s.created_at DESC LIMIT 30
        """))
        return [
            {
                "id": r[0],
                "last_message_at": str(r[4]) + "Z" if r[4] else "",
                "msg_count": r[2],
                "preview": r[3] or "",
            }
            for r in result.fetchall()
        ]


# ========== 记忆操作 ==========

async def save_memory(session_id: str, summary: str, mood_keywords: list):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO memories (session_id, summary, mood_keywords) VALUES (:sid, :sum, :mood)"),
            {"sid": session_id, "sum": summary, "mood": json.dumps(mood_keywords, ensure_ascii=False)},
        )


async def get_recent_memories(limit: int = 5) -> list:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT summary, mood_keywords, created_at FROM memories ORDER BY id DESC LIMIT :lim"),
            {"lim": limit},
        )
        return [
            {
                "summary": r[0],
                "mood_keywords": json.loads(r[1]) if r[1] else [],
                "created_at": str(r[2]),
            }
            for r in result.fetchall()
        ]


# ========== 用户画像 ==========

async def get_user_profile() -> dict:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT nickname, preferences FROM user_profile WHERE id = 1"))
        row = result.fetchone()
        if row:
            return {
                "nickname": row[0],
                "preferences": json.loads(row[1]) if row[1] else {},
            }
        return {"nickname": None, "preferences": {}}


async def update_user_profile(nickname: str = None, preferences: dict = None):
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT nickname, preferences FROM user_profile WHERE id = 1"))
        current = result.fetchone()
        new_nick = nickname if nickname is not None else (current[0] if current else None)
        new_prefs = json.dumps(preferences, ensure_ascii=False) if preferences is not None else (current[1] if current else None)
        await conn.execute(
            text("UPDATE user_profile SET nickname = :nick, preferences = :prefs, updated_at = :now WHERE id = 1"),
            {"nick": new_nick, "prefs": new_prefs, "now": datetime.now().isoformat()},
        )


# ========== 陪伴者配置 ==========

async def get_companion_profile() -> dict:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT nickname, personality_type, personality_desc, avatar_path FROM companion_profile WHERE id = 1")
        )
        row = result.fetchone()
        if row:
            return {
                "nickname": row[0],
                "personality_type": row[1],
                "personality_desc": row[2],
                "avatar_path": row[3],
            }
        return {"nickname": "小伴", "personality_type": "warm", "personality_desc": None, "avatar_path": None}


async def update_companion_profile(**kwargs):
    allowed = {"nickname", "personality_type", "personality_desc", "avatar_path"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return
    engine = get_engine()
    async with engine.begin() as conn:
        set_parts = ", ".join(f"{k} = :{k}" for k in updates)
        params = {**updates, "now": datetime.now().isoformat()}
        await conn.execute(
            text(f"UPDATE companion_profile SET {set_parts}, updated_at = :now WHERE id = 1"),
            params,
        )
