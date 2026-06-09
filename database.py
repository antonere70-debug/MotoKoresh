import aiosqlite
import time
from config import MEMORY_RETENTION_HOURS

DB_NAME = "alphavods_memory.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, nickname TEXT, bike TEXT
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, lat REAL, lon REAL, type TEXT
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS chat_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            chat_id INTEGER, 
            user_id INTEGER, 
            text TEXT,
            timestamp REAL
        )''')
        await db.commit()
    await cleanup_old_context()

async def cleanup_old_context():
    async with aiosqlite.connect(DB_NAME) as db:
        cutoff_time = time.time() - (MEMORY_RETENTION_HOURS * 3600)
        await db.execute("DELETE FROM chat_context WHERE timestamp < ?", (cutoff_time,))
        await db.commit()

async def save_user(user_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_user_field(user_id, field, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

async def save_context(chat_id, user_id, text):
    async with aiosqlite.connect(DB_NAME) as db:
        current_time = time.time()
        await db.execute(
            "INSERT INTO chat_context (chat_id, user_id, text, timestamp) VALUES (?, ?, ?, ?)", 
            (chat_id, user_id, text, current_time)
        )
        cutoff_time = current_time - (MEMORY_RETENTION_HOURS * 3600)
        await db.execute("""
            DELETE FROM chat_context 
            WHERE timestamp < ? 
            OR id NOT IN (SELECT id FROM chat_context ORDER BY id DESC LIMIT 50)
        """, (cutoff_time,))
        await db.commit()

async def get_context(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cutoff_time = time.time() - (MEMORY_RETENTION_HOURS * 3600)
        async with db.execute("""
            SELECT u.nickname, c.text 
            FROM chat_context c 
            LEFT JOIN users u ON c.user_id = u.user_id 
            WHERE c.chat_id = ? AND c.timestamp > ?
            ORDER BY c.id DESC LIMIT 10
        """, (chat_id, cutoff_time)) as cursor:
            rows = await cursor.fetchall()
            return "\n".join([f"{row[0] or 'Неизвестный'}: {row[1]}" for row in reversed(rows)])

async def save_place(name, lat, lon, type_place):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO places (name, lat, lon, type) VALUES (?, ?, ?, ?)", (name, lat, lon, type_place))
        await db.commit()

async def get_all_places():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT name, lat, lon, type FROM places") as cursor:
            return await cursor.fetchall()
