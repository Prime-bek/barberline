import asyncio
import logging
import os
import re
import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

# ============ CONFIG ============
@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "1265652628"))
    DB_PATH: str = "barbershop.db"
    TIMEZONE: str = "Asia/Tashkent"

config = Config()

# ============ TEXTS ============
TEXTS = {
    "ru": {
        "welcome": "Добро пожаловать в мужской салон ✂️\n\nВыберите действие:",
        "choose_language": "🌐 Выберите язык:",
        "choose_city": "🌍 Введите ваш город:",
        "choose_date": "📅 Выберите дату:",
        "choose_time": "⏰ Выберите время:",
        "enter_name": "✏️ Введите ваше имя:",
        "enter_phone": "📱 Введите номер телефона:",
        "choose_reminder": "🔔 Выберите за сколько минут напомнить:",
        "booking_sent": "⏳ Ваша заявка отправлена мастеру. Ожидайте подтверждения.",
        "approved": "✅ Ваша бронь подтверждена!\n\n📅 Дата: {date}\n⏰ Время: {time}",
        "rejected": "❌ Ваша бронь отклонена.\n\nПричина: {reason}",
        "reminder": "🔔 Напоминание! У вас запись сегодня в {time}",
        "queue_title": "📋 Записи на {date}:",
        "queue_empty": "На эту дату пока нет записей.",
        "no_access": "⛔ У вас нет доступа.",
        "invalid_phone": "❌ Неверный формат телефона.",
        "time_busy": "❌ Это время уже занято.",
        "already_booked": "❌ У вас уже есть активная бронь.",
        "new_booking_master": "🔔 Новая заявка!\n\n👤 Имя: {name}\n📱 Телефон: {phone}\n📅 Дата: {date}\n⏰ Время: {time}",
        "enter_reject_reason": "❌ Введите причину отказа:",
        "booking_rejected_master": "❌ Бронь отклонена.",
        "booking_approved_master": "✅ Бронь подтверждена!",
        "admin_menu": "🔧 Админ панель",
        "masters_management": "👨‍💼 Управление мастерами",
        "add_master": "➕ Добавить мастера",
        "remove_master": "➖ Удалить мастера",
        "list_masters": "📋 Список мастеров",
        "enter_master_id": "🆔 Введите ID пользователя:",
        "master_added": "✅ Мастер добавлен!\n\n👤 {name}\n🆔 ID: {id}",
        "master_removed": "✅ Мастер удалён!",
        "master_not_found": "❌ Мастер не найден.",
        "user_not_found": "❌ Пользователь не найден.",
        "master_already_exists": "⚠️ Уже является мастером.",
        "no_masters": "❌ Нет мастеров.",
        "masters_list": "👨‍💼 Мастера:\n\n",
        "master_info": "{num}. {name} (ID: {id})\n",
        "select_master_to_remove": "Выберите мастера для удаления:",
        "not_master": "⛔ Вы не мастер.",
        "users": "👥 Пользователи",
        "bookings": "📋 Брони",
        "statistics": "📊 Статистика",
        "back": "🔙 Назад",
        "main_menu": "📱 Главное меню",
        "my_bookings": "📋 Мои записи",
        "book": "📅 Записаться",
        "queue": "👥 Кто до меня?",
        "settings": "⚙️ Настройки",
        "admin_panel": "🔧 Админ панель",
        "minutes_10": "10 минут",
        "minutes_25": "25 минут",
        "minutes_30": "30 минут",
        "accept": "✅ Принять",
        "reject": "❌ Отклонить",
        "next": "➡️",
        "prev": "⬅️",
        "active": "Активен",
        "inactive": "Неактивен",
    },
    "uz": {
        "welcome": "Erkaklar saloniga xush kelibsiz ✂️",
        "choose_language": "🌐 Tilni tanlang:",
        "choose_city": "🌍 Shahringizni kiriting:",
        "choose_date": "📅 Sanani tanlang:",
        "choose_time": "⏰ Vaqtni tanlang:",
        "enter_name": "✏️ Ismingizni kiriting:",
        "enter_phone": "📱 Telefon raqamingizni kiriting:",
        "choose_reminder": "🔔 Eslatma uchun necha daqiqa:",
        "booking_sent": "⏳ Buyurtmangiz ustaga yuborildi.",
        "approved": "✅ Broningiz tasdiqlandi!\n\n📅 Sana: {date}\n⏰ Vaqt: {time}",
        "rejected": "❌ Broningiz rad etildi.\n\nSabab: {reason}",
        "reminder": "🔔 Eslatma! Bugun soat {time} da yozuvingiz bor",
        "queue_title": "📋 {date} uchun yozuvlar:",
        "queue_empty": "Bu sana uchun hali yozuvlar yo'q.",
        "no_access": "⛔ Ruxsatingiz yo'q.",
        "invalid_phone": "❌ Telefon raqami noto'g'ri.",
        "time_busy": "❌ Bu vaqt band.",
        "already_booked": "❌ Sizda allaqachon faol bron mavjud.",
        "new_booking_master": "🔔 Yangi so'rov!\n\n👤 Ism: {name}\n📱 Telefon: {phone}\n📅 Sana: {date}\n⏰ Vaqt: {time}",
        "enter_reject_reason": "❌ Rad etish sababini kiriting:",
        "booking_rejected_master": "❌ Bron rad etildi.",
        "booking_approved_master": "✅ Bron tasdiqlandi!",
        "admin_menu": "🔧 Admin panel",
        "masters_management": "👨‍💼 Ustalar boshqaruvi",
        "add_master": "➕ Usta qo'shish",
        "remove_master": "➖ Usta o'chirish",
        "list_masters": "📋 Ustalar ro'yxati",
        "enter_master_id": "🆔 Foydalanuvchi ID sini kiriting:",
        "master_added": "✅ Usta qo'shildi!\n\n👤 {name}\n🆔 ID: {id}",
        "master_removed": "✅ Usta o'chirildi!",
        "master_not_found": "❌ Usta topilmadi.",
        "user_not_found": "❌ Foydalanuvchi topilmadi.",
        "master_already_exists": "⚠️ Allaqachon usta.",
        "no_masters": "❌ Ustalar yo'q.",
        "masters_list": "👨‍💼 Ustalar:\n\n",
        "master_info": "{num}. {name} (ID: {id})\n",
        "select_master_to_remove": "O'chirish uchun ustani tanlang:",
        "not_master": "⛔ Siz usta emassiz.",
        "users": "👥 Foydalanuvchilar",
        "bookings": "📋 Bronlar",
        "statistics": "📊 Statistika",
        "back": "🔙 Orqaga",
        "main_menu": "📱 Asosiy menyu",
        "my_bookings": "📋 Mening yozuvlarim",
        "book": "📅 Yozilish",
        "queue": "👥 Menden oldin kim?",
        "settings": "⚙️ Sozlamalar",
        "admin_panel": "🔧 Admin panel",
        "minutes_10": "10 daqiqa",
        "minutes_25": "25 daqiqa",
        "minutes_30": "30 daqiqa",
        "accept": "✅ Qabul qilish",
        "reject": "❌ Rad etish",
        "next": "➡️",
        "prev": "⬅️",
        "active": "Faol",
        "inactive": "Faol emas",
    }
}

