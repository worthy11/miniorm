class QueryBuilder:
    def build_insert(self, mapper, instance):
        if mapper.inheritance == "SINGLE":
            fields = [name for name in mapper.columns.keys() if name != mapper.pk]
        else:
            fields = [name for name in mapper.local_columns.keys() if name != mapper.pk]
        
        values = []
        for f in fields:
            if f == "type":
                values.append(instance.__class__.__name__)
            else:
                values.append(getattr(instance, f, None))
        
        placeholders = ", ".join(["?" for _ in fields])
        columns = ", ".join(fields)
        
        sql = f"INSERT INTO {mapper.table_name} ({columns}) VALUES ({placeholders})"
        return sql, tuple(values)

    def build_delete(self, mapper, pk_value):
        sql = f"DELETE FROM {mapper.table_name} WHERE {mapper.pk} = ?"
        return sql, (pk_value,)

    def build_m2m_insert(self, assoc_table, local_id, remote_id, local_key, remote_key):
        sql = f"INSERT INTO {assoc_table} ({local_key}, {remote_key}) VALUES (?, ?)"
        return sql, (local_id, remote_id)

    def build_select(self, mapper, filters, limit=None, offset=None):
        column_names = ", ".join(mapper.columns.keys())
        sql = f"SELECT {column_names} FROM {mapper.table_name}"
        
        params = []
        if filters:
            where_clauses = []
            for col, val in filters.items():
                where_clauses.append(f"{col} = ?")
                params.append(val)
            sql += " WHERE " + " AND ".join(where_clauses)
        
        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"
            
        return sql, tuple(params)
    
    def build_update(self, mapper, instance):
        fields = [name for name in mapper.local_columns.keys() if name != mapper.pk]
        set_clause = ", ".join([f"{f} = ?" for f in fields])
        
        values = []
        for f in fields:
            if f == "type":
                values.append(instance.__class__.__name__)
            else:
                values.append(getattr(instance, f, None))
                
        pk_val = getattr(instance, mapper.pk)
        values.append(pk_val)
        
        sql = f"UPDATE {mapper.table_name} SET {set_clause} WHERE {mapper.pk} = ?"
        return sql, tuple(values)
