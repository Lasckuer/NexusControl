from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from app.config import config
from logger import logger

class AdminAuthMiddleware(BaseMiddleware):
    """
    Middleware для проверки прав администратора.
    Пропускает запросы только от пользователей, чьи ID присутствуют в config.admin_ids.
    Все остальные запросы блокируются с логированием попытки доступа.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        user_id = user.id if user else None
        username = user.username if user else "Unknown"

        # Если в конфигурации не указаны администраторы, логируем предупреждение
        if not config.admin_ids:
            logger.warning("Список ADMIN_IDS пуст! Доступ заблокирован для всех пользователей.")
            if isinstance(event, Message):
                await event.answer("⚠️ Бот не настроен: не указан ADMIN_ID в конфигурации.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⚠️ Бот не настроен (нет ADMIN_ID)", show_alert=True)
            return

        if not config.is_admin(user_id):
            logger.warning(
                f"Попытка несанкционированного доступа: user_id={user_id}, username=@{username}"
            )
            if isinstance(event, Message):
                await event.answer(
                    f"⛔ <b>Доступ запрещен.</b>\nВаш ID: <code>{user_id}</code> не зарегистрирован в системе управления.",
                    parse_mode="HTML"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещен: вы не администратор.", show_alert=True)
            return

        return await handler(event, data)
