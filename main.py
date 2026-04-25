# main.py - просто импортирует bot.py
from bot import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())