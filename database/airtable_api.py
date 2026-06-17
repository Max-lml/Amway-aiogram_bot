import  aiohttp
import logging
import time

from config import AIRTABLE_TOKEN, BASE_ID, TABLE_NAME


# --- НАСТРОЙКИ КЭША ---
# Словарь, где мы будем хранить скачанные данные
CACHE = {
    "data_with_desc": None,     # Для консультанта
    "data_without_desc": None,  # Для калькулятора
    "last_update": 0            # Время последнего скачивания
}
CACHE_LIFETIME = 7200  # 30 дней в секундах
# ==========================================
#  БИЗНЕС-ЛОГИКА (Функции)
# ==========================================
async def get_airtable_data(need_description=False, force_update=False):
    """Берет прайс из кэша. force_update=True заставит бота пойти в Airtable."""
    global CACHE
    current_time = time.time()

    # Если не просим принудительно и кэш еще живет — берем из памяти
    if not force_update and CACHE["last_update"] != 0 and (current_time - CACHE["last_update"] < CACHE_LIFETIME):
        logging.info("⚡ Беру данные из локального кэша")
        return CACHE["data_with_desc"] if need_description else CACHE["data_without_desc"]

    # 2. ЕСЛИ КЭШ УСТАРЕЛ: Идем в Airtable
    logging.info("🔄 Кэш устарел. Скачиваю свежие данные из Airtable...")
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()

                list_with_desc = []
                list_without_desc = []

                # Разбираем скачанные данные сразу на два списка
                for record in data.get("records", []):
                    fields = record.get("fields", {})

                    # 1. Копия с описанием (для консультанта)
                    list_with_desc.append(dict(fields))

                    # 2. Копия без описания (для калькулятора)
                    fields_no_desc = dict(fields)
                    fields_no_desc.pop("Attachment Summary", None)
                    list_without_desc.append(fields_no_desc)

                # 3. СОХРАНЯЕМ В КЭШ
                CACHE["data_with_desc"] = list_with_desc
                CACHE["data_without_desc"] = list_without_desc
                CACHE["last_update"] = current_time

                return CACHE["data_with_desc"] if need_description else CACHE["data_without_desc"]

            # Если Airtable недоступен, но у нас есть старый кэш — отдаем хотя бы его
            elif CACHE["last_update"] != 0:
                logging.warning("⚠️ Airtable недоступен! Отдаю старые данные из кэша.")
                return CACHE["data_with_desc"] if need_description else CACHE["data_without_desc"]

            return None