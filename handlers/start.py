from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db
from keyboards.user_kb import language_kb, main_menu_kb
from utils.texts import get_text

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await db.add_user(
            message.from_user.id,
            message.from_user.full_name,
            message.from_user.username
        )
        await message.answer(
            get_text("choose_language"),
            reply_markup=language_kb()
        )
    else:
        is_admin = message.from_user.id == 1265652628
        await message.answer(
            get_text("welcome", user['language']),
            reply_markup=main_menu_kb(user['language'], is_admin)
        )

@router.message(F.text.in_(["🇷🇺 Русский", "🇺🇿 O'zbekcha"]))
async def set_language(message: Message):
    lang = "ru" if "Русский" in message.text else "uz"
    await db.update_user_language(message.from_user.id, lang)
    
    is_admin = message.from_user.id == 1265652628
    await message.answer(
        get_text("welcome", lang),
        reply_markup=main_menu_kb(lang, is_admin)
    )