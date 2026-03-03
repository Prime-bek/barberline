import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
from database import db
from services.scheduler import init_scheduler
from middlewares.language import LanguageMiddleware
from handlers import (
    start_router, booking_router, master_router, 
    admin_router, settings_router, masters_router  # Добавляем masters_router
)

logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализация базы данных
    await db.init()
    
    # Добавляем админа как мастера при первом запуске (опционально)
    # await db.add_master(config.ADMIN_ID, "Admin", None, config.ADMIN_ID)
    
    # Инициализация бота
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())
    
    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(master_router)
    dp.include_router(admin_router)
    dp.include_router(settings_router)
    dp.include_router(masters_router)  # Добавляем новый роутер
    
    # Инициализация планировщика
    init_scheduler()
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())