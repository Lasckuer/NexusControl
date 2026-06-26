import sqlite3

class Database:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_monitors (
                    chat_id INTEGER PRIMARY KEY,
                    message_id INTEGER,
                    container_name TEXT
                )
            """)
            conn.commit()

    def save_monitor(self, chat_id, message_id, container_name=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO active_monitors (chat_id, message_id, container_name)
                VALUES (?, ?, ?)
            """, (chat_id, message_id, container_name))
            conn.commit()

    def get_all_monitors(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id, message_id, container_name FROM active_monitors")
            return cursor.fetchall()

    def delete_monitor(self, chat_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM active_monitors WHERE chat_id = ?", (chat_id,))
            conn.commit()

db = Database()