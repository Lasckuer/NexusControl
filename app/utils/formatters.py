import html

def safe_html(text: str | None) -> str:
    """Безопасное экранирование HTML для Telegram"""
    if text is None:
        return ""
    return html.escape(str(text))

def format_bytes(bytes_count: float | int, precision: int = 2) -> str:
    """Форматирование байт в человекочитаемый вид (B, KB, MB, GB, TB)"""
    if bytes_count < 0:
        bytes_count = 0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(bytes_count)
    unit_index = 0
    while value >= 1024.0 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1
    return f"{round(value, precision)} {units[unit_index]}"

def format_progress_bar(percent: float, length: int = 10) -> str:
    """Генерация текстового прогресс-бара, например: [████████░░]"""
    clamped = max(0.0, min(100.0, float(percent)))
    filled_len = int(round(length * clamped / 100))
    bar = "█" * filled_len + "░" * (length - filled_len)
    return f"[{bar}]"

def format_uptime(seconds: float | int) -> str:
    """Преобразование секунд в человекочитаемый формат времени (дни, часы, минуты, секунды)"""
    sec = int(seconds)
    if sec < 60:
        return f"{sec} сек"
    
    days = sec // 86400
    hours = (sec % 86400) // 3600
    minutes = (sec % 3600) // 60
    rem_sec = sec % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} дн")
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} мин")
    if days == 0 and hours == 0 and rem_sec > 0:
        parts.append(f"{rem_sec} сек")
        
    return " ".join(parts) if parts else "0 сек"

def format_status_badge(status: str) -> str:
    """Цветной значок для статуса контейнера"""
    st = status.lower() if status else ""
    if st == "running":
        return "🟢 Работает"
    elif st in ["exited", "stopped"]:
        return "🔴 Остановлен"
    elif st == "paused":
        return "⏸ На паузе"
    elif st == "restarting":
        return "🔄 Перезапуск"
    elif st == "dead":
        return "💀 Мертв"
    elif st == "created":
        return "🟡 Создан"
    return f"⚪ {status.capitalize()}"

def format_health_badge(health_status: str | None) -> str:
    """Значок состояния Healthcheck"""
    if not health_status:
        return "—"
    hs = health_status.lower()
    if hs == "healthy":
        return "💚 Здоров"
    elif hs == "unhealthy":
        return "💔 Ошибка (Unhealthy)"
    elif hs == "starting":
        return "⏳ Проверка при запуске..."
    return f"⚪ {health_status}"
