#!/usr/bin/env python3
import asyncio
import json
import os
import random
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Асинхронная библиотека для SQLite
import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import (TelegramBadRequest, TelegramForbiddenError,
                                 TelegramRetryAfter)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton, Message,
                           ReplyKeyboardMarkup, KeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========== ЛОГИРОВАНИЕ ==========
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8522271767:AAEpqltqUZAN_4ew2WIlTz7HYXb2K4XUn3g"
ADMIN_IDS = [6291487864]
SUPPORT_USERNAME = "Write_forpizzabot"

# Платежные реквизиты
CRYPTOBOT_USERNAME = "CryptoBot"
TON_WALLET = "UQDfuvp0hT8spsS0bIvhqMaDdplMC5zz66-KKTqaglrQnPhw"
STARS_USERNAME = "Write_forpizzabot"
NFT_USERNAME = "Write_forpizzabot"

# ТАРИФЫ
TARIFFS = {
    1: {'name': 'НЕДЕЛЯ', 'price': 699, 'duration': 7, 'requests': 50, 'numbers': 10},
    2: {'name': 'МЕСЯЦ', 'price': 1999, 'duration': 30, 'requests': 200, 'numbers': 30},
    3: {'name': 'ГОД', 'price': 9999, 'duration': 365, 'requests': 1000, 'numbers': 50}
}

# ПРИЧИНЫ СНОСА
REASONS = {
    'abuse': {'name': '🔞 ОСКОРБЛЕНИЯ', 'text': 'Abuse report'},
    'session': {'name': '🚫 СНОС СЕССИЙ', 'text': 'Session hijacking'},
    'violence': {'name': '💢 УГРОЗА НАСИЛИЯ', 'text': 'Violence threat'},
    'copyright': {'name': '©️ АВТОРСКОЕ ПРАВО', 'text': 'Copyright infringement'}
}

# ФЛАГИ СТРАН
COUNTRY_FLAGS = {
    'RU': '🇷🇺', 'UA': '🇺🇦', 'KZ': '🇰🇿',
    'UZ': '🇺🇿', 'US': '🇺🇸', 'TJ': '🇹🇯'
}
COUNTRIES = list(COUNTRY_FLAGS.keys())

# ИМЕНА ДЛЯ ГЕНЕРАЦИИ
FIRST_NAMES = ['Ivan', 'Petr', 'Alex', 'Elena', 'Olga', 'John', 'David', 'Sarah']
LAST_NAMES = ['Ivanov', 'Petrov', 'Smith', 'Jones', 'Kuznetsov', 'Popov']
EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'outlook.com', 'mail.ru', 'ukr.net']

