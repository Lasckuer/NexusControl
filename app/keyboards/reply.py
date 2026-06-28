from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

ALIASES = {
    "dhczomw": "Nexus Control", 
    "flzrgsoj": "Node Notes",
    "ud552te": "Personal Finance Bot",
    "seaweedfs-admin": "SeaweedFS Admin",
    "seaweedfs-master": "SeaweedFS Master",
    "n6welm1": "Redis",
    "Ogufwalvk": "Synapse"
}

def prettify_name(raw_name: str) -> str:
    for key, nice_name in ALIASES.items():
        if key in raw_name:
            return nice_name
            
    parts = raw_name.split('-')
    if len(parts) > 1 and len(parts[-1]) > 10:
        return " ".join(parts[:-1]).title()
        
    return raw_name.replace('-', ' ').title()

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
        nice_name = prettify_name(c.name)
        # В callback_data оставляем оригинальное имя c.name, чтобы Docker его нашел
        buttons.append([InlineKeyboardButton(text=f"🔹 {nice_name} [{c.status}]", callback_data=f"manage:{c.name}")])
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