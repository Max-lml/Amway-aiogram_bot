from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    waiting_for_calc = State()    # Режим калькулятора
    waiting_for_consult = State() # Режим консультантаа