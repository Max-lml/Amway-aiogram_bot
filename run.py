import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def main():
    # Инициализируем бота ключом из нашего нового config.py
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # ТУТ ПОЗЖЕ МЫ ПОДКЛЮЧИМ НАШИ ХЭНДЛЕРЫ
    # dp.include_router(main_router)

    logging.info("Бот успешно запущен!")
    # Запускаем опрос серверов Telegram
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Красиво завершаем работу, если нажали Ctrl+C в терминале
        logging.info("Бот остановлен вручную.")