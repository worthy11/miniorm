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

    def execute(self, sql, params=None, return_lastrowid=False):
        clean_params = []
        if params:
            for p in params:
                if hasattr(p, 'column_type'):
                    clean_params.append(getattr(p, 'value', None))
                else:
                    clean_params.append(p)

        self._log(sql, clean_params if clean_params else params)
        cursor = self.connection.cursor()
        cursor.execute(sql, tuple(clean_params) if clean_params else (params or ()))
        
        if return_lastrowid:
            return cursor.lastrowid
        return cursor.fetchall()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()