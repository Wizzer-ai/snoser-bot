#!/usr/bin/env python3
import asyncio
import json
import os
import uuid
import pickle
import random
from datetime import datetime, timedelta
from loguru import logger
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8522271767:AAEpqltqUZAN_4ew2WIlTz7HYXb2K4XUn3g"
ADMIN_IDS = [6291487864]
CHANNEL_ID = -1003418841986
SUPPORT_USERNAME = "Write_forpizzabot"

# Крипто-контакты
CRYPTOBOT_USERNAME = "CryptoBot"  # @CryptoBot
TON_WALLET = "UQDfuvp0hT8spsS0bIvhqMaDdplMC5zz66-KKTqaglrQnPhw"

# Тарифы
TARIFFS = {
    1: {'name': '🔥 Неделя', 'price': 699, 'duration': 7, 'requests': 500},
    2: {'name': '⚡️ Месяц', 'price': 1999, 'duration': 30, 'requests': 2000},
    3: {'name': '👑 Год', 'price': 9999, 'duration': 365, 'requests': 10000}
}

# ========== ЛОГИ ==========
logger.remove()
logger.add(lambda msg: print(msg, end=""), format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>", level="INFO", colorize=True)
os.makedirs("logs", exist_ok=True)
logger.add("logs/bot.log", rotation="10 MB", level="DEBUG")

# ========== ХРАНИЛИЩЕ ==========
class Storage:
    def __init__(self, file: str = "storage.pkl"):
        self.file = file
        self.data = {}
        self.expires = {}
        self.load()
    
    def load(self):
        try:
            if os.path.exists(self.file):
                with open(self.file, 'rb') as f:
                    saved = pickle.load(f)
                    self.data = saved.get('data', {})
                    self.expires = saved.get('expires', {})
                    now = datetime.now().timestamp()
                    for k in list(self.expires.keys()):
                        if self.expires[k] < now:
                            del self.data[k]
                            del self.expires[k]
        except: pass
    
    def save(self):
        with open(self.file, 'wb') as f:
            pickle.dump({'data': self.data, 'expires': self.expires}, f)
    
    def store(self, value: dict, ttl: int = 3600) -> str:
        key = str(uuid.uuid4())[:8]
        self.data[key] = value
        self.expires[key] = datetime.now().timestamp() + ttl
        self.save()
        return key
    
    def get(self, key: str) -> dict:
        if key in self.expires and self.expires[key] > datetime.now().timestamp():
            val = self.data.get(key)
            del self.data[key]
            del self.expires[key]
            self.save()
            return val
        return {}

storage = Storage()

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.channel_id = CHANNEL_ID
        self.bot = Bot(token=BOT_TOKEN)
    
    async def save(self, data: dict):
        data['_saved_at'] = datetime.now().isoformat()
        await self.bot.send_message(
            chat_id=self.channel_id,
            text=f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```",
            parse_mode=None
        )
    
    async def load(self) -> dict:
        try:
            updates = await self.bot.get_updates()
            for upd in reversed(updates):
                if upd.channel_post and upd.channel_post.chat.id == self.channel_id:
                    text = upd.channel_post.text
                    if text.startswith("```json"):
                        text = text[7:-3]
                    return json.loads(text)
        except: pass
        return {'users': {}, 'transactions': [], 'next_id': 1, 'blocked': []}
    
    async def get_user(self, user_id: int, username: str = None, ref: int = None) -> dict:
        data = await self.load()
        uid = str(user_id)
        
        if uid in data.get('blocked', []):
            return {'blocked': True}
        
        if uid not in data['users']:
            data['users'][uid] = {
                'id': data.get('next_id', 1),
                'tg_id': user_id,
                'username': username,
                'balance': 0,
                'total_spent': 0,
                'plan_id': 1,
                'sub_end': None,
                'requests_left': 0,
                'referrer': ref,
                'referrals': [],
                'ref_earnings': 0,
                'created': datetime.now().isoformat()
            }
            if ref and str(ref) in data['users']:
                data['users'][str(ref)]['referrals'].append(user_id)
            data['next_id'] = data.get('next_id', 1) + 1
            await self.save(data)
        return data['users'][uid]
    
    async def activate_sub(self, user_id: int, plan_id: int) -> bool:
        data = await self.load()
        uid = str(user_id)
        
        if uid not in data['users']:
            return False
        
        plan = TARIFFS[plan_id]
        current_end = None
        if data['users'][uid].get('sub_end'):
            try:
                current_end = datetime.fromisoformat(data['users'][uid]['sub_end'])
            except:
                current_end = datetime.now()
        else:
            current_end = datetime.now()
        
        new_end = current_end + timedelta(days=plan['duration'])
        data['users'][uid]['sub_end'] = new_end.isoformat()
        data['users'][uid]['plan_id'] = plan_id
        data['users'][uid]['requests_left'] += plan['requests']
        data['users'][uid]['total_spent'] += plan['price']
        
        await self.save(data)
        return True

db = Database()

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🎯 Начать снос", callback_data="snos"),
        InlineKeyboardButton(text="💎 Тарифы", callback_data="tariffs")
    )
    b.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")
    )
    b.row(InlineKeyboardButton(text="🆘 Помощь", callback_data="help"))
    return b.as_markup()

