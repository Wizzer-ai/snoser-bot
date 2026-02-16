from aiogram import Router, F
from aiogram.types import CallbackQuery
from config import TARIFFS
from keyboards.inline import tariffs_menu, main_menu

router = Router()

@router.callback_query(F.data == "tariffs")
async def show_tariffs(callback: CallbackQuery):
    text = "💰 **ТАРИФЫ**\n\n"
    for tid, t in TARIFFS.items():
        text += f"{t['name']}: {t['price']}₽\n"
    
    await callback.message.edit_text(text, reply_markup=tariffs_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def buy_tariff(callback: CallbackQuery):
    await callback.message.edit_text(
        "Оплата временно недоступна",
        reply_markup=main_menu()
    )
    await callback.answer()