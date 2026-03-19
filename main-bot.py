import asyncio
import aiohttp
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import time
import os
from dotenv import load_dotenv

load_dotenv() # Загружает переменные из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = os.getenv("BASE_ID")
TABLE_NAME = os.getenv("TABLE_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- НАСТРОЙКИ КЭША ---
# Словарь, где мы будем хранить скачанные данные
CACHE = {
    "data_with_desc": None,     # Для консультанта
    "data_without_desc": None,  # Для калькулятора
    "last_update": 0            # Время последнего скачивания
}
CACHE_LIFETIME = 3600 * 12 # Сколько секунд живут данные (12 часов)

# Настраиваем логирование: пишем всё от уровня INFO и выше
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
COMPANY_INFO = """
ИНФОРМАЦИЯ О НАШЕМ МАГАЗИНЕ (БАЗА ЗНАНИЙ ДЛЯ ОТВЕТОВ):
- Доставка: Осуществляется курьером. Стоимость доставки по городу — 300 рублей. При заказе от 5000 рублей доставка бесплатная.
- Самовывоз: Доступен бесплатно. Наш адрес: Куинён, центральный район (предварительно нужно позвонить).
- Доставка в другие города: Да, отправляем транспортными компаниями (СДЭК, Почта) по 100% предоплате.
- Скидки: Постоянным клиентам скидка 5% по номеру телефона.
- Режим работы: Ежедневно с 10:00 до 20:00.
"""

# Создаем наши "режимы"
class BotStates(StatesGroup):
    waiting_for_calc = State()    # Бот ждет список товаров для расчета
    waiting_for_consult = State() # Бот ждет вопрос от клиента

# ==========================================
# 1. НАСТРОЙКИ (Вставь свои ключи сюда)
# ==========================================


# Настраиваем нейросеть
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')  # Модель, которая у нас сработала

# Настраиваем бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==========================================
# 2. БИЗНЕС-ЛОГИКА (Функции)
# ==========================================
async def get_airtable_data(need_description=False):
    """Берет прайс из кэша. Если кэш устарел - скачивает из Airtable."""
    global CACHE  # Говорим функции, что мы используем глобальную переменную

    current_time = time.time()

    # 1. ПРОВЕРКА КЭША: Если данные есть и они свежие — отдаем моментально!
    if CACHE["last_update"] != 0 and (current_time - CACHE["last_update"] < CACHE_LIFETIME):
        # Выводим в консоль для отладки, чтобы ты видел, как быстро это работает
        logging.info("⚡ Беру данные из кэша (без запроса в Airtable)")
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
                    fields_no_desc.pop("Описание", None)
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


def ask_gemini(user_request, products, history_text):
    """Отправляет запрос в нейросеть с гибкой логикой (живой кассир)"""
    prompt = f"""
    Ты — вежливый, внимательный и живой ассистент-кассир нашего магазина. 
    Твоя задача — помогать клиентам с расчетом стоимости товаров.

    Прайс-лист (обращай внимание на объемы/размеры товаров):
    {products}

    --- ИСТОРИЯ ДИАЛОГА ---
    {history_text}
    -----------------------

    Запрос клиента:
    "{user_request}"

    ПРАВИЛА И ЛОГИКА РАБОТЫ:
    1. Проанализируй запрос. Если клиент назвал товар, у которого в прайсе есть разные варианты (например, разный вес, объем или количество капсул), а он НЕ уточнил, какой именно нужен — ВЕЖЛИВО ПРЕДОСТАВЬ ОБЕ ВАРИАЦИИ!
    2. Если клиент задает вопрос по расчету (например, "почему ты посчитал именно так?", "а можно убрать один?"), отвечай ему простым, живым человеческим языком.
    3. ТОЛЬКО ЕСЛИ все товары и их объемы точно определены, выдай красивый чек.

    КАК ОФОРМЛЯТЬ ЧЕК (если заказ понятен):
    Приветливо подтверди заказ и напиши список в таком формате:
    • [Название товара] ([Объем/размер]) — [Количество] шт. х [Цена] = [Сумма]

    Итого к оплате: [Общая сумма] (не забудь указать валюту, которая у нас в прайсе).

    Общайся естественно, как хороший и внимательный продавец, но старайся не задавать лишние вопросы, потому что к тебе может обращаться как клиент так и администратор магазина.
    """

    response = model.generate_content(prompt)
    return response.text

def ask_gemini_consult(user_question, products, company_info, history_text):
    """Синхронная функция для режима консультации (теперь с памятью!)"""
    prompt = f"""
    Ты — вежливый и профессиональный менеджер-консультант нашего магазина.
    Твоя задача — ответить на вопрос клиента, опираясь ТОЛЬКО на предоставленные ниже данные.

    БАЗА ЗНАНИЙ О КОМПАНИИ:
    {company_info}

    КАТАЛОГ ТОВАРОВ:
    {products}

    --- ИСТОРИЯ ДИАЛОГА ---
    {history_text}
    -----------------------

    Новый вопрос клиента:
    "{user_question}"

    ПРАВИЛА:
    1. Учитывай контекст диалога. Если клиент пишет "а как его пить?", посмотри в историю, чтобы понять, о каком товаре речь.
    2. Если ответа нет в базах, направляй к живому менеджеру.
    3. Не придумывай факты.
    """
    response = model.generate_content(prompt)
    return response.text

# Создаем постоянное меню с двумя кнопками
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Расчет стоимости")],
        [KeyboardButton(text="💬 Консультация")]
    ],
    resize_keyboard=True, # Делает кнопки аккуратными (не на пол-экрана)
    input_field_placeholder="Выберите действие..." # Подсказка в поле ввода
)
# ==========================================
# 3. ХЭНДЛЕРЫ (Общение с пользователем)
# ==========================================
# StateFilter('*') позволяет команде /start работать всегда
@dp.message(F.text == "/update", StateFilter('*'))
async def force_update_cache(message: types.Message):
    # Обнуляем время последнего обновления
    CACHE["last_update"] = 0
    await message.answer("🔄 Кэш сброшен! При следующем запросе бот скачает свежие цены из базы.")

