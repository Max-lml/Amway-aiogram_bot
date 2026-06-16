import logging
from aiogram import Router, F
from aiogram.types import Message
from database.airtable_api import CACHE

admin_tools_router = Router()

# Твой реальный Telegram ID (обязательно укажи свой)
ADMIN_IDS = [364213802]


@admin_tools_router.message(F.text == "📊 Оценить капитал склада")
async def handle_warehouse_capital(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    logging.info(f"Менеджер {message.from_user.id} запросил расчет капитала склада.")

    # Достаем данные из кэша бота
    raw_products = CACHE.get("data_with_desc")

    if not raw_products:
        await message.answer(
            "⏳ Кэш пуст. Пожалуйста, откройте сначала каталог (кнопка `🛍 Открыть каталог`), "
            "чтобы бот загрузил данные в оперативную память, а затем повторите расчет капитала!"
        )
        return

    total_capital = 0.0
    total_items = 0
    unknown_price_count = 0

    for p in raw_products:
        # Данные уже выпрямлены в корень словаря p ядра бота
        fields_dict = p if isinstance(p, dict) else {}

        # 1. Разбор количества с учетом скрытого пробела из Airtable API!
        availability_raw = fields_dict.get('Availability ') or fields_dict.get('Availability')
        qty = 0

        if availability_raw is not None:
            if isinstance(availability_raw, list) and len(availability_raw) > 0:
                val = availability_raw[0]
            else:
                val = availability_raw
            try:
                qty = int(float(val))
            except (ValueError, TypeError):
                qty = 0

        # 2. Разбор цены
        price_raw = fields_dict.get('Price') or fields_dict.get('price')
        price = 0.0

        if price_raw is not None:
            try:
                price = float(price_raw)
            except (ValueError, TypeError):
                price = 0.0
                if qty > 0:
                    unknown_price_count += 1

        # 3. Калькуляция
        if qty > 0:
            total_capital += price * qty
            total_items += qty

    # Красивый финальный ответ менеджера
    response_text = (
        "📊 *Актуальный отчет по мини-складу:*\n\n"
        f"📦 Всего товаров в наличии: *{total_items} шт.*\n"
        f"💰 Текущий капитал в товаре: *{total_capital:.2f} ₾*\n"
    )

    if unknown_price_count > 0:
        response_text += f"\n⚠️ У {unknown_price_count} товаров в наличии не удалось распознать цену."

    await message.answer(response_text, parse_mode="Markdown")