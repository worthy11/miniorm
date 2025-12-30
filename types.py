class Relationship:
    def __init__(self, target, backref=None, r_type="many-to-one", fk_name=None):
        self.target = target
        self.backref = backref
        self.r_type = r_type
        self.fk_name = fk_name
        self._resolved_target = None
        self._resolved_fk_name = None

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

class ForeignKey(Column):
    def __init__(self, target_table, target_column, nullable=True, default=None):
        super().__init__(int, pk=False, nullable=nullable, default=default)
        self.target_table = target_table
        self.target_column = target_column
        self.is_foreign_key = True