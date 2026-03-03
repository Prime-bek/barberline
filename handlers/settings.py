from aiogram import Router, F
from aiogram.types import Message
from database import db
from keyboards.user_kb import main_menu_kb, language_kb
from utils.texts import get_text

router = Router()

@router.message(F.text.in_(["⚙️ Настройки", "⚙️ Sozlamalar"]))
async def settings(message: Message, language: str):
    user = await db.get_user(message.from_user.id)
    
    text = f"""⚙️ {get_text('settings', language)}

🌐 {get_text('choose_language', language).replace('🌐 ', '')}: {language.upper()}
🔔 Напоминание: {user['reminder_minutes']} мин
🌍 {user['city'] or 'Не указан'}

Выберите действие:"""
    
    await message.answer(text, reply_markup=language_kb())

@router.message(F.text.in_(["📋 Мои записи", "📋 Mening yozuvlarim"]))
async def my_bookings(message: Message, language: str):
    bookings = await db.get_user_bookings(message.from_user.id)
    
    if not bookings:
        await message.answer("У вас нет записей.")
        return
    
    text = "📋 Ваши записи:\n\n"
    for booking in bookings:
        status = {
            'pending': '⏳ Ожидает',
            'approved': '✅ Подтверждено',
            'rejected': '❌ Отклонено'
        }.get(booking['status'], '❓')
        
        text += f"📅 {booking['date']} {booking['time']}\n"
        text += f"Статус: {status}\n"
        if booking['reject_reason']:
            text += f"Причина: {booking['reject_reason']}\n"
        text += "\n"
    
    await message.answer(text)

@router.message(F.text.in_(["👥 Кто до меня?", "👥 Menden oldin kim?"]))
async def show_queue(message: Message, language: str):
    from datetime import datetime
    
    today = datetime.now().strftime("%Y-%m-%d")
    bookings = await db.get_bookings_by_date(today, status='approved')
    
    if not bookings:
        await message.answer(get_text("queue_empty", language))
        return
    
    text = get_text("queue_title", language, date=today) + "\n\n"
    for i, booking in enumerate(bookings, 1):
        text += f"{i}. {booking['time']} — {booking['full_name']}\n"
    
    await message.answer(text)