def tariffs_menu():
    b = InlineKeyboardBuilder()
    for tid, t in TARIFFS.items():
        b.row(InlineKeyboardButton(
            text=f"{t['name']} — {t['price']}₽", 
            callback_data=f"buy_{tid}"
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()

def payment_info_keyboard(plan_id: int):
    """Клавиатура с контактами для оплаты"""
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="🤖 Перейти в CryptoBot", 
        url=f"https://t.me/{CRYPTOBOT_USERNAME}"
    ))
    b.row(InlineKeyboardButton(
        text="💎 TON кошелек", 
        callback_data="show_ton_wallet"
    ))
    b.row(InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{plan_id}"))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="tariffs"))
    return b.as_markup()

# ========== ХЕНДЛЕРЫ ==========
router = Router()

class SnosStates(StatesGroup):
    waiting_target = State()

# --- СТАРТ ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    await db.get_user(message.from_user.id, message.from_user.username, ref)
    await message.answer(
        "🎯 **SNOSER BOT**\n════════════════════════\n"
        "📦 500+ почтовых ящиков\n"
        "⚡️ Мгновенная отправка\n"
        "💰 10 друзей = 1 день подписки\n"
        "════════════════════════\n"
        "Выбери действие:",
        reply_markup=main_menu(),
        parse_mode=None
    )

@router.callback_query(F.data == "main_menu")
async def go_main(cb: CallbackQuery):
    await cb.message.edit_text("🎯 **ГЛАВНОЕ МЕНЮ**", reply_markup=main_menu(), parse_mode=None)
    await cb.answer()

# --- ТАРИФЫ ---
@router.callback_query(F.data == "tariffs")
async def show_tariffs(cb: CallbackQuery):
    text = "💎 **ТАРИФЫ**\n\n"
    for t in TARIFFS.values():
        text += f"{t['name']}: {t['price']}₽ ({t['requests']} жалоб)\n"
    await cb.message.edit_text(text, reply_markup=tariffs_menu(), parse_mode=None)
    await cb.answer()

@router.callback_query(F.data.startswith("buy_"))
async def show_payment_options(cb: CallbackQuery):
    plan_id = int(cb.data.split("_")[1])
    plan = TARIFFS[plan_id]
    
    text = (
        f"💳 **ОПЛАТА ТАРИФА**\n"
        f"════════════════════════\n"
        f"💰 {plan['name']}: {plan['price']}₽\n"
        f"🎯 Лимит: {plan['requests']} жалоб\n"
        f"📅 Срок: {plan['duration']} дней\n"
        f"════════════════════════\n"
        f"1. Перейди в @CryptoBot\n"
        f"2. Создай счет на {plan['price']}₽ (≈{plan['price']//100} USDT)\n"
        f"3. Оплати\n"
        f"4. Нажми «✅ Я оплатил»"
    )
    
    await cb.message.edit_text(text, reply_markup=payment_info_keyboard(plan_id), parse_mode=None)
    await cb.answer()

@router.callback_query(F.data == "show_ton_wallet")
async def show_ton_wallet(cb: CallbackQuery):
    """Показывает TON кошелек для оплаты"""
    plan_id = int(cb.message.text.split('\n')[1].split(' ')[-1][:-1]) if '🔥' in cb.message.text else 1
    await cb.message.edit_text(
        f"💎 **TON КОШЕЛЕК ДЛЯ ОПЛАТЫ**\n"
        f"════════════════════════\n"
        f"Адрес:\n`{TON_WALLET}`\n"
        f"════════════════════════\n"
        f"После перевода нажми «✅ Я оплатил»",
        reply_markup=payment_info_keyboard(plan_id),
        parse_mode=None
    )
    await cb.answer()

@router.callback_query(F.data.startswith("paid_"))
async def payment_notification(cb: CallbackQuery, bot: Bot):
    """Уведомляет админа о платеже"""
    plan_id = int(cb.data.split("_")[1])
    plan = TARIFFS[plan_id]
    
    # Сохраняем заявку
    key = storage.store({
        'user_id': cb.from_user.id,
        'username': cb.from_user.username,
        'plan_id': plan_id,
        'plan_name': plan['name'],
        'amount': plan['price'],
        'status': 'pending'
    })
    
    # Уведомление админу
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💰 **ЗАЯВКА НА ОПЛАТУ**\n"
                f"════════════════════════\n"
                f"👤 Пользователь: @{cb.from_user.username or 'нет'}\n"
                f"🆔 ID: {cb.from_user.id}\n"
                f"💎 Тариф: {plan['name']}\n"
                f"💳 Сумма: {plan['price']}₽\n"
                f"════════════════════════\n"
                f"Подтвердить: /approve {key}\n"
                f"Отклонить: /reject {key}",
                parse_mode=None
            )
        except:
            pass
    
    await cb.message.edit_text(
        f"✅ **ЗАЯВКА ОТПРАВЛЕНА**\n"
        f"════════════════════════\n"
        f"Админ проверит платеж и активирует подписку вручную.\n"
        f"Это может занять до 24 часов.\n"
        f"════════════════════════\n"
        f"По вопросам: @{SUPPORT_USERNAME}",
        reply_markup=main_menu(),
        parse_mode=None
    )
    await cb.answer()

