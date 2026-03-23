
import google.generativeai as genai
from google.generativeai import caching
import datetime
import logging
from config import GEMINI_API_KEY

# Настраиваем Google
genai.configure(api_key=GEMINI_API_KEY)


MODEL_NAME = 'gemini-2.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# Твоя база знаний без изменений
COMPANY_INFO = """
БАЗА ЗНАНИЙ МАГАЗИНА (ОСНОВНАЯ ИНФОРМАЦИЯ):
- Локация: Работаем в Батуми. Официального офиса нет, работаем только онлайн.
- Происхождение товара: Продукция Amway доставляется из соседних стран (в Грузии бренд официально не представлен).
- Доставка по Батуми: Курьером. Стоимость — 3 лари. При заказе от 100 лари — бесплатно.
- Доставка по Грузии: В другие города отправляем через логистическую компанию Inex (по запросу).
- Самовывоз: Батуми, ул. Тбел-Абусеридзе, д. 21. 
  ВАЖНО: О самовывозе нужно сообщить минимум за 30 минут по телефону или в мессенджеры (WhatsApp/Telegram): +995595052139.
- Заказ под заказ: Если товара нет в наличии, привозим по предоплате 30% от стоимости (минимальная сумма предоплаты — 20 лари).
- Режим связи: Ежедневно с 10:00 до 20:00.
- Заказать товар можно только связавшись с менеджером по телеграм/вотсап или по телефону напрямую, 
а получить уже либо самовывозом по заранее оговоренному времени либо доставкой. Оплата наличными при получении, либо 
перевод на карту TBC.
"""
current_cache = None


def create_or_update_cache(products_text):
    """Создает кэш контекста на серверах Google на 30 дней"""
    global current_cache

    # Если старый кэш был — удаляем его, чтобы не платить за хранение лишнего
    if current_cache:
        try:
            current_cache.delete()
        except:
            pass

    # Создаем новый кэш
    current_cache = caching.CachedContent.create(
        model='models/gemini-1.5-flash-001',  # Кэш привязывается к конкретной модели
        display_name="amway_price_cache",
        system_instruction="Ты — вежливый кассир магазина в Батуми. Используй этот прайс-лист для расчетов.",
        contents=[products_text],
        ttl=datetime.timedelta(days=30),  # Кэш живет в Google 30 дней
    )
    logging.info(f"✅ Создан новый кэш в Google: {current_cache.name}")
    return current_cache


def ask_gemini_with_cache(user_request, products_text, history_text):
    global current_cache

    # Если кэша еще нет в Google — создаем
    if not current_cache:
        create_or_update_cache(products_text)

    # Используем модель, привязанную к кэшу
    model = genai.GenerativeModel(model_name='models/gemini-1.5-flash-001')

    prompt = f"История: {history_text}\nЗапрос клиента: {user_request}"

    # Отправляем запрос, используя сохраненный контекст (это в разы дешевле!)
    response = model.generate_content(prompt, tool_config={'function_calling_config': 'NONE'})
    return response.text


def ask_gemini(user_request, products, history_text):
    """ТВОЙ ЖИВОЙ КАССИР (БЕЗ ИЗМЕНЕНИЙ В ТЕКСТЕ)"""
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
    1. Проанализируй запрос. Если клиент назвал товар, у которого в прайсе есть разные варианты (например, разный вес, объем или количество капсул), а он НЕ уточнил, какой именно нужен — ОТПРАВЬ ОБЕ ВАРИАЦИИ расчетов. Не выбирай за него!
    2. Если клиент задает вопрос по расчету (например, "почему ты посчитал именно так?", "а можно убрать один?"), отвечай ему простым, живым человеческим языком.
    3. ТОЛЬКО ЕСЛИ все товары и их объемы точно определены, выдай красивый чек.

    КАК ОФОРМЛЯТЬ ЧЕК (если заказ понятен):
    Приветливо подтверди заказ и напиши список в таком формате:
    • [Название товара] ([Объем/размер]) — [Количество] шт. х [Цена] = [Сумма]

    Итого к оплате: [Общая сумма].

    Общайся естественно, как хороший и внимательный продавец. Но после "ИТОГО" уже больше ничего писать не надо
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Ошибка Gemini (Calc): {e}")
        if "429" in str(e):
            return "🕒 Извините, лимит бесплатных запросов на сегодня исчерпан. Попробуйте чуть позже."
        return "⚠️ Произошла временная ошибка связи с ИИ. Попробуйте еще раз."

def ask_gemini_consult(user_question, products, history_text):
    """ТВОЙ КОНСУЛЬТАНТ (БЕЗ ИЗМЕНЕНИЙ В ТЕКСТЕ)"""
    prompt = f"""
    Ты — вежливый и профессиональный менеджер-консультант нашего магазина.
    Твоя задача — ответить на вопрос клиента, опираясь ТОЛЬКО на предоставленные ниже данные.

    БАЗА ЗНАНИЙ О КОМПАНИИ:
    {COMPANY_INFO}

    КАТАЛОГ ТОВАРОВ:
    {products}

    --- ИСТОРИЯ ДИАЛОГА ---
    {history_text}
    -----------------------

    Новый вопрос клиента:
    "{user_question}"

    ПРАВИЛА:
    1. Учитывай контекст диалога.
    2. Если ответа нет в базах, направляй к живому менеджеру.
    3. Не придумывай факты.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Ошибка Gemini (Consult): {e}")
        if "429" in str(e):
            return "🕒 Извините, лимит бесплатных консультаций исчерпан. Скоро буду снова в сети!"
        return "⚠️ Не удалось получить ответ от менеджера. Попробуйте позже."

def ask_gemini_voice(audio_path, products, history_text, mode="calc"):
    """ТВОЙ ГОЛОСОВОЙ РЕЖИМ (БЕЗ ИЗМЕНЕНИЙ В ТЕКСТЕ)"""
    try:
        audio_file = genai.upload_file(path=audio_path)

        if mode == "calc":
            prompt = f"Ты — вежливый кассир... Прайс: {products}. История: {history_text}." # Тут твои промпты из кода выше
        else:
            prompt = f"Ты — консультант... База: {COMPANY_INFO}. Прайс: {products}."

        response = model.generate_content([prompt, audio_file])
        audio_file.delete()
        return response.text
    except Exception as e:
        logging.error(f"Ошибка Gemini (Voice): {e}")
        return "❌ Ошибка обработки голосового сообщения. Попробуйте написать текстом."