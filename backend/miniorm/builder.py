import re

class QueryBuilder:
    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_#]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Unsafe SQL identifier: {identifier}")
        return f'"{identifier}"'

    def build_select(self, mapper, filters, filter_expressions=None, limit=None, offset=None, joins=None, order_by=None):
        table_name = mapper.table_name
        table = self._quote(table_name)

        params = []
        all_joins = []

        selects = mapper.prepare_select()
        cols = {}
        model_col_to_table = {}  # (model_class, column_name) -> table_ref for filter resolution
        select_list = []
        tables_used = set()
        for tbl, columns in selects.items():
            if "_join" in columns:
                join_table, join_on_local, join_on_remote = columns["_join"]
                all_joins.append(f'JOIN {join_table} ON {tbl}.{self._quote(join_on_local)} = {join_table}.{self._quote(join_on_remote)}')
                columns.pop("_join")
            tables_used.add(tbl)
            for col in columns:
                if col not in cols:
                    cols[col] = tbl
                model_col_to_table[(mapper.cls, col)] = tbl
                select_list.append((tbl, col))

        if joins:
            left_mapper = mapper
            left_table = self._quote(left_mapper.table_name)
            for i, rel in enumerate(joins):
                if not getattr(rel, "_resolved_target", None):
                    continue
                
                # For many-to-many, _resolved_target is always correct (bidirectional relationship)
                # For many-to-one/one-to-many, check if backref
                if rel.r_type == "many-to-many":
                    target_mapper = rel._resolved_target._mapper
                    is_backref = False
                else:
                    is_backref = getattr(rel, "local_table", None) and rel.local_table != left_mapper.table_name
                    if is_backref:
                        # For backref, target is the table that has the FK (local_table), not _resolved_target
                        from miniorm.base import MiniBase
                        target_mapper = None
                        for cls in MiniBase._registry:
                            if hasattr(cls, "_mapper") and cls._mapper.table_name == rel.local_table:
                                target_mapper = cls._mapper
                                break
                        if not target_mapper:
                            continue
                    else:
                        target_mapper = rel._resolved_target._mapper
                
                remote_pk = self._quote(target_mapper.pk)
                local_pk = self._quote(left_mapper.pk)

                # 1) Add relationship join first (so target table is in the query before inheritance joins)
                if rel.r_type == "many-to-one":
                    if is_backref:
                        # Backref: FK is on the target table, join target ON target.fk = left.pk
                        local_fk = self._quote(rel._resolved_fk_name)
                        target_table = self._quote(target_mapper.table_name)
                        all_joins.append(f'JOIN {target_table} ON {target_table}.{local_fk} = {left_table}.{local_pk}')
                    else:
                        # Forward: FK is on left table, join target ON left.fk = target.pk
                        local_fk = self._quote(rel._resolved_fk_name)
                        target_table = self._quote(target_mapper.table_name)
                        all_joins.append(f'JOIN {target_table} ON {left_table}.{local_fk} = {target_table}.{remote_pk}')
                elif rel.r_type == "one-to-many":
                    remote_fk = self._quote(rel._resolved_fk_name)
                    target_table = self._quote(target_mapper.table_name)
                    all_joins.append(f'JOIN {target_table} ON {left_table}.{local_pk} = {target_table}.{remote_fk}')
                elif rel.r_type == "many-to-many" and rel.association_table:
                    assoc = rel.association_table
                    assoc_table = self._quote(assoc.name)
                    a_alias = self._quote(f"assoc_{i}")
                    target_table = self._quote(target_mapper.table_name)
                    all_joins.append(
                        f'JOIN {assoc_table} AS {a_alias} ON {left_table}.{local_pk} = {a_alias}.{self._quote(assoc.local_key)}'
                    )
                    all_joins.append(
                        f'JOIN {target_table} ON {a_alias}.{self._quote(assoc.remote_key)} = {target_table}.{remote_pk}'
                    )

                # 2) Then add target's inheritance joins and columns (alias parent table if already in query)
                selects = target_mapper.prepare_select()
                table_alias = {}  # join_table -> alias when we alias a duplicate table
                for tbl, columns in selects.items():
                    cols_copy = dict(columns)
                    if "_join" in cols_copy:
                        join_table, join_on_local, join_on_remote = cols_copy.pop("_join")
                        if join_table in tables_used:
                            alias = f"{join_table}_{i}"
                            table_alias[join_table] = alias
                            tables_used.add(alias)
                            all_joins.append(
                                f'JOIN {join_table} AS {self._quote(alias)} ON {self._quote(tbl)}.{self._quote(join_on_local)} = {self._quote(alias)}.{self._quote(join_on_remote)}'
                            )
                        else:
                            tables_used.add(join_table)
                            all_joins.append(
                                f'JOIN {self._quote(join_table)} ON {self._quote(tbl)}.{self._quote(join_on_local)} = {self._quote(join_table)}.{self._quote(join_on_remote)}'
                            )
                    tbl_ref = table_alias.get(tbl, tbl)
                    if tbl_ref not in tables_used and tbl_ref == tbl:
                        tables_used.add(tbl)
                    for col in cols_copy:
                        if col not in cols:
                            cols[col] = tbl_ref
                        target_cls = target_mapper.cls if is_backref else rel._resolved_target
                        model_col_to_table[(target_cls, col)] = tbl_ref
                        select_list.append((tbl_ref, col))

                left_mapper = target_mapper
                left_table = self._quote(left_mapper.table_name)

        if joins and select_list:
            select_clause = ', '.join(
                f'{self._quote(t)}.{self._quote(c)} AS {self._quote(t + "#" + c)}'
                for t, c in select_list
            )
        else:
            select_clause = ', '.join([f'{t}.{self._quote(c)}' for t, c in select_list])
        sql = f"SELECT {select_clause} FROM {table}"
        if 'all_joins' in locals() and all_joins:
            sql += " " + " ".join(all_joins)

        where_parts = []
        
        actual_filters = dict(filters)
        if actual_filters:
            main_table = mapper.table_name
            for col, val in actual_filters.items():
                table_name = cols.get(col, main_table)
                prefixed_col = f"{table_name}.{self._quote(col)}"

                if val is None:
                    where_parts.append(f"{prefixed_col} IS NULL")
                else:
                    where_parts.append(f"{prefixed_col} = ?")
                    params.append(val)
        
        if filter_expressions:
            for expr in filter_expressions:
                sql_part, expr_params = self._build_filter_expression(expr, cols, table, model_col_to_table)
                where_parts.append(sql_part)
                params.extend(expr_params)
        
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)

        if order_by:
            order_clauses = []
            for item in order_by:
                if hasattr(item, 'column_name'):
                    column = item.column_name
                    direction = item.direction
                    
                    if item.model_class:
                        target_mapper = item.model_class._mapper
                        table_name = target_mapper.table_name
                        
                        curr = target_mapper
                        while curr:
                            if column in curr.columns:
                                table_name = curr.table_name
                                break
                            curr = curr.parent
                    else:
                        table_name = cols.get(column, mapper.table_name)
                else:
                    column, direction = item
                    table_name = cols.get(column, mapper.table_name)

                prefixed_col = f"{self._quote(table_name)}.{self._quote(column)}"
                order_clauses.append(f"{prefixed_col} {direction}")
            
            sql += " ORDER BY " + ", ".join(order_clauses)
        
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
            if offset is not None: sql += f" OFFSET {int(offset)}"
        elif offset is not None:
            sql += f" LIMIT -1 OFFSET {int(offset)}"

        return sql, tuple(params)
    
    def _resolve_filter_table(self, expr, cols, table, model_col_to_table):
        """Resolve table (or alias) for a filter expression column; use model_class when present."""
        default_table = table.strip('"') if isinstance(table, str) else table
        if model_col_to_table and getattr(expr, 'model_class', None) is not None:
            t = model_col_to_table.get((expr.model_class, expr.column_name))
            if t is not None:
                return t
        return cols.get(expr.column_name, default_table)

    def _build_filter_expression(self, expr, cols, table, model_col_to_table=None):
        """Convert a filter expression into SQL and parameters"""
        from miniorm.filters import (
            ComparisonFilter, InFilter, NotInFilter, LikeFilter, ILikeFilter,
            IsNullFilter, IsNotNullFilter, BetweenFilter, CombinedFilter, ColumnFilter, NotFilter
        )
        if model_col_to_table is None:
            model_col_to_table = {}
        params = []
        default_table = table.strip('"') if isinstance(table, str) else table

        if isinstance(expr, ComparisonFilter):
            table_name = self._resolve_filter_table(expr, cols, table, model_col_to_table)
            prefixed_col = f"{table_name}.{self._quote(expr.column_name)}"
            if expr.is_field_comparison:
                other_col = expr.value.column_name
                other_model = getattr(expr.value, 'model_class', None)
                if model_col_to_table and other_model is not None:
                    other_table_name = model_col_to_table.get((other_model, other_col), cols.get(other_col, default_table))
                else:
                    other_table_name = cols.get(other_col, default_table)
                prefixed_other_col = f"{other_table_name}.{self._quote(other_col)}"
                return f"{prefixed_col} {expr.operator} {prefixed_other_col}", params
            else:
                return f"{prefixed_col} {expr.operator} ?", [expr.value]
        elif isinstance(expr, InFilter):
            table_name = self._resolve_filter_table(expr, cols, table, model_col_to_table)
            prefixed_col = f"{table_name}.{self._quote(expr.column_name)}"
            placeholders = ", ".join(["?" for _ in expr.values])
            return f"{prefixed_col} IN ({placeholders})", list(expr.values)
        elif isinstance(expr, NotInFilter):
            table_name = self._resolve_filter_table(expr, cols, table, model_col_to_table)
            prefixed_col = f"{table_name}.{self._quote(expr.column_name)}"
            placeholders = ", ".join(["?" for _ in expr.values])
            return f"{prefixed_col} NOT IN ({placeholders})", list(expr.values)
        elif isinstance(expr, LikeFilter):
            table_name = self._resolve_filter_table(expr, cols, table, model_col_to_table)
            prefixed_col = f"{table_name}.{self._quote(expr.column_name)}"
            return f"{prefixed_col} LIKE ?", [expr.pattern]
        elif isinstance(expr, ILikeFilter):
            table_name = self._resolve_filter_table(expr, cols, table, model_col_to_table)
            prefixed_col = f"{table_name}.{self._quote(expr.column_name)}"
            return f"LOWER({prefixed_col}) LIKE LOWER(?)", [expr.pattern]
        elif isinstance(expr, IsNullFilter):
            table_name = self._resolve_filter_table(expr, cols, table, model_col_to_table)
            prefixed_col = f"{table_name}.{self._quote(expr.column_name)}"
            return f"{prefixed_col} IS NULL", []
        elif isinstance(expr, IsNotNullFilter):
            table_name = self._resolve_filter_table(expr, cols, table, model_col_to_table)
            prefixed_col = f"{table_name}.{self._quote(expr.column_name)}"
            return f"{prefixed_col} IS NOT NULL", []
        elif isinstance(expr, BetweenFilter):
            table_name = self._resolve_filter_table(expr, cols, table, model_col_to_table)
            prefixed_col = f"{table_name}.{self._quote(expr.column_name)}"
            return f"{prefixed_col} BETWEEN ? AND ?", [expr.lower, expr.upper]
        elif isinstance(expr, CombinedFilter):
            parts = []
            all_params = []
            for sub_expr in expr.filters:
                sql_part, expr_params = self._build_filter_expression(sub_expr, cols, table, model_col_to_table)
                parts.append(f"({sql_part})")
                all_params.extend(expr_params)
            return f" {expr.logic} ".join(parts), all_params
        elif isinstance(expr, NotFilter):
            sql_part, expr_params = self._build_filter_expression(expr.filter_expr, cols, table, model_col_to_table)
            return f"NOT ({sql_part})", expr_params
        else:
            raise TypeError(f"Unknown filter expression type: {type(expr)}")

    def build_insert(self, table_name, data):
        table = self._quote(table_name)
        fields = list(data.keys())
        if not fields:
            raise ValueError(f"Cannot build INSERT for {table_name}: no columns in data {data!r}")
        quoted_fields = [self._quote(f) for f in fields]
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[f] for f in fields]
        sql = f"INSERT INTO {table} ({', '.join(quoted_fields)}) VALUES ({placeholders})"
        return sql, tuple(values)
    
    def build_update(self, table_name, data):
        table = self._quote(table_name)
        set_parts = []
        params = []

        pk_info = data["_pk"]
        pk_col, pk_val = list(pk_info.items())[0]

        for col, val in data.items():
            if col == "_pk" or col == pk_col:
                continue
            set_parts.append(f"{self._quote(col)} = ?")
            params.append(val)
        params.append(pk_val)

        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {self._quote(pk_col)} = ?"
        return sql, tuple(params)

    def build_delete(self, table_name, data):
        params = []

        col, val = list(data.items())[0]
        params.append(val)
        
        sql = f"DELETE FROM {table_name} WHERE {self._quote(col)} = ?"
        return sql, tuple(params)

    def build_m2m_insert(self, assoc_table, local_id, remote_id, local_key, remote_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        r_key = self._quote(remote_key)
        sql = f"INSERT INTO {table} ({l_key}, {r_key}) VALUES (?, ?)"
        # print(f"DEBUG: M2M INSERT: {sql}")
        return sql, (local_id, remote_id)
        
    def build_m2m_delete(self, assoc_table, local_id, remote_id, local_key, remote_key):
        table = self._quote(assoc_table)
        l_key = self._quote(local_key)
        r_key = self._quote(remote_key)
        sql = f"DELETE FROM {table} WHERE {l_key} = ? AND {r_key} = ?"
        # print(f"DEBUG: M2M DELETE: {sql}")
        return sql, (local_id, remote_id)