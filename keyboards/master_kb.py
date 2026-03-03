from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def master_booking_kb(booking_id: int):
    """Клавиатура для принятия/отклонения брони"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"accept_{booking_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{booking_id}")
    builder.adjust(2)
    return builder.as_markup()

def master_menu_kb():
    """Меню мастера"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Моё расписание", callback_data="master_schedule")
    return builder.as_markup()