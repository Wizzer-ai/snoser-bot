from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎯 Начать снос", callback_data="snos"),
        InlineKeyboardButton(text="💎 Тарифы", callback_data="tariffs")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🆘 Помощь", callback_data="help")
    )
    return builder.as_markup()

def tariffs_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔥 699₽/неделя", callback_data="buy_1"),
        InlineKeyboardButton(text="⚡️ 1999₽/месяц", callback_data="buy_2")
    )
    builder.row(
        InlineKeyboardButton(text="👑 9999₽/год", callback_data="buy_3"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )
    return builder.as_markup()

def admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="💰 Доход", callback_data="admin_income")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_mail")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )
    return builder.as_markup()