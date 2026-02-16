from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import main_menu
import asyncio

router = Router()

class SnosStates(StatesGroup):
    waiting_target = State()

@router.callback_query(F.data == "snos")
async def start_snos(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SnosStates.waiting_target)
    await callback.message.edit_text("🎯 Введи ссылку на цель:")
    await callback.answer()

@router.message(SnosStates.waiting_target)
async def process_target(message: Message, state: FSMContext):
    target = message.text
    await state.clear()
    
    msg = await message.answer(f"🎯 Начинаю снос {target}...")
    
    for i in range(1, 11):
        await asyncio.sleep(0.5)
        await msg.edit_text(f"Снос: {i*10}%")
    
    await msg.edit_text("✅ Снос завершен!", reply_markup=main_menu())