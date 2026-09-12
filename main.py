import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from app.config import config
from app.middlewares.auth import AdminAuthMiddleware
from app.handlers import common, messages, containers
from app.handlers.common import setup_bot_commands
from app.handlers.scheduler import (
    metrics_refresher,
    container_crash_monitor,
    system_resource_monitor,
)
from app.database.db import db
from logger import logger

async def main():
    config.validate()

    session = None
    if config.proxy_url:
        session = AiohttpSession(proxy=config.proxy_url)
        logger.info(f"Прокси успешно подключен ({config.proxy_url}).")

    if config.redis_url:
        try:
            storage = RedisStorage.from_url(config.redis_url)
            logger.info("Подключено хранилище состояний Redis.")
        except Exception as e:
            logger.error(f"Не удалось подключиться к Redis: {e}. Переключение на MemoryStorage.")
            storage = MemoryStorage()
    else:
        storage = MemoryStorage()
        logger.info("Используется MemoryStorage для FSM состояний.")

    bot = Bot(token=config.bot_token, session=session)
    dp = Dispatcher(storage=storage)

    # Регистрация middleware авторизации администраторов
    auth_middleware = AdminAuthMiddleware()
    dp.message.outer_middleware(auth_middleware)
    dp.callback_query.outer_middleware(auth_middleware)

    # Подключение роутеров
    dp.include_router(common.router)
    dp.include_router(messages.router)
    dp.include_router(containers.router)

    # Инициализация базы данных и команд бота
    await db.init_db()
    await setup_bot_commands(bot)

    # Фоновые процессы
    background_tasks: list[asyncio.Task] = []
    background_tasks.append(
        asyncio.create_task(metrics_refresher(bot, interval=config.refresh_interval))
    )

    if config.admin_ids:
        logger.info(f"Активные администраторы: {list(config.admin_ids)}")
        background_tasks.append(
            asyncio.create_task(container_crash_monitor(bot, interval=config.crash_monitor_interval))
        )
        background_tasks.append(
            asyncio.create_task(system_resource_monitor(bot, interval=config.resource_monitor_interval))
        )
    else:
        logger.warning("ADMIN_IDS не задан! Алерты о падениях контейнеров и железа отключены.")

    logger.info("Бот NexusControl успешно запущен и готов к работе!")

    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Инициирована остановка бота NexusControl...")
        for task in background_tasks:
            task.cancel()
        
        await asyncio.gather(*background_tasks, return_exceptions=True)
        await db.close()
        await bot.session.close()
        logger.info("NexusControl корректно завершил работу.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass