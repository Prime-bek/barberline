import re
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, BaseMiddleware
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from pytz import timezone

from config import config
from database import db
from translations import get_text, format_date_uz
from keyboards import (
    language_kb, main_menu_kb, contact_kb, reminder_kb,
    dates_inline_kb, times_inline_kb, master_booking_kb, master_panel_kb,
    cancel_booking_kb, admin_menu_kb, masters_menu_kb, master_remove_kb,
    confirm_remove_master_kb, pagination_kb, settings_inline_kb, language_inline_kb
)

scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
bot_instance = None

def set_bot(bot):
    global bot_instance
    bot_instance = bot

async def send_reminder(user_id: int, booking_id: int, time: str, lang: str, minutes: int):
    if not bot_instance:
        return
    try:
        text = get_text("reminder", lang, minutes=minutes, time=time)
        await bot_instance.send_message(user_id, text)
        logging.info(f"✅ Напоминание отправлено {user_id}")
    except Exception as e:
        logging.error(f"❌ Ошибка напоминания: {e}")

async def notify_user_approved(user_id: int, date: str, time: str, lang: str):
    if not bot_instance:
        return
    try:
        formatted_date = format_date_uz(date, lang)
        text = get_text("approved", lang, date=formatted_date, time=time)
        await bot_instance.send_message(user_id, text)
    except Exception as e:
        logging.error(f"Error: {e}")

async def notify_user_rejected(user_id: int, reason: str, lang: str):
    if not bot_instance:
        return
    try:
        text = get_text("rejected", lang, reason=reason)
        await bot_instance.send_message(user_id, text)
    except Exception as e:
        logging.error(f"Error: {e}")

async def send_booking_to_masters(booking_id: int, name: str, phone: str, date: str, time: str):
    if not bot_instance:
        return
    try:
        formatted_date = format_date_uz(date, "ru")
        text = get_text("new_booking_master", "ru", name=name, phone=phone, date=formatted_date, time=time)
        masters = await db.get_all_masters()
        
        if not masters:
            await bot_instance.send_message(config.ADMIN_ID, "⚠️ Нет мастеров!\n\n" + text, 
                                          reply_markup=master_booking_kb(booking_id))
            return
        
        for master in masters:
            try:
                await bot_instance.send_message(master['id'], text, reply_markup=master_booking_kb(booking_id))
            except Exception as e:
                logging.error(f"Error sending to master {master['id']}: {e}")
    except Exception as e:
        logging.error(f"Error: {e}")

async def notify_new_master(master_id: int):
    if not bot_instance:
        return
    try:
        await bot_instance.send_message(master_id, "✅ Вам назначены права мастера!")
    except Exception as e:
        logging.error(f"Error: {e}")

async def notify_master_removed(master_id: int):
    if not bot_instance:
        return
    try:
        await bot_instance.send_message(master_id, "❌ Ваши права мастера отозваны.")
    except Exception as e:
        logging.error(f"Error: {e}")

async def schedule_reminder(booking_id: int):
    booking = await db.get_booking(booking_id)
    if not booking or booking['status'] != 'approved':
        return
    
    user = await db.get_user(booking['user_id'])
    if not user:
        return
    
    date_str = booking['date']
    time_str = booking['time']
    reminder_minutes = user['reminder_minutes']
    
    tz = timezone(config.TIMEZONE)
    booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    booking_datetime = tz.localize(booking_datetime)
    
    reminder_datetime = booking_datetime - timedelta(minutes=reminder_minutes)
    now = datetime.now(tz)
    
    if reminder_datetime <= now:
        return
    
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=reminder_datetime),
        args=[booking['user_id'], booking_id, time_str, user['language'], reminder_minutes],
        id=f"reminder_{booking_id}",
        replace_existing=True
    )
    logging.info(f"✅ Напоминание запланировано: {reminder_datetime}")

