import re

class QueryBuilder:
    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Niebezpieczna nazwa identyfikatora SQL: {identifier}")
        return f'"{identifier}"'

    def build_insert(self, mapper, data):
        table = self._quote(mapper.table_name)
        fields = list(data.keys())
        
        quoted_fields = [self._quote(f) for f in fields]
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[f] for f in fields]
        
        sql = f"INSERT INTO {table} ({', '.join(quoted_fields)}) VALUES ({placeholders})"
        return sql, tuple(values)

    def build_select(self, mapper, filters, limit=None, offset=None, joins=None):
        table = self._quote(mapper.table_name)
        cols = [f"{table}.{self._quote(c)}" for c in mapper.columns.keys()]
        
        join_clauses = []
        if joins:
            for rel in joins:
                target_mapper = rel._resolved_target._mapper
                target_table = self._quote(target_mapper.table_name)
                
                if rel.r_type == "many-to-one":
                    local_fk = self._quote(rel._resolved_fk_name)
                    remote_pk = self._quote(target_mapper.pk)
                    join_clauses.append(
                        f'JOIN {target_table} ON {table}.{local_fk} = {target_table}.{remote_pk}'
                    )
                elif rel.r_type == "one-to-many":
                    local_pk = self._quote(mapper.pk)
                    remote_fk = self._quote(rel._resolved_fk_name)
                    join_clauses.append(
                        f'JOIN {target_table} ON {table}.{local_pk} = {target_table}.{remote_fk}'
                    )

        sql = f"SELECT {', '.join(cols)} FROM {table}"
        
        if join_clauses:
            sql += " " + " ".join(join_clauses)
            
        params = []
        if filters:
            where_parts = []
            for col, val in filters.items():
                where_parts.append(f"{table}.{self._quote(col)} = ?")
                params.append(val)
            sql += " WHERE " + " AND ".join(where_parts)
            
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
            if offset is not None:
                sql += f" OFFSET {int(offset)}"
        elif offset is not None:
            sql += f" LIMIT -1 OFFSET {int(offset)}"
            
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

    def build_update(self, mapper, data, pk_value):
        table = self._quote(mapper.table_name)
        pk_col = self._quote(mapper.pk)
        
        fields = list(data.keys())
        set_clause = ", ".join([f"{self._quote(f)} = ?" for f in fields])
        
        values = [data[f] for f in fields]
        values.append(pk_value)
        
        sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = ?"
        return sql, tuple(values)