from miniorm.base import MiniBase
from miniorm.orm_types import Column
from miniorm.states import ObjectState
from miniorm.filters import FilterExpression

class Query:
    def __init__(self, model_class, session):
        self.model_class = model_class
        self.session = session
        self.filters = {}
        self.filter_expressions = []
        self._limit = None
        self._offset = None
        self._joins = []
        self._order_by = []

    def filter(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, FilterExpression):
                self.filter_expressions.append(arg)
            else:
                raise TypeError(f"Expected FilterExpression, got {type(arg)}")
        
        if kwargs:
            self.filters.update(kwargs)
        
        return self

    def limit(self, value: int):
        self._limit = value
        return self
    
    def order_by(self, *args):
        for arg in args:
            if isinstance(arg, OrderByExpression):
                self._order_by.append(arg)
            elif isinstance(arg, ColumnFilter):
                self._order_by.append(arg.asc())
            else:
                raise TypeError(f"Expected OrderByExpression or ColumnFilter, got {type(arg)}")
        
        return self
    
    def all(self):
        results = getattr(self, '_results', None)
        if results is not None:
            del self._results
            return results
        self.session._autoflush()
        mapper = MiniBase._registry.get(self.model_class)
        sql, params = self.session.query_builder.build_select(
            mapper, self.filters, filter_expressions=self.filter_expressions,
            limit=self._limit, offset=self._offset, joins=self._joins, order_by=self._order_by
        )
        rows = self.session.engine.execute(sql, params)
        return self._collect_results(rows, mapper)

    def _collect_results(self, rows, mapper):
        main_tables = set(mapper.prepare_select().keys())
        has_joins = [rel for rel in self._joins if getattr(rel, "_resolved_target", None)]
        joined_tables_per_join = []
        for i, rel in enumerate(has_joins):
            target_mapper = rel._resolved_target._mapper
            target_table_set = set(target_mapper.prepare_select().keys())
            alias_set = set()
            for tbl in target_table_set:
                if tbl in main_tables or any(tbl in s for s in joined_tables_per_join):
                    alias_set.add(f"{tbl}_{i}")
                else:
                    alias_set.add(tbl)
            joined_tables_per_join.append(alias_set)

        if not has_joins:
            results = []
            for row in rows:
                row_dict = dict(row) if hasattr(row, 'keys') else {}
                obj = mapper.hydrate(row_dict)
                if not obj:
                    continue
                pk_val = getattr(obj, mapper.pk, None)
                if pk_val is not None:
                    existing = self.session.identity_map.get(obj.__class__, pk_val)
                    if existing:
                        if getattr(existing, '_orm_state', None) == ObjectState.DELETED:
                            continue
                        for col in mapper.get_tracked_column_names():
                            if col != mapper.pk and col in obj.__dict__:
                                object.__setattr__(existing, col, obj.__dict__[col])
                        results.append(existing)
                        continue
                obj = self.session._make_persistent(obj)
                results.append(obj)
            return results

        results = []
        seen_main_pks = set()
        for row in rows:
            row_dict = dict(row) if hasattr(row, 'keys') else {}
            main_dict = {k: v for k, v in row_dict.items() if "#" in k and k.split("#", 1)[0] in main_tables}
            if not main_dict:
                continue
            main_obj = mapper.hydrate(main_dict)
            if not main_obj:
                continue
            pk_val = getattr(main_obj, mapper.pk, None)
            if pk_val is None:
                continue
            existing = self.session.identity_map.get(main_obj.__class__, pk_val)
            result_main = existing if existing else main_obj

            for j, rel in enumerate(has_joins):
                joined_tables = joined_tables_per_join[j] if j < len(joined_tables_per_join) else set()
                joined_dict = {k: v for k, v in row_dict.items() if "#" in k and k.split("#", 1)[0] in joined_tables}
                if not joined_dict:
                    continue
                rel_name = next((n for n, r in self.model_class._mapper.relationships.items() if r is rel), None)
                if rel_name is None:
                    continue
                target_mapper = rel._resolved_target._mapper
                joined_obj = target_mapper.hydrate(joined_dict)
                if not joined_obj:
                    continue
                joined_pk = getattr(joined_obj, target_mapper.pk, None)
                if joined_pk is not None:
                    existing_joined = self.session.identity_map.get(rel._resolved_target, joined_pk)
                    if existing_joined:
                        joined_obj = existing_joined
                    else:
                        joined_obj = self.session._make_persistent(joined_obj)
                if rel_name not in result_main.__dict__:
                    object.__setattr__(result_main, rel_name, [])
                coll = result_main.__dict__[rel_name]
                if not isinstance(coll, list):
                    object.__setattr__(result_main, rel_name, [])
                    coll = result_main.__dict__[rel_name]
                seen_pks = {getattr(o, target_mapper.pk) for o in coll}
                if joined_pk not in seen_pks:
                    coll.append(joined_obj)
                    self.session._take_snapshot(result_main)

            if pk_val not in seen_main_pks:
                seen_main_pks.add(pk_val)
                if not existing:
                    result_main = self.session._make_persistent(result_main)
                results.append(result_main)
        return results

    def first(self):
        self.limit(1)
        results = self.all()
        if not results:
            return None
        obj = results[0]
        if getattr(obj, '_orm_state', None) == ObjectState.DELETED:
            return None
        return obj
    
    def join(self, target_cls, condition=None):
        """Add a join to target_cls. Uses the query model's relationship, or the last-joined model's (for chained joins)."""
        target_table = target_cls._mapper.table_name
        # First try the query model, then any already-joined target (for Student -> Subject -> Teacher)
        to_check = [self.model_class._mapper]
        for rel in self._joins:
            if getattr(rel, "_resolved_target", None):
                to_check.append(rel._resolved_target._mapper)
        for mapper in to_check:
            for name, rel in mapper.relationships.items():
                if getattr(rel, "_resolved_target", None) is target_cls or rel.remote_table == target_table:
                    self._joins.append(rel)
                    if condition:
                        self._joins.append(condition)
                    return self
        return self
    
 
    def join_m2m(self, assoc_table, local_key, remote_key, local_id):
        target_mapper = self.model_class._mapper
        target_table = target_mapper.table_name
        target_pk = target_mapper.pk
        
        sql = (f'SELECT t.* FROM "{target_table}" AS t '
               f'JOIN "{assoc_table}" AS a ON t."{target_pk}" = a."{remote_key}" '
               f'WHERE a."{local_key}" = ?')
        
        rows = self.session.engine.execute(sql, (local_id,))
        
        results = []
        seen_pks = set()
        for row in rows:
            row_dict = dict(row) if hasattr(row, 'keys') else {}
            pk_val = row_dict.get(target_pk)
            if pk_val is None or pk_val in seen_pks:
                continue
            seen_pks.add(pk_val)
            existing = self.session.identity_map.get(self.model_class, pk_val)
            if existing:
                results.append(existing)
            else:
                obj = target_mapper.hydrate(row_dict)
                from miniorm.states import ObjectState
                object.__setattr__(obj, '_orm_state', ObjectState.PERSISTENT)
                object.__setattr__(obj, '_session', self.session)
                self.session.identity_map.add(self.model_class, pk_val, obj)
                self.session._take_snapshot(obj)
                results.append(obj)
        self._results = results
        return self

    
