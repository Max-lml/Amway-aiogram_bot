import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

print("🔍 Ищу активные кэши в Google Cloud...")
try:
    # Получаем список всех зависших кэшей
    active_caches = list(genai.caching.CachedContent.list())

    if not active_caches:
        print("✅ Активных кэшей не найдено! Хранилище уже пустое.")
    else:
        print(f"⚠️ Найдено кэшей: {len(active_caches)}. Начинаю удаление...")
        for c in active_caches:
            print(f"🗑 Удаляю кэш: {c.name} ({c.display_name})")
            c.delete()
        print("🎉 Все старые кэши успешно уничтожены! Списания за хранение остановлены.")

except Exception as e:
    print(f"❌ Ошибка при очистке: {e}")