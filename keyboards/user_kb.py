from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from utils.texts import get_text

def language_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🇷🇺 Русский")
    builder.button(text="🇺🇿 O'zbekcha")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def main_menu_kb(lang: str = "ru", is_admin: bool = False):
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text("book", lang))
    builder.button(text=get_text("my_bookings", lang))
    builder.button(text=get_text("queue", lang))
    builder.button(text=get_text("settings", lang))
    if is_admin:
        builder.button(text=get_text("admin_panel", lang))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def reminder_kb(lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text("minutes_10", lang))
    builder.button(text=get_text("minutes_25", lang))
    builder.button(text=get_text("minutes_30", lang))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def back_kb(lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text("back", lang))
    return builder.as_markup(resize_keyboard=True)

def generate_dates_kb(dates: list, lang: str = "ru"):
    """Генерация клавиатуры с датами"""
    builder = ReplyKeyboardBuilder()
    for date in dates:
        builder.button(text=date)
    builder.button(text=get_text("back", lang))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def generate_times_kb(times: list, lang: str = "ru"):
    """Генерация клавиатуры со временем"""
    builder = ReplyKeyboardBuilder()
    for time in times:
        builder.button(text=time)
    builder.button(text=get_text("back", lang))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)