@dp.message(CommandStart(), StateFilter('*'))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear() # Обнуляем режим при старте
    await message.answer(
        "Привет! Я AI-ассистент.\nВыберите нужный режим в меню ниже:",
        reply_markup=main_keyboard
    )
    await state.update_data(history=[])

# Хэндлер сработает ТОЛЬКО если текст сообщения равен названию кнопки
@dp.message(F.text == "💰 Расчет стоимости", StateFilter('*'))
async def btn_calc(message: types.Message, state: FSMContext):
    await message.answer("🧮 Включен режим КАЛЬКУЛЯТОРА.\nПишите списки товаров, я буду их считать! (Чтобы сменить режим, просто нажмите другую кнопку)")
    await state.set_state(BotStates.waiting_for_calc)
    await state.update_data(history=[])

@dp.message(F.text == "💬 Консультация", StateFilter('*'))
async def btn_consult(message: types.Message, state: FSMContext):
    await message.answer("👨‍💼 Включен режим КОНСУЛЬТАНТА.\nЗадавайте любые вопросы по товарам или доставке! (Чтобы сменить режим, просто нажмите другую кнопку)")
    await state.set_state(BotStates.waiting_for_consult)
    await state.update_data(history=[])


@dp.message(BotStates.waiting_for_calc)
async def handle_text(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ Ищу товары в базе и считаю...")

    try:
        products = await get_airtable_data()
        if not products:
            await processing_msg.edit_text("❌ Ошибка: не удалось получить прайс-лист.")
            return

        # 1. ДОСТАЕМ ПАМЯТЬ
        user_data = await state.get_data()
        history = user_data.get("history", [])  # Получаем список (если пустой - вернет [])

        # Превращаем список в текст для промпта
        history_text = "\n".join(history) if history else "Это первое сообщение."

        # 2. ПЕРЕДАЕМ ИСТОРИЮ В AI
        ai_response = await asyncio.to_thread(ask_gemini, message.text, products, history_text)

        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "\n\n[Ответ обрезан]"

        await processing_msg.edit_text(ai_response)

        # 3. ОБНОВЛЯЕМ ПАМЯТЬ
        # Добавляем текущий вопрос и ответ ИИ в наш список
        history.append(f"Клиент: {message.text}")
        history.append(f"Кассир: {ai_response}")

        # Оставляем только последние 6 записей (3 вопроса и 3 ответа), чтобы не перегружать ИИ
        if len(history) > 6:
            history = history[-6:]

        # 4. СОХРАНЯЕМ ПАМЯТЬ ОБРАТНО В STATE
        await state.update_data(history=history)

    except Exception as e:
        await processing_msg.edit_text("❌ Произошла ошибка при расчетах.")
        print(f"Ошибка в коде: {e}")


# Ловим текст ТОЛЬКО когда бот в режиме консультации
@dp.message(BotStates.waiting_for_consult)
async def handle_consult_request(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ Ищу информацию...")

    try:
        products = await get_airtable_data(need_description=True)
        if not products:
            await processing_msg.edit_text("❌ Ошибка: временно нет доступа к каталогу.")
            return

        # 1. ДОСТАЕМ ПАМЯТЬ
        user_data = await state.get_data()
        history = user_data.get("history", [])
        history_text = "\n".join(history) if history else "Это первое сообщение."

        # 2. ПЕРЕДАЕМ ИСТОРИЮ В AI (добавили history_text в вызов функции)
        ai_response = await asyncio.to_thread(
            ask_gemini_consult,
            message.text,
            products,
            COMPANY_INFO,
            history_text
        )

        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "\n\n[Ответ обрезан]"

        await processing_msg.edit_text(ai_response)

        # 3. ОБНОВЛЯЕМ ПАМЯТЬ КОНСУЛЬТАНТА
        history.append(f"Клиент: {message.text}")
        history.append(f"Менеджер: {ai_response}")

        if len(history) > 6:
            history = history[-6:]

        await state.update_data(history=history)

    except Exception as e:
        await processing_msg.edit_text("❌ Произошла ошибка. Попробуй позже.")
        logging.error(f"Ошибка консультанта: {e}")

# ==========================================
# 4. ЗАПУСК БОТА
# ==========================================
async def main():
    print("Бот-кассир запущен и готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())