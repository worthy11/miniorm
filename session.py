from states import ObjectState
from identity_map import IdentityMap
from dependency_graph import DependencyGraph
from base import MiniBase 
from query import Query

class Session:
    def __init__(self, engine, query_builder):
        self.engine = engine
        self.query_builder = query_builder
        self.identity_map = IdentityMap()
        self._new = set()
        self._deleted = set()
        self._dirty = set()
        self._snapshots = {}

    def query(self, model_class):
        return Query(model_class, self)
    
    def get(self, model_class, pk):
        existing = self.identity_map.get(model_class, pk)
        if existing:
            if getattr(existing, '_orm_state', None) == ObjectState.DELETED:
                return None
            return existing
        mapper = MiniBase._registry.get(model_class)
        return self.query(model_class).filter(**{mapper.pk: pk}).first()
    
    def _take_snapshot(self, instance):
        mapper = instance._mapper
        state = {name: getattr(instance, name) for name in mapper.columns if hasattr(instance, name)}
        self._snapshots[id(instance)] = state


    def _get_dirty_objects(self):
        dirty = []
        for obj in self.identity_map._map.values():
            if getattr(obj, '_orm_state', None) != ObjectState.PERSISTENT:
                continue
            
            old_state = self._snapshots.get(id(obj))
            if old_state is None: continue
            
            for key, old_val in old_state.items():
                if getattr(obj, key) != old_val:
                    dirty.append(obj)
                    break
        return dirty
    

    def add(self, instance):
        if getattr(instance, '_orm_state', None) == ObjectState.PENDING:
            return

        mapper = getattr(instance, '_mapper', None)
        if mapper is None:
            return

        state = getattr(instance, '_orm_state', ObjectState.TRANSIENT)
    
        if state == ObjectState.DELETED:
            if instance in self._deleted:
                self._deleted.remove(instance)
            object.__setattr__(instance, '_orm_state', ObjectState.PERSISTENT)
            return

        if state == ObjectState.TRANSIENT:
            object.__setattr__(instance, '_orm_state', ObjectState.PENDING)
            object.__setattr__(instance, '_session', self)
            self._new.add(instance)

        for rel_name, rel in mapper.relationships.items():
            val = instance.__dict__.get(rel_name)
            
            if val is None:
                continue

            if rel.r_type in ("many-to-one", "one-to-one"):
                self.add(val)
            elif rel.r_type in ("one-to-many", "many-to-many") and isinstance(val, list):
                for item in val:
                    self.add(item)

    def delete(self, instance):
        if hasattr(instance, '_orm_state') and instance._orm_state == ObjectState.PERSISTENT:
            instance._orm_state = ObjectState.DELETED
            self._deleted.add(instance)

    def flush(self):
        if not (self._new or self._dirty or self._deleted):
            return

        actual_dirty = self._get_dirty_objects()
        self._dirty.update(actual_dirty)
        
        to_insert = list(self._new)
        to_update = list(self._dirty)
        objects_to_snapshot = set(to_insert + to_update)
        
        try:
            if objects_to_snapshot:
                save_graph = DependencyGraph(objects_to_snapshot)
                save_plan = save_graph.sort()

                for obj in save_plan:
                    # Skip parent objects created by DependencyGraph - they're not in _new
                    # They'll be handled when we process their children
                    if obj not in self._new and obj not in self._dirty:
                        # This is a parent object created for CLASS inheritance
                        # Check if it needs to be inserted
                        if getattr(obj, '_orm_state', None) == ObjectState.PENDING:
                            self._new.add(obj)
                            object.__setattr__(obj, '_session', self)
                    
                    self._sync_foreign_keys(obj)
                    if obj in self._new:
                        self._perform_insert(obj)
                    elif obj in self._dirty:
                        self._perform_update(obj)

            for obj in objects_to_snapshot:
                self._flush_m2m(obj, obj._mapper)

            if self._deleted:
                delete_graph = DependencyGraph(self._deleted)
                delete_plan = reversed(delete_graph.sort())
                for obj in delete_plan:
                    self._perform_delete(obj)
                    self._snapshots.pop(id(obj), None)

            for obj in objects_to_snapshot:
                if getattr(obj, '_orm_state', None) == ObjectState.PERSISTENT:
                    self._take_snapshot(obj)
                
        except Exception as e:
            self.rollback()
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}"
            raise RuntimeError(f"Krytyczny błąd synchronizacji Unit of Work: {error_details}") from e
        
    def _sync_foreign_keys(self, obj):
        mapper = obj._mapper
        for rel_name, rel in mapper.relationships.items():
            if rel.r_type == "many-to-one":
                parent = getattr(obj, rel_name, None)
                from orm_types import Relationship
                if parent is None or isinstance(parent, Relationship):
                    continue

                if hasattr(parent, '_mapper'):
                    parent_mapper = parent._mapper
                    parent_pk_val = getattr(parent, parent_mapper.pk, None)
                    
                    if parent_pk_val is not None:
                        object.__setattr__(obj, rel._resolved_fk_name, parent_pk_val)
        
    def _perform_insert(self, obj):
        mapper = MiniBase._registry.get(obj.__class__)
        
        # Check if this is a parent object created for CLASS inheritance
        # We check if it has the _class_inheritance_children attribute set by DependencyGraph
        is_class_parent = hasattr(obj, '_class_inheritance_children')
        
        try:
            data = self._prepare_data(obj, mapper)
            sql, params = self.query_builder.build_insert(mapper, data)
            new_id = self.engine.execute_insert(sql, params)
            object.__setattr__(obj, mapper.pk, new_id)
            object.__setattr__(obj, '_orm_state', ObjectState.PERSISTENT)
            self.identity_map.add(obj.__class__, new_id, obj)
            # Remove from _new if it was there (might have been added by DependencyGraph)
            if obj in self._new:
                self._new.remove(obj)
            
            # If this is a CLASS inheritance parent, update children's FK fields
            if is_class_parent:
                children = getattr(obj, '_class_inheritance_children', [])
                for child_obj in children:
                    child_mapper = child_obj._mapper
                    # Find the relationship that points to the parent
                    for rel_name, rel in child_mapper.relationships.items():
                        target_cls = child_mapper._resolve_target_class(rel.target)
                        if target_cls == mapper.cls and rel.r_type in ("many-to-one", "one-to-one"):
                            if hasattr(rel, '_resolved_fk_name'):
                                object.__setattr__(child_obj, rel._resolved_fk_name, new_id)
                            break
        except Exception as e:
            # Re-raise with more context about which object failed
            raise RuntimeError(f"Błąd podczas wstawiania {obj}: {e}") from e

    def _perform_update(self, obj):
        mapper = MiniBase._registry.get(obj.__class__)
        data = self._prepare_data(obj, mapper)
        pk_val = getattr(obj, mapper.pk)
        sql, params = self.query_builder.build_update(mapper, data, pk_val)
        self.engine.execute(sql, params)
        self._dirty.remove(obj)

    def _perform_delete(self, obj):
        mapper = MiniBase._registry.get(obj.__class__)
        pk_val = getattr(obj, mapper.pk)
        sql, params = self.query_builder.build_delete(mapper, pk_val)
        self.engine.execute(sql, params)
        self.identity_map.remove(obj.__class__, pk_val)
        self._deleted.remove(obj)


    def _prepare_data(self, obj, mapper):
        data = {}
        # For SINGLE inheritance, use all columns. For CLASS/CONCRETE, use only local columns
        if mapper.inheritance and mapper.inheritance.strategy.name == "SINGLE":
            fields = mapper.columns.keys()
        else:
            fields = mapper.local_columns.keys()
        
        for f in fields:
            if f == mapper.pk:
                continue
            if f == "type":
                data[f] = obj.__class__.__name__
            else:
                data[f] = getattr(obj, f, None)
        return data
    
    
    def _autoflush(self):
        if self._new or self._dirty or self._deleted:
            self.engine.logger.info("[AUTOFLUSH] Synchronizacja...")
            self.flush()
        
    def _flush_m2m(self, instance, mapper):  #To do
        for name, rel in mapper.relationships.items():
            if rel.r_type == "many-to-many":
                collection = instance.__dict__.get(name, [])
                
                for target_obj in collection:
                    if getattr(target_obj, '_orm_state', None) == ObjectState.TRANSIENT:
                        self.add(target_obj)
                    
                    local_id = getattr(instance, mapper.pk, None)
                    target_mapper = getattr(target_obj, '_mapper', None)
                    remote_id = getattr(target_obj, target_mapper.pk, None) if target_mapper else None
                    if local_id is not None and remote_id is not None:
                        sql, params = self.query_builder.build_m2m_insert(
                            rel.association_table,
                            local_id,
                            remote_id,
                            rel._resolved_local_key,
                            rel._resolved_remote_key
                        )
                        try:
                            self.engine.execute(sql, params)
                        except Exception:
                            continue

    def commit(self):
        try:
            self.flush()
            self.engine.commit()
            for obj in self.identity_map._map.values():
                object.__setattr__(obj, '_orm_state', ObjectState.EXPIRED)
            
            self.engine.logger.info("[TRANSACTION]: Commit i wygaszenie (EXPIRE) obiektów.")
        except Exception as e:
            self.rollback()
            raise e


    def refresh(self, instance):
        mapper = MiniBase._registry.get(instance.__class__)
        pk_name = mapper.pk
        pk_val = object.__getattribute__(instance, pk_name)
        
        sql, params = self.query_builder.build_select(mapper, {pk_name: pk_val}, limit=1)
        rows = self.engine.execute(sql, params)
        
        if rows:
            row = rows[0]
            for name in mapper.columns.keys():
                object.__setattr__(instance, name, row[name])
            object.__setattr__(instance, '_orm_state', ObjectState.PERSISTENT)
        else:
            object.__setattr__(instance, '_orm_state', ObjectState.TRANSIENT)

    def rollback(self):
        """Cofa transakcję w bazie i przywraca spójność obiektów w pamięci."""
        self.engine.rollback()
        self.engine.logger.warning("[TRANSACTION]: Rollback wykonany. Przywracanie stanu obiektów...")

        for obj in list(self._new):
            mapper = obj._mapper
            object.__setattr__(obj, mapper.pk, None)
            object.__setattr__(obj, '_orm_state', ObjectState.TRANSIENT)

        for obj in list(self._deleted):
            mapper = obj._mapper
            pk_val = getattr(obj, mapper.pk)
            self.identity_map.add(obj.__class__, pk_val, obj)
            object.__setattr__(obj, '_orm_state', ObjectState.EXPIRED)

        for obj in self.identity_map._map.values():
            if getattr(obj, '_orm_state', None) != ObjectState.TRANSIENT:
                object.__setattr__(obj, '_orm_state', ObjectState.EXPIRED)

        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()
        
        self.engine.logger.warning("[TRANSACTION]: Stan sesji zresetowany.")


    def close(self):
        for obj in self.identity_map._map.values():
            object.__setattr__(obj, '_orm_state', ObjectState.DETACHED)
            object.__setattr__(obj, '_session', None)
        self.identity_map.clear()
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()
        self.engine.logger.info("[SESSION]: Zamknięto i wyczyszczono mapę tożsamości.")

    def _make_persistent(self, obj):
        """Ensure an object from a query is attached to this session and identity map.

        If an instance with the same class and primary key already exists in the
        identity map, return that existing instance. Otherwise mark the object
        as PERSISTENT, attach the session, add to the identity map and take a
        snapshot for change detection.
        """
        if obj is None:
            return None

        mapper = getattr(obj, '_mapper', None)
        if mapper is None:
            return obj

        # determine primary key name
        pk_name = mapper.pk if isinstance(mapper.pk, str) else (mapper.pk[0] if isinstance(mapper.pk, list) and mapper.pk else None)
        pk_val = getattr(obj, pk_name, None) if pk_name else None

        if pk_val is None:
            # Nothing we can do without a primary key; just attach session
            object.__setattr__(obj, '_session', self)
            return obj

        existing = self.identity_map.get(obj.__class__, pk_val)
        if existing:
            # ensure existing is attached to this session
            object.__setattr__(existing, '_session', self)
            return existing

        # register new persistent instance
        object.__setattr__(obj, '_session', self)
        object.__setattr__(obj, '_orm_state', ObjectState.PERSISTENT)
        self.identity_map.add(obj.__class__, pk_val, obj)
        # take snapshot for change detection
        self._take_snapshot(obj)
        return obj

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()