import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")

# ========== НАСТРОЙТЕ ВАШИ ID ==========
REQUESTS_CHAT_ID = -73976896940711   # ID группы для заявок
FEEDBACK_CHAT_ID = -73977260665511   # ID чата для обращений
ADMIN_ID = 33534631                   # Ваш личный ID

print("✅ config.py загружен")
print(f"📋 Чат для справок: {REQUESTS_CHAT_ID}")
print(f"💬 Чат для обращений: {FEEDBACK_CHAT_ID}")