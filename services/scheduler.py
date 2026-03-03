from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from config import config
from database import db

scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)

async def schedule_reminder(booking_id: int):
    """Запланировать напоминание"""
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
    
    # Импортируем здесь, чтобы избежать циклического импорта
    from services.notifications import send_reminder
    
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=reminder_datetime),
        args=[booking['user_id'], booking_id, time_str, user['language']],
        id=f"reminder_{booking_id}",
        replace_existing=True
    )

def init_scheduler():
    """Инициализация планировщика"""
    scheduler.start()

async def reschedule_all_reminders():
    """Перепланировать все напоминания при перезапуске бота"""
    pass