async def restore_reminders():
    bookings = await db.get_approved_bookings()
    tz = timezone(config.TIMEZONE)
    now = datetime.now(tz)
    
    count = 0
    for booking in bookings:
        try:
            date_str = booking['date']
            time_str = booking['time']
            reminder_minutes = booking['reminder_minutes']
            
            booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            booking_datetime = tz.localize(booking_datetime)
            reminder_datetime = booking_datetime - timedelta(minutes=reminder_minutes)
            
            if reminder_datetime > now:
                scheduler.add_job(
                    send_reminder,
                    trigger=DateTrigger(run_date=reminder_datetime),
                    args=[booking['user_id'], booking['id'], time_str, booking['language'], reminder_minutes],
                    id=f"reminder_{booking['id']}",
                    replace_existing=True
                )
                count += 1
        except Exception as e:
            logging.error(f"Error restoring reminder: {e}")
    
    logging.info(f"✅ Восстановлено {count} напоминаний")

def init_scheduler():
    scheduler.start()
    logging.info(f"✅ Планировщик запущен: {config.TIMEZONE}")

class LanguageMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not hasattr(event, 'from_user') or not event.from_user:
            return await handler(event, data)
        
        user = await db.get_user(event.from_user.id)
        if user:
            data['language'] = user.get('language', 'ru')
        else:
            data['language'] = 'ru'
        return await handler(event, data)

class BookingStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_reminder = State()

class MasterStates(StatesGroup):
    waiting_reject_reason = State()

class MasterManagementStates(StatesGroup):
    waiting_master_id = State()

start_router = Router()
booking_router = Router()
master_router = Router()
admin_router = Router()
settings_router = Router()
masters_router = Router()

@start_router.message(Command("start"))
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await db.add_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
        await message.answer(get_text("welcome", "ru"), reply_markup=language_kb())
    else:
        is_admin = message.from_user.id == config.ADMIN_ID
        lang = user.get('language', 'ru')
        await message.answer(get_text("main_menu", lang), reply_markup=main_menu_kb(lang, is_admin))

@start_router.message(F.text.in_(["🇷🇺 Русский", "🇺🇿 O'zbekcha"]))
async def set_language(message: Message):
    lang = "ru" if "Русский" in message.text else "uz"
    await db.update_user_language(message.from_user.id, lang)
    is_admin = message.from_user.id == config.ADMIN_ID
    await message.answer(get_text("main_menu", lang), reply_markup=main_menu_kb(lang, is_admin))

@booking_router.message(F.text.in_(["📅 Записаться", "📅 Yozilish"]))
async def start_booking(message: Message, state: FSMContext, language: str):
    if await db.has_active_booking(message.from_user.id):
        await message.answer(get_text("already_booked", language))
        return
    
    await state.set_state(BookingStates.waiting_name)
    await message.answer(get_text("enter_name", language), reply_markup=ReplyKeyboardRemove())

@booking_router.message(BookingStates.waiting_name)
async def process_name(message: Message, state: FSMContext, language: str):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_phone)
    await message.answer(get_text("enter_phone", language), reply_markup=contact_kb(language))

@booking_router.message(BookingStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext, language: str):
    phone = None
    
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()
        if not re.match(r'^\+?[\d\s\-\(\)]{9,15}$', phone):
            await message.answer(get_text("invalid_phone", language), reply_markup=contact_kb(language))
            return
    
    await state.update_data(phone=phone)
    await state.set_state(BookingStates.waiting_reminder)
    await message.answer(get_text("choose_reminder", language), reply_markup=reminder_kb(language))

@booking_router.message(BookingStates.waiting_reminder)
async def process_reminder(message: Message, state: FSMContext, language: str):
    reminder_map = {
        "10 минут": 10, "10 daqiqa": 10,
        "25 минут": 25, "25 daqiqa": 25,
        "30 минут": 30, "30 daqiqa": 30
    }
    minutes = reminder_map.get(message.text, 30)
    await db.update_reminder_minutes(message.from_user.id, minutes)
    
    await message.answer(get_text("choose_date", language), reply_markup=dates_inline_kb(language))

