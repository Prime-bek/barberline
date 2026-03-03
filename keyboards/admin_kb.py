from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.texts import get_text

def admin_menu_kb(lang: str = "ru"):
    """Главное меню админа"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("users", lang), callback_data="admin_users_0")
    builder.button(text=get_text("bookings", lang), callback_data="admin_bookings_0")
    builder.button(text=get_text("statistics", lang), callback_data="admin_stats")
    builder.adjust(2, 1)
    return builder.as_markup()

def pagination_kb(current_page: int, total_pages: int, prefix: str, lang: str = "ru"):
    """Клавиатура пагинации"""
    builder = InlineKeyboardBuilder()
    
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton(
            text=get_text("prev", lang), 
            callback_data=f"{prefix}_{current_page - 1}"
        ))
    
    buttons.append(InlineKeyboardButton(
        text=f"{current_page + 1}/{total_pages}", 
        callback_data="ignore"
    ))
    
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(
            text=get_text("next", lang), 
            callback_data=f"{prefix}_{current_page + 1}"
        ))
    
    builder.row(*buttons)
    builder.button(text=get_text("back", lang), callback_data="admin_back")
    return builder.as_markup()

def user_details_kb(user_id: int, lang: str = "ru"):
    """Клавиатура деталей пользователя"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("back", lang), callback_data="admin_users_0")
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.texts import get_text

def admin_menu_kb(lang: str = "ru"):
    """Главное меню админа"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("users", lang), callback_data="admin_users_0")
    builder.button(text=get_text("bookings", lang), callback_data="admin_bookings_0")
    builder.button(text=get_text("statistics", lang), callback_data="admin_stats")
    builder.button(text="👨‍💼 " + get_text("masters_management", lang).split('\n')[0], callback_data="admin_masters_menu")
    builder.adjust(2, 2)
    return builder.as_markup()

def masters_menu_kb(lang: str = "ru"):
    """Меню управления мастерами"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("add_master", lang), callback_data="master_add")
    builder.button(text=get_text("remove_master", lang), callback_data="master_remove_list")
    builder.button(text=get_text("list_masters", lang), callback_data="master_list")
    builder.button(text=get_text("back", lang), callback_data="admin_back")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def master_remove_kb(masters: list, lang: str = "ru"):
    """Клавиатура для удаления мастера"""
    builder = InlineKeyboardBuilder()
    for master in masters:
        name = master['full_name'] or f"ID: {master['id']}"
        builder.button(
            text=f"❌ {name[:20]}", 
            callback_data=f"master_del_{master['id']}"
        )
    builder.button(text=get_text("back_to_masters", lang), callback_data="admin_masters_menu")
    builder.adjust(1)
    return builder.as_markup()

def confirm_remove_master_kb(master_id: int, lang: str = "ru"):
    """Подтверждение удаления мастера"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("remove_master_confirm", lang), 
        callback_data=f"master_confirm_del_{master_id}"
    )
    builder.button(text=get_text("back_to_masters", lang), callback_data="master_remove_list")
    return builder.as_markup()

# ... (остальные функции без изменений) ...