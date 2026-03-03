from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from services.scheduler import schedule_reminder
from services.notifications import notify_user_approved, notify_user_rejected
from utils.texts import get_text

router = Router()

class MasterStates(StatesGroup):
    waiting_reject_reason = State()

@router.callback_query(F.data.startswith("accept_"))
async def accept_booking(callback: CallbackQuery):
    if not await db.is_master(callback.from_user.id):
        await callback.answer(get_text("not_master", "ru"))
        return
    
    booking_id = int(callback.data.split("_")[1])
    booking = await db.get_booking(booking_id)
    
    if not booking:
        await callback.answer("Бронь не найдена")
        return
    
    if booking['status'] != 'pending':
        await callback.answer("Эта заявка уже обработана")
        return
    
    await db.update_booking_status(booking_id, "approved")
    await schedule_reminder(booking_id)
    
    await notify_user_approved(
        booking['user_id'],
        booking['date'],
        booking['time'],
        booking['language']
    )
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ ПРИНЯТО"
    )
    await callback.answer("Бронь подтверждена")

@router.callback_query(F.data.startswith("reject_"))
async def reject_booking_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_master(callback.from_user.id):
        await callback.answer(get_text("not_master", "ru"))
        return
    
    booking_id = int(callback.data.split("_")[1])
    await state.update_data(booking_id=booking_id)
    await state.set_state(MasterStates.waiting_reject_reason)
    
    await callback.message.answer(get_text("enter_reject_reason", "ru"))
    await callback.answer()

@router.message(MasterStates.waiting_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    booking_id = data['booking_id']
    
    booking = await db.get_booking(booking_id)
    if not booking:
        await message.answer("Бронь не найдена")
        await state.clear()
        return
    
    await db.update_booking_status(booking_id, "rejected", message.text)
    
    await notify_user_rejected(
        booking['user_id'],
        message.text,
        booking['language']
    )
    
    await message.answer(get_text("booking_rejected_master", "ru"))
    await state.clear()