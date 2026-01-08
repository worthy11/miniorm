from mapper import Mapper
from orm_types import Column
from states import ObjectState

class MiniBase:
    _registry = {}

    def __repr__(self):
        pk_val = getattr(self, self._mapper.pk, "New")
        return f"<{self.__class__.__name__}(id={pk_val})>"

    def __init__(self, **kwargs):
        self.type = self.__class__.__name__
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        columns = {
            name: dtype
            for name, dtype in cls.__dict__.items()
            if isinstance(dtype, Column)
        }

        mapper_args = getattr(cls, "mapper_args", None)
        cls._mapper = Mapper(cls, columns, mapper_args)
        MiniBase._registry[cls] = cls._mapper

    def __getattribute__(self, name):
        if name.startswith('_') or name == 'id':
            return object.__getattribute__(self, name)

        mapper = object.__getattribute__(self, '_mapper')
        
        if name in mapper.relationships:
            if name in self.__dict__:
                return self.__dict__[name]

            session = object.__getattribute__(self, '_session')
            if session:
                rel = mapper.relationships[name]
                value = self._load_relationship(session, rel)
                object.__setattr__(self, name, value)
                return value

        return object.__getattribute__(self, name)

    def _load_relationship(self, session, rel):
        from states import ObjectState
        
        if rel.r_type == "many-to-one":
            fk_val = getattr(self, rel._resolved_fk_name, None)
            return session.get(rel.remote_model, fk_val) if fk_val else None

        if rel.r_type == "one-to-many":
            return session.query(rel.remote_model).filter(**{rel._resolved_fk_name: self.id}).all()

        if rel.r_type == "many-to-many":
            return session.query(rel.remote_model).join_m2m(
                rel.association_table, 
                rel._resolved_local_key, 
                rel._resolved_remote_key, 
                self.id
            ).all()
        return None
    
    def __setattr__(self, name, value):
        is_column = name in self._mapper.columns
        
        object.__setattr__(self, name, value)

        state = getattr(self, '_orm_state', None)
        if is_column and state in (ObjectState.PERSISTENT, ObjectState.EXPIRED):
            session = getattr(self, '_session', None)
            if session:
                object.__setattr__(self, '_orm_state', ObjectState.PERSISTENT)
                session.mark_dirty(self)

        #TO DO: relacje many to many, one to one