@booking_router.callback_query(F.data.startswith("date_"))
async def process_date_callback(callback: CallbackQuery, state: FSMContext, language: str):
    date_str = callback.data.replace("date_", "")
    await state.update_data(date=date_str)
    
    kb = await times_inline_kb(date_str, language, db)
    await callback.message.edit_text(get_text("choose_time", language), reply_markup=kb)

@booking_router.callback_query(F.data == "ignore_busy")
async def ignore_busy(callback: CallbackQuery):
    await callback.answer("❌ Это время занято", show_alert=True)

@booking_router.callback_query(F.data.startswith("time_"))
async def process_time_callback(callback: CallbackQuery, state: FSMContext, language: str):
    time_str = callback.data.replace("time_", "")
    data = await state.get_data()
    
    if await db.is_time_busy(data.get('date'), time_str):
        await callback.answer(get_text("time_busy", language), show_alert=True)
        return
    
    booking_id = await db.add_booking(
        callback.from_user.id,
        data['date'],
        time_str,
        data['phone']
    )
    
    await send_booking_to_masters(booking_id, data['name'], data['phone'], data['date'], time_str)
    
    await state.clear()
    
    # Берем язык из базы для точности
    user = await db.get_user(callback.from_user.id)
    lang = user.get('language', 'ru') if user else 'ru'
    is_admin = callback.from_user.id == config.ADMIN_ID
    
    await callback.message.delete()
    await callback.message.answer(get_text("booking_sent", lang), 
                                reply_markup=main_menu_kb(lang, is_admin))

@booking_router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, language: str):
    await callback.message.edit_text(get_text("choose_date", language), 
                                   reply_markup=dates_inline_kb(language))

@master_router.callback_query(F.data.startswith("accept_"))
async def accept_booking(callback: CallbackQuery):
    if not await db.is_master(callback.from_user.id):
        await callback.answer(get_text("not_master", "ru"))
        return
    
    booking_id = int(callback.data.split("_")[1])
    booking = await db.get_booking(booking_id)
    
    if not booking or booking['status'] != 'pending':
        await callback.answer("Уже обработано")
        return
    
    await db.update_booking_status(booking_id, "approved")
    await schedule_reminder(booking_id)
    await notify_user_approved(booking['user_id'], booking['date'], booking['time'], booking['language'])
    
    formatted_date = format_date_uz(booking['date'], "ru")
    new_text = f"✅ ПРИНЯТО\n\n{callback.message.text}\n\n📅 {formatted_date}"
    
    await callback.message.edit_text(new_text, reply_markup=master_panel_kb(booking_id, "ru"))
    await callback.answer("Подтверждено")

@master_router.callback_query(F.data.startswith("reject_"))
async def reject_booking_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_master(callback.from_user.id):
        await callback.answer(get_text("not_master", "ru"))
        return
    
    booking_id = int(callback.data.split("_")[1])
    await state.update_data(booking_id=booking_id)
    await state.set_state(MasterStates.waiting_reject_reason)
    await callback.message.answer(get_text("enter_reject_reason", "ru"))
    await callback.answer()

