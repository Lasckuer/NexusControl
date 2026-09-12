from aiogram import Router, Bot
from aiogram.types import Message, BotCommand
from aiogram.filters import CommandStart, Command
from app.keyboards.reply import get_main_keyboard
from app.database.db import db
from logger import logger

router = Router()

async def setup_bot_commands(bot: Bot) -> None:
    """Регистрация команд в интерфейсе Telegram"""
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="status", description="Статус сервера (CPU, RAM, Диск)"),
        BotCommand(command="containers", description="Список и управление контейнерами"),
        BotCommand(command="docker", description="Информация о Docker демоне"),
        BotCommand(command="prune", description="Очистка неиспользуемых ресурсов Docker"),
        BotCommand(command="help", description="Справка по работе с ботом"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Не удалось установить команды бота: {e}")

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start: приветствие и инициализация клавиатуры"""
    await db.delete_monitor(message.chat.id)
    text = (
        "👋 <b>Добро пожаловать в NexusControl!</b>\n\n"
        "Система мониторинга и управления Docker-контейнерами готова к работе.\n\n"
        "🔹 <b>Статус Сервера:</b> мониторинг CPU, RAM, диска и сети хоста\n"
        "🔹 <b>Контейнеры:</b> перезапуск, остановка, логи, просмотр метрик\n"
        "🔹 <b>Docker инфо:</b> общая статистика демона Docker\n"
        "🔹 <b>Очистка Docker:</b> безопасное освобождение дискового пространства\n\n"
        "Используйте кнопки меню ниже для управления."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help: подробное описание функций"""
    text = (
        "📖 <b>Справка по NexusControl</b>\n\n"
        "<b>Основные возможности:</b>\n"
        "• <b>Живой мониторинг:</b> автообновление метрик контейнера или сервера в реальном времени с прогресс-барами.\n"
        "• <b>Управление контейнерами:</b> Start, Stop, Restart, Pause, Kill.\n"
        "• <b>Логи:</b> просмотр 50/100/300 строк или скачивание лог-файла целиком на устройство.\n"
        "• <b>Подробности:</b> инспекция портов, IP-адресов, тегов и healthcheck.\n"
        "• <b>Алерты:</b> мгновенное уведомление в Telegram при падении контейнера или перегрузке сервера (>90% CPU/RAM/Диск).\n"
        "• <b>Пагинация и фильтры:</b> удобный просмотр запущенных и остановленных контейнеров.\n\n"
        "<b>Команды:</b>\n"
        "/start — Перезапуск меню\n"
        "/status — Метрики сервера\n"
        "/containers — Список контейнеров\n"
        "/docker — Статус Docker демона\n"
        "/prune — Очистка неиспользуемых данных\n"
        "/help — Данная справка"
    )
    await message.answer(text, parse_mode="HTML")
