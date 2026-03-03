from aiogram import Bot
from config import config
from utils.texts import get_text
from database import db

bot = Bot(token=config.BOT_TOKEN)

async def send_reminder(user_id: int, booking_id: int, time: str, lang: str):
    """Отправить напоминание пользователю"""
    try:
        text = get_text("reminder", lang, time=time)
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"Error sending reminder to {user_id}: {e}")

async def notify_user_approved(user_id: int, date: str, time: str, lang: str):
    """Уведомить о подтверждении брони"""
    try:
        text = get_text("approved", lang, date=date, time=time)
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"Error notifying user {user_id}: {e}")

async def notify_user_rejected(user_id: int, reason: str, lang: str):
    """Уведомить об отклонении брони"""
    try:
        text = get_text("rejected", lang, reason=reason)
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"Error notifying user {user_id}: {e}")

async def send_booking_to_masters(booking_id: int, name: str, phone: str, 
                                 date: str, time: str):
    """Отправить заявку ВСЕМ активным мастерам"""
    try:
        from keyboards.master_kb import master_booking_kb
        
        text = get_text("new_booking_master", "ru", 
                       name=name, phone=phone, date=date, time=time)
        
        # Получаем всех мастеров
        masters = await db.get_all_masters()
        
        if not masters:
            # Если мастеров нет, отправляем админу
            await bot.send_message(
                config.ADMIN_ID,
                "⚠️ Нет активных мастеров!\n\n" + text,
                reply_markup=master_booking_kb(booking_id)
            )
            return
        
        # Отправляем каждому мастеру
        for master in masters:
            try:
                await bot.send_message(
                    master['id'],
                    text,
                    reply_markup=master_booking_kb(booking_id)
                )
            except Exception as e:
                print(f"Could not send to master {master['id']}: {e}")
                
    except Exception as e:
        print(f"Error sending booking to masters: {e}")