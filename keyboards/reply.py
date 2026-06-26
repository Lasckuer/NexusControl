from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Мониторинг Сервера"), KeyboardButton(text="📦 Контейнеры")],
            [KeyboardButton(text="♻️ Очистка Docker-системы")]
        ],
        resize_keyboard=True
    )

def get_containers_keyboard(containers):
    buttons = []
    for c in containers:
        buttons.append([InlineKeyboardButton(text=f"🔹 {c.name} [{c.status}]", callback_data=f"manage:{c.name}")])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить список", callback_data="refresh_list")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_container_actions_keyboard(name):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Перезапустить", callback_data=f"action:restart:{name}"),
                InlineKeyboardButton(text="🛑 Остановить", callback_data=f"action:stop:{name}")
            ],
            [
                InlineKeyboardButton(text="▶️ Запустить", callback_data=f"action:start:{name}"),
                InlineKeyboardButton(text="📋 Логи (50 строк)", callback_data=f"logs:{name}")
            ],
            [
                InlineKeyboardButton(text="📈 Мониторить", callback_data=f"monitor_c:{name}")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="refresh_list")
            ]
        ]
    )

def get_stop_monitor_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛑 Остановить обновление", callback_data="stop_monitoring")]]
    )