def get_text(key: str, lang: str = "ru", **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    return text

# ============ DATABASE ============
class Database:
    def __init__(self):
        self.db_path = config.DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
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
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    time TEXT,
                    phone TEXT,
                    status TEXT DEFAULT 'pending',
                    reject_reason TEXT,
                    created_at TEXT
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

    async def update_user_city(self, user_id: int, city: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET city = ? WHERE id = ?", (city, user_id))
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

    async def get_user_bookings(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM bookings WHERE user_id = ? ORDER BY date, time
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_users(self, limit: int = 10, offset: int = 0):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users ORDER BY registration_date DESC LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
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
            print(f"Error adding master: {e}")
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

# ============ KEYBOARDS ============
def language_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🇷🇺 Русский")
    builder.button(text="🇺🇿 O'zbekcha")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def main_menu_kb(lang: str = "ru", is_admin: bool = False):
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text("book", lang))
    builder.button(text=get_text("my_bookings", lang))
    builder.button(text=get_text("queue", lang))
    builder.button(text=get_text("settings", lang))
    if is_admin:
        builder.button(text=get_text("admin_panel", lang))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def reminder_kb(lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text("minutes_10", lang))
    builder.button(text=get_text("minutes_25", lang))
    builder.button(text=get_text("minutes_30", lang))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def back_kb(lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text("back", lang))
    return builder.as_markup(resize_keyboard=True)

def generate_dates_kb(dates: list, lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    for date in dates:
        builder.button(text=date)
    builder.button(text=get_text("back", lang))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def generate_times_kb(times: list, lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    for time in times:
        builder.button(text=time)
    builder.button(text=get_text("back", lang))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)

def master_booking_kb(booking_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"accept_{booking_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{booking_id}")
    builder.adjust(2)
    return builder.as_markup()

def admin_menu_kb(lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("users", lang), callback_data="admin_users_0")
    builder.button(text=get_text("bookings", lang), callback_data="admin_bookings_0")
    builder.button(text=get_text("statistics", lang), callback_data="admin_stats")
    builder.button(text=get_text("masters_management", lang)[:20], callback_data="admin_masters_menu")
    builder.adjust(2, 2)
    return builder.as_markup()

def masters_menu_kb(lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("add_master", lang), callback_data="master_add")
    builder.button(text=get_text("remove_master", lang), callback_data="master_remove_list")
    builder.button(text=get_text("list_masters", lang), callback_data="master_list")
    builder.button(text=get_text("back", lang), callback_data="admin_back")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def master_remove_kb(masters: list, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    for master in masters:
        name = master['full_name'] or f"ID: {master['id']}"
        builder.button(text=f"❌ {name[:20]}", callback_data=f"master_del_{master['id']}")
    builder.button(text=get_text("back", lang), callback_data="admin_masters_menu")
    builder.adjust(1)
    return builder.as_markup()

def confirm_remove_master_kb(master_id: int, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("remove_master", lang), callback_data=f"master_confirm_del_{master_id}")
    builder.button(text=get_text("back", lang), callback_data="master_remove_list")
    return builder.as_markup()

def pagination_kb(current_page: int, total_pages: int, prefix: str, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton(text=get_text("prev", lang), callback_data=f"{prefix}_{current_page - 1}"))
    buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text=get_text("next", lang), callback_data=f"{prefix}_{current_page + 1}"))
    builder.row(*buttons)
    builder.button(text=get_text("back", lang), callback_data="admin_back")
    return builder.as_markup()

# ============ MIDDLEWARE ============
class LanguageMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = await db.get_user(event.from_user.id)
        if user:
            data['language'] = user.get('language', 'ru')
        else:
            data['language'] = 'ru'
        return await handler(event, data)

# ============ SERVICES ============
scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
bot_instance: Bot = None

def set_bot(bot: Bot):
    global bot_instance
    bot_instance = bot

async def send_reminder(user_id: int, booking_id: int, time: str, lang: str):
    if not bot_instance:
        return
    try:
        text = get_text("reminder", lang, time=time)
        await bot_instance.send_message(user_id, text)
    except Exception as e:
        print(f"Error sending reminder: {e}")

async def notify_user_approved(user_id: int, date: str, time: str, lang: str):
    if not bot_instance:
        return
    try:
        text = get_text("approved", lang, date=date, time=time)
        await bot_instance.send_message(user_id, text)
    except Exception as e:
        print(f"Error notifying user: {e}")

async def notify_user_rejected(user_id: int, reason: str, lang: str):
    if not bot_instance:
        return
    try:
        text = get_text("rejected", lang, reason=reason)
        await bot_instance.send_message(user_id, text)
    except Exception as e:
        print(f"Error notifying user: {e}")

async def send_booking_to_masters(booking_id: int, name: str, phone: str, date: str, time: str):
    if not bot_instance:
        return
    try:
        text = get_text("new_booking_master", "ru", name=name, phone=phone, date=date, time=time)
        masters = await db.get_all_masters()
        
        if not masters:
            await bot_instance.send_message(config.ADMIN_ID, "⚠️ Нет мастеров!\n\n" + text, reply_markup=master_booking_kb(booking_id))
            return
        
        for master in masters:
            try:
                await bot_instance.send_message(master['id'], text, reply_markup=master_booking_kb(booking_id))
            except Exception as e:
                print(f"Could not send to master {master['id']}: {e}")
    except Exception as e:
        print(f"Error sending booking: {e}")

async def notify_new_master(master_id: int):
    if not bot_instance:
        return
    try:
        await bot_instance.send_message(master_id, "✅ Вам назначены права мастера!")
    except Exception as e:
        print(f"Could not notify master: {e}")

async def notify_master_removed(master_id: int):
    if not bot_instance:
        return
    try:
        await bot_instance.send_message(master_id, "❌ Ваши права мастера отозваны.")
    except Exception as e:
        print(f"Could not notify master: {e}")

async def schedule_reminder(booking_id: int):
    booking = await db.get_booking(booking_id)
    if not booking or booking['status'] != 'approved':
        return
    user = await db.get_user(booking['user_id'])
    if not user:
        return
    
    date_str = booking['date']
    time_str = booking['time']
    reminder_minutes = user['reminder_minutes']
    
    booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    reminder_datetime = booking_datetime - timedelta(minutes=reminder_minutes)
    
    if reminder_datetime <= datetime.now():
        return
    
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=reminder_datetime),
        args=[booking['user_id'], booking_id, time_str, user['language']],
        id=f"reminder_{booking_id}",
        replace_existing=True
    )

