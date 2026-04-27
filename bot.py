import asyncio
from handlers import dp, bot

async def main():
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН")
    print("🏫 Здание на ул. Марченко и Здание на ул. Танкистов - разные чаты")
    print("⚠️ Обращения и Предложения - разные чаты")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())