import sqlite3
import logging

class DatabaseEngine:
    logger = logging.getLogger("MiniORM")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

    def __init__(self, db_path=":memory:"):
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row 

    def _log(self, sql, params=None):
        msg = f"[SQL EXECUTE]: {sql}"
        if params:
            msg += f" | [PARAMS]: {params}"
        self.logger.info(msg)

    def execute(self, sql, params=None):
        self._log(sql, params)
        cursor = self.connection.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchall()

    def execute_insert(self, sql, params=None):
        self._log(sql, params)
        cursor = self.connection.cursor()
        cursor.execute(sql, params or ())
        return cursor.lastrowid

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()