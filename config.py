import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Читаем переменные
BOT_TOKEN = os.getenv("BOT_TOKEN")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = os.getenv("BASE_ID")
TABLE_NAME = os.getenv("TABLE_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Твой Telegram ID для проверки прав админа
ADMIN_ID = 364213802

# Проверка: если какого-то важного ключа нет, программа сразу остановится с ошибкой
if not all([BOT_TOKEN, AIRTABLE_TOKEN, BASE_ID, TABLE_NAME, GEMINI_API_KEY]):
    raise ValueError("Ошибка: Один или несколько ключей не найдены в файле .env!")