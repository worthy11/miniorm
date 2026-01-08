import re

class QueryBuilder:
    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Niebezpieczna nazwa identyfikatora SQL: {identifier}")
        return f'"{identifier}"'

    def build_insert(self, mapper, instance):
        table = self._quote(mapper.table_name)
        
        if mapper.inheritance == "SINGLE":
            fields = [name for name in mapper.columns.keys() if name != mapper.pk]
        else:
            fields = [name for name in mapper.local_columns.keys() if name != mapper.pk]
        
        quoted_fields = [self._quote(f) for f in fields]
        placeholders = ", ".join(["?" for _ in fields])
        
        values = []
        for f in fields:
            values.append(instance.__class__.__name__ if f == "type" else getattr(instance, f, None))
        
        sql = f"INSERT INTO {table} ({', '.join(quoted_fields)}) VALUES ({placeholders})"
        return sql, tuple(values)

    def build_select(self, mapper, filters, limit=None, offset=None):
        table = self._quote(mapper.table_name)
        quoted_columns = ", ".join([self._quote(c) for c in mapper.columns.keys()])
        
        sql = f"SELECT {quoted_columns} FROM {table}"
        params = []
        
        if filters:
            clauses = []
            for col, val in filters.items():
                clauses.append(f"{self._quote(col)} = ?")
                params.append(val)
            sql += " WHERE " + " AND ".join(clauses)
        
        if isinstance(limit, int):
            sql += f" LIMIT {limit}"
        return sql, tuple(params)
    
    def build_delete(self, mapper, pk_value):
        table = self._quote(mapper.table_name)
        pk_col = self._quote(mapper.pk)
        sql = f"DELETE FROM {table} WHERE {pk_col} = ?"
        return sql, (pk_value,)

    def build_m2m_insert(self, assoc_table, local_id, remote_id, local_key, remote_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        r_key = self._quote(remote_key)
        
        sql = f"INSERT INTO {table} ({l_key}, {r_key}) VALUES (?, ?)"
        return sql, (local_id, remote_id)

    def build_update(self, mapper, instance):
        table = self._quote(mapper.table_name)
        pk_col = self._quote(mapper.pk)
        
        fields = [name for name in mapper.local_columns.keys() if name != mapper.pk]
        
        set_clause = ", ".join([f"{self._quote(f)} = ?" for f in fields])
        
        values = []
        for f in fields:
            values.append(instance.__class__.__name__ if f == "type" else getattr(instance, f, None))
                
        pk_val = getattr(instance, mapper.pk)
        values.append(pk_val)
        
        sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = ?"
        return sql, tuple(values)