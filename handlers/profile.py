from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import Database
from keyboards.inline import main_menu

router = Router()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"👤 Профиль\n\nID: {user['tg_id']}",
        reply_markup=main_menu()
    )
    await callback.answer()