from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from services.notifications import send_booking_to_masters
import re
from database import db
from keyboards.user_kb import (
    main_menu_kb, reminder_kb, back_kb, 
    generate_dates_kb, generate_times_kb
)
from services.notifications import send_booking_to_master, send_booking_to_masters, send_booking_to_masters
from utils.texts import get_text

router = Router()

class BookingStates(StatesGroup):
    waiting_city = State()
    waiting_date = State()
    waiting_time = State()
    waiting_name = State()
    waiting_phone = State()
    waiting_reminder = State()

def generate_available_dates():
    """Генерация доступных дат (следующие 14 дней)"""
    dates = []
    today = datetime.now()
    for i in range(14):
        date = today + timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
    return dates

def generate_available_times():
    """Генерация доступного времени (с 9:00 до 18:00)"""
    times = []
    for hour in range(9, 19):
        times.append(f"{hour:02d}:00")
    return times

def validate_phone(phone: str) -> bool:
    """Валидация номера телефона"""
    pattern = r'^\+?[\d\s\-\(\)]{9,15}$'
    return bool(re.match(pattern, phone))

@router.message(F.text == "📅 Записаться")
@router.message(F.text == "📅 Yozilish")
async def start_booking(message: Message, state: FSMContext, language: str):
    user = await db.get_user(message.from_user.id)
    
    # Проверка на активную бронь
    if await db.has_active_booking(message.from_user.id):
        await message.answer(get_text("already_booked", language))
        return
    
    await state.set_state(BookingStates.waiting_city)
    await message.answer(
        get_text("choose_city", language),
        reply_markup=back_kb(language)
    )

@router.message(BookingStates.waiting_city)
async def process_city(message: Message, state: FSMContext, language: str):
    if message.text == get_text("back", language):
        await state.clear()
        is_admin = message.from_user.id == 1265652628
        await message.answer(
            get_text("main_menu", language),
            reply_markup=main_menu_kb(language, is_admin)
        )
        return
    
    await state.update_data(city=message.text)
    await db.update_user_city(message.from_user.id, message.text)
    
    dates = generate_available_dates()
    await state.set_state(BookingStates.waiting_date)
    await message.answer(
        get_text("choose_date", language),
        reply_markup=generate_dates_kb(dates, language)
    )

@router.message(BookingStates.waiting_date)
async def process_date(message: Message, state: FSMContext, language: str):
    if message.text == get_text("back", language):
        await state.set_state(BookingStates.waiting_city)
        await message.answer(
            get_text("choose_city", language),
            reply_markup=back_kb(language)
        )
        return
    
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        await state.update_data(date=message.text)
        
        times = generate_available_times()
        await state.set_state(BookingStates.waiting_time)
        await message.answer(
            get_text("choose_time", language),
            reply_markup=generate_times_kb(times, language)
        )
    except ValueError:
        await message.answer("❌ Неверный формат даты. Выберите из списка:")

@router.message(BookingStates.waiting_time)
async def process_time(message: Message, state: FSMContext, language: str):
    if message.text == get_text("back", language):
        dates = generate_available_dates()
        await state.set_state(BookingStates.waiting_date)
        await message.answer(
            get_text("choose_date", language),
            reply_markup=generate_dates_kb(dates, language)
        )
        return
    
    data = await state.get_data()
    date = data.get('date')
    
    # Проверка занятости времени
    if await db.is_time_busy(date, message.text):
        await message.answer(get_text("time_busy", language))
        return
    
    await state.update_data(time=message.text)
    await state.set_state(BookingStates.waiting_name)
    await message.answer(get_text("enter_name", language))

@router.message(BookingStates.waiting_name)
async def process_name(message: Message, state: FSMContext, language: str):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_phone)
    await message.answer(get_text("enter_phone", language))

@router.message(BookingStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext, language: str):
    if not validate_phone(message.text):
        await message.answer(get_text("invalid_phone", language))
        return
    
    await state.update_data(phone=message.text)
    await state.set_state(BookingStates.waiting_reminder)
    await message.answer(
        get_text("choose_reminder", language),
        reply_markup=reminder_kb(language)
    )

@router.message(BookingStates.waiting_reminder)
async def process_reminder(message: Message, state: FSMContext, language: str):
    reminder_map = {
        "10 минут": 10, "10 daqiqa": 10,
        "25 минут": 25, "25 daqiqa": 25,
        "30 минут": 30, "30 daqiqa": 30
    }
    
    minutes = reminder_map.get(message.text, 30)
    await db.update_reminder_minutes(message.from_user.id, minutes)
    
    data = await state.get_data()
    
    # Создаем бронь
    booking_id = await db.add_booking(
        message.from_user.id,
        data['date'],
        data['time'],
        data['phone']
    )
    
    # Отправляем мастеру
    await send_booking_to_masters(
        booking_id,
        data['name'],
        data['phone'],
        data['date'],
        data['time']
    )
    await state.clear()
    is_admin = message.from_user.id == 1265652628
    
    await message.answer(
        get_text("booking_sent", language),
        reply_markup=main_menu_kb(language, is_admin)
    )
    