import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import db
from handlers import (
    start_router, booking_router, master_router, admin_router, 
    settings_router, masters_router, set_bot, init_scheduler, 
    restore_reminders, LanguageMiddleware
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    if not config.BOT_TOKEN:
        logging.error("❌ BOT_TOKEN не установлен!")
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
    await restore_reminders()
    
    logging.info("✅ Бот запущен!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("🛑 Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())