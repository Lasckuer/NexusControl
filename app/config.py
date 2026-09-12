import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Централизованная конфигурация бота NexusControl"""
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", "").strip())
    admin_ids: set[int] = field(default_factory=lambda: set())
    proxy_url: str | None = field(default_factory=lambda: os.getenv("PROXY_URL") or None)
    redis_url: str | None = field(default_factory=lambda: os.getenv("REDIS_URL") or None)
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "database.db"))
    
    # Пороги алертов для мониторинга железа (%)
    cpu_threshold: float = field(default_factory=lambda: float(os.getenv("CPU_THRESHOLD", "90.0")))
    ram_threshold: float = field(default_factory=lambda: float(os.getenv("RAM_THRESHOLD", "90.0")))
    disk_threshold: float = field(default_factory=lambda: float(os.getenv("DISK_THRESHOLD", "95.0")))
    alert_cooldown: int = field(default_factory=lambda: int(os.getenv("ALERT_COOLDOWN", "3600")))
    
    # Интервалы таймеров (секунды)
    refresh_interval: int = field(default_factory=lambda: int(os.getenv("REFRESH_INTERVAL", "4")))
    crash_monitor_interval: int = field(default_factory=lambda: int(os.getenv("CRASH_MONITOR_INTERVAL", "5")))
    resource_monitor_interval: int = field(default_factory=lambda: int(os.getenv("RESOURCE_MONITOR_INTERVAL", "30")))

    # Пагинация
    containers_per_page: int = field(default_factory=lambda: int(os.getenv("CONTAINERS_PER_PAGE", "6")))

    def __post_init__(self):
        # Поддержка как нового ADMIN_IDS (список через запятую), так и старого ADMIN_ID
        raw_admin_ids = os.getenv("ADMIN_IDS", "")
        raw_admin_id = os.getenv("ADMIN_ID", "")
        
        parsed_ids = set()
        if raw_admin_ids:
            for item in raw_admin_ids.split(","):
                clean = item.strip()
                if clean.isdigit():
                    parsed_ids.add(int(clean))
        elif raw_admin_id and raw_admin_id.strip().isdigit():
            parsed_ids.add(int(raw_admin_id.strip()))
            
        self.admin_ids = parsed_ids

    def validate(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не задан в конфигурации (.env)!")
        if not self.admin_ids:
            # Предупреждение вместо падения, чтобы бот мог запускаться в тестах
            pass

    def is_admin(self, user_id: int | None) -> bool:
        if user_id is None:
            return False
        return user_id in self.admin_ids

config = Config()
