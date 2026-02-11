from abc import ABC, abstractmethod

class Transaction(ABC):
    def __init__(self, session, entity):
        self.session = session
        self.entity = entity
        self.mapper = entity._mapper

    @abstractmethod
    def prepare(self):
        """Prepare SQL and parameters. Returns list of (sql, params, callback, rebuild_fn) tuples.
        
        callback is a function that takes (result, previous_id) and applies side effects.
        rebuild_fn is called before execution to rebuild SQL if needed (for FK updates).
        """
        pass


class InsertTransaction(Transaction):
    def prepare(self):
        operations = self.mapper.prepare_insert(self.entity, self.session.query_builder)
        results = []
        
        for i, (sql, params, op_meta) in enumerate(operations):
            table_name = op_meta['table']
            table_mapper = self.mapper._get_mapper_for_table(table_name)
            
            if 'type' in table_mapper.columns and 'type' not in op_meta['data']:
                op_meta['data']['type'] = self.entity.__class__.__name__
                sql, params = self.session.query_builder.build_insert(table_mapper, op_meta['data'])

            is_last = (i == len(operations) - 1)
            needs_fk = 'fk_from_previous' in op_meta
            
            def make_rebuild_fn(op_meta, needs_fk):
                def rebuild_sql(previous_id):
                    if needs_fk and previous_id is not None:
                        fk_name = op_meta['fk_from_previous']
                        setattr(self.entity, fk_name, previous_id)
                        op_meta['data'][fk_name] = previous_id
                        
                        t_mapper = self.mapper._get_mapper_for_table(op_meta['table'])
                        if 'type' in t_mapper.columns and 'type' not in op_meta['data']:
                            op_meta['data']['type'] = self.entity.__class__.__name__
                            
                        return self.session.query_builder.build_insert(t_mapper, op_meta['data'])
                    return None, None
                return rebuild_sql
            
            def make_callback(is_last):
                def apply_side_effects(new_id, previous_id):
                    final_id = new_id if new_id is not None else previous_id
                    if is_last:
                        object.__setattr__(self.entity, self.mapper.pk, final_id)
                        self.session.identity_map.add(self.entity.__class__, final_id, self.entity)
                        from states import ObjectState
                        object.__setattr__(self.entity, '_orm_state', ObjectState.PERSISTENT)
                        self.session._flush_m2m(self.entity)
                        self.session._take_snapshot(self.entity)
                return apply_side_effects
            
            rebuild_fn = make_rebuild_fn(op_meta, needs_fk)
            callback = make_callback(is_last)
            results.append((sql, params, callback, rebuild_fn))
        
        return results


class UpdateTransaction(Transaction):
    def prepare(self):
        old_state = self.session._snapshots.get(id(self.entity))
        
        operations = self.mapper.prepare_update(self.entity, self.session.query_builder, old_state)
        
        if not operations:
            return None, None, None, None
        
        results = []
        for sql, params, op_meta in operations:
            def apply_side_effects(result, previous_id):
                self.session._flush_m2m(self.entity)
                self.session._take_snapshot(self.entity)
            
            results.append((sql, params, apply_side_effects, None))
        
        return results if len(results) > 1 else results[0] if results else (None, None, None, None)

class DeleteTransaction(Transaction):
    def prepare(self):
        operations = self.mapper.prepare_delete(self.entity, self.session.query_builder)
        
        results = []
        pk_val = getattr(self.entity, self.mapper.pk)
        
        for i, (sql, params, op_meta) in enumerate(operations):
            is_last = (i == len(operations) - 1)
            
            def apply_side_effects(result, previous_id, final_step=is_last):
                if final_step:
                    self.session.identity_map.remove(self.entity.__class__, pk_val)
                    
                    if id(self.entity) in self.session._snapshots:
                        del self.session._snapshots[id(self.entity)]
                    
                    from states import ObjectState
                    object.__setattr__(self.entity, '_orm_state', ObjectState.DELETED)
            
            results.append((sql, params, apply_side_effects, None))
        
        if not results:
            return (None, None, None, None)
        return results if len(results) > 1 else results[0]