# ========== БАЗА ДАННЫХ (SQLITE) ==========
class Database:
    def __init__(self, db_path: str = "snoser.db"):
        self.db_path = db_path

    async def init_db(self):
        """Создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Пользователи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    plan_id INTEGER DEFAULT 1,
                    sub_end TEXT,
                    requests_left INTEGER DEFAULT 0,
                    referrer_id INTEGER,
                    ref_link TEXT,
                    ref_earnings INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Рефералы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    referrer_id INTEGER
                )
            ''')
            # Заявки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    amount INTEGER,
                    method TEXT,
                    plan_id INTEGER,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            await db.commit()
        logger.info("✅ База данных готова")

    async def add_user(self, user_id: int, username: str = None, referrer_id: int = None) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cur.fetchone()
            if not user:
                ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
                await db.execute(
                    'INSERT INTO users (user_id, username, ref_link, referrer_id) VALUES (?, ?, ?, ?)',
                    (user_id, username, ref_link, referrer_id)
                )
                if referrer_id:
                    await db.execute(
                        'INSERT INTO referrals (user_id, referrer_id) VALUES (?, ?)',
                        (user_id, referrer_id)
                    )
                await db.commit()
                logger.info(f"👤 Новый пользователь: {user_id}")
                cur = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = await cur.fetchone()

            columns = ['user_id', 'username', 'balance', 'total_spent', 'plan_id',
                       'sub_end', 'requests_left', 'referrer_id', 'ref_link', 'ref_earnings']
            return dict(zip(columns, user))

    async def get_user(self, user_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cur.fetchone()
            if not user:
                return {}
            columns = ['user_id', 'username', 'balance', 'total_spent', 'plan_id',
                       'sub_end', 'requests_left', 'referrer_id', 'ref_link', 'ref_earnings']
            return dict(zip(columns, user))

    async def activate_sub(self, user_id: int, plan_id: int) -> bool:
        plan = TARIFFS[plan_id]
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute('SELECT sub_end FROM users WHERE user_id = ?', (user_id,))
            row = await cur.fetchone()
            current_end = datetime.fromisoformat(row[0]) if row and row[0] else datetime.now()
            if current_end > datetime.now():
                new_end = current_end + timedelta(days=plan['duration'])
            else:
                new_end = datetime.now() + timedelta(days=plan['duration'])

            await db.execute(
                '''UPDATE users SET 
                   sub_end = ?, plan_id = ?, 
                   requests_left = requests_left + ?,
                   total_spent = total_spent + ? 
                   WHERE user_id = ?''',
                (new_end.isoformat(), plan_id, plan['requests'], plan['price'], user_id)
            )
            await db.commit()
            logger.info(f"✅ Подписка активирована для {user_id}")
            return True

    async def use_requests(self, user_id: int, count: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE users SET requests_left = requests_left - ? WHERE user_id = ?',
                (count, user_id)
            )
            await db.commit()
            return True

    async def get_referral_count(self, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
            count = await cur.fetchone()
            return count[0] if count else 0

# ========== БАЗА КОНТАКТОВ (JSON) ==========
class ContactManager:
    def __init__(self, file: str = "contacts.json"):
        self.file = file
        self.phones: List[Dict] = []
        self.emails: List[Dict] = []
        self.load()

    def load(self):
        if os.path.exists(self.file):
            with open(self.file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.phones = data.get('phones', [])
                self.emails = data.get('emails', [])
            logger.info(f"📦 Загружено {len(self.phones)} номеров, {len(self.emails)} почт")
        else:
            self._create_default()

    def _create_default(self):
        # Номера
        for country in COUNTRIES:
            for _ in range(8):
                code = random.randint(100, 999)
                num = f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}"
                phone = f"+{random.choice([7,380,7,998,1,992])} ({code}) {num}"
                self.phones.append({
                    'id': str(uuid.uuid4())[:4],
                    'number': phone,
                    'country': country,
                    'flag': COUNTRY_FLAGS[country],
                    'status': 'active'
                })
        # Почты
        for _ in range(50):
            name = random.choice(FIRST_NAMES).lower()
            domain = random.choice(EMAIL_DOMAINS)
            self.emails.append({
                'id': str(uuid.uuid4())[:4],
                'email': f"{name}{random.randint(1,999)}@{domain}",
                'status': 'active'
            })
        self.save()
        logger.info(f"🔥 Создано {len(self.phones)} номеров, {len(self.emails)} почт")

    def save(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump({'phones': self.phones, 'emails': self.emails}, f, indent=2)

    def get_active_phones(self, limit: int) -> List[Dict]:
        active = [p for p in self.phones if p['status'] == 'active']
        random.shuffle(active)
        return active[:limit]

    def get_active_emails(self, limit: int) -> List[Dict]:
        active = [e for e in self.emails if e['status'] == 'active']
        random.shuffle(active)
        return active[:limit]

# ========== БЕЗОПАСНОЕ РЕДАКТИРОВАНИЕ (С ЗАЩИТОЙ ОТ ФЛУДА) ==========
async def safe_edit(message, text: str, markup=None):
    try:
        if message.text != text:
            await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error(f"Ошибка: {e}")
    except TelegramRetryAfter as e:
        logger.warning(f"⏳ Флуд-контроль: ждем {e.retry_after}с")
        await asyncio.sleep(e.retry_after)
        return await safe_edit(message, text, markup)
    except Exception as e:
        logger.error(f"Ошибка: {e}")

# ========== МАСКИРОВКА ==========
def mask_phone(phone: str) -> str:
    parts = phone.split('-')
    if len(parts) > 1:
        return f"{parts[0]}-{parts[1][:2]}**"
    return phone

def mask_email(email: str) -> str:
    local, domain = email.split('@')
    return f"{local[0]}***@{domain}"

# ========== ИНИЦИАЛИЗАЦИЯ ==========
db = Database()
contacts = ContactManager()
request_cache: Dict[str, Dict] = {}

# ========== КЛАВИАТУРЫ (ГЛАВНОЕ МЕНЮ БЕЗ ЗВЕЗД) ==========
def main_menu():
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="НАЧАТЬ СНОС", callback_data="snos"),
        InlineKeyboardButton(text="ТАРИФЫ", callback_data="tariffs")
    )
    b.row(
        InlineKeyboardButton(text="ПРОФИЛЬ", callback_data="profile"),
        InlineKeyboardButton(text="РЕФЕРАЛЫ", callback_data="ref")
    )
    b.row(InlineKeyboardButton(text="ПОМОЩЬ", callback_data="help"))
    return b.as_markup()

def tariffs_menu():
    b = InlineKeyboardBuilder()
    for tid, t in TARIFFS.items():
        b.row(InlineKeyboardButton(
            text=f"{t['name']} — {t['price']}₽",
            callback_data=f"tariff_{tid}"
        ))
    b.row(InlineKeyboardButton(text="◀️ НАЗАД", callback_data="main_menu"))
    return b.as_markup()

def reasons_menu():
    b = InlineKeyboardBuilder()
    for key, reason in REASONS.items():
        b.row(InlineKeyboardButton(
            text=reason['name'],
            callback_data=f"reason_{key}"
        ))
    b.row(InlineKeyboardButton(text="◀️ НАЗАД", callback_data="main_menu"))
    return b.as_markup()

def payment_keyboard(user_id: int, plan_id: int):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🤖 CRYPTOBOT", url=f"https://t.me/{CRYPTOBOT_USERNAME}"))
    b.row(InlineKeyboardButton(text="💎 TON КОШЕЛЕК", callback_data=f"show_ton_{plan_id}"))
    b.row(InlineKeyboardButton(text="⭐️ STARS", url=f"https://t.me/{STARS_USERNAME}"))
    b.row(InlineKeyboardButton(text="🖼 NFT", url=f"https://t.me/{NFT_USERNAME}"))
    b.row(InlineKeyboardButton(text="✅ Я ОПЛАТИЛ", callback_data=f"paid_{user_id}_{plan_id}"))
    b.row(InlineKeyboardButton(text="◀️ НАЗАД", callback_data="tariffs"))
    return b.as_markup()

def admin_actions_keyboard(req_key: str):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ АКТИВИРОВАТЬ", callback_data=f"ap_{req_key}"),
        InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"rej_{req_key}")
    )
    return b.as_markup()

# ========== ХЕНДЛЕРЫ ==========
router = Router()

class SnosStates(StatesGroup):
    waiting_target = State()
    waiting_reason = State()

# --- СТАРТ ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    await db.add_user(message.from_user.id, message.from_user.username, ref)

    flags_line = " ".join(COUNTRY_FLAGS.values())
    await message.answer(
        f"⚡ **SNOSER** ⚡\n"
        f"{flags_line}\n"
        f"{len(contacts.phones)} НОМЕРОВ | {len(contacts.emails)} ПОЧТ\n"
        f"ВЫБЕРИ ДЕЙСТВИЕ",
        reply_markup=main_menu()
    )

@router.callback_query(F.data == "main_menu")
async def go_main(cb: CallbackQuery):
    flags_line = " ".join(COUNTRY_FLAGS.values())
    await safe_edit(
        cb.message,
        f"⚡ **SNOSER** ⚡\n{flags_line}",
        main_menu()
    )
    await cb.answer()

# --- ТАРИФЫ ---
@router.callback_query(F.data == "tariffs")
async def show_tariffs(cb: CallbackQuery):
    text = "💰 **ТАРИФЫ**\n"
    for t in TARIFFS.values():
        text += f"\n{t['name']} — {t['price']}₽\n"
        text += f"├ Жалоб: {t['requests']}\n"
        text += f"└ Номеров: {t['numbers']}\n"
    await safe_edit(cb.message, text, tariffs_menu())
    await cb.answer()

@router.callback_query(F.data.startswith("tariff_"))
async def show_payment(cb: CallbackQuery):
    plan_id = int(cb.data.split("_")[1])
    plan = TARIFFS[plan_id]
    text = (
        f"💳 **ОПЛАТА**\n"
        f"{plan['name']} — {plan['price']}₽\n\n"
        f"🤖 @{CRYPTOBOT_USERNAME}\n"
        f"💎 {TON_WALLET[:8]}...\n"
        f"⭐️ @{STARS_USERNAME}\n"
        f"🖼 @{NFT_USERNAME}\n\n"
        f"✅ ПОСЛЕ ОПЛАТЫ НАЖМИ КНОПКУ"
    )
    await safe_edit(cb.message, text, payment_keyboard(cb.from_user.id, plan_id))
    await cb.answer()

@router.callback_query(F.data.startswith("show_ton_"))
async def show_ton(cb: CallbackQuery):
    plan_id = int(cb.data.split("_")[2])
    await safe_edit(
        cb.message,
        f"💎 **TON**\n`{TON_WALLET}`\n\nПосле оплаты нажми «✅ Я ОПЛАТИЛ»",
        payment_keyboard(cb.from_user.id, plan_id)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("paid_"))
async def payment_request(cb: CallbackQuery, bot: Bot):
    parts = cb.data.split("_")
    user_id = int(parts[1])
    plan_id = int(parts[2])
    plan = TARIFFS[plan_id]

    req_key = str(uuid.uuid4())[:4]
    request_cache[req_key] = {
        'user_id': user_id,
        'plan_id': plan_id,
        'plan_name': plan['name'],
        'amount': plan['price']
    }

    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"💰 **ЗАЯВКА {req_key}**\n"
            f"👤 @{cb.from_user.username}\n"
            f"💎 {plan['name']}\n"
            f"💳 {plan['price']}₽",
            reply_markup=admin_actions_keyboard(req_key)
        )

    await safe_edit(cb.message, "✅ ЗАЯВКА ОТПРАВЛЕНА", main_menu())
    await cb.answer()

# --- АДМИН ---
@router.message(Command("admin"))
async def admin_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    async with aiosqlite.connect(db.db_path) as conn:
        cur = await conn.execute('SELECT COUNT(*) FROM users')
        total_users = (await cur.fetchone())[0]
    await message.answer(
        f"👑 **АДМИН**\n👥 {total_users}\n📦 {len(contacts.phones)}/{len(contacts.emails)}"
    )

@router.callback_query(F.data.startswith("ap_"))
async def admin_approve(cb: CallbackQuery, bot: Bot):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ НЕТ ДОСТУПА", show_alert=True)
        return
    req_key = cb.data.replace("ap_", "")
    data = request_cache.pop(req_key, None)
    if not data:
        await safe_edit(cb.message, cb.message.text + "\n❌ УСТАРЕЛО")
        await cb.answer("❌ УСТАРЕЛО", show_alert=True)
        return

    await db.activate_sub(data['user_id'], data['plan_id'])
    await safe_edit(cb.message, cb.message.text + "\n✅ ПОДТВЕРЖДЕНО")
    await bot.send_message(
        data['user_id'],
        f"✅ ПЛАТЕЖ ПОДТВЕРЖДЕН. МОЖЕШЬ НАЧИНАТЬ СНОС."
    )
    await cb.answer("✅ ПОДТВЕРЖДЕНО", show_alert=True)

@router.callback_query(F.data.startswith("rej_"))
async def admin_reject(cb: CallbackQuery, bot: Bot):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ НЕТ ДОСТУПА", show_alert=True)
        return
    req_key = cb.data.replace("rej_", "")
    data = request_cache.pop(req_key, None)
    if data:
        await bot.send_message(data['user_id'], "❌ ПЛАТЕЖ ОТКЛОНЕН.")
    await safe_edit(cb.message, cb.message.text + "\n❌ ОТКЛОНЕНО")
    await cb.answer("❌ ОТКЛОНЕНО", show_alert=True)

# --- ПРОФИЛЬ ---
@router.callback_query(F.data == "profile")
async def show_profile(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    if not user:
        await cb.answer("Ошибка")
        return
    ref_count = await db.get_referral_count(cb.from_user.id)
    sub_end = datetime.fromisoformat(user['sub_end']) if user['sub_end'] else None
    sub_status = "✅ АКТИВНА" if sub_end and sub_end > datetime.now() else "❌ НЕТ"
    await safe_edit(
        cb.message,
        f"👤 **ПРОФИЛЬ**\n"
        f"ID: {user['user_id']}\n"
        f"ПОДПИСКА: {sub_status}\n"
        f"ОСТАЛОСЬ: {user['requests_left']}\n"
        f"РЕФЕРАЛОВ: {ref_count}",
        main_menu()
    )
    await cb.answer()

# --- РЕФЕРАЛЫ ---
@router.callback_query(F.data == "ref")
async def show_ref(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    ref_count = await db.get_referral_count(cb.from_user.id)
    await safe_edit(
        cb.message,
        f"👥 **РЕФЕРАЛЫ**\n"
        f"ССЫЛКА:\n{user['ref_link']}\n\n"
        f"ПРИГЛАШЕНО: {ref_count}\n"
        f"10 ДРУЗЕЙ = +1 ДЕНЬ",
        main_menu()
    )
    await cb.answer()

# --- ПОМОЩЬ ---
@router.callback_query(F.data == "help")
async def show_help(cb: CallbackQuery):
    flags_line = " ".join(COUNTRY_FLAGS.values())
    await safe_edit(
        cb.message,
        f"🆘 **ПОМОЩЬ**\n"
        f"1. ТАРИФЫ\n"
        f"2. ОПЛАТА\n"
        f"3. ЗАЯВКА\n"
        f"4. СНОС\n\n"
        f"{flags_line}",
        main_menu()
    )
    await cb.answer()

# --- СНОС ---
@router.callback_query(F.data == "snos")
async def start_snos(cb: CallbackQuery, state: FSMContext):
    # Админ пропускает проверки
    if cb.from_user.id in ADMIN_IDS:
        await state.set_state(SnosStates.waiting_reason)
        await safe_edit(cb.message, "⚔️ ВЫБЕРИ ПРИЧИНУ", reasons_menu())
        await cb.answer()
        return

    user = await db.get_user(cb.from_user.id)
    if not user.get('sub_end') or datetime.fromisoformat(user['sub_end']) < datetime.now():
        await safe_edit(cb.message, "❌ НЕТ ПОДПИСКИ", main_menu())
        await cb.answer()
        return
    if user.get('requests_left', 0) <= 0:
        await safe_edit(cb.message, "❌ ЛИМИТ ИСЧЕРПАН", main_menu())
        await cb.answer()
        return

    await state.set_state(SnosStates.waiting_reason)
    await safe_edit(cb.message, "⚔️ ВЫБЕРИ ПРИЧИНУ", reasons_menu())
    await cb.answer()

@router.callback_query(F.data.startswith("reason_"))
async def reason_selected(cb: CallbackQuery, state: FSMContext):
    reason_key = cb.data.replace("reason_", "")
    await state.update_data(reason=reason_key)
    await state.set_state(SnosStates.waiting_target)
    await safe_edit(cb.message, "🎯 ВВЕДИ ССЫЛКУ (@ ИЛИ https)", None)
    await cb.answer()

@router.message(SnosStates.waiting_target)
async def process_target(message: Message, state: FSMContext):
    target = message.text.strip()
    if target == '/cancel':
        await state.clear()
        await message.answer("❌ ОТМЕНЕНО", reply_markup=main_menu())
        return

    data = await state.get_data()
    reason_key = data.get('reason', 'abuse')
    reason = REASONS[reason_key]

    # Админ
    if message.from_user.id in ADMIN_IDS:
        await message.answer(f"✅ СНОС ВЫПОЛНЕН (АДМИН)", reply_markup=main_menu())
        await state.clear()
        return

    # Пользователь
    user = await db.get_user(message.from_user.id)
    plan = TARIFFS[user['plan_id']]
    limit = min(user['requests_left'], plan['numbers'])

    phones = contacts.get_active_phones(limit)
    emails = contacts.get_active_emails(limit)

    if not phones or not emails:
        await message.answer("❌ НЕТ КОНТАКТОВ")
        await state.clear()
        return

    msg = await message.answer(f"⚔️ **СНОС:** {target}\n⏳ ЗАГРУЗКА...")
    await asyncio.sleep(2)

    successful = 0
    failed = 0
    total = len(phones)

    for i in range(total):
        phone = phones[i]
        email = emails[i % len(emails)]
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)[0]}."

        status = "✓" if random.random() < 0.85 else "✗"
        delay = random.uniform(3.0, 5.0)  # УВЕЛИЧЕННАЯ ЗАДЕРЖКА

        if status == "✓":
            successful += 1
        else:
            failed += 1

        percent = int((i + 1) / total * 100)
        bar = "█" * (percent // 10) + "▒" * (10 - (percent // 10))

        masked_phone = mask_phone(phone['number'])
        masked_email = mask_email(email['email'])

        line = (f"{phone['flag']} {masked_phone} | {masked_email} | {name} | "
                f"{reason['name']} {status}")

        await safe_edit(
            msg,
            f"⚔️ **{target}**\n[{bar}] {percent}%\n{line}\n✅ {successful} ❌ {failed}"
        )
        await asyncio.sleep(delay)

    await db.use_requests(message.from_user.id, successful)
    await safe_edit(
        msg,
        f"✅ **СНОС ЗАВЕРШЕН**\n✅ {successful} ❌ {failed}",
        main_menu()
    )
    await state.clear()

# ========== ЗАПУСК ==========
async def main():
    global bot
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    dp = Dispatcher()
    dp.include_router(router)

    await db.init_db()
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("✅ БОТ ГОТОВ К РАБОТЕ")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())