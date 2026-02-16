from collections import deque

from miniorm.states import ObjectState
from miniorm.identity_map import IdentityMap
from miniorm.query import Query
from miniorm.transactions import InsertTransaction, UpdateTransaction, DeleteTransaction
from miniorm.mapper import Mapper
from miniorm.orm_types import Column, Relationship
from miniorm.builder import QueryBuilder
from miniorm.base import MiniBase

class Session:
    def __init__(self, engine):
        Mapper.finalize_mappers()
        
        self.engine = engine
        self.query_builder = QueryBuilder()
        self.identity_map = IdentityMap()
        self.unit_of_work = deque() 
        self._snapshots = {}
        self._processed_transactions = []
        self._in_flush = False
        self._is_loading = False
        self._transaction_active = False

    def query(self, model_class):
        self._autoflush()
        return Query(model_class, self)
    
    def get(self, model_class, pk):
        existing = self.identity_map.get(model_class, pk)
        if existing: return existing
        return self.query(model_class).filter(**{model_class._mapper.pk: pk}).first()

    def add(self, entity):
        state = getattr(entity, '_orm_state', None)
        
        if any(t.entity is entity and isinstance(t, InsertTransaction) for t in self.unit_of_work):
            return

        if state == ObjectState.DETACHED:
            object.__setattr__(entity, '_session', self)
            object.__setattr__(entity, '_orm_state', ObjectState.PERSISTENT)
            pk_val = object.__getattribute__(entity, entity._mapper.pk)
            if pk_val:
                self.identity_map.add(entity.__class__, pk_val, entity)
            return

        if state == ObjectState.TRANSIENT:
            object.__setattr__(entity, '_session', self)
            object.__setattr__(entity, '_orm_state', ObjectState.PENDING)
            self._take_snapshot(entity)
            
            for attr in entity.__dict__:
                value = getattr(entity, attr)
                if hasattr(value, '_mapper'):
                    self.add(value)
                if isinstance(value, list):
                    for item in value:
                        if hasattr(item, '_mapper'):
                            self.add(item)
            self.unit_of_work.append(InsertTransaction(self, entity))

    def update(self, entity, _seen=None):
        if _seen is None:
            _seen = set()
        if id(entity) in _seen:
            return
        state = getattr(entity, '_orm_state', None)
        if state in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
            if not any(t.entity is entity and isinstance(t, UpdateTransaction) for t in self.unit_of_work):
                _seen.add(id(entity))
                for attr in entity.__dict__:
                    value = getattr(entity, attr)
                    if hasattr(value, '_mapper'):
                        self.update(value, _seen=_seen)
                    if isinstance(value, list):
                        for item in value:
                            if hasattr(item, '_mapper'):
                                self.update(item, _seen=_seen)
                self.unit_of_work.append(UpdateTransaction(self, entity))

    def delete(self, entity):
        state = getattr(entity, '_orm_state', None)
        if state == ObjectState.PENDING:
            for t in self.unit_of_work:
                if t.entity is entity and isinstance(t, InsertTransaction):
                    self.unit_of_work.remove(t)
                    object.__setattr__(entity, '_orm_state', ObjectState.TRANSIENT)
                    return
            
        if state in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
            object.__setattr__(entity, '_orm_state', ObjectState.DELETED)
            already_queued = {t.entity for t in self.unit_of_work
                             if isinstance(t, DeleteTransaction)}
            if entity not in already_queued:
                object.__setattr__(entity, '_orm_state', ObjectState.DELETED)
                self.unit_of_work.append(DeleteTransaction(self, entity))
                already_queued.add(entity)

    def flush(self):
        if self._in_flush:
            return
            
        self._in_flush = True
        self._processed_transactions = []

        dirty_objects = self._get_dirty_objects()
        for obj in dirty_objects:
            self.update(obj)

        if not self.unit_of_work:
            self._in_flush = False
            return

        self.unit_of_work = self._sort_unit_of_work()
        entities_to_sync = set()

        try:
            if not self._transaction_active:
                self.engine.execute("BEGIN TRANSACTION")
                self._transaction_active = True

            while self.unit_of_work:
                transaction = self.unit_of_work.popleft()
                transaction_type = type(transaction)
                self._processed_transactions.append(transaction)
                
                operations = transaction.prepare()
                
                current_id = None
                first_insert_done = False
                for op in operations:
                    table_name, data = op["table_name"], op["data"]
                    if transaction_type == InsertTransaction:
                        fk_col = op.get("fk_col")
                        if fk_col:
                            if isinstance(fk_col, tuple):
                                local_key, remote_key = fk_col
                                data[local_key] = current_id
                                data[remote_key] = transaction.entity._mapper.pk
                            else:
                                data[fk_col] = current_id
                        sql, params = self.query_builder.build_insert(table_name, data)
                    elif transaction_type == UpdateTransaction:
                        sql, params = self.query_builder.build_update(table_name, data)
                    elif transaction_type == DeleteTransaction:
                        sql, params = self.query_builder.build_delete(table_name, data)

                    current_id = self.engine.execute(
                        sql, params, return_lastrowid=(transaction_type == InsertTransaction)
                    )
                    if transaction_type == InsertTransaction and current_id is not None and not first_insert_done:
                        object.__setattr__(transaction.entity, transaction.entity._mapper.pk, current_id)
                        first_insert_done = True

                    if transaction_type != DeleteTransaction:
                        self._make_persistent(transaction.entity)

                entities_to_sync.add(transaction.entity)

                
            for entity in list(entities_to_sync):
                state = getattr(entity, '_orm_state', None)
                if state == ObjectState.DELETED:
                    continue
                self._flush_m2m(entity)
                self._make_persistent(entity)

            for entity in entities_to_sync:
                if getattr(entity, '_orm_state', None) != ObjectState.DELETED:
                    self._take_snapshot(entity)

            deleted_entities = [
                obj for (_, _), obj in list(self.identity_map._map.items())
                if getattr(obj, '_orm_state', None) == ObjectState.DELETED
            ]
            for deleted in deleted_entities:
                self._remove_deleted_from_m2m_collections(deleted)
            for (model_class, pk_val), obj in list(self.identity_map._map.items()):
                if getattr(obj, '_orm_state', None) == ObjectState.DELETED:
                    self.identity_map.remove(model_class, pk_val)
                    self._snapshots.pop(id(obj), None)
                    object.__setattr__(obj, '_session', None)
                    object.__setattr__(obj, '_orm_state', ObjectState.DETACHED)

            self._processed_transactions = []

        except Exception as e:
            if self._transaction_active:
                self.engine.execute("ROLLBACK")
                self._transaction_active = False
            self.rollback()
            raise RuntimeError(f"Error during flush: {e}")
        finally:
            self._in_flush = False
    
    def commit(self):
        self.flush()
        if self._transaction_active:
            self.engine.execute("COMMIT")
            self._transaction_active = False
        for obj in list(self.identity_map._map.values()):
            state = getattr(obj, '_orm_state', None)
            if state in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
                self._take_snapshot(obj)
                object.__setattr__(obj, '_orm_state', ObjectState.EXPIRED)

    def rollback(self):
        if self._transaction_active:
            try:
                self.engine.execute("ROLLBACK")
            except:
                pass
            self._transaction_active = False
            
        to_undo = self._processed_transactions + list(self.unit_of_work)
        
        for transaction in to_undo:
            entity = transaction.entity
            mapper = entity._mapper 
            
            if isinstance(transaction, InsertTransaction):
                object.__setattr__(entity, mapper.pk, None)
                object.__setattr__(entity, '_orm_state', ObjectState.TRANSIENT)
            elif isinstance(transaction, (UpdateTransaction, DeleteTransaction)):
                object.__setattr__(entity, '_orm_state', ObjectState.PERSISTENT)

        self.unit_of_work.clear()
        self._processed_transactions = []
        self.identity_map.clear()
        self._snapshots.clear()
        print("DEBUG: Rollback completed. Objects reset to safe state.")

    def refresh(self, instance):
        print(f"DEBUG: Refreshing {instance}...")
        mapper = instance._mapper
        pk_name = mapper.pk
        pk_val = instance.__dict__.get(pk_name)
        
        if pk_val is None:
            return

        fresh = self.query(type(instance)).filter(**{pk_name: pk_val}).first()
        
        if fresh:
            for col in mapper.columns:
                val = fresh.__dict__.get(col)
                instance.__dict__[col] = val
            
            object.__setattr__(instance, '_orm_state', ObjectState.PERSISTENT)
            self._take_snapshot(instance)
                
    def close(self):
        
        all_tracked_objects = list(self.identity_map._map.values())
        
        for obj in all_tracked_objects:
            object.__setattr__(obj, '_session', None)
            object.__setattr__(obj, '_orm_state', ObjectState.DETACHED)
        
        self.rollback()
        self.identity_map.clear()
        self._snapshots.clear()
        self.unit_of_work.clear()
        
        print(f"DEBUG: Detached {len(all_tracked_objects)} objects.")

    def _flush_m2m(self, instance):
        mapper = instance._mapper
        for name, rel in mapper.relationships.items():
            if rel.r_type != "many-to-many":
                continue

            assoc = rel.association_table
            # Use __dict__ so we never trigger lazy load during flush (DB may not have assoc rows yet)
            current_val = instance.__dict__.get(name)
            current_objects = current_val if isinstance(current_val, list) else []
            for obj in current_objects:
                if getattr(obj, '_orm_state', None) == ObjectState.TRANSIENT:
                    self.add(obj)

            def safe_int(val):
                if val is None or isinstance(val, Column):
                    return None
                try:
                    return int(val)
                except Exception:
                    return str(val)

            current_ids = {
                safe_int(getattr(o, o._mapper.pk))
                for o in current_objects
                if hasattr(o, '_mapper') and safe_int(getattr(o, o._mapper.pk)) is not None
            }
            old_snapshot = self._snapshots.get(id(instance), {})
            old_ids = {safe_int(x) for x in old_snapshot.get(name, [])}

            local_id = safe_int(getattr(instance, mapper.pk))
            if local_id is None:
                continue

            to_add = current_ids - old_ids
            to_remove = old_ids - current_ids

            for target_id in to_add:
                sql, params = self.query_builder.build_m2m_insert(
                    assoc.name, local_id, target_id, assoc.local_key, assoc.remote_key
                )
                self.engine.execute(sql, params)

            for target_id in to_remove:
                sql, params = self.query_builder.build_m2m_delete(
                    assoc.name, local_id, target_id, assoc.local_key, assoc.remote_key
                )
                self.engine.execute(sql, params)

    def _remove_deleted_from_m2m_collections(self, deleted_entity):
        """Remove a deleted entity from any in-memory M2M collections so cached objects stay consistent."""
        if not getattr(deleted_entity, '_mapper', None):
            return
        deleted_cls = deleted_entity.__class__
        deleted_pk = getattr(deleted_entity, deleted_entity._mapper.pk, None)
        for (_, _), obj in list(self.identity_map._map.items()):
            if obj is deleted_entity or getattr(obj, '_orm_state', None) == ObjectState.DELETED:
                continue
            if not getattr(obj, '_mapper', None):
                continue
            for name, rel in obj._mapper.relationships.items():
                if rel.r_type != "many-to-many":
                    continue
                coll = obj.__dict__.get(name)
                if not isinstance(coll, list):
                    continue
                removed = False
                for i in range(len(coll) - 1, -1, -1):
                    x = coll[i]
                    if x is deleted_entity:
                        coll.pop(i)
                        removed = True
                    elif hasattr(x, '_mapper') and x.__class__ == deleted_cls:
                        x_pk = getattr(x, x._mapper.pk, None)
                        if x_pk is not None and x_pk == deleted_pk:
                            coll.pop(i)
                            removed = True
                if removed:
                    self._take_snapshot(obj)

    def _take_snapshot(self, instance):
        if not instance._mapper: return

        state = {}
        for col in instance._mapper.get_tracked_column_names():
            if col in instance.__dict__:
                state[col] = instance.__dict__[col]

        for name, rel in instance._mapper.relationships.items():
            if rel.r_type == "many-to-many":
                current_val = instance.__dict__.get(name)
                if isinstance(current_val, list):
                    ids = []
                    for o in current_val:
                        pk_val = getattr(o, o._mapper.pk, None)
                        if pk_val is not None and not isinstance(pk_val, Column):
                            try: ids.append(int(pk_val))
                            except: ids.append(str(pk_val))
                    state[name] = sorted(ids)
                
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

        from miniorm.states import ObjectState
        object.__setattr__(obj, '_orm_state', ObjectState.PERSISTENT)
        object.__setattr__(obj, '_session', self)
        
        self.identity_map.add(obj.__class__, pk_val, obj)
        
        # self._take_snapshot(obj)
        
        return obj


    def _sort_unit_of_work(self):
        from miniorm.transactions import InsertTransaction
        
        inserts = [t for t in self.unit_of_work if isinstance(t, InsertTransaction)]
        others = [t for t in self.unit_of_work if not isinstance(t, InsertTransaction)]
        
        sorted_inserts = []
        visited = set()

        def visit(trans):
            if trans in visited: return
            visited.add(trans)
            
            mapper = trans.entity._mapper
            for rel_name, rel in mapper.relationships.items():
                if rel.r_type == "many-to-one":
                    related_obj = getattr(trans.entity, rel_name, None)
                    if related_obj:
                        dep = next((t for t in inserts if t.entity is related_obj), None)
                        if dep: visit(dep)
            sorted_inserts.append(trans)

        for t in inserts:
            visit(t)
            
        return deque(sorted_inserts + others)

    def _get_dirty_objects(self):
        dirty = []
        for obj in list(self.identity_map._map.values()):
            if getattr(obj, '_orm_state', None) not in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
                continue
            
            old_state = self._snapshots.get(id(obj))
            if old_state is None: continue
            
            is_dirty = False
            for col in obj._mapper.get_tracked_column_names():
                if col == obj._mapper.pk: continue
                if obj.__dict__.get(col) != old_state.get(col):
                    is_dirty = True; break
            
            if not is_dirty:
                for name, rel in obj._mapper.relationships.items():
                    current_val = obj.__dict__.get(name)

                    if rel.r_type in ("many-to-one", "one-to-one"):
                        if hasattr(current_val, '_mapper'):
                            current_id = getattr(current_val, current_val._mapper.pk, None)
                        else:
                            current_id = current_val
                        
                        if current_id != old_state.get(name):
                            is_dirty = True
                            break
                    
                    elif rel.r_type == "many-to-many":
                        if isinstance(current_val, list):
                            c_ids = []
                            for o in current_val:
                                pk_val = getattr(o, o._mapper.pk, None)
                                if pk_val is None or isinstance(pk_val, Column):
                                    c_ids.append(f"new_{id(o)}")
                                else:
                                    try: c_ids.append(int(pk_val))
                                    except: c_ids.append(str(pk_val))
                            
                            c_ids.sort(key=lambda x: str(x))
                            o_ids = sorted(old_state.get(name, []), key=lambda x: str(x))
                            
                            if c_ids != o_ids:
                                is_dirty = True; break
            
            if is_dirty: dirty.append(obj)
        return dirty

        
    def _cascade_add(self, instance):
        mapper = instance._mapper
        for rel_name in mapper.relationships:
            val = getattr(instance, rel_name, None)
            if not val:
                continue
                
            items = val if isinstance(val, list) else [val]
            for item in items:
                if hasattr(item, '_mapper') and getattr(item, '_orm_state', None) == ObjectState.TRANSIENT:
                    self.add(item)

    def _autoflush(self):
        if self._is_loading:
            return
        if self.unit_of_work or self._get_dirty_objects():
            self.flush()
            
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type: self.rollback()
        self.close()