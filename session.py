from collections import deque
from states import ObjectState
from identity_map import IdentityMap
from query import Query
from transactions import InsertTransaction, UpdateTransaction, DeleteTransaction
from mapper import Mapper

class Session:
    def __init__(self, engine, query_builder):
        Mapper.finalize_mappers()
        
        self.engine = engine
        self.query_builder = query_builder
        self.identity_map = IdentityMap()
        self.unit_of_work = deque() 
        self._snapshots = {}
        self._in_flush = False

    def query(self, model_class):
        self._autoflush()
        return Query(model_class, self)
    
    def get(self, model_class, pk):
        existing = self.identity_map.get(model_class, pk)
        if existing: return existing
        return self.query(model_class).filter(**{model_class._mapper.pk: pk}).first()

    def add(self, entity):
        if getattr(entity, '_orm_state', None) == ObjectState.TRANSIENT:
            object.__setattr__(entity, '_orm_state', ObjectState.PENDING)
            object.__setattr__(entity, '_session', self)
            
            self._cascade_add(entity)
            
            self.unit_of_work.append(InsertTransaction(self, entity))

    def update(self, entity):
        if getattr(entity, '_orm_state', None) == ObjectState.PERSISTENT:
             self.unit_of_work.append(UpdateTransaction(self, entity))

    def delete(self, entity):
        if getattr(entity, '_orm_state', None) == ObjectState.PERSISTENT:
            object.__setattr__(entity, '_orm_state', ObjectState.DELETED)
            self.unit_of_work.append(DeleteTransaction(self, entity))

    def flush(self):
        if self._in_flush:
            return
            
        self._in_flush = True
        dirty_objects = self._get_dirty_objects()
        for obj in dirty_objects:
            is_queued = any(t.entity is obj and isinstance(t, UpdateTransaction) for t in self.unit_of_work)
            if not is_queued:
                self.unit_of_work.append(UpdateTransaction(self, obj))

        if not self.unit_of_work:
            self._in_flush = False
            return

        try:
            while self.unit_of_work:
                transaction = self.unit_of_work.popleft()
                operations = transaction.prepare()
                
                # Handle both single operation and list of operations
                if not isinstance(operations, list):
                    operations = [operations]
                
                previous_id = None
                for i, op in enumerate(operations):
                    sql, params, apply_side_effects, rebuild_fn = op
                    
                    # Rebuild SQL if needed (for FK updates in CLASS inheritance)
                    if rebuild_fn and previous_id is not None:
                        new_sql, new_params = rebuild_fn(previous_id)
                        if new_sql:
                            sql, params = new_sql, new_params
                    
                    # Skip if no SQL to execute (e.g., update with no changes)
                    if sql is None:
                        continue
                    
                    # Execute SQL via engine
                    from transactions import InsertTransaction
                    if isinstance(transaction, InsertTransaction):
                        result = self.engine.execute(sql, params, return_lastrowid=True)
                        # Apply side effects before next operation (for FK propagation)
                        if apply_side_effects:
                            apply_side_effects(result, previous_id)
                        previous_id = result
                    else:
                        self.engine.execute(sql, params)
                        result = None
                        # Apply side effects after execution
                        if apply_side_effects:
                            apply_side_effects(result, previous_id)
        except Exception as e:
            self.rollback()
            raise RuntimeError(f"Błąd podczas flush: {e}")
        finally:
            self._in_flush = False

    def _flush_m2m(self, instance):
        mapper = instance._mapper
        for name, rel in mapper.relationships.items():
            if rel.r_type != "many-to-many": continue

            current_objects = getattr(instance, name, [])
            current_ids = set()
            for obj in current_objects:

                if getattr(obj, '_orm_state', None) == ObjectState.TRANSIENT:
                    self.add(obj) 
                    self.flush()
                
                pk = getattr(obj, obj._mapper.pk, None)
                if pk: current_ids.add(pk)

            old_snapshot = self._snapshots.get(id(instance))
            old_ids = set()
            if old_snapshot and name in old_snapshot:
                 old_ids = set(old_snapshot[name])

            local_id = getattr(instance, mapper.pk)

            to_add = current_ids - old_ids
            to_remove = old_ids - current_ids

            assoc = rel.association_table
            for target_id in to_add:
                sql, params = self.query_builder.build_m2m_insert(
                    assoc.name, local_id, target_id,
                    assoc.local_key, assoc.remote_key
                )
                try: self.engine.execute(sql, params)
                except: pass

            for target_id in to_remove:
                sql, params = self.query_builder.build_m2m_delete(
                    assoc.name, local_id, target_id,
                    assoc.local_key, assoc.remote_key
                )
                self.engine.execute(sql, params)

    def _take_snapshot(self, instance):
        if not instance._mapper: return
        state = {col: getattr(instance, col) for col in instance._mapper.columns if hasattr(instance, col)}
        
        for name, rel in instance._mapper.relationships.items():
            if rel.r_type == "many-to-many" and name in instance.__dict__:
                ids = [o.id for o in getattr(instance, name, []) if hasattr(o, 'id')]
                state[name] = ids
                
        self._snapshots[id(instance)] = state

    def _make_persistent(self, obj):
        if not obj:
            return None
        
        pk_val = getattr(obj, obj._mapper.pk, None)
        if pk_val is None:
            return obj

        existing = self.identity_map.get(obj.__class__, pk_val)
        if existing:
            return existing

        from states import ObjectState
        object.__setattr__(obj, '_orm_state', ObjectState.PERSISTENT)
        object.__setattr__(obj, '_session', self)
        
        self.identity_map.add(obj.__class__, pk_val, obj)
        
        self._take_snapshot(obj)
        
        return obj

    def _get_dirty_objects(self):
        dirty = []
        for obj in self.identity_map._map.values():
            if getattr(obj, '_orm_state', None) != ObjectState.PERSISTENT: continue
            
            old_state = self._snapshots.get(id(obj))
            if not old_state: continue
            
            is_dirty = False
            for col in obj._mapper.columns:
                if col == obj._mapper.pk: continue
                if getattr(obj, col, None) != old_state.get(col):
                    is_dirty = True
                    break
            
            if not is_dirty:
                for name, rel in obj._mapper.relationships.items():
                    if rel.r_type == "many-to-many" and name in obj.__dict__:
                        current_ids = set(o.id for o in getattr(obj, name, []) if hasattr(o, 'id'))
                        old_ids = set(old_state.get(name, []))
                        if current_ids != old_ids:
                            is_dirty = True
                            break
            
            if is_dirty: dirty.append(obj)
        return dirty

    def commit(self):
        self.flush()
        self.engine.commit()
        for obj in self.identity_map._map.values():
            if getattr(obj, '_orm_state', None) == ObjectState.PERSISTENT:
                self._take_snapshot(obj)

    def rollback(self):
        self.engine.rollback()
        self.unit_of_work.clear()
        self.identity_map.clear()
        self._snapshots.clear()
        
    def _cascade_add(self, instance):
        mapper = instance._mapper
        for rel_name, rel in mapper.relationships.items():
            if rel_name in instance.__dict__:
                val = instance.__dict__[rel_name]
                if isinstance(val, list):
                    for child in val: self.add(child)
                elif val:
                    self.add(val)

    def _autoflush(self):
        if self.unit_of_work or self._get_dirty_objects():
            self.flush()
            
    def refresh(self, instance):
        pk = getattr(instance, instance._mapper.pk)
        fresh = self.query(type(instance)).filter(**{instance._mapper.pk: pk}).first()
        if fresh:
            for col in instance._mapper.columns:
                setattr(instance, col, getattr(fresh, col))
            object.__setattr__(instance, '_orm_state', ObjectState.PERSISTENT)
            self._take_snapshot(instance)

    def close(self):
        self.rollback()
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type: self.rollback()
        else: self.commit()
        self.close()