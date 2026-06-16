from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# Твоя админская клавиатура
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        # Первый ряд кнопок (две кнопки вместе)
        [
            KeyboardButton(text="💰 Расчет стоимости"),
            KeyboardButton(text="💬 Консультация")
        ],
        # Второй ряд (кнопка на всю ширину)
        [
            KeyboardButton(text="🛍 Открыть каталог", web_app=WebAppInfo(url="https://aiamway-maxlml.amvera.io/"))
        ],
        # Третий ряд (кнопка на всю ширину)
        [
            KeyboardButton(text="📊 Оценить капитал склада")
        ]
    ],
    resize_keyboard=True
)
# Клиентская клавиатура с Web App кнопкой
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="💰 Рассчитать заказ"),
            # ДЛЯ ТЕСТА НА КОМПЬЮТЕРЕ СТАВИМ LOCALHOST:
            KeyboardButton(text="🛍 Открыть каталог", web_app=WebAppInfo(url="https://aiamway-maxlml.amvera.io/"))
        ],
        [
            KeyboardButton(text="📦 О доставке и самовывозе"),
            KeyboardButton(text="💬 Задать вопрос менеджеру")
        ]
    ],
    resize_keyboard=True
)