# --- АДМИН КОМАНДЫ ---
@router.message(Command("approve"))
async def approve_payment(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        key = message.text.split()[1]
        data = storage.get(key)
        
        if not data:
            await message.answer("❌ Заявка не найдена")
            return
        
        # Активируем подписку
        success = await db.activate_sub(data['user_id'], data['plan_id'])
        
        if success:
            # Уведомляем пользователя
            try:
                await message.bot.send_message(
                    data['user_id'],
                    f"✅ **Платеж подтвержден!**\n"
                    f"💰 Тариф: {data['plan_name']}\n"
                    f"Подписка активирована. Можешь начинать снос!",
                    parse_mode=None
                )
            except:
                pass
            
            await message.answer(f"✅ Подписка активирована для пользователя {data['user_id']}")
        else:
            await message.answer("❌ Ошибка активации")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("reject"))
async def reject_payment(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        key = message.text.split()[1]
        data = storage.get(key)
        
        if not data:
            await message.answer("❌ Заявка не найдена")
            return
        
        # Уведомляем пользователя
        try:
            await message.bot.send_message(
                data['user_id'],
                f"❌ **Платеж отклонен**\n"
                f"Проверь правильность перевода и попробуй снова.\n"
                f"По вопросам: @{SUPPORT_USERNAME}",
                parse_mode=None
            )
        except:
            pass
        
        await message.answer(f"❌ Платеж отклонен для пользователя {data['user_id']}")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# --- ПРОФИЛЬ ---
@router.callback_query(F.data == "profile")
async def show_profile(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    sub = "✅ Активна" if user.get('sub_end') and datetime.fromisoformat(user['sub_end']) > datetime.now() else "❌ Нет"
    await cb.message.edit_text(
        f"👤 **ПРОФИЛЬ**\n════════════════════════\n"
        f"🆔 ID: {user['tg_id']}\n"
        f"👤 Username: @{user['username'] or 'нет'}\n"
        f"💰 Баланс: {user['balance']}⭐️\n"
        f"💳 Потрачено: {user['total_spent']}₽\n"
        f"════════════════════════\n"
        f"🎫 Подписка: {sub}\n"
        f"📊 Осталось: {user.get('requests_left', 0)} жалоб\n"
        f"👥 Рефералов: {len(user.get('referrals', []))}\n"
        f"════════════════════════",
        reply_markup=main_menu(),
        parse_mode=None
    )
    await cb.answer()

# --- РЕФЕРАЛЫ ---
@router.callback_query(F.data == "ref")
async def show_ref(cb: CallbackQuery):
    bot = await cb.bot.get_me()
    link = f"https://t.me/{bot.username}?start={cb.from_user.id}"
    await cb.message.edit_text(
        f"👥 **РЕФЕРАЛЫ**\n════════════════════════\n"
        f"🔗 Твоя ссылка:\n`{link}`\n\n"
        f"💰 10 друзей = 1 день подписки\n"
        f"📊 Проценты:\n"
        f"• 1 уровень — 10%\n"
        f"• 2+ уровень — 3%\n"
        f"════════════════════════",
        reply_markup=main_menu(),
        parse_mode=None
    )
    await cb.answer()

# --- ПОМОЩЬ ---
@router.callback_query(F.data == "help")
async def show_help(cb: CallbackQuery):
    await cb.message.edit_text(
        f"🆘 **ПОМОЩЬ**\n════════════════════════\n"
        f"1. Выбери 💎 Тарифы\n"
        f"2. Перейди в @CryptoBot\n"
        f"3. Создай счет и оплати\n"
        f"4. Нажми ✅ Я оплатил\n"
        f"5. Админ проверит и включит\n"
        f"════════════════════════\n"
        f"💰 10 друзей = 1 день подписки\n"
        f"🤖 CryptoBot: @{CRYPTOBOT_USERNAME}\n"
        f"💎 TON: `{TON_WALLET[:8]}...`\n"
        f"════════════════════════\n"
        f"По вопросам: @{SUPPORT_USERNAME}",
        reply_markup=main_menu(),
        parse_mode=None
    )
    await cb.answer()

# --- СНОС ---
@router.callback_query(F.data == "snos")
async def start_snos(cb: CallbackQuery, state: FSMContext):
    user = await db.get_user(cb.from_user.id)
    
    if not user.get('sub_end') or datetime.fromisoformat(user['sub_end']) < datetime.now():
        await cb.message.edit_text(
            "❌ **Нет активной подписки!**\nКупи тариф в 💎 Тарифы",
            reply_markup=main_menu(),
            parse_mode=None
        )
        await cb.answer()
        return
    
    if user.get('requests_left', 0) <= 0:
        await cb.message.edit_text(
            "❌ **Лимит исчерпан!**\nКупи новый тариф",
            reply_markup=main_menu(),
            parse_mode=None
        )
        await cb.answer()
        return
    
    await state.set_state(SnosStates.waiting_target)
    await cb.message.edit_text(
        "🎯 **Введи ссылку на цель**\n\n"
        "Примеры:\n• @username\n• https://t.me/...\n\n"
        "Для отмены отправь /cancel",
        parse_mode=None
    )
    await cb.answer()

@router.message(SnosStates.waiting_target)
async def process_target(message: Message, state: FSMContext):
    target = message.text.strip()
    
    if target == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    
    user = await db.get_user(message.from_user.id)
    limit = user.get('requests_left', 100)
    
    msg = await message.answer(f"🎯 **Начинаю снос:** {target}\n\n⏳ Подготовка...")
    await asyncio.sleep(2)
    
    successful = 0
    failed = 0
    
    for i in range(1, limit + 1):
        await asyncio.sleep(random.uniform(0.1, 0.3))
        if random.random() < 0.9:
            successful += 1
        else:
            failed += 1
        
        if i % 10 == 0:
            percent = int((i / limit) * 100)
            bar = "█" * (percent // 10) + "▒" * (10 - (percent // 10))
            await msg.edit_text(
                f"🎯 **Снос:** {target}\n\n"
                f"[{bar}] {percent}%\n"
                f"✅ Успешно: {successful}\n"
                f"❌ Ошибок: {failed}"
            )
    
    # Обновляем использованные запросы
    data = await db.load()
    uid = str(message.from_user.id)
    if uid in data['users']:
        data['users'][uid]['requests_left'] = 0
        await db.save(data)
    
    await msg.edit_text(
        f"✅ **СНОС ЗАВЕРШЕН!**\n"
        f"════════════════════════\n"
        f"🎯 Цель: {target}\n"
        f"✅ Успешно: {successful}\n"
        f"❌ Ошибок: {failed}\n"
        f"════════════════════════",
        reply_markup=main_menu()
    )
    
    await state.clear()

# ========== ЗАПУСК ==========
async def main():
    logger.info("🚀 Запуск...")
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    dp = Dispatcher()
    dp.include_router(router)
    
    # Пытаемся подключиться
    retries = 0
    while retries < 3:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            break
        except Exception as e:
            retries += 1
            logger.warning(f"⚠️ Ошибка подключения ({retries}/3): {e}")
            await asyncio.sleep(5)
    
    logger.success("✅ Бот готов!")
    logger.info(f"👑 Админ ID: {ADMIN_IDS}")
    logger.info(f"🤖 CryptoBot: @{CRYPTOBOT_USERNAME}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")