def init_scheduler():
    scheduler.start()

# ============ STATES ============
class BookingStates(StatesGroup):
    waiting_city = State()
    waiting_date = State()
    waiting_time = State()
    waiting_name = State()
    waiting_phone = State()
    waiting_reminder = State()

class MasterStates(StatesGroup):
    waiting_reject_reason = State()

class MasterManagementStates(StatesGroup):
    waiting_master_id = State()

# ============ HANDLERS ============
start_router = Router()
booking_router = Router()
master_router = Router()
admin_router = Router()
settings_router = Router()
masters_router = Router()

# Start handlers
@start_router.message(Command("start"))
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await db.add_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
        await message.answer(get_text("choose_language"), reply_markup=language_kb())
    else:
        is_admin = message.from_user.id == config.ADMIN_ID
        await message.answer(get_text("welcome", user['language']), reply_markup=main_menu_kb(user['language'], is_admin))

@start_router.message(F.text.in_(["🇷🇺 Русский", "🇺🇿 O'zbekcha"]))
async def set_language(message: Message):
    lang = "ru" if "Русский" in message.text else "uz"
    await db.update_user_language(message.from_user.id, lang)
    is_admin = message.from_user.id == config.ADMIN_ID
    await message.answer(get_text("welcome", lang), reply_markup=main_menu_kb(lang, is_admin))

