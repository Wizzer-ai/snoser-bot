from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import Database
from keyboards.inline import main_menu

router = Router()

@router.callback_query(F.data == "ref")
async def show_referrals(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"👥 Рефералы\n\nПриглашено: {user['referrals_count']}",
        reply_markup=main_menu()
    )
    await callback.answer()