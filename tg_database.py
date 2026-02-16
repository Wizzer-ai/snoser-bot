import json
import asyncio
from aiogram import Bot
from datetime import datetime

class TGDatabase:
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
        self.channel_id = -1003418841986  # ТВОЙ ID КАНАЛА
        self.cache = {}

    async def save(self, data: dict):
        """Сохраняет данные в канал"""
        data['_saved_at'] = datetime.now().isoformat()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        msg = await self.bot.send_message(
            chat_id=self.channel_id,
            text=f"```json\n{json_str}\n```",
            parse_mode="Markdown"
        )
        
        self.cache = data
        return msg.message_id

    async def load(self) -> dict:
        """Загружает последние данные из канала"""
        try:
            msgs = await self.bot.get_updates()
            
            for msg in reversed(msgs):
                if msg.channel_post and msg.channel_post.chat.id == self.channel_id:
                    text = msg.channel_post.text
                    if text.startswith("```json"):
                        text = text[7:-3]
                    data = json.loads(text)
                    self.cache = data
                    return data
        except:
            pass
        return {'users': {}}

    async def get_user(self, user_id: int, username: str = None) -> dict:
        """Получает или создает пользователя"""
        data = await self.load()
        
        uid = str(user_id)
        if uid not in data['users']:
            data['users'][uid] = {
                'tg_id': user_id,
                'username': username,
                'balance': 0,
                'plan_id': 1,
                'subscription_end': None,
                'referrals_count': 0,
                'created_at': datetime.now().isoformat()
            }
            await self.save(data)
        
        return data['users'][uid]

    async def update_user(self, user_id: int, updates: dict):
        """Обновляет данные пользователя"""
        data = await self.load()
        uid = str(user_id)
        
        if uid in data['users']:
            data['users'][uid].update(updates)
            await self.save(data)