@master_router.message(MasterStates.waiting_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    booking = await db.get_booking(data['booking_id'])
    
    if not booking:
        await message.answer("Бронь не найдена")
        await state.clear()
        return
    
    await db.update_booking_status(data['booking_id'], "rejected", message.text)
    await notify_user_rejected(booking['user_id'], message.text, booking['language'])
    await message.answer(get_text("booking_rejected_master", "ru"))
    await state.clear()

@master_router.callback_query(F.data.startswith("complete_"))
async def complete_booking(callback: CallbackQuery):
    if not await db.is_master(callback.from_user.id):
        await callback.answer(get_text("not_master", "ru"))
        return
    
    booking_id = int(callback.data.split("_")[1])
    await db.complete_booking(booking_id, early=False)
    
    await callback.message.edit_text(callback.message.text + "\n\n✅ УСЛУГА ЗАВЕРШЕНА")
    await callback.answer(get_text("booking_completed", "ru"))

@master_router.callback_query(F.data.startswith("early_"))
async def early_complete_booking(callback: CallbackQuery):
    if not await db.is_master(callback.from_user.id):
        await callback.answer(get_text("not_master", "ru"))
        return
    
    booking_id = int(callback.data.split("_")[1])
    await db.complete_booking(booking_id, early=True)
    
    await callback.message.edit_text(callback.message.text + "\n\n🏃 УСЛУГА ЗАВЕРШЕНА ДОСРОЧНО")
    await callback.answer(get_text("booking_early_completed", "ru"))

@master_router.message(Command("master"))
async def master_panel_cmd(message: Message, language: str):
    if not await db.is_master(message.from_user.id):
        await message.answer(get_text("not_master", language))
        return
    
    bookings = await db.get_master_bookings()
    
    if not bookings:
        await message.answer(get_text("no_active_bookings", language))
        return
    
    for booking in bookings:
        status_text = {"pending": "⏳ Ожидает", "approved": "✅ Подтверждено"}.get(booking['status'], booking['status'])
        formatted_date = format_date_uz(booking['date'], language)
        
        text = get_text("booking_details", language,
                       name=booking['full_name'],
                       phone=booking['phone'],
                       date=formatted_date,
                       time=booking['time'],
                       status=status_text)
        
        if booking['status'] == 'approved':
            await message.answer(text, reply_markup=master_panel_kb(booking['id'], language))
        else:
            await message.answer(text, reply_markup=master_booking_kb(booking['id']))

@admin_router.message(Command("admin"))
async def admin_cmd(message: Message, language: str):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer(get_text("no_access", language))
        return
    await message.answer(get_text("admin_menu", language), reply_markup=admin_menu_kb(language))

@admin_router.message(F.text.in_([get_text("settings_btn", "ru"), get_text("settings_btn", "uz")]))
async def admin_text_handler(message: Message, language: str):
    await admin_cmd(message, language)

@admin_router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, language: str):
    await callback.message.edit_text(get_text("admin_menu", language), reply_markup=admin_menu_kb(language))

