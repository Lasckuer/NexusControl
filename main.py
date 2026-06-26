import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from dotenv import load_dotenv
from app.handlers import messages, containers
from app.handlers.scheduler import metrics_refresher
from logger import logger

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в конфигурации .env!")

def log_redis_on_info():
    logger.info(f"Redis подключен и используется для хранения состояния бота...")

def log_redis_off_info():
    logger.warning("Redis не подключен. Используется MemoryStorage для хранения состояния бота...")

async def main():
    session = None
    
    if PROXY_URL:
        session = AiohttpSession(proxy=PROXY_URL)
        logger.info("Прокси успешно применен...")

    if REDIS_URL:
        storage = RedisStorage.from_url(REDIS_URL)
        log_redis_on_info()
    else:
        storage = MemoryStorage()
        log_redis_off_info()

    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher(storage=storage)

    dp.include_router(messages.router)
    dp.include_router(containers.router)

    asyncio.create_task(metrics_refresher(bot, interval=4))

    logger.info("Бот NexusControl успешно запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Остановка планировщика и закрытие сессии бота...")
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())