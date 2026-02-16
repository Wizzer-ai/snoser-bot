import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger

class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn)
        await self.init_db()
        logger.success("Database connected")

    async def init_db(self):
        async with self.pool.acquire() as conn:
            # Тарифы
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS plans (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50),
                    price INT,
                    duration_days INT,
                    requests_limit INT,
                    features TEXT
                )
            ''')

            # Пользователи
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT UNIQUE,
                    username VARCHAR(255),
                    balance INT DEFAULT 0,
                    plan_id INT REFERENCES plans(id) DEFAULT 1,
                    subscription_end TIMESTAMP,
                    referrals_count INT DEFAULT 0,
                    referral_link VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

            # Жалобы
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS complaints (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id),
                    target VARCHAR(255),
                    status VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW(),
                    result TEXT
                )
            ''')

            # Транзакции
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id),
                    amount INT,
                    currency VARCHAR(20),
                    status VARCHAR(50),
                    tx_hash VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

            # Добавляем тарифы если их нет
            tariffs = await conn.fetch('SELECT * FROM plans')
            if not tariffs:
                from config import TARIFFS
                for tid, t in TARIFFS.items():
                    await conn.execute('''
                        INSERT INTO plans (id, name, price, duration_days, requests_limit, features)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    ''', tid, t['name'], t['price'], t['duration_days'], t['requests_limit'], '')

    async def get_user(self, tg_id: int, username: str = None) -> dict:
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow('SELECT * FROM users WHERE tg_id = $1', tg_id)
            if not user:
                ref_link = f"https://t.me/{(await conn.fetchval('SELECT username FROM users WHERE tg_id = $1', 1))}?start={tg_id}"
                user = await conn.fetchrow('''
                    INSERT INTO users (tg_id, username, referral_link)
                    VALUES ($1, $2, $3)
                    RETURNING *
                ''', tg_id, username, ref_link)
            return dict(user)

    async def update_subscription(self, user_id: int, plan_id: int):
        async with self.pool.acquire() as conn:
            plan = await conn.fetchrow('SELECT * FROM plans WHERE id = $1', plan_id)
            end_date = datetime.now() + timedelta(days=plan['duration_days'])
            await conn.execute('''
                UPDATE users 
                SET plan_id = $1, subscription_end = $2 
                WHERE id = $3
            ''', plan_id, end_date, user_id)

    async def add_complaint(self, user_id: int, target: str) -> int:
        async with self.pool.acquire() as conn:
            cid = await conn.fetchval('''
                INSERT INTO complaints (user_id, target, status)
                VALUES ($1, $2, 'pending')
                RETURNING id
            ''', user_id, target)
            return cid