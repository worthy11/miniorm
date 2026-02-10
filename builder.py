import re

class QueryBuilder:
    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Niebezpieczna nazwa identyfikatora SQL: {identifier}")
        return f'"{identifier}"'

    def build_insert(self, mapper, data):
        """Build INSERT SQL from mapper and data dict.
        Data dict should already contain all necessary columns in the correct form
        (inheritance strategies handle discriminator values).
        """
        table = self._quote(mapper.table_name)
        
        fields = list(data.keys())
        quoted_fields = [self._quote(f) for f in fields]
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[f] for f in fields]
        
        sql = f"INSERT INTO {table} ({', '.join(quoted_fields)}) VALUES ({placeholders})"
        return sql, tuple(values)

    def build_select(self, mapper, filters, limit=None, offset=None, joins=None):
        table_name = mapper.table_name
        table = self._quote(table_name)
        
        columns = getattr(mapper, 'columns', {})
        cols = [f"{table}.{self._quote(c)}" for c in columns.keys()] if columns else [f"{table}.*"]
        
        class_inheritance_joins = []
        children = getattr(mapper, 'children', [])
        
        is_class_strategy = False
        if children and hasattr(children[0], 'inheritance'):
            if children[0].inheritance.strategy.name == "CLASS":
                is_class_strategy = True
            
        if is_class_strategy:
            local_pk = self._quote(mapper.pk)
            for subclass_mapper in children:
                subclass_table = self._quote(subclass_mapper.table_name)
                fk_col = f"{table_name.rstrip('s')}_id"
                remote_fk = self._quote(fk_col)
                
                class_inheritance_joins.append(
                    f'LEFT JOIN {subclass_table} ON {table}.{local_pk} = {subclass_table}.{remote_fk}'
                )
                
                for col_name in getattr(subclass_mapper, 'local_columns', {}).keys():
                    if col_name == fk_col: continue
                    alias = f"{subclass_mapper.table_name}_{col_name}"
                    cols.append(f"{subclass_table}.{self._quote(col_name)} AS {self._quote(alias)}")

        join_clauses = []
        if joins:
            for i, rel in enumerate(joins):
                target_mapper = rel._resolved_target._mapper
                target_table = self._quote(target_mapper.table_name)
                remote_pk_val = target_mapper.pk if isinstance(target_mapper.pk, str) else target_mapper.pk[0]
                remote_pk = self._quote(remote_pk_val)
                local_pk_val = mapper.pk if isinstance(mapper.pk, str) else mapper.pk[0]
                local_pk = self._quote(local_pk_val)

                if rel.r_type == "many-to-one":
                    local_fk = self._quote(rel._resolved_fk_name)
                    join_clauses.append(
                        f'JOIN {target_table} ON {table}.{local_fk} = {target_table}.{remote_pk}'
                    )
                elif rel.r_type == "one-to-many":
                    remote_fk = self._quote(rel._resolved_fk_name)
                    join_clauses.append(
                        f'JOIN {target_table} ON {table}.{local_pk} = {target_table}.{remote_fk}'
                    )
                elif rel.r_type == "many-to-many" and rel.association_table:
                    assoc = rel.association_table
                    a_alias = f"a{i}"
                    assoc_table = self._quote(assoc.name)
                    l_key = self._quote(assoc.local_key)
                    r_key = self._quote(assoc.remote_key)
                    join_clauses.append(
                        f'JOIN {assoc_table} AS {a_alias} ON {table}.{local_pk} = {a_alias}.{l_key} '
                        f'JOIN {target_table} ON {a_alias}.{r_key} = {target_table}.{remote_pk}'
                    )

        sql = f"SELECT {', '.join(cols)} FROM {table}"
        
        if class_inheritance_joins:
            sql += " " + " ".join(class_inheritance_joins)

        params = []
        actual_filters = dict(filters)
        
        if mapper.inheritance and mapper.inheritance.strategy.name == "SINGLE":
             if mapper.discriminator not in actual_filters and mapper.discriminator in mapper.columns:
                actual_filters[mapper.discriminator] = mapper.discriminator_value
        
        if join_clauses:
            sql += " " + " ".join(join_clauses)
            
        params = []
        if filters:
            where_parts = []
            for col, val in actual_filters.items():
                quoted_col = f"{table}.{self._quote(col)}"
                if val is None:
                    where_parts.append(f"{quoted_col} IS NULL")
                else:
                    where_parts.append(f"{quoted_col} = ?")
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
        pk_val = mapper.pk if isinstance(mapper.pk, str) else mapper.pk[0]
        pk_col = self._quote(pk_val)
        sql = f"DELETE FROM {table} WHERE {pk_col} = ?"
        return sql, (pk_value,)

    def build_m2m_insert(self, assoc_table, local_id, remote_id, local_key, remote_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        r_key = self._quote(remote_key)
        sql = f"INSERT INTO {table} ({l_key}, {r_key}) VALUES (?, ?)"
        return sql, (local_id, remote_id)
        
    def build_m2m_delete(self, assoc_table, local_id, remote_id, local_key, remote_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        r_key = self._quote(remote_key)
        sql = f"DELETE FROM {table} WHERE {l_key} = ? AND {r_key} = ?"
        return sql, (local_id, remote_id)

    def build_update(self, mapper, data, pk_value):
        table = self._quote(mapper.table_name)
        pk_val = mapper.pk if isinstance(mapper.pk, str) else mapper.pk[0]
        pk_col = self._quote(pk_val)
        
        fields = list(data.keys())
        set_clause = ", ".join([f"{self._quote(f)} = ?" for f in fields])
        
        values = [data[f] for f in fields]
        values.append(pk_value)
        
        sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = ?"
        return sql, tuple(values)