import asyncio
import logging
import os

from aiogram import Router, F, types
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext

from database.airtable_api import get_airtable_data, CACHE
from services.gemini_api import ask_gemini, ask_gemini_consult, ask_gemini_voice, COMPANY_INFO
from tg_bot.states import BotStates
from tg_bot.keyboards import main_keyboard, admin_keyboard
from config import ADMIN_ID
router = Router()



@router.message(CommandStart(), StateFilter('*'))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    # Разделяем интерфейс на Максима (Администратора) и Клиентов
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "👋 Привет, Максим! Добро пожаловать в панель твоего AI-ассистента.\n"
            "Выбери нужный режим работы:",
            reply_markup=admin_keyboard
        )
    else:
        await message.answer(
            "👋 Здравствуйте! Я — автоматизированный помощник по базе продукции Amway в Батуми. "
            "Помогу сориентироваться в стоимости товаров, узнать детали доставки или рассчитать итоговую сумму заказа. "
            "Выберите подходящий раздел в меню или перейдите в «🛍 Открыть каталог» для "
            "просмотра полного списка товаров 👇",
            reply_markup=main_keyboard
        )


@router.message(F.text == "🔄 Обновить прайс")
async def refresh_price_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🔄 Начинаю обновление данных из Airtable...")
        try:
            # Принудительно сбрасываем локальный кэш Airtable и скачиваем свежие данные
            await get_airtable_data(need_description=True, force_update=True)
            await message.answer("✅ Прайс-лист успешно обновлен в памяти бота! Платный кэш Google не задействован.")
        except Exception as e:
            logging.error(f"Ошибка при обновлении: {e}")
            await message.answer(f"❌ Произошла ошибка при обновлении: {e}")
    else:
        await message.answer("У вас нет прав для этой команды.")


# --- ОБРАБОТКА СТАТИЧЕСКИХ КЛИЕНТСКИХ КНОПОК ---

@router.message(F.text == "📦 О доставке и самовывозе", StateFilter('*'))
async def btn_delivery_info(message: types.Message):
    await message.answer(COMPANY_INFO.strip())


@router.message(F.text == "💬 Задать вопрос менеджеру", StateFilter('*'))
async def btn_contact_manager(message: types.Message):
    await message.answer(
        "📝 Чтобы оформить заказ или задать вопрос напрямую, вы можете написать или позвонить менеджеру:\n\n"
        "📞 <b>Телефон / WhatsApp / Telegram:</b>\n+995595052139\n\n"
        "🔗 <b>Прямая ссылка:</b> <a href='https://t.me/amway_ge'>@amway_ge</a>",
        parse_mode="HTML"
    )

# --- РЕЖИМЫ КАЛЬКУЛЯТОРА И КОНСУЛЬТАНТА ---

@router.message(F.text.in_(["💰 Расчет стоимости", "💰 Рассчитать заказ"]), StateFilter('*'))
async def btn_calc(message: types.Message, state: FSMContext):
    await message.answer(
        "🧮 Включен режим КАЛЬКУЛЯТОРА.\nПишите списки товаров или надиктуйте их голосом, я всё посчитаю!")
    await state.set_state(BotStates.waiting_for_calc)
    await state.update_data(history=[])


@router.message(F.text == "💬 Консультация", StateFilter('*'))
async def btn_consult(message: types.Message, state: FSMContext):
    await message.answer("👨‍💼 Включен режим КОНСУЛЬТАНТА.\nЗадавайте вопросы по свойствам товаров!")
    await state.set_state(BotStates.waiting_for_consult)
    await state.update_data(history=[])


# --- РАСПРЕДЕЛЕНИЕ ТЕКСТА ПО РЕЖИМАМ ---

@router.message(F.text, StateFilter('*'))
async def handle_text_messages(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == BotStates.waiting_for_calc.state:
        await handle_calc_logic(message, state)
    elif current_state == BotStates.waiting_for_consult.state:
        await handle_consult_logic(message, state)
    else:
        await message.answer(
            "Пожалуйста, выберите нужный режим на клавиатуре ниже, чтобы я смог вам помочь 👇\n\n"
            "🛍 Чтобы посмотреть ассортимент товаров с описаниями, нажмите кнопку «Открыть каталог».",
            reply_markup=main_keyboard
        )


async def handle_calc_logic(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ Считаю...")
    try:
        is_admin = (message.from_user.id == ADMIN_ID)
        products = await get_airtable_data(need_description=False)
        if not products:
            await processing_msg.edit_text("❌ Ошибка: не удалось получить прайс-лист.")
            return

        user_data = await state.get_data()
        history = user_data.get("history", [])
        history_text = "\n".join(history) if history else "Это первое сообщение."

        # Передаем флаг администратора для текстовых расчетов профита
        ai_response = await asyncio.to_thread(ask_gemini, message.text, products, history_text, is_admin=is_admin)

        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "\n\n[Ответ обрезан]"

        await processing_msg.edit_text(ai_response)

        history.append(f"Клиент: {message.text}")
        history.append(f"Кассир: {ai_response}")
        if len(history) > 6:
            history = history[-6:]

        await state.update_data(history=history)
    except Exception as e:
        await processing_msg.edit_text("❌ Произошла ошибка при расчетах.")
        logging.error(f"Ошибка калькулятора: {e}")


async def handle_consult_logic(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ Ищу информацию...")
    try:
        products = await get_airtable_data(need_description=True)
        if not products:
            await processing_msg.edit_text("❌ Ошибка: нет доступа к каталогу.")
            return

        user_data = await state.get_data()
        history = user_data.get("history", [])
        history_text = "\n".join(history) if history else "Это первое сообщение."

        ai_response = await asyncio.to_thread(ask_gemini_consult, message.text, products, history_text)

        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "\n\n[Ответ обрезан]"

        await processing_msg.edit_text(ai_response)

        history.append(f"Клиент: {message.text}")
        history.append(f"Менеджер: {ai_response}")
        if len(history) > 6:
            history = history[-6:]

        await state.update_data(history=history)
    except Exception as e:
        await processing_msg.edit_text("❌ Произошла ошибка. Попробуй позже.")
        logging.error(f"Ошибка консультанта: {e}")


@router.message(F.voice, StateFilter(BotStates.waiting_for_calc, BotStates.waiting_for_consult))
async def handle_voice_message(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("🎧 Слушаю ваше голосовое сообщение...")
    current_state = await state.get_state()
    mode = "calc" if current_state == BotStates.waiting_for_calc.state else "consult"
    file_id = message.voice.file_id
    file_path = f"voice_{file_id}.ogg"

    try:
        is_admin = (message.from_user.id == ADMIN_ID)
        file = await message.bot.get_file(file_id)
        await message.bot.download_file(file.file_path, destination=file_path)

        need_desc = (mode == "consult")
        products = await get_airtable_data(need_description=need_desc)

        user_data = await state.get_data()
        history = user_data.get("history", [])
        history_text = "\n".join(history) if history else "Это первое сообщение."

        # Теперь и в голосовой режим передается флаг is_admin для скрытого подсчета профита
        ai_response = await asyncio.to_thread(
            ask_gemini_voice, file_path, products, history_text, mode, is_admin=is_admin
        )

        if os.path.exists(file_path):
            os.remove(file_path)

        await processing_msg.edit_text(ai_response)

        history.append(f"Клиент (Голосовое): [Аудио сообщение]")
        history.append(f"Бот: {ai_response}")
        if len(history) > 6:
            history = history[-6:]
        await state.update_data(history=history)

    except Exception as e:
        await processing_msg.edit_text("❌ Извините, не удалось распознать голосовое сообщение.")
        logging.error(f"Ошибка голосового: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)