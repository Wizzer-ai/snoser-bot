from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from loguru import logger
from keyboards.inline import main_menu
from utils.design import Emoji

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    logger.info(f"User {user_id} started bot")
    
    text = (
        f"{Emoji.TARGET} **SNOSER BOT** {Emoji.TARGET}\n"
        f"{Emoji.CROWN}─────────────────────────────{Emoji.CROWN}\n"
        f"{Emoji.CHECK} 500+ почт\n"
        f"{Emoji.RU} {Emoji.UA} {Emoji.KZ} {Emoji.UZ} {Emoji.US}  номера\n"
        f"{Emoji.FIRE} Мгновенная отправка\n"
        f"{Emoji.CROWN}─────────────────────────────{Emoji.CROWN}\n"
        f"{Emoji.STAR} Выбери действие в меню ниже:"
    )
    
    await message.answer(text, reply_markup=main_menu())

@router.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery):
    text = f"{Emoji.CROWN} **ГЛАВНОЕ МЕНЮ** {Emoji.CROWN}\n\n{Emoji.STAR} Выбери действие:"
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()

@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    text = (
        f"{Emoji.INFO} **ПОМОЩЬ** {Emoji.INFO}\n"
        f"{Emoji.CROWN}─────────────────────────────{Emoji.CROWN}\n"
        f"{Emoji.CHECK} 1. Выбери Тарифы\n"
        f"{Emoji.CHECK} 2. Оплати\n"
        f"{Emoji.CHECK} 3. Нажми Начать снос\n"
        f"{Emoji.CHECK} 4. Введи ссылку\n"
        f"{Emoji.CROWN}─────────────────────────────{Emoji.CROWN}\n"
        f"{Emoji.ROBOT} По вопросам: @Write_forpizzabot"
    )
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()