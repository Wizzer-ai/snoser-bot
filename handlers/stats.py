from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import main_menu

router = Router()

@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    await callback.message.edit_text(
        "📊 Статистика временно недоступна",
        reply_markup=main_menu()
    )
    await callback.answer()