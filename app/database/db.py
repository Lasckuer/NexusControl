import time
import aiosqlite
from logger import logger

class Database:
    """Асинхронное хранилище состояния на базе aiosqlite"""
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def get_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def init_db(self) -> None:
        """Инициализация таблиц базы данных"""
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            # Активные сообщения с автообновлением метрик
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_monitors (
                    chat_id INTEGER PRIMARY KEY,
                    message_id INTEGER NOT NULL,
                    container_name TEXT,
                    last_text TEXT DEFAULT '',
                    updated_at REAL
                )
            """)
            # Таблица намеренно остановленных контейнеров для исключения ложных алертов о падении
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS intentional_stops (
                    container_name TEXT PRIMARY KEY,
                    stopped_at REAL NOT NULL
                )
            """)
        await conn.commit()
        logger.info(f"База данных успешно инициализирована ({self.db_path})")

    async def save_monitor(self, chat_id: int, message_id: int, container_name: str | None = None, last_text: str = "") -> None:
        """Сохранить или обновить монитор для чата"""
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO active_monitors (chat_id, message_id, container_name, last_text, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, message_id, container_name, last_text, time.time()))
        await conn.commit()

    async def update_monitor_text(self, chat_id: int, last_text: str) -> None:
        """Обновить кэш последнего текста сообщения для предотвращения лишних запросов к Telegram"""
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                UPDATE active_monitors SET last_text = ?, updated_at = ? WHERE chat_id = ?
            """, (last_text, time.time(), chat_id))
        await conn.commit()

    async def get_all_monitors(self) -> list[tuple[int, int, str | None, str]]:
        """Получить список всех активных мониторов: [(chat_id, message_id, container_name, last_text), ...]"""
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT chat_id, message_id, container_name, COALESCE(last_text, '') FROM active_monitors")
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2], row[3]) for row in rows]

    async def delete_monitor(self, chat_id: int) -> None:
        """Удалить монитор чата"""
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM active_monitors WHERE chat_id = ?", (chat_id,))
        await conn.commit()

    async def add_intentional_stop(self, container_name: str) -> None:
        """Отметить контейнер как намеренно остановленный администратором"""
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO intentional_stops (container_name, stopped_at)
                VALUES (?, ?)
            """, (container_name, time.time()))
        await conn.commit()

    async def remove_intentional_stop(self, container_name: str) -> None:
        """Снять отметку о намеренной остановке при последующем запуске"""
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM intentional_stops WHERE container_name = ?", (container_name,))
        await conn.commit()

    async def is_intentional_stop(self, container_name: str) -> bool:
        """Проверить, был ли контейнер намеренно остановлен через бота"""
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT 1 FROM intentional_stops WHERE container_name = ?", (container_name,))
            row = await cursor.fetchone()
            return row is not None

    async def close(self) -> None:
        """Корректно закрыть соединение с базой данных"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Соединение с базой данных закрыто.")

db = Database()