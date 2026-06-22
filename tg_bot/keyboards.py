from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# Твоя админская клавиатура
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        # 1. Основные рабочие инструменты
        [
            KeyboardButton(text="💰 Расчет стоимости"),
            KeyboardButton(text="💬 Консультация")
        ],
        # 2. Витрина (на всю ширину)
        [
            KeyboardButton(text="🛍 Открыть каталог", web_app=WebAppInfo(url="https://aiamway-maxlml.amvera.io/?v=3"))
        ],
        # 3. Аналитика и управление (по 2 в ряд — самый удобный формат)
        [
            KeyboardButton(text="📊 Оценить капитал склада"),
            KeyboardButton(text="🔄 Обновить прайс")
        ],
        [
            KeyboardButton(text="📦 О доставке и самовывозе"),
            KeyboardButton(text="💬 Задать вопрос менеджеру")
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
            KeyboardButton(text="🛍 Открыть каталог", web_app=WebAppInfo(url="https://aiamway-maxlml.amvera.io/?v=3"))
        ],
        [
            KeyboardButton(text="📦 О доставке и самовывозе"),
            KeyboardButton(text="💬 Задать вопрос менеджеру")
        ]
    ],
    resize_keyboard=True
)