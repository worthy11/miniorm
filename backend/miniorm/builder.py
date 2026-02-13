import re

class QueryBuilder:
    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_#]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Unsafe SQL identifier: {identifier}")
        return f'"{identifier}"'

    def build_insert(self, table_name, data):
        """Build INSERT SQL from table name and data dict. Does not use mapper."""
        table = self._quote(table_name)
        fields = list(data.keys())
        quoted_fields = [self._quote(f) for f in fields]
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[f] for f in fields]
        sql = f"INSERT INTO {table} ({', '.join(quoted_fields)}) VALUES ({placeholders})"
        return sql, tuple(values)

    def build_select(self, mapper, filters, limit=None, offset=None, joins=None, order_by=None):
        table_name = mapper.table_name
        table = self._quote(table_name)
        order_by_prefix = table_name

        params = []
        filter_prefix = table

        if mapper.inheritance and mapper.inheritance.strategy.name == "CONCRETE" and not mapper.parent and mapper.children:
            def _concrete_descendant_mappers(m):
                out = []
                for child_cls in m.children:
                    cm = child_cls._mapper
                    out.append(cm)
                    out.extend(_concrete_descendant_mappers(cm))
                return out
            all_mappers = _concrete_descendant_mappers(mapper)
            all_possible_cols = set()
            for m in all_mappers:
                all_possible_cols.update(m.columns.keys())
            sorted_cols = sorted(list(all_possible_cols))

            union_parts = []
            for m in all_mappers:
                m_quoted_table = self._quote(m.table_name)
                m_select_cols = []
                for c_name in sorted_cols:
                    alias = f"{m.table_name}#{c_name}"
                    if c_name in m.columns:
                        m_select_cols.append(f"{m_quoted_table}.{self._quote(c_name)} AS {self._quote(alias)}")
                    else:
                        m_select_cols.append(f"NULL AS {self._quote(alias)}")
                
                m_select_cols.append(f"'{m.cls.__name__}' AS _concrete_type")
                union_parts.append(f"SELECT DISTINCT {', '.join(m_select_cols)} FROM {m_quoted_table}")
            
            subquery = " UNION ALL ".join(union_parts)
            table = f"({subquery})"
            order_by_prefix = all_mappers[0].table_name if all_mappers else table_name
            cols = [self._quote(f'{mapper.table_name}#{c}') for c in sorted_cols] + ["_concrete_type"]
            filter_prefix = ""
        
        else:
            if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS":
                local_cols = mapper.declared_columns.keys()
            else:
                local_cols = mapper.columns.keys()

            cols = [f"{table}.{self._quote(c)} AS {self._quote(f'{table_name}#{c}')}" for c in local_cols]

            if mapper.inheritance and mapper.inheritance.strategy.name == "SINGLE":
                root = mapper
                while root.parent: root = root.parent
                if root.discriminator not in local_cols:
                    cols.append(f"{table}.{self._quote(root.discriminator)} AS {self._quote(f'{table_name}#{root.discriminator}')}")

            all_joins = []

            if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS" and mapper.parent:
                pm = mapper.parent
                p_table = self._quote(pm.table_name)
                all_joins.append(f'JOIN {p_table} ON {table}.{self._quote(mapper.pk)} = {p_table}.{self._quote(pm.pk)}')
                for c in pm.columns.keys():
                    if c not in local_cols:
                        cols.append(f"{p_table}.{self._quote(c)}")

            children = getattr(mapper, 'children', [])
            is_class_parent = any(hasattr(c, '_mapper') and c._mapper.inheritance and 
                                 c._mapper.inheritance.strategy.name == "CLASS" for c in children)
            if is_class_parent:
                for child_cls in children:
                    cm = child_cls._mapper
                    sub_table = self._quote(cm.table_name)
                    all_joins.append(f'LEFT JOIN {sub_table} ON {table}.{self._quote(mapper.pk)} = {sub_table}.{self._quote(cm.pk)}')
                    
                    child_pk_alias = f"{cm.table_name}#{cm.pk}"
                    cols.append(f"{sub_table}.{self._quote(cm.pk)} AS {self._quote(child_pk_alias)}")
                    for col_name in cm.declared_columns.keys():
                        if col_name == cm.pk: continue
                        alias = f"{cm.table_name}#{col_name}"
                        cols.append(f"{sub_table}.{self._quote(col_name)} AS {self._quote(alias)}")

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

 
        sql = f"SELECT {', '.join(cols)} FROM {table}"
        if 'all_joins' in locals() and all_joins:
            sql += " " + " ".join(all_joins)

 
        actual_filters = dict(filters)
 
        if mapper.inheritance and mapper.inheritance.strategy.name == "SINGLE" and mapper.parent:
            root = mapper
            while root.parent: root = root.parent
            actual_filters[root.discriminator] = mapper.discriminator_value

        if actual_filters:
            where_parts = []
            for col, val in actual_filters.items():
                if "(" in table:
                    quoted_col = self._quote(f"{table_name}#{col}")
                else:
                    target_prefix = table
                    if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS":
                        if col not in mapper.declared_columns and mapper.parent:
                            if col in mapper.parent.columns:
                                target_prefix = self._quote(mapper.parent.table_name)
                    quoted_col = f"{target_prefix}.{self._quote(col)}" if target_prefix else self._quote(col)

                if val is None:
                    where_parts.append(f"{quoted_col} IS NULL")
                else:
                    where_parts.append(f"{quoted_col} = ?")
                    params.append(val)
            sql += " WHERE " + " AND ".join(where_parts)

        if order_by:
            order_clauses = []
            for col, dir in order_by:
                if mapper.inheritance and mapper.inheritance.strategy.name == "CONCRETE" and not mapper.parent and mapper.children:
                    ref = self._quote(f"{order_by_prefix}#{col}")
                elif "(" in table:
                    ref = self._quote(f"{order_by_prefix}#{col}")
                else:
                    ref = f"{table}.{self._quote(col)}"
                order_clauses.append(f"{ref} {dir}")
            sql += " ORDER BY " + ", ".join(order_clauses)
        
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
            if offset is not None: sql += f" OFFSET {int(offset)}"
        elif offset is not None:
            sql += f" LIMIT -1 OFFSET {int(offset)}"

        return sql, tuple(params)
    
    def build_delete(self, table_name, pk_value, pk_column="id"):
        """Build DELETE SQL from table name and pk. Does not use mapper."""
        table = self._quote(table_name)
        pk_col = self._quote(pk_column)
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
    
    def build_m2m_cleanup(self, assoc_table, local_id, local_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        
        sql = f"DELETE FROM {table} WHERE {l_key} = ?"
        
        return sql, (local_id,)

    def build_update(self, table_name, data, pk_column="id"):
        """Build UPDATE SQL from table name and data dict. data must contain _pk for WHERE. Does not use mapper."""
        table = self._quote(table_name)
        data = dict(data)
        pk_val = data.pop("_pk", None)
        if pk_val is None:
            raise ValueError("update data must contain _pk for WHERE clause")
        set_parts = []
        params = []
        for col, val in data.items():
            set_parts.append(f"{self._quote(col)} = ?")
            params.append(val)
        params.append(pk_val)
        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {self._quote(pk_column)} = ?"
        return sql, tuple(params)