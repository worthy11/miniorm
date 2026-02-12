from miniorm.mapper import Mapper
from miniorm.orm_types import Column, Relationship
from miniorm.states import ObjectState

class MiniBase:
    _registry = {}

    def __repr__(self):
        pk_val = getattr(self, self._mapper.pk, "New")
        return f"<{self.__class__.__name__}(id={pk_val})>"

    def __init__(self, **kwargs):
        from miniorm.states import ObjectState
        object.__setattr__(self, '_orm_state', ObjectState.TRANSIENT)
        object.__setattr__(self, '_session', None)
        self.type = self.__class__.__name__
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        columns = {
            name: col
            for name, col in cls.__dict__.items()
            if isinstance(col, Column)
        }

        relationships = {
            name: rel
            for name, rel in cls.__dict__.items()
            if isinstance(rel, Relationship)
        }

        meta_cls = getattr(cls, "Meta", None)
        meta_attrs = {}
        if meta_cls:
            for attr in dir(meta_cls):
                if not attr.startswith('_'):
                    meta_attrs[attr] = getattr(meta_cls, attr)
        
        cls._mapper = Mapper(cls, columns, relationships, meta_attrs)
        MiniBase._registry[cls] = cls._mapper

    def __getattribute__(self, name):
        if name.startswith('_') or name in ('mapper_args', 'Meta'):
            return object.__getattribute__(self, name)

        state = object.__getattribute__(self, '_orm_state')
        mapper = object.__getattribute__(self, '_mapper')
        session = object.__getattribute__(self, '_session')

        if name == mapper.pk:
            val = object.__getattribute__(self, name)
            if isinstance(val, Column):
                return self.__dict__.get(name, None)
            return val

        if name in mapper.relationships:
            rel = mapper.relationships[name]
            current_val = self.__dict__.get(name)
            
            is_loaded = False
            if rel.r_type == "many-to-one":
                is_loaded = current_val is not None and hasattr(current_val, '_orm_state')
            else:
                is_loaded = isinstance(current_val, list)

            if not is_loaded:
                if session:
                    value = self._load_relationship(session, rel)
                    object.__setattr__(self, name, value)
                    return value
                else:
                    # No session yet - return empty list for collections, None for many-to-one
                    if rel.r_type in ("one-to-many", "many-to-many"):
                        empty_list = []
                        object.__setattr__(self, name, empty_list)
                        return empty_list
                    return None

        val = object.__getattribute__(self, name)

        # Handle Relationship/Column objects for TRANSIENT/PENDING states
        if state in (ObjectState.TRANSIENT, ObjectState.PENDING):
            if isinstance(val, Relationship):
                if val.r_type in ("one-to-many", "many-to-many"):
                    empty_list = []
                    object.__setattr__(self, name, empty_list)
                    return empty_list
                return None
            if isinstance(val, (Column, type)) and not name.startswith('_'):
                return None
            return val

        if isinstance(val, Column) and state != ObjectState.TRANSIENT:
            return None
        
        if isinstance(val, (Column, type)) and not name.startswith('_'):
            return None

        return val

    def _load_relationship(self, session, rel):
        target_cls = rel._resolved_target
        if not target_cls:
            return None

        session._internal_loading = True
        try:
            if rel.r_type == "many-to-one":
                fk_val = object.__getattribute__(self, rel._resolved_fk_name)
                from miniorm.orm_types import Column
                if isinstance(fk_val, (Column, type(rel))) or fk_val is None:
                    return None
                
                return session.get(rel._resolved_target, fk_val)
            
            pk_val = object.__getattribute__(self, self._mapper.pk)
            from miniorm.orm_types import Column
            if isinstance(pk_val, Column) or pk_val is None:
                return [] if rel.r_type in ("one-to-many", "many-to-many") else None

            if rel.r_type == "one-to-many":
                return session.query(target_cls).filter(**{rel._resolved_fk_name: pk_val}).all()

            if rel.r_type == "many-to-many":
                assoc = rel.association_table
                return session.query(target_cls).join_m2m(
                    assoc.name, assoc.local_key, assoc.remote_key, pk_val
                ).all()
        finally:
            session._internal_loading = False
        return None
    
    def __setattr__(self, name, value):
        mapper = getattr(self, '_mapper', None)
        if mapper and name == mapper.pk:
            current_id = self.__dict__.get(name)
            state = getattr(self, '_orm_state', None)
            
            if state in (ObjectState.PERSISTENT, ObjectState.EXPIRED) and current_id is not None:
                if current_id != value:
                    raise AttributeError(
                        f"Critical error: Cannot change primary key '{name}' "
                        f"for {self.__class__.__name__} after it has been persisted."
                    )

        object.__setattr__(self, name, value)

        if not name.startswith('_') and mapper and name in mapper.columns:
            if getattr(self, '_orm_state', None) == ObjectState.EXPIRED:
                object.__setattr__(self, '_orm_state', ObjectState.PERSISTENT)
