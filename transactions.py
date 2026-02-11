from abc import ABC, abstractmethod

class Transaction(ABC):
    def __init__(self, session, entity):
        self.session = session
        self.entity = entity

    @abstractmethod
    def prepare(self):
        """Prepare SQL and parameters. Returns list of (sql, params, callback, rebuild_fn) tuples.
        
        callback is a function that takes (result, previous_id) and applies side effects.
        rebuild_fn is called before execution to rebuild SQL if needed (for FK updates).
        """
        pass


class InsertTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper
        builder = self.session.query_builder
        operations = mapper.prepare_insert(self.entity)

        fk_from = operations.pop("_fk_from_previous", None)  # { table_name: fk_column_name }

        table_order = [k for k in operations if not k.startswith("_")]
        results = []

        for i, table_name in enumerate(table_order):
            data = dict(operations[table_name])
            
            fk_col = fk_from.get(table_name) if fk_from else None
            needs_fk = fk_col is not None
            
            sql, params = builder.build_insert(table_name, data)
            is_last = (i == len(table_order) - 1)

            def make_rebuild_fn(tname, d, fk_col, needs_fk):
                def rebuild_sql(previous_id):
                    if needs_fk and previous_id is not None:
                        setattr(self.entity, fk_col, previous_id)
                        d[fk_col] = previous_id
                        return builder.build_insert(tname, d)
                    return None, None
                return rebuild_sql

            def make_callback(is_last):
                def apply_side_effects(new_id, previous_id):
                    final_id = new_id if new_id is not None else previous_id
                    if is_last:
                        m = self.entity._mapper
                        object.__setattr__(self.entity, m.pk, final_id)
                        self.session.identity_map.add(self.entity.__class__, final_id, self.entity)
                        from states import ObjectState
                        object.__setattr__(self.entity, '_orm_state', ObjectState.PERSISTENT)
                        self.session._flush_m2m(self.entity)
                        self.session._take_snapshot(self.entity)
                return apply_side_effects

            rebuild_fn = make_rebuild_fn(table_name, data, fk_col, needs_fk)
            callback = make_callback(is_last)
            results.append((sql, params, callback, rebuild_fn))
        return results


class UpdateTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper
        old_state = self.session._snapshots.get(id(self.entity))
        operations = mapper.prepare_update(self.entity, old_state)
        if not operations:
            return None, None, None, None
        builder = self.session.query_builder
        results = []
        for table_name, data in operations.items():
            table_mapper = mapper._get_mapper_for_table(table_name)
            pk_col = getattr(table_mapper, "pk", "id")
            sql, params = builder.build_update(table_name, data, pk_column=pk_col)
            def apply_side_effects(result, previous_id):
                self.session._flush_m2m(self.entity)
                self.session._take_snapshot(self.entity)
            results.append((sql, params, apply_side_effects, None))
        return results if len(results) > 1 else results[0] if results else (None, None, None, None)

class DeleteTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper
        builder = self.session.query_builder

        operations = mapper.prepare_delete(self.entity)
        m2m = operations.pop("_m2m_cleanup", [])
        
        results = []
        for item in m2m:
            sql, params = builder.build_m2m_cleanup(
                item["assoc_table"], item["pk_val"], item["local_key"]
            )
            results.append((sql, params, lambda r, p: None, None))
        
        delete_items = list(operations.items())
        for idx, (table_name, pk_data) in enumerate(delete_items):
            table_mapper = mapper._get_mapper_for_table(table_name)
            pk_col = getattr(table_mapper, "pk", "id")
            pk_val = pk_data[pk_col] if isinstance(pk_data, dict) else pk_data
            sql, params = builder.build_delete(table_name, pk_val, pk_column=pk_col)
            is_last = (idx == len(delete_items) - 1)
            pk_val_entity = getattr(self.entity, mapper.pk)

            def apply_side_effects(result, previous_id, final_step=is_last):
                if final_step:
                    self.session.identity_map.remove(self.entity.__class__, pk_val_entity)
                    if id(self.entity) in self.session._snapshots:
                        del self.session._snapshots[id(self.entity)]
                    from states import ObjectState
                    object.__setattr__(self.entity, '_orm_state', ObjectState.DELETED)
            results.append((sql, params, apply_side_effects, None))
        if not results:
            return (None, None, None, None)
        return results if len(results) > 1 else results[0]