# Booking handlers
def generate_available_dates():
    dates = []
    today = datetime.now()
    for i in range(14):
        date = today + timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
    return dates

def generate_available_times():
    return [f"{hour:02d}:00" for hour in range(9, 19)]

def validate_phone(phone: str) -> bool:
    return bool(re.match(r'^\+?[\d\s\-\(\)]{9,15}$', phone))

@booking_router.message(F.text.in_(["📅 Записаться", "📅 Yozilish"]))
async def start_booking(message: Message, state: FSMContext, language: str):
    if await db.has_active_booking(message.from_user.id):
        await message.answer(get_text("already_booked", language))
        return
    await state.set_state(BookingStates.waiting_city)
    await message.answer(get_text("choose_city", language), reply_markup=back_kb(language))

@booking_router.message(BookingStates.waiting_city)
async def process_city(message: Message, state: FSMContext, language: str):
    if message.text == get_text("back", language):
        await state.clear()
        is_admin = message.from_user.id == config.ADMIN_ID
        await message.answer(get_text("main_menu", language), reply_markup=main_menu_kb(language, is_admin))
        return
    await state.update_data(city=message.text)
    await db.update_user_city(message.from_user.id, message.text)
    dates = generate_available_dates()
    await state.set_state(BookingStates.waiting_date)
    await message.answer(get_text("choose_date", language), reply_markup=generate_dates_kb(dates, language))

