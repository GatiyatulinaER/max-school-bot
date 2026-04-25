import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from config import BOT_TOKEN
from handlers import dp, bot


async def main():
    if not BOT_TOKEN:
        print("❌ ОШИБКА: Токен не найден!")
        print("Проверьте файл .env")
        return

    print("=" * 50)
    print("🤖 БОТ ДЛЯ MAX ЗАПУЩЕН")
    print("=" * 50)

    await bot.delete_webhook()
    print("🚀 Бот ожидает сообщений...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())