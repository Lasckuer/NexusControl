from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.utils.aliases import prettify_name
from app.keyboards.inline import (
    get_containers_keyboard,
    get_container_actions_keyboard,
    get_stop_monitor_keyboard,
    get_logs_options_keyboard,
    get_confirm_keyboard,
    get_prune_confirm_keyboard,
)

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная панель кнопок Telegram"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Статус Сервера"),
                KeyboardButton(text="📦 Контейнеры")
            ],
            [
                KeyboardButton(text="🐳 Docker инфо"),
                KeyboardButton(text="♻️ Очистка Docker")
            ],
            [
                KeyboardButton(text="ℹ️ Справка")
            ]
        ],
        resize_keyboard=True
    )

__all__ = [
    "get_main_keyboard",
    "prettify_name",
    "get_containers_keyboard",
    "get_container_actions_keyboard",
    "get_stop_monitor_keyboard",
    "get_logs_options_keyboard",
    "get_confirm_keyboard",
    "get_prune_confirm_keyboard",
]