@booking_router.message(BookingStates.waiting_date)
async def process_date(message: Message, state: FSMContext, language: str):
    if message.text == get_text("back", language):
        await state.set_state(BookingStates.waiting_city)
        await message.answer(get_text("choose_city", language), reply_markup=back_kb(language))
        return
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        await state.update_data(date=message.text)
        times = generate_available_times()
        await state.set_state(BookingStates.waiting_time)
        await message.answer(get_text("choose_time", language), reply_markup=generate_times_kb(times, language))
    except ValueError:
        await message.answer("❌ Неверный формат даты")

@booking_router.message(BookingStates.waiting_time)
async def process_time(message: Message, state: FSMContext, language: str):
    if message.text == get_text("back", language):
        dates = generate_available_dates()
        await state.set_state(BookingStates.waiting_date)
        await message.answer(get_text("choose_date", language), reply_markup=generate_dates_kb(dates, language))
        return
    data = await state.get_data()
    if await db.is_time_busy(data.get('date'), message.text):
        await message.answer(get_text("time_busy", language))
        return
    await state.update_data(time=message.text)
    await state.set_state(BookingStates.waiting_name)
    await message.answer(get_text("enter_name", language))

@booking_router.message(BookingStates.waiting_name)
async def process_name(message: Message, state: FSMContext, language: str):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_phone)
    await message.answer(get_text("enter_phone", language))

@booking_router.message(BookingStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext, language: str):
    if not validate_phone(message.text):
        await message.answer(get_text("invalid_phone", language))
        return
    await state.update_data(phone=message.text)
    await state.set_state(BookingStates.waiting_reminder)
    await message.answer(get_text("choose_reminder", language), reply_markup=reminder_kb(language))

@booking_router.message(BookingStates.waiting_reminder)
async def process_reminder(message: Message, state: FSMContext, language: str):
    reminder_map = {"10 минут": 10, "10 daqiqa": 10, "25 минут": 25, "25 daqiqa": 25, "30 минут": 30, "30 daqiqa": 30}
    minutes = reminder_map.get(message.text, 30)
    await db.update_reminder_minutes(message.from_user.id, minutes)
    data = await state.get_data()
    booking_id = await db.add_booking(message.from_user.id, data['date'], data['time'], data['phone'])
    await send_booking_to_masters(booking_id, data['name'], data['phone'], data['date'], data['time'])
    await state.clear()
    is_admin = message.from_user.id == config.ADMIN_ID
    await message.answer(get_text("booking_sent", language), reply_markup=main_menu_kb(language, is_admin))

# Master handlers
@master_router.callback_query(F.data.startswith("accept_"))
async def accept_booking(callback: CallbackQuery):
    if not await db.is_master(callback.from_user.id):
        await callback.answer(get_text("not_master", "ru"))
        return
    booking_id = int(callback.data.split("_")[1])
    booking = await db.get_booking(booking_id)
    if not booking or booking['status'] != 'pending':
        await callback.answer("Уже обработано")
        return
    await db.update_booking_status(booking_id, "approved")
    await schedule_reminder(booking_id)
    await notify_user_approved(booking['user_id'], booking['date'], booking['time'], booking['language'])
    await callback.message.edit_text(callback.message.text + "\n\n✅ ПРИНЯТО")
    await callback.answer("Подтверждено")

