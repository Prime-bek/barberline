from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import config
from database import db
from keyboards.admin_kb import masters_menu_kb, master_remove_kb, confirm_remove_master_kb
from utils.texts import get_text

router = Router()

class MasterManagementStates(StatesGroup):
    waiting_master_id = State()

def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID

@router.callback_query(F.data == "admin_masters_menu")
async def masters_menu(callback: CallbackQuery, language: str):
    """Главное меню управления мастерами"""
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    
    await callback.message.edit_text(
        get_text("masters_management", language),
        reply_markup=masters_menu_kb(language)
    )

@router.callback_query(F.data == "master_add")
async def add_master_start(callback: CallbackQuery, state: FSMContext, language: str):
    """Начало добавления мастера"""
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    
    await state.set_state(MasterManagementStates.waiting_master_id)
    await callback.message.edit_text(get_text("enter_master_id", language))
    await callback.answer()

@router.message(MasterManagementStates.waiting_master_id)
async def process_master_id(message: Message, state: FSMContext, language: str):
    """Обработка ID мастера"""
    if not is_admin(message.from_user.id):
        await message.answer(get_text("no_access", language))
        await state.clear()
        return
    
    try:
        master_id = int(message.text.strip())
        
        # Проверяем, не является ли уже мастером
        if await db.is_master(master_id):
            await message.answer(get_text("master_already_exists", language))
            return
        
        # Получаем данные пользователя
        user = await db.get_user(master_id)
        if not user:
            await message.answer(get_text("user_not_found", language))
            return
        
        # Добавляем мастера
        success = await db.add_master(
            master_id, 
            user['full_name'], 
            user['username'], 
            message.from_user.id
        )
        
        if success:
            await message.answer(
                get_text("master_added", language, 
                        name=user['full_name'],
                        id=master_id,
                        username=user['username'] or "нет"),
                reply_markup=masters_menu_kb(language)
            )
            
            # Уведомляем нового мастера
            try:
                from aiogram import Bot
                from config import config
                bot = Bot(token=config.BOT_TOKEN)
                await bot.send_message(
                    master_id,
                    "✅ Вам назначены права мастера!\n\nТеперь вы будете получать заявки на бронь."
                )
            except Exception as e:
                print(f"Could not notify new master: {e}")
        else:
            await message.answer("❌ Ошибка при добавлении мастера.")
            
    except ValueError:
        await message.answer("❌ Пожалуйста, введите числовой ID пользователя.")
    
    await state.clear()

@router.callback_query(F.data == "master_list")
async def list_masters(callback: CallbackQuery, language: str):
    """Список всех мастеров"""
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    
    masters = await db.get_all_masters()
    
    if not masters:
        await callback.message.edit_text(
            get_text("no_masters", language),
            reply_markup=masters_menu_kb(language)
        )
        return
    
    text = get_text("masters_list", language)
    for i, master in enumerate(masters, 1):
        text += get_text("master_info", language,
                        num=i,
                        name=master['full_name'],
                        id=master['id'],
                        username=master['username'] or "нет",
                        date=master['added_at'][:10])
    
    await callback.message.edit_text(
        text,
        reply_markup=masters_menu_kb(language)
    )

@router.callback_query(F.data == "master_remove_list")
async def remove_master_list(callback: CallbackQuery, language: str):
    """Показать список для удаления"""
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    
    masters = await db.get_all_masters()
    
    if not masters:
        await callback.message.edit_text(
            get_text("no_masters", language),
            reply_markup=masters_menu_kb(language)
        )
        return
    
    await callback.message.edit_text(
        get_text("select_master_to_remove", language),
        reply_markup=master_remove_kb(masters, language)
    )

@router.callback_query(F.data.startswith("master_del_"))
async def confirm_remove_master(callback: CallbackQuery, language: str):
    """Подтверждение удаления"""
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    
    master_id = int(callback.data.split("_")[2])
    master = await db.get_master(master_id)
    
    if not master:
        await callback.answer(get_text("master_not_found", language))
        return
    
    text = f"❌ Удалить мастера?\n\n👤 {master['full_name']}\n🆔 ID: {master_id}"
    
    await callback.message.edit_text(
        text,
        reply_markup=confirm_remove_master_kb(master_id, language)
    )

@router.callback_query(F.data.startswith("master_confirm_del_"))
async def do_remove_master(callback: CallbackQuery, language: str):
    """Фактическое удаление мастера"""
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("no_access", language))
        return
    
    master_id = int(callback.data.split("_")[3])
    
    # Уведомляем мастера об удалении прав
    try:
        from aiogram import Bot
        from config import config
        bot = Bot(token=config.BOT_TOKEN)
        await bot.send_message(
            master_id,
            "❌ Ваши права мастера были отозваны."
        )
    except Exception as e:
        print(f"Could not notify master: {e}")
    
    await db.remove_master(master_id)
    
    await callback.message.edit_text(
        get_text("master_removed", language),
        reply_markup=masters_menu_kb(language)
    )