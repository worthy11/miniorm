class Column:
    def __init__(self, dtype, pk=False, nullable=True, default=None):
        self.dtype = dtype
        self.pk = pk
        self.nullable = nullable
        self.default = default

class Text(Column):
    def __init__(self, pk=False, nullable=True, default=None):
        super().__init__(str, pk, nullable, default)

class Number(Column):
    def __init__(self, pk=False, nullable=True, default=None):
        super().__init__(int, pk, nullable, default)