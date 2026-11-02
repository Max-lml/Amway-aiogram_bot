from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# Админская клавиатура
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="💰 Расчет стоимости"),
            KeyboardButton(text="💬 Консультация")
        ],
        [
            KeyboardButton(text="🛍 Открыть каталог", web_app=WebAppInfo(url="https://ai-amway-maiami-maxlml.mia0.amvera.tech"))
        ],
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

# Клиентская клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="💰 Рассчитать заказ"),
            KeyboardButton(text="🛍 Открыть каталог", web_app=WebAppInfo(url="https://ai-amway-maiami-maxlml.mia0.amvera.tech"))
        ],
        [
            KeyboardButton(text="📦 О доставке и самовывозе"),
            KeyboardButton(text="💬 Задать вопрос менеджеру")
        ]
    ],
    resize_keyboard=True
)