@master_router.callback_query(F.data.startswith("reject_"))
async def reject_booking_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_master(callback.from_user.id):
        await callback.answer(get_text("not_master", "ru"))
        return
    booking_id = int(callback.data.split("_")[1])
    await state.update_data(booking_id=booking_id)
    await state.set_state(MasterStates.waiting_reject_reason)
    await callback.message.answer(get_text("enter_reject_reason", "ru"))
    await callback.answer()

@master_router.message(MasterStates.waiting_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    booking = await db.get_booking(data['booking_id'])
    if not booking:
        await message.answer("Бронь не найдена")
        await state.clear()
        return
    await db.update_booking_status(data['booking_id'], "rejected", message.text)
    await notify_user_rejected(booking['user_id'], message.text, booking['language'])
    await message.answer(get_text("booking_rejected_master", "ru"))
    await state.clear()

# Admin handlers
def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID

@admin_router.message(F.text.in_(["🔧 Админ панель", "🔧 Admin panel"]))
async def admin_panel(message: Message, language: str):
    if not is_admin(message.from_user.id):
        await message.answer(get_text("no_access", language))
        return
    await message.answer(get_text("admin_menu", language), reply_markup=admin_menu_kb(language))

@admin_router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, language: str):
    await callback.message.edit_text(get_text("admin_menu", language), reply_markup=admin_menu_kb(language))

