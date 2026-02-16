import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS').split(','))) if os.getenv('ADMIN_IDS') else []
DATABASE_URL = os.getenv('DATABASE_URL')

TARIFFS = {
    1: {'name': 'Неделя', 'price': 699, 'duration_days': 7, 'requests_limit': 500},
    2: {'name': 'Месяц', 'price': 1999, 'duration_days': 30, 'requests_limit': 2000},
    3: {'name': 'Год', 'price': 9999, 'duration_days': 365, 'requests_limit': 10000}
}