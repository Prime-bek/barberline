from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from config import config
from database import db
from keyboards.admin_kb import admin_menu_kb, pagination_kb
from keyboards.user_kb import main_menu_kb
from utils.texts import get_text

router = Router()

ITEMS_PER_PAGE = 5

def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID

@router.message(F.text.in_(["🔧 Админ панель", "🔧 Admin panel"]))
async def admin_panel(message: Message, language: str):
    if not is_admin(message.from_user.id):
        await message.answer(get_text("no_access", language))
        return
    
    await message.answer(
        get_text("admin_menu", language),
        reply_markup=admin_menu_kb(language)
    )

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, language: str):
    await callback.message.edit_text(
        get_text("admin_menu", language),
        reply_markup=admin_menu_kb(language)
    )

@router.callback_query(F.data.startswith("admin_users_"))
async def show_users(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return
    
    page = int(callback.data.split("_")[2])
    users = await db.get_all_users(limit=ITEMS_PER_PAGE, offset=page * ITEMS_PER_PAGE)
    
    if not users:
        await callback.answer("Нет пользователей")
        return
    
    stats = await db.get_statistics()
    total_pages = (stats['total_users'] + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    text = get_text("users_list", language, page=page + 1) + "\n\n"
    for user in users:
        text += f"👤 {user['full_name']} (ID: {user['id']})\n"
        text += f"   @{user['username'] or 'нет'} | {user['city'] or 'нет города'}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=pagination_kb(page, max(1, total_pages), "admin_users", language)
    )

@router.callback_query(F.data.startswith("admin_bookings_"))
async def show_bookings(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return
    
    page = int(callback.data.split("_")[2])
    bookings = await db.get_all_bookings(limit=ITEMS_PER_PAGE, offset=page * ITEMS_PER_PAGE)
    
    if not bookings:
        await callback.answer("Нет броней")
        return
    
    stats = await db.get_statistics()
    total_pages = (stats['total_bookings'] + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    text = get_text("bookings_list", language, page=page + 1) + "\n\n"
    for booking in bookings:
        status_emoji = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌'
        }.get(booking['status'], '❓')
        
        text += f"{status_emoji} {booking['full_name']}\n"
        text += f"   📅 {booking['date']} {booking['time']}\n"
        text += f"   📱 {booking['phone']}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=pagination_kb(page, max(1, total_pages), "admin_bookings", language)
    )

@router.callback_query(F.data == "admin_stats")
async def show_statistics(callback: CallbackQuery, language: str):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return
    
    stats = await db.get_statistics()
    text = get_text("stats_text", language, **stats)
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_menu_kb(language)
    )

@router.message(F.text == "/user")
async def show_user_details(message: Message, language: str):
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.split()[1])
        user = await db.get_user(user_id)
        
        if not user:
            await message.answer("Пользователь не найден")
            return
        
        lang_name = "Русский 🇷🇺" if user['language'] == 'ru' else "O'zbekcha 🇺🇿"
        status_text = get_text("active" if user['status'] == 'active' else "inactive", language)
        
        text = get_text("user_details", language,
                       id=user['id'],
                       full_name=user['full_name'],
                       username=f"@{user['username']}" if user['username'] else "Нет",
                       language=lang_name,
                       city=user['city'] or "Не указан",
                       reminder_min=user['reminder_minutes'],
                       reg_date=user['registration_date'],
                       last_activity=user['last_activity'],
                       status=status_text)
        
        await message.answer(text)
        
    except (IndexError, ValueError):
        await message.answer("Использование: /user ID")