import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
from database import db
from services.scheduler import init_scheduler
from services.notifications import set_bot
from middlewares.language import LanguageMiddleware
from handlers import (
    start_router, booking_router, master_router, 
    admin_router, settings_router, masters_router
)

logging.basicConfig(level=logging.INFO)

async def main():
    # Проверяем токен
    if not config.BOT_TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не установлен!")
        print("Установите переменную окружения BOT_TOKEN в Railway")
        return
    
    print(f"✅ BOT_TOKEN получен: {config.BOT_TOKEN[:10]}...")
    
    # Инициализация базы данных
    await db.init()
    
    # Инициализация бота
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Устанавливаем бот для notifications
    set_bot(bot)
    
    # Регистрация middleware
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())
    
    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(master_router)
    dp.include_router(admin_router)
    dp.include_router(settings_router)
    dp.include_router(masters_router)
    
    # Инициализация планировщика
    init_scheduler()
    
    print("✅ Бот запущен!")
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())