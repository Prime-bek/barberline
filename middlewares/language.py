from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from database import db

class LanguageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Определяем язык пользователя
        user = await db.get_user(event.from_user.id)
        if user:
            data['language'] = user.get('language', 'ru')
            await db.update_user_activity(event.from_user.id)
        else:
            data['language'] = 'ru'
        
        return await handler(event, data)