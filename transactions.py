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
        # Call mapper to prepare insert operations
        operations = self.mapper.prepare_insert(self.entity, self.session.query_builder)
        
        # Convert to list of (sql, params, callback, rebuild_fn) tuples
        results = []
        
        for i, (sql, params, op_meta) in enumerate(operations):
            is_last = (i == len(operations) - 1)
            needs_fk = 'fk_from_previous' in op_meta
            
            def make_rebuild_fn(op_meta, needs_fk):
                def rebuild_sql(previous_id):
                    if needs_fk and previous_id is not None:
                        fk_name = op_meta['fk_from_previous']
                        setattr(self.entity, fk_name, previous_id)
                        op_meta['data'][fk_name] = previous_id
                        table_mapper = self.mapper._get_mapper_for_table(op_meta['table'])
                        return self.session.query_builder.build_insert(table_mapper, op_meta['data'])
                    return None, None
                return rebuild_sql
            
            def make_callback(is_last):
                def apply_side_effects(new_id, previous_id):
                    # Only apply final side effects on last operation
                    if is_last:
                        setattr(self.entity, self.mapper.pk, new_id)
                        self.session.identity_map.add(self.entity.__class__, new_id, self.entity)
                        
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
        
        # Call mapper to prepare update operations
        operations = self.mapper.prepare_update(self.entity, self.session.query_builder, old_state)
        
        if not operations:
            return None, None, None, None  # No update needed
        
        # Convert to list of (sql, params, callback, rebuild_fn) tuples
        results = []
        for sql, params, op_meta in operations:
            def apply_side_effects(result, previous_id):
                self.session._flush_m2m(self.entity)
                self.session._take_snapshot(self.entity)
            
            results.append((sql, params, apply_side_effects, None))
        
        return results if len(results) > 1 else results[0] if results else (None, None, None, None)

class DeleteTransaction(Transaction):
    def prepare(self):
        # Call mapper to prepare delete operations
        operations = self.mapper.prepare_delete(self.entity, self.session.query_builder)
        
        # Convert to list of (sql, params, callback, rebuild_fn) tuples
        results = []
        pk_val = getattr(self.entity, self.mapper.pk)
        
        for sql, params, op_meta in operations:
            def apply_side_effects(result, previous_id):
                self.session.identity_map.remove(self.entity.__class__, pk_val)
            
            results.append((sql, params, apply_side_effects, None))
        
        return results if len(results) > 1 else results[0] if results else (None, None, None, None)