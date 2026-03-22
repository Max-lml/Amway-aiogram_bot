import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN

# Импортируем наш роутер из папки tg_bot
from tg_bot.handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # ПОДКЛЮЧАЕМ РОУТЕР
    dp.include_router(router)

    logging.info("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен вручную.")