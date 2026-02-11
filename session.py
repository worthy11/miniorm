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
        self._is_loading = False

    def query(self, model_class):
        self._autoflush()
        return Query(model_class, self)
    
    def get(self, model_class, pk):
        existing = self.identity_map.get(model_class, pk)
        if existing: return existing
        return self.query(model_class).filter(**{model_class._mapper.pk: pk}).first()

    def add(self, entity):
        state = getattr(entity, '_orm_state', None)
        if state == ObjectState.DETACHED:
            object.__setattr__(entity, '_session', self)
            object.__setattr__(entity, '_orm_state', ObjectState.PERSISTENT)
            pk_val = object.__getattribute__(entity, entity._mapper.pk)
            if pk_val:
                self.identity_map.add(entity.__class__, pk_val, entity)
            return

        if state == ObjectState.TRANSIENT:
            object.__setattr__(entity, '_orm_state', ObjectState.PENDING)
            object.__setattr__(entity, '_session', self)
            
            self._cascade_add(entity)
            
            self.unit_of_work.append(InsertTransaction(self, entity))

    def update(self, entity):
        state = getattr(entity, '_orm_state', None)
        if state in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
            if not any(t.entity is entity and isinstance(t, UpdateTransaction) for t in self.unit_of_work):
                self.unit_of_work.append(UpdateTransaction(self, entity))

    def delete(self, entity):
        state = getattr(entity, '_orm_state', None)
        if state in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
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

        self.unit_of_work = self._sort_unit_of_work()

        try:
            self.engine.execute("BEGIN TRANSACTION")

            while self.unit_of_work:
                transaction = self.unit_of_work.popleft()
                operations = transaction.prepare()
                
                if not isinstance(operations, list):
                    operations = [operations]
                
                current_id = None
                for op in operations:
                    sql, params, apply_side_effects, rebuild_fn = op
                    
                    if rebuild_fn and current_id is not None:
                        sql, params = rebuild_fn(current_id)
                    
                    if sql is None:
                        continue
                    
                    from transactions import InsertTransaction
                    if isinstance(transaction, InsertTransaction):
                        result = self.engine.execute(sql, params, return_lastrowid=True)
                        if apply_side_effects:
                            apply_side_effects(result, current_id)
                        current_id = result
                    else:
                        self.engine.execute(sql, params)
                        if apply_side_effects:
                            apply_side_effects(None, None)

                from transactions import DeleteTransaction
                if not isinstance(transaction, DeleteTransaction):
                    self._flush_m2m(transaction.entity)

            self.engine.execute("COMMIT")

        except Exception as e:
            self.engine.execute("ROLLBACK")
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


    def _sort_unit_of_work(self):
        from transactions import InsertTransaction
        
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
        for obj in self.identity_map._map.values():
            if getattr(obj, '_orm_state', None) != ObjectState.PERSISTENT: continue
            
            old_state = self._snapshots.get(id(obj))
            if not old_state: continue
            
            is_dirty = False
            for col in obj._mapper.columns:
                if col == obj._mapper.pk: continue
                current_val = obj.__dict__.get(col)
                if current_val != old_state.get(col):
                    is_dirty = True
                    break
            
            if not is_dirty:
                for name, rel in obj._mapper.relationships.items():
                    if rel.r_type == "many-to-many":
                        current_collection = obj.__dict__.get(name)
                        
                        if isinstance(current_collection, list):
                            current_ids = set(o.id for o in current_collection if hasattr(o, 'id'))
                            old_ids = set(old_state.get(name, []))
                            if current_ids != old_ids:
                                is_dirty = True
                                break
            
            if is_dirty: dirty.append(obj)
        return dirty

    def commit(self):
        self.flush()
        self.engine.commit()
        for obj in list(self.identity_map._map.values()):
            if getattr(obj, '_orm_state', None) == ObjectState.PERSISTENT:
                self._take_snapshot(obj)
                object.__setattr__(obj, '_orm_state', ObjectState.EXPIRED)

    def rollback(self):
        self.engine.rollback()
        
        # 2. Sprzątanie obiektów w pamięci
        for transaction in self.unit_of_work:
            entity = transaction.entity
            
            # Jeśli to był INSERT, Edek musi stać się znów 'nowy' (bez ID)
            if isinstance(transaction, InsertTransaction):
                # Używamy object.__setattr__, żeby ominąć magię __setattr__ (jeśli ją masz)
                object.__setattr__(entity, self.mapper.pk, None)
                object.__setattr__(entity, '_orm_state', ObjectState.TRANSIENT)
                object.__setattr__(entity, '_session', self)
            
            # Jeśli to był UPDATE lub DELETE, obiekt wciąż żyje w bazie w starej wersji
            elif isinstance(transaction, (UpdateTransaction, DeleteTransaction)):
                object.__setattr__(entity, '_orm_state', ObjectState.PERSISTENT)

        # 3. Czyszczenie struktur sesji
        self.unit_of_work.clear()
        self.identity_map.clear()  # Najbezpieczniejszy ruch - po błędzie nie ufamy mapie
        self._snapshots.clear()
        
        print("DEBUG: Sprzątanie po rollbacku zakończone. Obiekty zresetowane.")
        
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
        
        print(f"DEBUG: Odpięto {len(all_tracked_objects)} obiektów.")
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type: self.rollback()
        else: self.commit()
        self.close()