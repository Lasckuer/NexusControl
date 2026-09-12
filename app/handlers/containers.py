import io
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from app.services.docker_service import docker_service
from app.keyboards.inline import (
    get_containers_keyboard,
    get_container_actions_keyboard,
    get_logs_options_keyboard,
    get_confirm_keyboard,
    get_stop_monitor_keyboard,
)
from app.utils.aliases import prettify_name
from app.utils.formatters import safe_html
from app.database.db import db
from logger import logger

router = Router()

@router.callback_query(F.data == "refresh_list")
async def refresh_containers_list(callback: CallbackQuery):
    """Обновить список контейнеров"""
    await db.delete_monitor(callback.message.chat.id)
    containers = await docker_service.get_containers_list()
    if not containers:
        await callback.message.edit_text(
            "⚠️ Контейнеры не найдены или Docker недоступен.",
            reply_markup=get_containers_keyboard([])
        )
    else:
        await callback.message.edit_text(
            "📦 <b>Выберите контейнер для управления:</b>",
            parse_mode="HTML",
            reply_markup=get_containers_keyboard(containers, page=0)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("page:"))
async def change_page(callback: CallbackQuery):
    """Переключение страницы в списке контейнеров"""
    page = int(callback.data.split(":")[1])
    containers = await docker_service.get_containers_list()
    await callback.message.edit_reply_markup(
        reply_markup=get_containers_keyboard(containers, page=page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("filter:"))
async def change_filter(callback: CallbackQuery):
    """Фильтрация контейнеров по статусу"""
    status_filter = callback.data.split(":")[1]
    actual_filter = None if status_filter == "all" else status_filter

    containers = await docker_service.get_containers_list()
    await callback.message.edit_reply_markup(
        reply_markup=get_containers_keyboard(containers, page=0, status_filter=actual_filter)
    )
    await callback.answer()

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустое действие (для некликабельных элементов навигации)"""
    await callback.answer()

@router.callback_query(F.data.startswith("manage:"))
async def manage_container(callback: CallbackQuery):
    """Экран управления конкретным контейнером"""
    await db.delete_monitor(callback.message.chat.id)
    c_name = callback.data.split(":")[1]
    nice_name = prettify_name(c_name)

    # Определяем текущий статус для отображения соответствующих кнопок
    containers = await docker_service.get_containers_list()
    current = next((c for c in containers if c.name == c_name), None)
    is_running = current.status == "running" if current else False

    text = (
        f"⚙️ <b>Управление контейнером:</b>\n"
        f"🏷 <b>Имя:</b> <code>{safe_html(c_name)}</code> ({safe_html(nice_name)})\n"
        f"Статус: <b>{current.status if current else 'неизвестно'}</b>\n\n"
        f"Выберите действие:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_container_actions_keyboard(c_name, is_running=is_running)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("action:"))
async def action_container(callback: CallbackQuery):
    """Выполнение стандартного действия над контейнером (start, stop, restart, pause, unpause)"""
    _, action, name = callback.data.split(":")
    await callback.message.edit_text(f"⏳ Выполняется действие <b>{action}</b> для <code>{safe_html(name)}</code>...", parse_mode="HTML")

    # Если администратор штатно останавливает контейнер, помечаем это, чтобы не было ложного алерта о падении
    if action in ["stop", "kill", "pause"]:
        await db.add_intentional_stop(name)
    elif action in ["start", "restart", "unpause"]:
        await db.remove_intentional_stop(name)

    success, msg = await docker_service.control_container(name, action)

    # Проверяем обновленный статус
    containers = await docker_service.get_containers_list()
    current = next((c for c in containers if c.name == name), None)
    is_running = current.status == "running" if current else False

    status_str = "✅ Успешно выполнено" if success else f"❌ Ошибка: {safe_html(msg)}"
    result_text = (
        f"Действие <b>{action}</b> для <code>{safe_html(name)}</code>:\n"
        f"{status_str}\n\n"
        f"Текущий статус: <b>{current.status if current else 'неизвестно'}</b>"
    )

    await callback.message.edit_text(
        result_text,
        parse_mode="HTML",
        reply_markup=get_container_actions_keyboard(name, is_running=is_running)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_req:"))
async def confirm_request(callback: CallbackQuery):
    """Запрос подтверждения опасной операции"""
    _, action, name = callback.data.split(":")
    nice_name = prettify_name(name)
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение действия:</b>\n"
        f"Вы действительно хотите принудительно завершить (<code>{action.upper()}</code>) контейнер <b>{safe_html(nice_name)}</b>?",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard(action, name)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm:"))
async def execute_confirmed_action(callback: CallbackQuery):
    """Выполнение подтвержденного опасного действия"""
    _, action, name = callback.data.split(":")
    await db.add_intentional_stop(name)
    await callback.message.edit_text(f"⏳ Принудительное выполнение {action}...")
    success, msg = await docker_service.control_container(name, action)

    status_str = "✅ Принудительно остановлен (killed)" if success else f"❌ Ошибка: {safe_html(msg)}"
    await callback.message.edit_text(
        f"Результат для <code>{safe_html(name)}</code>:\n{status_str}",
        parse_mode="HTML",
        reply_markup=get_container_actions_keyboard(name, is_running=False)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_action:"))
async def cancel_action(callback: CallbackQuery):
    """Отмена подтверждения действия"""
    name = callback.data.split(":")[1]
    containers = await docker_service.get_containers_list()
    current = next((c for c in containers if c.name == name), None)
    is_running = current.status == "running" if current else False

    await callback.message.edit_text(
        f"Действие отменено.",
        reply_markup=get_container_actions_keyboard(name, is_running=is_running)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("logs_menu:"))
async def logs_menu(callback: CallbackQuery):
    """Меню выбора логов"""
    name = callback.data.split(":")[1]
    nice_name = prettify_name(name)
    await callback.message.edit_text(
        f"📋 <b>Логи контейнера:</b> {safe_html(nice_name)} (<code>{safe_html(name)}</code>)\n"
        f"Выберите количество последних строк или скачайте лог файлом:",
        parse_mode="HTML",
        reply_markup=get_logs_options_keyboard(name)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("get_logs:"))
async def get_logs_text(callback: CallbackQuery):
    """Получение и отправка логов в виде текста в Telegram"""
    _, name, tail_str = callback.data.split(":")
    tail = int(tail_str)

    logs = await docker_service.get_logs(name, tail=tail)

    # Ограничение Telegram на длину сообщения (4096 символов)
    max_len = 3800
    if len(logs) > max_len:
        logs = logs[-max_len:]

    text = f"📋 <b>Логи {safe_html(name)} ({tail} строк):</b>\n<pre>{safe_html(logs)}</pre>"

    try:
        await callback.message.answer(text, parse_mode="HTML")
    except Exception:
        # Если возникли сложности с парсингом, отправляем чистым текстом
        await callback.message.answer(f"📋 Логи {name} ({tail} строк):\n\n{logs[:3800]}")
    await callback.answer()

@router.callback_query(F.data.startswith("get_logs_file:"))
async def get_logs_file(callback: CallbackQuery):
    """Отправка логов в виде текстового файла"""
    name = callback.data.split(":")[1]
    await callback.answer("⏳ Подготовка лог-файла...")
    logs = await docker_service.get_logs(name, tail=2000)

    file_bytes = logs.encode("utf-8")
    input_file = BufferedInputFile(file_bytes, filename=f"logs_{name}.log")

    await callback.message.answer_document(
        document=input_file,
        caption=f"📁 Логи контейнера <code>{safe_html(name)}</code> (последние 2000 строк)",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("inspect:"))
async def inspect_container_info(callback: CallbackQuery):
    """Детальная информация о контейнере (порты, образ, uptime)"""
    name = callback.data.split(":")[1]
    info_text = await docker_service.inspect_container(name)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к управлению", callback_data=f"manage:{name}")]]
    )
    await callback.message.edit_text(info_text, parse_mode="HTML", reply_markup=back_kb)
    await callback.answer()

@router.callback_query(F.data.startswith("monitor_c:"))
async def start_container_monitor(callback: CallbackQuery):
    """Включение живого мониторинга для конкретного контейнера"""
    name = callback.data.split(":")[1]
    stats = await docker_service.get_container_stats(name)
    await callback.message.edit_text(
        stats,
        parse_mode="HTML",
        reply_markup=get_stop_monitor_keyboard(container_name=name)
    )
    await db.save_monitor(callback.message.chat.id, callback.message.message_id, name, last_text=stats)
    await callback.answer()

@router.callback_query(F.data == "stop_monitoring")
async def stop_monitoring_action(callback: CallbackQuery):
    """Остановка автообновления метрик"""
    await db.delete_monitor(callback.message.chat.id)
    await callback.message.edit_text("📈 <b>Обновление метрик остановлено.</b>", parse_mode="HTML")
    await callback.answer()