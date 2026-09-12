import math
from typing import Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.aliases import prettify_name

def get_containers_keyboard(
    containers: list[Any],
    page: int = 0,
    per_page: int = 6,
    status_filter: str | None = None
) -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура списка контейнеров с пагинацией и фильтрами
    """
    buttons: list[list[InlineKeyboardButton]] = []

    # 1. Фильтры
    all_mark = "🔘" if status_filter is None else "⚪"
    run_mark = "🔘" if status_filter == "running" else "⚪"
    stop_mark = "🔘" if status_filter == "exited" else "⚪"

    filter_row = [
        InlineKeyboardButton(text=f"{all_mark} Все", callback_data="filter:all"),
        InlineKeyboardButton(text=f"{run_mark} 🟢 Вкл", callback_data="filter:running"),
        InlineKeyboardButton(text=f"{stop_mark} 🔴 Выкл", callback_data="filter:exited")
    ]
    buttons.append(filter_row)

    # 2. Фильтрация списка
    if status_filter:
        filtered = [c for c in containers if c.status == status_filter]
    else:
        filtered = list(containers)

    total_items = len(filtered)
    total_pages = max(1, math.ceil(total_items / per_page))
    current_page = max(0, min(page, total_pages - 1))

    # Срез для текущей страницы
    start_idx = current_page * per_page
    end_idx = start_idx + per_page
    page_items = filtered[start_idx:end_idx]

    # 3. Кнопки контейнеров
    for c in page_items:
        nice_name = prettify_name(c.name)
        status_icon = "🟢" if c.status == "running" else ("⏸" if c.status == "paused" else "🔴")
        btn_text = f"{status_icon} {nice_name}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"manage:{c.name}")])

    # 4. Пагинация (если страниц > 1)
    if total_pages > 1:
        nav_row: list[InlineKeyboardButton] = []
        if current_page > 0:
            nav_row.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"page:{current_page - 1}"))
        else:
            nav_row.append(InlineKeyboardButton(text="⏹", callback_data="noop"))

        nav_row.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="noop"))

        if current_page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"page:{current_page + 1}"))
        else:
            nav_row.append(InlineKeyboardButton(text="⏹", callback_data="noop"))

        buttons.append(nav_row)

    # 5. Управление списком
    buttons.append([InlineKeyboardButton(text="🔄 Обновить список", callback_data="refresh_list")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_container_actions_keyboard(name: str, is_running: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура действий над выбранным контейнером"""
    buttons = []

    if is_running:
        buttons.append([
            InlineKeyboardButton(text="🔄 Перезапуск", callback_data=f"action:restart:{name}"),
            InlineKeyboardButton(text="🛑 Остановка", callback_data=f"action:stop:{name}")
        ])
        buttons.append([
            InlineKeyboardButton(text="⏸ Пауза", callback_data=f"action:pause:{name}"),
            InlineKeyboardButton(text="💀 Kill", callback_data=f"confirm_req:kill:{name}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="▶️ Запустить", callback_data=f"action:start:{name}"),
            InlineKeyboardButton(text="🔄 Перезапуск", callback_data=f"action:restart:{name}")
        ])

    buttons.append([
        InlineKeyboardButton(text="📋 Логи", callback_data=f"logs_menu:{name}"),
        InlineKeyboardButton(text="ℹ️ Подробно", callback_data=f"inspect:{name}")
    ])
    buttons.append([
        InlineKeyboardButton(text="📈 Живой монитор", callback_data=f"monitor_c:{name}")
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ К списку контейнеров", callback_data="refresh_list")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_logs_options_keyboard(name: str) -> InlineKeyboardMarkup:
    """Меню выбора формата и количества логов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 50 строк", callback_data=f"get_logs:{name}:50"),
                InlineKeyboardButton(text="📄 100 строк", callback_data=f"get_logs:{name}:100"),
                InlineKeyboardButton(text="📄 300 строк", callback_data=f"get_logs:{name}:300")
            ],
            [
                InlineKeyboardButton(text="📁 Скачать файлом (.log)", callback_data=f"get_logs_file:{name}")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад к контейнеру", callback_data=f"manage:{name}")
            ]
        ]
    )


def get_confirm_keyboard(action: str, target: str) -> InlineKeyboardMarkup:
    """Диалог подтверждения опасных операций (kill, prune)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, подтверждаю", callback_data=f"confirm:{action}:{target}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_action:{target}")
            ]
        ]
    )


def get_prune_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения очистки Docker"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="♻️ Очистить (без Volumes)", callback_data="confirm_prune:standard"),
            ],
            [
                InlineKeyboardButton(text="⚠️ Полная очистка (+ Volumes)", callback_data="confirm_prune:all"),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_prune")
            ]
        ]
    )


def get_stop_monitor_keyboard(container_name: str | None = None) -> InlineKeyboardMarkup:
    """Клавиатура остановки активного мониторинга"""
    buttons = [
        [InlineKeyboardButton(text="🛑 Остановить автообновление", callback_data="stop_monitoring")]
    ]
    if container_name:
        buttons.append([
            InlineKeyboardButton(text="⬅️ Управление контейнером", callback_data=f"manage:{container_name}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
