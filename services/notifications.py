from aiogram import Bot
from config import config
from utils.texts import get_text
from database import db

bot: Bot = None

def set_bot(bot_instance: Bot):
    """Установить экземпляр бота"""
    global bot
    bot = bot_instance

def get_bot() -> Bot:
    """Получить экземпляр бота"""
    global bot
    return bot

async def send_reminder(user_id: int, booking_id: int, time: str, lang: str):
    """Отправить напоминание пользователю"""
    global bot
    if not bot:
        print("Bot not initialized")
        return
    try:
        text = get_text("reminder", lang, time=time)
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"Error sending reminder to {user_id}: {e}")

async def notify_user_approved(user_id: int, date: str, time: str, lang: str):
    """Уведомить о подтверждении брони"""
    global bot
    if not bot:
        print("Bot not initialized")
        return
    try:
        text = get_text("approved", lang, date=date, time=time)
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"Error notifying user {user_id}: {e}")

async def notify_user_rejected(user_id: int, reason: str, lang: str):
    """Уведомить об отклонении брони"""
    global bot
    if not bot:
        print("Bot not initialized")
        return
    try:
        text = get_text("rejected", lang, reason=reason)
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"Error notifying user {user_id}: {e}")

async def send_booking_to_masters(booking_id: int, name: str, phone: str, 
                                 date: str, time: str):
    """Отправить заявку ВСЕМ активным мастерам"""
    global bot
    if not bot:
        print("Bot not initialized")
        return
    try:
        from keyboards.master_kb import master_booking_kb
        
        text = get_text("new_booking_master", "ru", 
                       name=name, phone=phone, date=date, time=time)
        
        masters = await db.get_all_masters()
        
        if not masters:
            await bot.send_message(
                config.ADMIN_ID,
                "⚠️ Нет активных мастеров!\n\n" + text,
                reply_markup=master_booking_kb(booking_id)
            )
            return
        
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

async def notify_new_master(master_id: int):
    """Уведомить нового мастера"""
    global bot
    if not bot:
        return
    try:
        await bot.send_message(
            master_id,
            "✅ Вам назначены права мастера!\n\nТеперь вы будете получать заявки на бронь."
        )
    except Exception as e:
        print(f"Could not notify new master: {e}")

async def notify_master_removed(master_id: int):
    """Уведомить об удалении прав мастера"""
    global bot
    if not bot:
        return
    try:
        await bot.send_message(
            master_id,
            "❌ Ваши права мастера были отозваны."
        )
    except Exception as e:
        print(f"Could not notify master: {e}")