@admin_router.callback_query(F.data.startswith("admin_users_"))
async def show_users(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return
    page = int(callback.data.split("_")[2])
    users = await db.get_all_users(limit=5, offset=page * 5)
    if not users:
        await callback.answer("Нет пользователей")
        return
    stats = await db.get_statistics()
    total_pages = max(1, (stats['total_users'] + 4) // 5)
    text = get_text("users", language) + f" (стр. {page+1}):\n\n"
    for user in users:
        text += f"👤 {user['full_name']} (ID: {user['id']})\n@{user['username'] or 'нет'}\n\n"
    await callback.message.edit_text(text, reply_markup=pagination_kb(page, total_pages, "admin_users", language))

@admin_router.callback_query(F.data.startswith("admin_bookings_"))
async def show_bookings(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return
    page = int(callback.data.split("_")[2])
    bookings = await db.get_all_bookings(limit=5, offset=page * 5)
    if not bookings:
        await callback.answer("Нет броней")
        return
    stats = await db.get_statistics()
    total_pages = max(1, (stats['total_bookings'] + 4) // 5)
    text = get_text("bookings", language) + f" (стр. {page+1}):\n\n"
    for b in bookings:
        emoji = {'pending': '⏳', 'approved': '✅', 'rejected': '❌'}.get(b['status'], '❓')
        text += f"{emoji} {b['full_name']} - {b['date']} {b['time']}\n"
    await callback.message.edit_text(text, reply_markup=pagination_kb(page, total_pages, "admin_bookings", language))

@admin_router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return
    stats = await db.get_statistics()
    text = f"""📊 Статистика:
👥 Пользователей: {stats['total_users']}
📋 Броней: {stats['total_bookings']}
✅ Подтверждено: {stats['approved']}
⏳ Ожидают: {stats['pending']}
❌ Отклонено: {stats['rejected']}"""
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(language))

# Masters management handlers
@masters_router.callback_query(F.data == "admin_masters_menu")
async def masters_menu(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    await callback.message.edit_text(get_text("masters_management", language), reply_markup=masters_menu_kb(language))

@masters_router.callback_query(F.data == "master_add")
async def add_master_start(callback: CallbackQuery, state: FSMContext, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    await state.set_state(MasterManagementStates.waiting_master_id)
    await callback.message.edit_text(get_text("enter_master_id", language))

@masters_router.message(MasterManagementStates.waiting_master_id)
async def process_master_id(message: Message, state: FSMContext, language: str):
    if not is_admin(message.from_user.id):
        await message.answer(get_text("no_access", language))
        await state.clear()
        return
    try:
        master_id = int(message.text.strip())
        if await db.is_master(master_id):
            await message.answer(get_text("master_already_exists", language))
            return
        user = await db.get_user(master_id)
        if not user:
            await message.answer(get_text("user_not_found", language))
            return
        await db.add_master(master_id, user['full_name'], user['username'], message.from_user.id)
        await notify_new_master(master_id)
        await message.answer(get_text("master_added", language, name=user['full_name'], id=master_id), reply_markup=masters_menu_kb(language))
    except ValueError:
        await message.answer("❌ Введите числовой ID")
    await state.clear()

@masters_router.callback_query(F.data == "master_list")
async def list_masters(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    masters = await db.get_all_masters()
    if not masters:
        await callback.message.edit_text(get_text("no_masters", language), reply_markup=masters_menu_kb(language))
        return
    text = get_text("masters_list", language)
    for i, master in enumerate(masters, 1):
        text += get_text("master_info", language, num=i, name=master['full_name'], id=master['id'])
    await callback.message.edit_text(text, reply_markup=masters_menu_kb(language))

@masters_router.callback_query(F.data == "master_remove_list")
async def remove_master_list(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    masters = await db.get_all_masters()
    if not masters:
        await callback.message.edit_text(get_text("no_masters", language), reply_markup=masters_menu_kb(language))
        return
    await callback.message.edit_text(get_text("select_master_to_remove", language), reply_markup=master_remove_kb(masters, language))

@masters_router.callback_query(F.data.startswith("master_del_"))
async def confirm_remove_master(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    master_id = int(callback.data.split("_")[2])
    master = await db.get_master(master_id)
    if not master:
        await callback.answer(get_text("master_not_found", language))
        return
    text = f"❌ Удалить {master['full_name']} (ID: {master_id})?"
    await callback.message.edit_text(text, reply_markup=confirm_remove_master_kb(master_id, language))

@masters_router.callback_query(F.data.startswith("master_confirm_del_"))
async def do_remove_master(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    master_id = int(callback.data.split("_")[3])
    await notify_master_removed(master_id)
    await db.remove_master(master_id)
    await callback.message.edit_text(get_text("master_removed", language), reply_markup=masters_menu_kb(language))

# Settings handlers
@settings_router.message(F.text.in_(["⚙️ Настройки", "⚙️ Sozlamalar"]))
async def settings(message: Message, language: str):
    user = await db.get_user(message.from_user.id)
    text = f"⚙️ Настройки\n\n🌐 Язык: {language}\n🔔 Напоминание: {user['reminder_minutes']} мин"
    await message.answer(text, reply_markup=language_kb())

@settings_router.message(F.text.in_(["📋 Мои записи", "📋 Mening yozuvlarim"]))
async def my_bookings(message: Message, language: str):
    bookings = await db.get_user_bookings(message.from_user.id)
    if not bookings:
        await message.answer("У вас нет записей.")
        return
    text = "📋 Ваши записи:\n\n"
    for b in bookings:
        status = {'pending': '⏳', 'approved': '✅', 'rejected': '❌'}.get(b['status'], '❓')
        text += f"{status} {b['date']} {b['time']}\n"
    await message.answer(text)

@settings_router.message(F.text.in_(["👥 Кто до меня?", "👥 Menden oldin kim?"]))
async def show_queue(message: Message, language: str):
    today = datetime.now().strftime("%Y-%m-%d")
    bookings = await db.get_bookings_by_date(today, status='approved')
    if not bookings:
        await message.answer(get_text("queue_empty", language))
        return
    text = get_text("queue_title", language, date=today) + "\n\n"
    for i, b in enumerate(bookings, 1):
        text += f"{i}. {b['time']} — {b['full_name']}\n"
    await message.answer(text)

# ============ MAIN ============
async def main():
    if not config.BOT_TOKEN:
        print("❌ BOT_TOKEN не установлен!")
        return
    
    await db.init()
    
    bot = Bot(token=config.BOT_TOKEN)
    set_bot(bot)
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())
    
    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(master_router)
    dp.include_router(admin_router)
    dp.include_router(settings_router)
    dp.include_router(masters_router)
    
    init_scheduler()
    
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())