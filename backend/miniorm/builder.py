import re

class QueryBuilder:
    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_#]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Unsafe SQL identifier: {identifier}")
        return f'"{identifier}"'

    def build_select(self, mapper, filters, limit=None, offset=None, joins=None, order_by=None):
        table_name = mapper.table_name
        table = self._quote(table_name)

        params = []
        all_joins = []

        selects = mapper.prepare_select()
        cols = {}
        for table_name, columns in selects.items():
            if "_join" in columns:
                join_table, join_on_local, join_on_remote = columns["_join"]
                all_joins.append(f'JOIN {join_table} ON {table_name}.{self._quote(join_on_local)} = {join_table}.{self._quote(join_on_remote)}')
                columns.pop("_join")

            cols.update({col: table_name for col in columns})
        
        if joins:
            for i, rel in enumerate(joins):
                target_mapper = rel._resolved_target._mapper
                target_table = self._quote(target_mapper.table_name)
                remote_pk = self._quote(target_mapper.pk)
                local_pk = self._quote(mapper.pk)
                if rel.r_type == "many-to-one":
                    local_fk = self._quote(rel._resolved_fk_name)
                    all_joins.append(f'JOIN {target_table} ON {table}.{local_fk} = {target_table}.{remote_pk}')
                elif rel.r_type == "one-to-many":
                    remote_fk = self._quote(rel._resolved_fk_name)
                    all_joins.append(f'JOIN {target_table} ON {table}.{local_pk} = {target_table}.{remote_fk}')

                elif rel.r_type == "many-to-many" and rel.association_table:
                    assoc = rel.association_table
                    assoc_table = self._quote(assoc.name)
                    a_alias = self._quote(f"assoc_{i}")
                    
                    all_joins.append(
                        f'JOIN {assoc_table} AS {a_alias} ON {table}.{local_pk} = {a_alias}.{self._quote(assoc.local_key)}'
                    )
                    all_joins.append(
                        f'JOIN {target_table} ON {a_alias}.{self._quote(assoc.remote_key)} = {target_table}.{remote_pk}'
                    )

        sql = f"SELECT {', '.join([f'{table_name}.{self._quote(col)}' for col, table_name in cols.items()])} FROM {table}"
        if 'all_joins' in locals() and all_joins:
            sql += " " + " ".join(all_joins)

        actual_filters = dict(filters)
        if actual_filters:
            where_parts = []
            for col, val in actual_filters.items():
                table_name = cols[col]
                prefixed_col = f"{table_name}.{self._quote(col)}"

                if val is None:
                    where_parts.append(f"{prefixed_col} IS NULL")
                else:
                    where_parts.append(f"{prefixed_col} = ?")
                    params.append(val)
            sql += " WHERE " + " AND ".join(where_parts)

        if order_by:
            order_clauses = []
            for col, direction in order_by:
                table_name = cols[col]
                prefixed_col = f"{table_name}.{self._quote(col)}"
                order_clauses.append(f"{prefixed_col} {direction}")
            sql += " ORDER BY " + ", ".join(order_clauses)
        
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
            if offset is not None: sql += f" OFFSET {int(offset)}"
        elif offset is not None:
            sql += f" LIMIT -1 OFFSET {int(offset)}"

        # print(f"DEBUG: SELECT: {sql}")

        return sql, tuple(params)

    def build_insert(self, table_name, data):
        """Build INSERT SQL from table name and data dict. Does not use mapper."""
        table = self._quote(table_name)
        fields = list(data.keys())
        quoted_fields = [self._quote(f) for f in fields]
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[f] for f in fields]
        sql = f"INSERT INTO {table} ({', '.join(quoted_fields)}) VALUES ({placeholders})"
        return sql, tuple(values)
    
    def build_update(self, table_name, data):
        print(f"DEBUG: UPDATE: {data}")
        table = self._quote(table_name)
        set_parts = []
        params = []

        pk_info = data["_pk"]
        pk_col, pk_val = list(pk_info.items())[0]
        
        for col, val in data.items():
            if col == "_pk":
                continue
            set_parts.append(f"{self._quote(col)} = ?")
            params.append(val)
        params.append(pk_val)

        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {self._quote(pk_col)} = ?"
        print(f"DEBUG: UPDATE: {sql}")
        return sql, tuple(params)

    def build_delete(self, table_name, data):
        where_parts = []
        params = []

        pk_info = data["_pk"]
        pk_col, pk_val = list(pk_info.items())[0]
        params.append(pk_val)
        
        sql = f"DELETE FROM {table_name} WHERE {self._quote(pk_col)} = ?"
        print(f"DEBUG: DELETE: {sql}")
        return sql, tuple(params)

    def build_m2m_insert(self, assoc_table, local_id, remote_id, local_key, remote_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        r_key = self._quote(remote_key)
        sql = f"INSERT INTO {table} ({l_key}, {r_key}) VALUES (?, ?)"
        print(f"DEBUG: M2M INSERT: {sql}")
        return sql, (local_id, remote_id)
        
    def build_m2m_delete(self, assoc_table, local_id, remote_id, local_key, remote_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        r_key = self._quote(remote_key)
        sql = f"DELETE FROM {table} WHERE {l_key} = ? AND {r_key} = ?"
        print(f"DEBUG: M2M DELETE: {sql}")
        return sql, (local_id, remote_id)
    
    def build_m2m_cleanup(self, assoc_table, local_id, local_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        
        sql = f"DELETE FROM {table} WHERE {l_key} = ?"
        
        print(f"DEBUG: M2M CLEANUP: {sql}")
        return sql, (local_id,)