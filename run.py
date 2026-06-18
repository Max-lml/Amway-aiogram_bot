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
    """Отдает HTML страницу каталога из папки web в виде явного текстового ответа с UTF-8"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'web', 'catalog.html')

    if os.path.exists(file_path):
        try:
            # Читаем файл вручную, чтобы избежать багов с кэшированием размера FileResponse
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            logging.info(f"📄 [ВЕБ] Файл catalog.html успешно прочитан. Размер: {len(html_content)} символов.")

            return web.Response(
                text=html_content,
                content_type='text/html',
                charset='utf-8'
            )
        except Exception as e:
            logging.error(f"❌ [ВЕБ] Ошибка при чтении файла catalog.html: {e}")
            return web.Response(text="Внутренняя ошибка сервера при чтении каталога.", status=500)

    logging.error(f"❌ [ВЕБ] Файл не найден по пути: {file_path}")
    return web.Response(text="Файл каталога не найден на сервере.", status=404)


async def handle_get_products_api(request):
    """Отдает JSON товаров с максимальным локальным логированием для отладки"""
    logging.info("==================================================")
    logging.info("🚀 [БЭКЕНД] Локальная витрина вызвала API /api/products")

    try:
        logging.info("📡 [БЭКЕНД] Запрашиваем данные из get_airtable_data()...")
        raw_products = await get_airtable_data(need_description=True)

        if raw_products is None:
            logging.error("❌ [БЭКЕНД] Airtable вернул None! Проверь токены, базу или подключение к интернету.")
            return web.json_response([])

        logging.info(f"📋 [БЭКЕНД] Получено {len(raw_products)} сырых строк из Airtable.")

        # Если пришел пустой список, пишем предупреждение
        if len(raw_products) == 0:
            logging.warning(
                "⚠️ [БЭКЕНД] Массив из Airtable пустой. Возможно, кэш еще не создался. Напиши боту /update !")

    except Exception as e:
        logging.error(f"💥 [БЭКЕНД] Критическая ошибка при чтении Airtable: {e}", exc_info=True)
        return web.json_response([], status=500)

    clean_products = []
    MY_BRAND_LOGO = "https://disk.yandex.ru/i/dRTX_P_WOfyIXw"

    for index, p in enumerate(raw_products):
        # Смотрим, какие ключи вообще есть в первой строчке (для отладки структуры)
        if index == 0:
            logging.info(f"🔍 [ОТЛАДКА] Ключи первой строки из Airtable: {list(p.keys())}")

        category = p.get('Category') or ''
        name = p.get('Names') or ''
        articul = p.get('Articul') or '—'
        volume = p.get('Values') or ''
        price = p.get('Price') or '—'
        description = p.get('Attachment Summary') or ''

        # Проверяем, не пустая ли строка
        if not name and not category:
            logging.warning(f"⚠️ [БЭКЕНД] Строка #{index} пропущена: нет ни имени, ни категории. Данные: {p}")
            continue

        # Разбор доступности
        availability_raw = p.get('Availability') or p.get('Availability ')
        quantity = 0
        if availability_raw is not None:
            if isinstance(availability_raw, list) and len(availability_raw) > 0:
                val = availability_raw[0]
            else:
                val = availability_raw
            try:
                quantity = int(float(val))
            except (ValueError, TypeError):
                val_str = str(val).strip().lower()
                if val_str in ['в наличии', 'yes', 'true', 'available', 'вналичии', '1', '3']:
                    quantity = 3

        # Разбор фото
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

    logging.info(f"📦 [БЭКЕНД] Успешно обработано и отправлено на витрину {len(clean_products)} карточек.")
    logging.info("==================================================")
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