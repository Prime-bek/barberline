from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from translations import get_text, format_date_uz
from datetime import datetime, timedelta

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
    builder.button(text=get_text("settings_btn", lang))
    if is_admin:
        builder.button(text=get_text("admin_panel_cmd", lang))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def contact_kb(lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text("share_contact", lang), request_contact=True)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def reminder_kb(lang: str = "ru"):
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text("minutes_10", lang))
    builder.button(text=get_text("minutes_25", lang))
    builder.button(text=get_text("minutes_30", lang))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def dates_inline_kb(lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    today = datetime.now()
    
    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        display = format_date_uz(date_str, lang)
        
        if i == 0:
            display = get_text("today", lang) + f" ({display})"
        elif i == 1:
            display = get_text("tomorrow", lang) + f" ({display})"
        
        builder.button(text=display, callback_data=f"date_{date_str}")
    
    builder.adjust(1)
    return builder.as_markup()

async def times_inline_kb(date_str: str, lang: str, db):
    """Async версия с проверкой занятости"""
    builder = InlineKeyboardBuilder()
    
    hours = list(range(8, 21))
    for hour in hours:
        for minute in [0, 30]:
            if hour == 20 and minute == 30:
                continue
            time_str = f"{hour:02d}:{minute:02d}"
            
            # Проверяем занятость
            is_busy = await db.is_time_busy(date_str, time_str)
            
            if is_busy:
                builder.button(text=f"❌ {time_str}", callback_data="ignore_busy")
            else:
                builder.button(text=time_str, callback_data=f"time_{time_str}")
    
    builder.button(text=get_text("back", lang), callback_data="back_to_dates")
    builder.adjust(4)
    return builder.as_markup()

def master_booking_kb(booking_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"accept_{booking_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{booking_id}")
    builder.adjust(2)
    return builder.as_markup()

def master_panel_kb(booking_id: int, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("complete_booking", lang), callback_data=f"complete_{booking_id}")
    builder.button(text=get_text("early_complete", lang), callback_data=f"early_{booking_id}")
    builder.adjust(2)
    return builder.as_markup()

def cancel_booking_kb(booking_id: int, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("cancel_booking", lang), callback_data=f"cancel_{booking_id}")
    return builder.as_markup()

def admin_menu_kb(lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("users", lang), callback_data="admin_users_0")
    builder.button(text=get_text("bookings", lang), callback_data="admin_bookings_0")
    builder.button(text=get_text("statistics", lang), callback_data="admin_stats")
    builder.button(text=get_text("masters_management", lang)[:20], callback_data="admin_masters_menu")
    builder.adjust(2, 2)
    return builder.as_markup()

def masters_menu_kb(lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("add_master", lang), callback_data="master_add")
    builder.button(text=get_text("remove_master", lang), callback_data="master_remove_list")
    builder.button(text=get_text("list_masters", lang), callback_data="master_list")
    builder.button(text=get_text("back", lang), callback_data="admin_back")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def master_remove_kb(masters: list, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    for master in masters:
        name = master['full_name'] or f"ID: {master['id']}"
        builder.button(text=f"❌ {name[:20]}", callback_data=f"master_del_{master['id']}")
    builder.button(text=get_text("back", lang), callback_data="admin_masters_menu")
    builder.adjust(1)
    return builder.as_markup()

def confirm_remove_master_kb(master_id: int, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("remove_master", lang), callback_data=f"master_confirm_del_{master_id}")
    builder.button(text=get_text("back", lang), callback_data="master_remove_list")
    return builder.as_markup()

def pagination_kb(current_page: int, total_pages: int, prefix: str, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}_{current_page - 1}"))
    buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}_{current_page + 1}"))
    builder.row(*buttons)
    builder.button(text=get_text("back", lang), callback_data="admin_back")
    return builder.as_markup()

def settings_inline_kb(lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("change_language", lang), callback_data="change_lang")
    builder.button(text=get_text("back", lang), callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()

def language_inline_kb(lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="set_lang_ru")
    builder.button(text="🇺🇿 O'zbekcha", callback_data="set_lang_uz")
    builder.button(text=get_text("back", lang), callback_data="back_to_settings")
    builder.adjust(2, 1)
    return builder.as_markup()