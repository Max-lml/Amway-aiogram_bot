import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
import os

from config import BOT_TOKEN
from tg_bot.handlers import router
from admin_tools.warehouse import admin_tools_router
from database.airtable_api import get_airtable_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# --- ЭНДПОИНТЫ ДЛЯ WEB APP ---

async def handle_catalog_page(request):
    """Отдает HTML страницу каталога из папки web"""
    # Находим абсолютный путь к папке, где лежит run.py
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # ИСПРАВИЛИ: Добавили 'web' в склейку путей
    file_path = os.path.join(current_dir, 'web', 'catalog.html')

    if os.path.exists(file_path):
        return web.FileResponse(file_path)

    logging.error(f"❌ Файл не найден по пути: {file_path}")
    return web.Response(text=f"Файл catalog.html не найден по пути: {file_path}", status=404)


async def handle_get_products_api(request):
    """Отдает JSON со всеми товарами, используя точные английские имена колонок Airtable"""
    raw_products = await get_airtable_data(need_description=True)
    if raw_products is None:
        return web.json_response([], status=500)

    MY_BRAND_LOGO = "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=500"

    clean_products = []
    for p in raw_products:
        category = p.get('Category') or ''
        name = p.get('Names') or 'Товар'
        articul = p.get('Articul') or '—'
        volume = p.get('Values') or ''
        price = p.get('Price') or '—'
        description = p.get('Attachment Summary') or ''

        # РАЗБОР ДОСТУПНОСТИ (Availability)
        availability_raw = p.get('Availability') or p.get('Availability ')
        quantity = 0

        if availability_raw is not None:
            # Если Airtable вернул массив (например: [3]), достаем число из него
            if isinstance(availability_raw, list) and len(availability_raw) > 0:
                val = availability_raw[0]
            else:
                val = availability_raw

            try:
                # Пробуем перевести в число (float -> int обрабатывает и 3, и 3.0)
                quantity = int(float(val))
            except (ValueError, TypeError):
                # Если там вдруг остался текст ("В наличии")
                val_str = str(val).strip().lower()
                if val_str in ['в наличии', 'yes', 'true', 'available', 'вналичии']:
                    quantity = 1
                else:
                    quantity = 0

            try:
                # Сначала переводим во float (чтобы понять 3.0), а затем в int
                quantity = int(float(val))
            except (ValueError, TypeError):
                # На случай, если в базе остался текст
                val_str = str(val).strip().lower()
                if val_str in ['в наличии', 'yes', 'true', 'available', 'вналичии', '1', '3', '3.0']:
                    quantity = 3
                else:
                    quantity = 0

        # Разбор картинок
        raw_photo = p.get('Photo')
        photo_url = MY_BRAND_LOGO
        if raw_photo:
            if isinstance(raw_photo, list) and len(raw_photo) > 0:
                photo_url = raw_photo[0].get('url', MY_BRAND_LOGO)
            elif isinstance(raw_photo, str):
                photo_url = raw_photo

        clean_products.append({
            "category": str(category),
            "articul": str(articul),
            "name": str(name),
            "volume": str(volume),
            "price": str(price),
            "description": str(description),
            "quantity": quantity,
            "photo": str(photo_url)
        })

    return web.json_response(clean_products)

# --- ЗАПУСК ВСЕЙ СИСТЕМЫ ---

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_tools_router)
    dp.include_router(router)


    # Создаем веб-сервер aiohttp
    app = web.Application()

    # Регистрируем маршруты для Web App витрины
    app.router.add_get('/', handle_catalog_page)
    app.router.add_get('/api/products', handle_get_products_api)

    # Инициализируем бота в фоновом режиме внутри веб-сервера
    runner = web.AppRunner(app)
    await runner.setup()

    # Amvera по умолчанию дает порт 8080 или использует переменную среды PORT
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Веб-сервер витрины успешно запущен на порту {port}!")

    # Запускаем поллинг бота
    logging.info("🤖 Бот успешно запущен в режиме polling!")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Приложение остановлено вручную.")