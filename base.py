from mapper import Mapper
from types import Column

class MiniBase:
    _registry = {}

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