@admin_router.callback_query(F.data == "ignore")
async def ignore(callback: CallbackQuery):
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_users_"))
async def show_users(callback: CallbackQuery, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔")
        return
    page = int(callback.data.split("_")[2])
    users = await db.get_all_users(limit=5, offset=page * 5)
    if not users:
        await callback.answer("Нет пользователей")
        return
    stats = await db.get_statistics()
    total_pages = max(1, (stats['total_users'] + 4) // 5)
    text = f"👥 Пользователи (стр. {page+1}):\n\n"
    for user in users:
        text += f"• {user['full_name']} (ID: {user['id']})\n"
    await callback.message.edit_text(text, reply_markup=pagination_kb(page, total_pages, "admin_users", language))

@admin_router.callback_query(F.data.startswith("admin_bookings_"))
async def show_bookings(callback: CallbackQuery, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔")
        return
    page = int(callback.data.split("_")[2])
    bookings = await db.get_all_bookings(limit=5, offset=page * 5)
    if not bookings:
        await callback.answer("Нет броней")
        return
    stats = await db.get_statistics()
    total_pages = max(1, (stats['total_bookings'] + 4) // 5)
    text = f"📋 Брони (стр. {page+1}):\n\n"
    for b in bookings:
        emoji = {'pending': '⏳', 'approved': '✅', 'rejected': '❌', 'completed': '✅', 'completed_early': '🏃'}.get(b['status'], '❓')
        text += f"{emoji} {b['full_name']} - {format_date_uz(b['date'], language)} {b['time']}\n"
    await callback.message.edit_text(text, reply_markup=pagination_kb(page, total_pages, "admin_bookings", language))

@admin_router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔")
        return
    stats = await db.get_statistics()
    text = f"""📊 Статистика:
👥 Пользователей: {stats['total_users']}
📋 Броней: {stats['total_bookings']}
✅ Подтверждено: {stats['approved']}
⏳ Ожидают: {stats['pending']}
❌ Отклонено: {stats['rejected']}"""
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(language))

@masters_router.callback_query(F.data == "admin_masters_menu")
async def masters_menu(callback: CallbackQuery, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer(get_text("no_access", language))
        return
    await callback.message.edit_text(get_text("masters_management", language), reply_markup=masters_menu_kb(language))

@masters_router.callback_query(F.data == "master_add")
async def add_master_start(callback: CallbackQuery, state: FSMContext, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer(get_text("no_access", language))
        return
    await state.set_state(MasterManagementStates.waiting_master_id)
    await callback.message.edit_text(get_text("enter_master_id", language))

@masters_router.message(MasterManagementStates.waiting_master_id)
async def process_master_id(message: Message, state: FSMContext, language: str):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer(get_text("no_access", language))
        await state.clear()
        return
    try:
        master_id = int(message.text.strip())
        if await db.is_master(master_id):
            await message.answer(get_text("master_already_exists", language))
            return
        user = await db.get_user(master_id)
        if not user:
            await message.answer(get_text("user_not_found", language))
            return
        await db.add_master(master_id, user['full_name'], user['username'], message.from_user.id)
        await notify_new_master(master_id)
        await message.answer(get_text("master_added", language, name=user['full_name'], id=master_id), 
                           reply_markup=masters_menu_kb(language))
    except ValueError:
        await message.answer("❌ Введите числовой ID")
    await state.clear()

@masters_router.callback_query(F.data == "master_list")
async def list_masters(callback: CallbackQuery, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer(get_text("no_access", language))
        return
    masters = await db.get_all_masters()
    if not masters:
        await callback.message.edit_text(get_text("no_masters", language), reply_markup=masters_menu_kb(language))
        return
    text = get_text("masters_list", language)
    for i, master in enumerate(masters, 1):
        text += get_text("master_info", language, num=i, name=master['full_name'], id=master['id'])
    await callback.message.edit_text(text, reply_markup=masters_menu_kb(language))

@masters_router.callback_query(F.data == "master_remove_list")
async def remove_master_list(callback: CallbackQuery, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer(get_text("no_access", language))
        return
    masters = await db.get_all_masters()
    if not masters:
        await callback.message.edit_text(get_text("no_masters", language), reply_markup=masters_menu_kb(language))
        return
    await callback.message.edit_text(get_text("select_master_to_remove", language), reply_markup=master_remove_kb(masters, language))

@masters_router.callback_query(F.data.startswith("master_del_"))
async def confirm_remove_master(callback: CallbackQuery, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer(get_text("no_access", language))
        return
    master_id = int(callback.data.split("_")[2])
    master = await db.get_master(master_id)
    if not master:
        await callback.answer(get_text("master_not_found", language))
        return
    text = f"❌ Удалить {master['full_name']}?"
    await callback.message.edit_text(text, reply_markup=confirm_remove_master_kb(master_id, language))

@masters_router.callback_query(F.data.startswith("master_confirm_del_"))
async def do_remove_master(callback: CallbackQuery, language: str):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer(get_text("no_access", language))
        return
    master_id = int(callback.data.split("_")[3])
    await notify_master_removed(master_id)
    await db.remove_master(master_id)
    await callback.message.edit_text(get_text("master_removed", language), reply_markup=masters_menu_kb(language))

@settings_router.message(F.text.in_([get_text("settings_btn", "ru"), get_text("settings_btn", "uz")]))
async def settings(message: Message, language: str):
    user = await db.get_user(message.from_user.id)
    lang_name = "Русский 🇷🇺" if language == "ru" else "O'zbekcha 🇺🇿"
    text = get_text("settings", language, lang=lang_name, min=user['reminder_minutes'])
    await message.answer(text, reply_markup=settings_inline_kb(language))

@settings_router.callback_query(F.data == "change_lang")
async def change_lang(callback: CallbackQuery, language: str):
    await callback.message.edit_text(get_text("choose_language", language), 
                                   reply_markup=language_inline_kb(language))

@settings_router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery, language: str):
    user = await db.get_user(callback.from_user.id)
    lang_name = "Русский 🇷🇺" if language == "ru" else "O'zbekcha 🇺🇿"
    await callback.message.edit_text(
        get_text("settings", language, lang=lang_name, min=user['reminder_minutes']),
        reply_markup=settings_inline_kb(language)
    )

@settings_router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, language: str):
    is_admin = callback.from_user.id == config.ADMIN_ID
    await callback.message.delete()
    await callback.message.answer(get_text("main_menu", language), reply_markup=main_menu_kb(language, is_admin))

@settings_router.callback_query(F.data.startswith("set_lang_"))
async def set_lang_callback(callback: CallbackQuery):
    new_lang = callback.data.replace("set_lang_", "")
    await db.update_user_language(callback.from_user.id, new_lang)
    
    # Обновляем меню сразу
    is_admin = callback.from_user.id == config.ADMIN_ID
    
    await callback.message.delete()
    await callback.message.answer(
        get_text("main_menu", new_lang),
        reply_markup=main_menu_kb(new_lang, is_admin)
    )

@settings_router.message(F.text.in_([get_text("my_bookings", "ru"), get_text("my_bookings", "uz")]))
async def my_bookings(message: Message, language: str):
    bookings = await db.get_user_bookings(message.from_user.id)
    
    active_bookings = [b for b in bookings if b['status'] in ['pending', 'approved']]
    
    if not active_bookings:
        if not bookings:
            await message.answer(get_text("no_bookings", language))
            return
        
        text = "📋 История:\n\n"
        for b in bookings[:5]:
            emoji = {'pending': '⏳', 'approved': '✅', 'rejected': '❌', 'completed': '✅', 
                    'completed_early': '🏃', 'cancelled': '❌'}.get(b['status'], '❓')
            date_str = format_date_uz(b['date'], language)
            text += f"{emoji} {date_str} {b['time']}\n"
        await message.answer(text)
        return
    
    for b in active_bookings:
        status_text = {"pending": "⏳ Ожидает", "approved": "✅ Подтверждено"}.get(b['status'], b['status'])
        date_str = format_date_uz(b['date'], language)
        
        text = f"📋 Активная запись:\n\n📅 {date_str}\n⏰ {b['time']}\n📱 {b['phone']}\nСтатус: {status_text}"
        await message.answer(text, reply_markup=cancel_booking_kb(b['id'], language))

@settings_router.callback_query(F.data.startswith("cancel_"))
async def cancel_booking_handler(callback: CallbackQuery, language: str):
    booking_id = int(callback.data.split("_")[1])
    booking = await db.get_booking(booking_id)
    
    if not booking or booking['user_id'] != callback.from_user.id:
        await callback.answer("Ошибка", show_alert=True)
        return
    
    if booking['status'] not in ['pending', 'approved']:
        await callback.answer("Нельзя отменить", show_alert=True)
        return
    
    await db.cancel_booking(booking_id)
    await callback.message.edit_text(callback.message.text + "\n\n❌ ОТМЕНЕНО")
    await callback.answer(get_text("booking_cancelled", language))

@settings_router.message(F.text.in_([get_text("queue", "ru"), get_text("queue", "uz")]))
async def show_queue(message: Message, language: str):
    today = datetime.now().strftime("%Y-%m-%d")
    bookings = await db.get_bookings_by_date(today, status='approved')
    
    if not bookings:
        await message.answer(get_text("queue_empty", language))
        return
    
    date_str = format_date_uz(today, language)
    text = get_text("queue_title", language, date=date_str) + "\n"
    
    for i, b in enumerate(bookings, 1):
        text += f"{i}. {b['time']} — {b['full_name']}\n"
    
    await message.answer(text)