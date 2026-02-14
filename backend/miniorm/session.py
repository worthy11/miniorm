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
            
            self.unit_of_work.append(InsertTransaction(self, entity))
            
            self._cascade_add(entity)

    def update(self, entity):
        state = getattr(entity, '_orm_state', None)
        if state in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
            if not any(t.entity is entity and isinstance(t, UpdateTransaction) for t in self.unit_of_work):
                self.unit_of_work.append(UpdateTransaction(self, entity))

    def delete(self, entity):
        state = getattr(entity, '_orm_state', None)
        if state == ObjectState.PENDING:
            found_insert = None
            for t in self.unit_of_work:
                if t.entity is entity and isinstance(t, InsertTransaction):
                    found_insert = t
                    break
            
            if found_insert:
                self.unit_of_work.remove(found_insert)
                object.__setattr__(entity, '_orm_state', ObjectState.TRANSIENT)
                print(f"DEBUG: Cancelled adding object {entity}. Removed from queue.")
            return
            
        if state in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
            object.__setattr__(entity, '_orm_state', ObjectState.DELETED)
            dependents = self._collect_cascade_dependents(entity)
            already_queued = {t.entity for t in self.unit_of_work
                             if isinstance(t, DeleteTransaction)}
            for e in dependents:
                if e not in already_queued:
                    object.__setattr__(e, '_orm_state', ObjectState.DELETED)
                    self.unit_of_work.append(DeleteTransaction(self, e))
                    already_queued.add(e)

    def flush(self):
        if self._in_flush:
            return
            
        self._in_flush = True
        self._processed_transactions = []

        dirty_objects = self._get_dirty_objects()
        for obj in dirty_objects:
            is_queued = any(t.entity is obj and isinstance(t, UpdateTransaction) for t in self.unit_of_work)
            if not is_queued:
                self.unit_of_work.append(UpdateTransaction(self, obj))

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
                for op in operations:
                    print(f"DEBUG: Processing operation: {op}")
                    table_name, data = op["table_name"], op["data"]

                    if transaction_type == InsertTransaction:
                        # jeżeli to jest insert z CLASS inheritance, to potrzebujemy pk rodzica
                        fk_col = op.get("fk_col")
                        if fk_col:
                            data[fk_col] = current_id
                        sql, params = self.query_builder.build_insert(table_name, data)
                    elif transaction_type == UpdateTransaction:
                        sql, params = self.query_builder.build_update(table_name, data)
                    elif transaction_type == DeleteTransaction:
                        sql, params = self.query_builder.build_delete(table_name, data)

                    current_id = self.engine.execute(
                        sql, params, return_lastrowid=(transaction_type == InsertTransaction)
                    )

                entities_to_sync.add(transaction.entity)

                
            for entity in list(entities_to_sync):
                state = getattr(entity, '_orm_state', None)
                if state == ObjectState.DELETED:
                    continue
                self._flush_m2m(entity)
                self.refresh(entity)

            self._processed_transactions = []

        except Exception as e:
            if self._transaction_active:
                self.engine.execute("ROLLBACK")
                self._transaction_active = False
            self.rollback()
            raise RuntimeError(f"Error during flush: {e}")
        finally:
            self._in_flush = False
    

    def _flush_m2m(self, instance):
        mapper = instance._mapper
        for name, rel in mapper.relationships.items():
            if rel.r_type != "many-to-many": continue
            
            assoc = rel.association_table
            current_objects = getattr(instance, name, [])
            
            for obj in current_objects:
                if getattr(obj, '_orm_state', None) == ObjectState.TRANSIENT:
                    self.add(obj)

            def safe_int(val):
                if val is None or isinstance(val, Column): return None
                try: return int(val)
                except: return str(val)

            current_ids = {safe_int(getattr(o, o._mapper.pk)) for o in current_objects 
                           if hasattr(o, '_mapper') and safe_int(getattr(o, o._mapper.pk)) is not None}
            
            old_snapshot = self._snapshots.get(id(instance), {})
            old_ids = {safe_int(x) for x in old_snapshot.get(name, [])}

            local_id = safe_int(getattr(instance, mapper.pk))
            if local_id is None: continue

            to_add = current_ids - old_ids
            to_remove = old_ids - current_ids

            if to_add or to_remove:
                print(f"DEBUG M2M [{instance}]: Sync {assoc.name} | Adding: {to_add}, Removing: {to_remove}")

            for target_id in to_add:
                sql, params = self.query_builder.build_m2m_insert(
                    assoc.name, local_id, target_id, assoc.local_key, assoc.remote_key
                )
                try: self.engine.execute(sql, params)
                except: pass 

            for target_id in to_remove:
                sql, params = self.query_builder.build_m2m_delete(
                    assoc.name, local_id, target_id, assoc.local_key, assoc.remote_key
                )
                self.engine.execute(sql, params)

    def _take_snapshot(self, instance):
        if not instance._mapper: return

        state = {}
        for col in instance._mapper.columns:
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
        
        self._take_snapshot(obj)
        
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

    def _collect_cascade_dependents(self, entity, _visited=None):
        """Return list of entities to delete in order: dependents first (cascade_delete), then entity. No duplicates."""
        if _visited is None:
            _visited = set()
        if id(entity) in _visited:
            return []
        _visited.add(id(entity))
        out = []
        mapper = entity._mapper
        
        entity_pk = getattr(entity, mapper.pk, None)
        if entity_pk is None:
            return [entity]

        target_tables = {mapper.table_name}
        if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS" and mapper.parent:
            target_tables.add(mapper.parent.table_name)
        
        for other_mapper in MiniBase._registry.values():
            if other_mapper.cls is entity.__class__:
                continue
            for rel in other_mapper.relationships.values():
                if not getattr(rel, 'cascade_delete', True):
                    continue
                if rel.r_type not in ('many-to-one', 'one-to-one'):
                    continue
                if not getattr(rel, '_resolved_target', None):
                    continue
                
                fk_target_table = getattr(rel, 'remote_table', None)
                if not fk_target_table:
                    fk_target_table = rel._resolved_target._mapper.table_name
                
                if fk_target_table not in target_tables:
                    continue
                
                fk_name = getattr(rel, '_resolved_fk_name', None)
                if not fk_name:
                    continue
                self._is_loading = True
                try:
                    refs = self.query(other_mapper.cls).filter(**{fk_name: entity_pk}).all()
                finally:
                    self._is_loading = False
                for ref in refs:
                    out.extend(self._collect_cascade_dependents(ref, _visited))
        out.append(entity)
        return out

    def _get_dirty_objects(self):
        dirty = []
        for obj in list(self.identity_map._map.values()):
            if getattr(obj, '_orm_state', None) not in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
                continue
            
            old_state = self._snapshots.get(id(obj))
            if old_state is None: continue
            
            is_dirty = False
            for col in obj._mapper.columns:
                if col == obj._mapper.pk: continue
                if obj.__dict__.get(col) != old_state.get(col):
                    is_dirty = True
                    break
            
            if not is_dirty:
                for name, rel in obj._mapper.relationships.items():
                    if rel.r_type == "many-to-many":
                        current_collection = obj.__dict__.get(name)
                        if isinstance(current_collection, list):
                            c_ids = []
                            for o in current_collection:
                                pk_val = getattr(o, o._mapper.pk, None)
                                if pk_val is None or isinstance(pk_val, Column):
                                    c_ids.append(f"new_{id(o)}")
                                else:
                                    try: c_ids.append(int(pk_val))
                                    except: c_ids.append(str(pk_val))
                            
                            c_ids.sort(key=lambda x: str(x))
                            o_ids = sorted(old_state.get(name, []), key=lambda x: str(x))
                            
                            if c_ids != o_ids:
                                is_dirty = True
                                break
            
            if is_dirty: dirty.append(obj)
        return dirty

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
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type: self.rollback()
        self.close()