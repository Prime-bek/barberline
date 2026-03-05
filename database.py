import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import config

class Database:
    def __init__(self):
        self.db_path = config.DB_PATH
        self._pool = None

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    language TEXT DEFAULT 'ru',
                    reminder_minutes INTEGER DEFAULT 30,
                    registration_date TEXT,
                    last_activity TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    time TEXT,
                    phone TEXT,
                    status TEXT DEFAULT 'pending',
                    reject_reason TEXT,
                    created_at TEXT,
                    completed_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS masters (
                    id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    added_by INTEGER,
                    added_at TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            await db.commit()

    async def add_user(self, user_id: int, full_name: str, username: Optional[str], language: str = "ru"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users 
                (id, full_name, username, language, registration_date, last_activity, status)
                VALUES (?, ?, ?, ?, COALESCE((SELECT registration_date FROM users WHERE id = ?), ?), ?, 'active')
            """, (user_id, full_name, username, language, user_id, now, now))
            await db.commit()

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_user_language(self, user_id: int, language: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
            await db.commit()

    async def update_reminder_minutes(self, user_id: int, minutes: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET reminder_minutes = ? WHERE id = ?", (minutes, user_id))
            await db.commit()

    async def add_booking(self, user_id: int, date: str, time: str, phone: str) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO bookings (user_id, date, time, phone, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (user_id, date, time, phone, now))
            await db.commit()
            return cursor.lastrowid

    async def get_booking(self, booking_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT b.*, u.full_name, u.language 
                FROM bookings b 
                JOIN users u ON b.user_id = u.id 
                WHERE b.id = ?
            """, (booking_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_booking_status(self, booking_id: int, status: str, reject_reason: Optional[str] = None):
        async with aiosqlite.connect(self.db_path) as db:
            if reject_reason:
                await db.execute("UPDATE bookings SET status = ?, reject_reason = ? WHERE id = ?", 
                               (status, reject_reason, booking_id))
            else:
                await db.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
            await db.commit()

    async def complete_booking(self, booking_id: int, early: bool = False):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "completed_early" if early else "completed"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE bookings SET status = ?, completed_at = ? WHERE id = ?", 
                           (status, now, booking_id))
            await db.commit()

    async def cancel_booking(self, booking_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
            await db.commit()

    async def has_active_booking(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE user_id = ? AND status IN ('pending', 'approved')
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] > 0

    async def is_time_busy(self, date: str, time: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE date = ? AND time = ? AND status IN ('pending', 'approved')
            """, (date, time)) as cursor:
                row = await cursor.fetchone()
                return row[0] > 0

    async def get_user_active_booking(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM bookings 
                WHERE user_id = ? AND status IN ('pending', 'approved')
                ORDER BY id DESC LIMIT 1
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_bookings(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_master_bookings(self, status: Optional[str] = None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                async with db.execute("""
                    SELECT b.*, u.full_name 
                    FROM bookings b 
                    JOIN users u ON b.user_id = u.id 
                    WHERE b.status = ? ORDER BY b.date, b.time
                """, (status,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
            else:
                async with db.execute("""
                    SELECT b.*, u.full_name 
                    FROM bookings b 
                    JOIN users u ON b.user_id = u.id 
                    WHERE b.status IN ('pending', 'approved') ORDER BY b.date, b.time
                """) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]

    async def get_bookings_by_date(self, date: str, status: Optional[str] = None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT b.*, u.full_name FROM bookings b JOIN users u ON b.user_id = u.id WHERE b.date = ?"
            params = [date]
            if status:
                query += " AND b.status = ?"
                params.append(status)
            query += " ORDER BY b.time"
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_users(self, limit: int = 10, offset: int = 0):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users ORDER BY registration_date DESC LIMIT ? OFFSET ?", 
                                (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_bookings(self, limit: int = 10, offset: int = 0):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT b.*, u.full_name, u.username 
                FROM bookings b 
                JOIN users u ON b.user_id = u.id 
                ORDER BY b.created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_approved_bookings(self):
        """Для восстановления напоминаний при перезапуске"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT b.*, u.reminder_minutes, u.language
                FROM bookings b 
                JOIN users u ON b.user_id = u.id 
                WHERE b.status = 'approved'
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_statistics(self):
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                stats['total_users'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM bookings") as cursor:
                stats['total_bookings'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'approved'") as cursor:
                stats['approved'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'pending'") as cursor:
                stats['pending'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'rejected'") as cursor:
                stats['rejected'] = (await cursor.fetchone())[0]
            return stats

    async def add_master(self, master_id: int, full_name: str, username: Optional[str], added_by: int) -> bool:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO masters (id, full_name, username, added_by, added_at, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (master_id, full_name, username, added_by, now))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    async def remove_master(self, master_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM masters WHERE id = ?", (master_id,))
            await db.commit()
            return True

    async def get_master(self, master_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM masters WHERE id = ? AND is_active = 1", (master_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_masters(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM masters WHERE is_active = 1 ORDER BY added_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def is_master(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM masters WHERE id = ? AND is_active = 1", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] > 0

db = Database()