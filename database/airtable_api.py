import aiohttp
import logging
import time

from config import AIRTABLE_TOKEN, BASE_ID, TABLE_NAME

# --- НАСТРОЙКИ КЭША ---
CACHE = {
    "data_with_desc": None,  # Для консультанта
    "data_without_desc": None,  # Для калькулятора
    "last_update": 0  # Время последнего скачивания
}
CACHE_LIFETIME = 7200  # 2 часа в секундах


# ==========================================
#  БИЗНЕС-ЛОГИКА (Функции)
# ==========================================
async def get_airtable_data(need_description=False, force_update=False):
    """Берет прайс из кэша. force_update=True заставит бота пойти в Airtable."""
    global CACHE
    current_time = time.time()

    if not force_update and CACHE["last_update"] != 0 and (current_time - CACHE["last_update"] < CACHE_LIFETIME):
        logging.info("⚡ Беру данные из локального кэша")
        return CACHE["data_with_desc"] if need_description else CACHE["data_without_desc"]

    logging.info("🔄 Кэш устарел или сброшен принудительно. Скачиваю свежие данные из Airtable...")
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()

                list_with_desc = []
                list_without_desc = []

                records = data.get("records", [])

                # 🚨 ОДНОРАЗОВЫЙ ОТЛАДОЧНЫЙ ЛОГ: смотрим поля самой первой записи в таблице
                if records:
                    first_fields = records[0].get("fields", {})
                    logging.info(f"❓ [ОТЛАДКА] Реальные ключи из Airtable: {list(first_fields.keys())}")

                for record in records:
                    fields = record.get("fields", {})

                    # 1. Копия с описанием (для консультанта)
                    list_with_desc.append(dict(fields))

                    # 2. Копия без описания (для калькулятора)
                    fields_no_desc = dict(fields)
                    fields_no_desc.pop("Attachment Summary", None)
                    list_without_desc.append(fields_no_desc)

                CACHE["data_with_desc"] = list_with_desc
                CACHE["data_without_desc"] = list_without_desc
                CACHE["last_update"] = current_time

                return CACHE["data_with_desc"] if need_description else CACHE["data_without_desc"]

            elif CACHE["last_update"] != 0:
                logging.warning("⚠️ Airtable недоступен! Отдаю старые данные из кэша.")
                return CACHE["data_with_desc"] if need_description else CACHE["data_without_desc"]

            return None