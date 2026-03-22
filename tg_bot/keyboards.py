from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Расчет стоимости")],
        [KeyboardButton(text="💬 Консультация")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие..."
)