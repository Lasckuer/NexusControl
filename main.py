import os
import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from app.handlers import messages, containers
from app.handlers.scheduler import metrics_refresher
from logger import logger

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в конфигурации .env!")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(messages.router)
    dp.include_router(containers.router)

    asyncio.create_task(metrics_refresher(bot, interval=4))

    logger.info("Бот NexusControl успешно запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())