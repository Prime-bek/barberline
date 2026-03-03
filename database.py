import sqlite3
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import config

class Database:
    def __init__(self):
        self.db_path = config.DB_PATH

    async def init(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    language TEXT DEFAULT 'ru',
                    city TEXT,
                    reminder_minutes INTEGER DEFAULT 30,
                    registration_date TEXT,
                    last_activity TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Таблица броней
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
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Таблица мастеров
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

    async def add_user(self, user_id: int, full_name: str, username: Optional[str], 
                      language: str = "ru") -> None:
        """Добавить или обновить пользователя"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users 
                (id, full_name, username, language, registration_date, last_activity, status)
                VALUES (?, ?, ?, ?, COALESCE((SELECT registration_date FROM users WHERE id = ?), ?), ?, 'active')
            """, (user_id, full_name, username, language, user_id, now, now))
            await db.commit()

    async def update_user_activity(self, user_id: int) -> None:
        """Обновить время последней активности"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET last_activity = ? WHERE id = ?",
                (now, user_id)
            )
            await db.commit()

    async def update_user_city(self, user_id: int, city: str) -> None:
        """Обновить город пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET city = ? WHERE id = ?",
                (city, user_id)
            )
            await db.commit()

    async def update_user_language(self, user_id: int, language: str) -> None:
        """Обновить язык пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET language = ? WHERE id = ?",
                (language, user_id)
            )
            await db.commit()

    async def update_reminder_minutes(self, user_id: int, minutes: int) -> None:
        """Обновить время напоминания"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET reminder_minutes = ? WHERE id = ?",
                (minutes, user_id)
            )
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def add_booking(self, user_id: int, date: str, time: str, phone: str) -> int:
        """Добавить бронь"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO bookings (user_id, date, time, phone, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (user_id, date, time, phone, now))
            await db.commit()
            return cursor.lastrowid

    async def update_booking_status(self, booking_id: int, status: str, 
                                   reject_reason: Optional[str] = None) -> None:
        """Обновить статус брони"""
        async with aiosqlite.connect(self.db_path) as db:
            if reject_reason:
                await db.execute("""
                    UPDATE bookings SET status = ?, reject_reason = ? WHERE id = ?
                """, (status, reject_reason, booking_id))
            else:
                await db.execute("""
                    UPDATE bookings SET status = ? WHERE id = ?
                """, (status, booking_id))
            await db.commit()

    async def get_booking(self, booking_id: int) -> Optional[Dict[str, Any]]:
        """Получить бронь по ID"""
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

    async def get_user_bookings(self, user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получить брони пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM bookings WHERE user_id = ?"
            params = [user_id]
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY date, time"
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def has_active_booking(self, user_id: int) -> bool:
        """Проверить есть ли активная бронь"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE user_id = ? AND status IN ('pending', 'approved')
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] > 0

    async def is_time_busy(self, date: str, time: str) -> bool:
        """Проверить занято ли время"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE date = ? AND time = ? AND status IN ('pending', 'approved')
            """, (date, time)) as cursor:
                row = await cursor.fetchone()
                return row[0] > 0

    async def get_bookings_by_date(self, date: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получить брони на дату"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT b.*, u.full_name 
                FROM bookings b 
                JOIN users u ON b.user_id = u.id 
                WHERE b.date = ?
            """
            params = [date]
            if status:
                query += " AND b.status = ?"
                params.append(status)
            query += " ORDER BY b.time"
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_users(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить всех пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users 
                ORDER BY registration_date DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_bookings(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить все брони"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT b.*, u.full_name, u.username 
                FROM bookings b 
                JOIN users u ON b.user_id = u.id 
                ORDER BY b.created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_statistics(self) -> Dict[str, int]:
        """Получить статистику"""
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

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С МАСТЕРАМИ =====

    async def add_master(self, master_id: int, full_name: str, username: Optional[str], added_by: int) -> bool:
        """Добавить мастера"""
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
            print(f"Error adding master: {e}")
            return False

    async def remove_master(self, master_id: int) -> bool:
        """Удалить мастера"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM masters WHERE id = ?", (master_id,))
            await db.commit()
            return True

    async def get_master(self, master_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные мастера"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM masters WHERE id = ? AND is_active = 1", (master_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_masters(self) -> List[Dict[str, Any]]:
        """Получить всех активных мастеров"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM masters WHERE is_active = 1 ORDER BY added_at DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def is_master(self, user_id: int) -> bool:
        """Проверить является ли пользователь мастером"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM masters WHERE id = ? AND is_active = 1
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] > 0

    async def toggle_master_status(self, master_id: int, is_active: bool) -> None:
        """Включить/выключить мастера"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE masters SET is_active = ? WHERE id = ?
            """, (1 if is_active else 0, master_id))
            await db.commit()

db = Database()