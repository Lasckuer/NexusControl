from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, or_f
from app.keyboards.reply import (
    get_containers_keyboard,
    get_stop_monitor_keyboard,
    get_prune_confirm_keyboard,
)
from app.services.docker_service import docker_service
from app.services.system_service import system_service
from app.database.db import db
from app.handlers.common import cmd_help

router = Router()

@router.message(or_f(F.text.in_({"📊 Статус Сервера", "📊 Мониторинг Сервера"}), Command("status")))
async def server_monitoring(message: Message):
    """Показ и запуск живого мониторинга ресурсов сервера"""
    await db.delete_monitor(message.chat.id)
    stats_text = await system_service.get_server_stats_message()
    msg = await message.answer(
        stats_text,
        parse_mode="HTML",
        reply_markup=get_stop_monitor_keyboard()
    )
    await db.save_monitor(message.chat.id, msg.message_id, container_name=None, last_text=stats_text)

@router.message(or_f(F.text == "📦 Контейнеры", Command("containers")))
async def list_containers_msg(message: Message):
    """Список всех контейнеров хоста"""
    await db.delete_monitor(message.chat.id)
    containers = await docker_service.get_containers_list()
    if not containers:
        await message.answer("⚠️ Контейнеры не найдены или Docker недоступен.")
        return
    await message.answer(
        "📦 <b>Выберите контейнер для управления:</b>",
        parse_mode="HTML",
        reply_markup=get_containers_keyboard(containers, page=0)
    )

@router.message(or_f(F.text == "🐳 Docker инфо", Command("docker")))
async def docker_info_msg(message: Message):
    """Информация о Docker демоне"""
    await db.delete_monitor(message.chat.id)
    info_text = await docker_service.get_docker_system_info()
    await message.answer(info_text, parse_mode="HTML")

@router.message(or_f(F.text.in_({"♻️ Очистка Docker", "♻️ Очистка Docker-системы"}), Command("prune")))
async def prune_system_request(message: Message):
    """Запрос на очистку неиспользуемых ресурсов Docker с выбором уровня очистки"""
    await db.delete_monitor(message.chat.id)
    text = (
        "♻️ <b>Очистка Docker (Docker Prune)</b>\n\n"
        "Выберите режим очистки:\n"
        "• <b>Очистить (без Volumes):</b> удаляет остановленные контейнеры, неиспользуемые сети и образы без тегов. Безопасно для данных.\n"
        "• <b>Полная очистка (+ Volumes):</b> удаляет также неиспользуемые тома данных (Volumes). <i>Внимание: может удалить данные неактивных баз данных!</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_prune_confirm_keyboard())

@router.callback_query(F.data.startswith("confirm_prune:"))
async def confirm_prune_callback(callback: CallbackQuery):
    """Выполнение выбранного режима очистки"""
    mode = callback.data.split(":")[1]
    prune_volumes = (mode == "all")

    await callback.message.edit_text("⏳ <b>Выполняется очистка Docker...</b> Это может занять несколько секунд.", parse_mode="HTML")
    result_text = await docker_service.prune_system(prune_volumes=prune_volumes)
    await callback.message.edit_text(result_text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "cancel_prune")
async def cancel_prune_callback(callback: CallbackQuery):
    """Отмена очистки"""
    await callback.message.edit_text("❌ Очистка Docker отменена.")
    await callback.answer()

@router.message(F.text == "ℹ️ Справка")
async def help_menu_msg(message: Message):
    """Вызов справки по кнопке"""
    await cmd_help(message)