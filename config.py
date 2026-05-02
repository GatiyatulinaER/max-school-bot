import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("f9LHodD0cOKcj3PaUTHLw2zeRW7AS7JBlgX2IBCuR63mYgzujVmLshD0Vvcs68aC2hqBQtWCpJgtnNnRMvRH")

# ========== ВАШИ ID ==========
ADMIN_ID = 33534631  # Ваш личный ID

# ========== ЧАТЫ ДЛЯ ЗАЯВОК НА СПРАВКИ ==========
# ЗАМЕНИТЕ НА РЕАЛЬНЫЕ ID ВАШИХ ЧАТОВ!
BUILDING_1_CHAT_ID = -73976896940711    # Чат для справок Здание на ул. Марченко
BUILDING_2_CHAT_ID = -74041172486823    # Чат для справок Здание на ул. Танкистов

# ========== ЧАТЫ ДЛЯ ОБРАЩЕНИЙ ==========
# ЗАМЕНИТЕ НА РЕАЛЬНЫЕ ID ВАШИХ ЧАТОВ!
COMPLAINTS_CHAT_ID = -73977260665511       # Чат для жалоб/обращений
SUGGESTIONS_CHAT_ID = -74041178450599       # Чат для предложений

print("=" * 50)
print("✅ config.py загружен")
print(f"🏫 Здание на ул. Марченко: {BUILDING_1_CHAT_ID}")
print(f"🏫 Здание на ул. Танкистов: {BUILDING_2_CHAT_ID}")
print(f"⚠️ Обращения: {COMPLAINTS_CHAT_ID}")
print(f"💡 Предложения: {SUGGESTIONS_CHAT_ID}")
print("=" * 50)