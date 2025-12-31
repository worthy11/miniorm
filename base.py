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
        if name.startswith('_') or name == 'mapper_args':
            return object.__getattribute__(self, name)

        try:
            state = object.__getattribute__(self, '_orm_state')
        except AttributeError:
            state = None

        if state == ObjectState.EXPIRED:
            session = object.__getattribute__(self, '_session')
            if session:
                object.__setattr__(self, '_orm_state', ObjectState.DETACHED)
                session.refresh(self)

        return object.__getattribute__(self, name)
    
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