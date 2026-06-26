import asyncio
from aiogram import Bot
from app.database.db import db
from app.services.docker_service import docker_service
from app.keyboards.reply import get_stop_monitor_keyboard
from logger import logger

async def metrics_refresher(bot: Bot, interval: int = 4):
    while True:
        await asyncio.sleep(interval)
        monitors = db.get_all_monitors()
        for chat_id, message_id, container_name in monitors:
            try:
                if container_name:
                    text = docker_service.get_container_stats(container_name)
                else:
                    text = docker_service.get_server_stats()
                
                await bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode="Markdown",
                    reply_markup=get_stop_monitor_keyboard()
                )
            except Exception as e:
                logger.error(f"Ошибка обновления сообщения {message_id} в чате {chat_id}: {e}")
                db.delete_monitor(chat_id)