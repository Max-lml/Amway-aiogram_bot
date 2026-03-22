import asyncio
import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
import os
import asyncio

# Импортируем наши собственные модули!
from database.airtable_api import get_airtable_data, CACHE
from services.gemini_api import ask_gemini, ask_gemini_consult, ask_gemini_voice
from tg_bot.states import BotStates
from tg_bot.keyboards import main_keyboard

# Создаем роутер (вместо dp)
router = Router()


@router.message(CommandStart(), StateFilter('*'))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я AI-ассистент.\nВыберите нужный режим в меню ниже:",
        reply_markup=main_keyboard
    )


@router.message(F.text == "/update", StateFilter('*'))
async def force_update_cache(message: types.Message):
    CACHE["last_update"] = 0
    await message.answer("🔄 Кэш сброшен! База обновится при следующем запросе.")


@router.message(F.text == "💰 Расчет стоимости", StateFilter('*'))
async def btn_calc(message: types.Message, state: FSMContext):
    await message.answer("🧮 Включен режим КАЛЬКУЛЯТОРА.\nПишите списки товаров, я буду их считать!")
    await state.set_state(BotStates.waiting_for_calc)
    await state.update_data(history=[])


@router.message(F.text == "💬 Консультация", StateFilter('*'))
async def btn_consult(message: types.Message, state: FSMContext):
    await message.answer("👨‍💼 Включен режим КОНСУЛЬТАНТА.\nЗадавайте вопросы по товарам или доставке!")
    await state.set_state(BotStates.waiting_for_consult)
    await state.update_data(history=[])


@router.message(BotStates.waiting_for_calc, F.text)
async def handle_calc_request(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ Считаю...")
    try:
        products = await get_airtable_data(need_description=False)
        if not products:
            await processing_msg.edit_text("❌ Ошибка: не удалось получить прайс-лист.")
            return

        user_data = await state.get_data()
        history = user_data.get("history", [])
        history_text = "\n".join(history) if history else "Это первое сообщение."

        # Отправляем в Gemini (функция из services/gemini_api.py)
        ai_response = await asyncio.to_thread(ask_gemini, message.text, products, history_text)

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


@router.message(BotStates.waiting_for_consult, F.text)
async def handle_consult_request(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ Ищу информацию...")
    try:
        products = await get_airtable_data(need_description=True)
        if not products:
            await processing_msg.edit_text("❌ Ошибка: нет доступа к каталогу.")
            return

        user_data = await state.get_data()
        history = user_data.get("history", [])
        history_text = "\n".join(history) if history else "Это первое сообщение."

        # Отправляем в Gemini консультанту
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

    # Узнаем, в каком режиме сейчас находится пользователь
    current_state = await state.get_state()
    mode = "calc" if current_state == BotStates.waiting_for_calc.state else "consult"

    # Создаем уникальное имя для аудиофайла
    file_id = message.voice.file_id
    file_path = f"voice_{file_id}.ogg"

    try:
        # 1. Скачиваем аудио из Телеграма на наш компьютер/сервер
        file = await message.bot.get_file(file_id)
        await message.bot.download_file(file.file_path, destination=file_path)

        # 2. Подготавливаем данные
        need_desc = (mode == "consult")
        products = await get_airtable_data(need_description=need_desc)

        user_data = await state.get_data()
        history = user_data.get("history", [])
        history_text = "\n".join(history) if history else "Это первое сообщение."

        # 3. Отправляем файл в Gemini (наша новая функция)
        ai_response = await asyncio.to_thread(
            ask_gemini_voice, file_path, products, history_text, mode
        )

        # 4. Удаляем временный файл с диска, чтобы сервер не переполнился мусором!
        if os.path.exists(file_path):
            os.remove(file_path)

        # 5. Отправляем ответ пользователю
        await processing_msg.edit_text(ai_response)

        # Записываем в память
        history.append(f"Клиент (Голосовое): [Аудио сообщение]")
        history.append(f"Бот: {ai_response}")
        if len(history) > 6:
            history = history[-6:]
        await state.update_data(history=history)

    except Exception as e:
        await processing_msg.edit_text("❌ Извините, не удалось распознать голосовое сообщение.")
        logging.error(f"Ошибка голосового: {e}")

        # Если произошла ошибка, всё равно пытаемся удалить файл
        if os.path.exists(file_path):
            os.remove(file_path)