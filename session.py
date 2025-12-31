from states import ObjectState
from identity_map import IdentityMap
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
    
    def mark_dirty(self, instance):
        if hasattr(instance, '_orm_state') and instance._orm_state == ObjectState.PERSISTENT:
            self._dirty.add(instance)

    def add(self, instance):
        state = getattr(instance, '_orm_state', ObjectState.TRANSIENT)
    
        if state == ObjectState.DELETED:
            if instance in self._deleted:
                self._deleted.remove(instance)
            object.__setattr__(instance, '_orm_state', ObjectState.PERSISTENT)
            self.mark_dirty(instance)
            return

        if state == ObjectState.TRANSIENT:
            instance._orm_state = ObjectState.PENDING
            instance._session = self
            self._new.add(instance)
        mapper = MiniBase._registry.get(instance.__class__)
        for rel_name, rel in mapper.relationships.items():
            if rel.r_type == "one-to-many":
                children = getattr(instance, rel_name, [])
                for child in children:
                    self.add(child)

    def delete(self, instance):
        if hasattr(instance, '_orm_state') and instance._orm_state == ObjectState.PERSISTENT:
            instance._orm_state = ObjectState.DELETED
            self._deleted.add(instance)

    def flush(self): # TO DO: tutaj powinno się brać po grafie zależności 
        try:
            new_objects = list(self._new)
            new_objects.sort(key=lambda obj: len([
                col for col in MiniBase._registry[obj.__class__].columns.values() 
                if hasattr(col, 'is_foreign_key') and col.is_foreign_key
            ]))

            for obj in new_objects:
                self._perform_insert(obj)

            for obj in list(self._dirty):
                self._perform_update(obj)

            deleted_objects = list(self._deleted)
            deleted_objects.sort(key=lambda obj: len([
                col for col in MiniBase._registry[obj.__class__].columns.values() 
                if hasattr(col, 'is_foreign_key') and col.is_foreign_key
            ]), reverse=True)

            for obj in deleted_objects:
                self._perform_delete(obj)
                
        except Exception as e:
            self.rollback()
            raise RuntimeError(f"Błąd podczas operacji flush: {str(e)}")
        
    def _perform_insert(self, obj):
        mapper = MiniBase._registry.get(obj.__class__)
        sql, params = self.query_builder.build_insert(mapper, obj)
        new_id = self.engine.execute_insert(sql, params)
        object.__setattr__(obj, mapper.pk, new_id)
        object.__setattr__(obj, '_orm_state', ObjectState.PERSISTENT)
        self.identity_map.add(obj.__class__, new_id, obj)
        self._new.remove(obj)

    def _perform_update(self, obj):
        mapper = MiniBase._registry.get(obj.__class__)
        sql, params = self.query_builder.build_update(mapper, obj)
        self.engine.execute(sql, params)
        self._dirty.remove(obj)

    def _perform_delete(self, obj):
        mapper = MiniBase._registry.get(obj.__class__)
        pk_val = getattr(obj, mapper.pk)
        sql, params = self.query_builder.build_delete(mapper, pk_val)
        self.engine.execute(sql, params)
        self.identity_map.remove(obj.__class__, pk_val)
        self._deleted.remove(obj)
    
    
    def _autoflush(self):
        if self._new or self._dirty or self._deleted:
            self.engine.logger.info("[AUTOFLUSH] Synchronizacja...")
            self.flush()
        
    def _flush_m2m(self, instance, mapper): #to do
        for name, rel in mapper.relationships.items():
            if rel.r_type == "many-to-many":
                collection = getattr(instance, name, [])
                for target_obj in collection:
                    if getattr(target_obj, '_orm_state', None) == ObjectState.PENDING:
                        self.add(target_obj)
                        self.flush()

                    target_mapper = MiniBase._registry.get(target_obj.__class__)
                    
                    sql, params = self.query_builder.build_m2m_insert(
                        rel.association_table,
                        getattr(instance, mapper.pk),
                        getattr(target_obj, target_mapper.pk),
                        rel._resolved_local_key,
                        rel._resolved_remote_key
                    )
                    self.engine.execute(sql, params)

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
        self.engine.rollback()
        self.engine.logger.warning("[TRANSACTION]: Rollback wykonany")

        for obj in list(self._deleted):
            mapper = MiniBase._registry.get(obj.__class__)
            pk_val = getattr(obj, mapper.pk)
            self.identity_map.add(obj.__class__, pk_val, obj)
            object.__setattr__(obj, '_orm_state', ObjectState.EXPIRED)
        
        for obj in self.identity_map._map.values():
            object.__setattr__(obj, '_orm_state', ObjectState.EXPIRED)
            
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()
        self.engine.logger.warning("[TRANSACTION]: Rollback wykonany i przywrócono obiekty.")


    def close(self):
        for obj in self.identity_map._map.values():
            object.__setattr__(obj, '_orm_state', ObjectState.DETACHED)
            object.__setattr__(obj, '_session', None)
        self.identity_map.clear()
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()
        self.engine.logger.info("[SESSION]: Zamknięto i wyczyszczono mapę tożsamości.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()