import logging
import sys
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "bot_log.log")

handlers: list[logging.Handler] = [
    logging.StreamHandler(sys.stdout)
]

# Если указан LOG_FILE или включен в docker / продакшене, пишем также в файл
if LOG_FILE:
    try:
        handlers.append(logging.FileHandler(LOG_FILE, encoding="utf-8"))
    except Exception:
        pass

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=handlers
)

logger = logging.getLogger("NexusControl")