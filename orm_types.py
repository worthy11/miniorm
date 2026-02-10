class AssociationTable:
    def __init__(self, name, local_key, remote_key, local_table=None, remote_table=None):
        self.name = name
        self.local_key = local_key
        self.remote_key = remote_key
        self.local_table = local_table
        self.remote_table = remote_table

    def __repr__(self):
        return f"<AssociationTable {self.name}({self.local_key}, {self.remote_key})>"


class Relationship:
    def __init__(self, target, r_type="many-to-one", pk=False, backref=None):
        self.target_table = target
        self.r_type = r_type
        self.pk = pk
        self.backref = backref
        self.local_table = None   # table that declares this relationship (resolved by mapper)
        self.remote_table = None  # target table (resolved by mapper)
        self._resolved_target = None
        self._resolved_fk_name = None
        self.association_table = None  # AssociationTable for many-to-many (set by mapper)

    def __repr__(self):
        target = getattr(self._resolved_target, "__name__", self.target_table)
        parts = [f"{self.r_type}", f"target={target}"]
        if self.local_table:
            parts.append(f"local_table={self.local_table}")
        if self.remote_table:
            parts.append(f"remote_table={self.remote_table}")
        if self.association_table:
            parts.append(f"association_table={self.association_table.name}")
        return f"<Relationship {', '.join(parts)}>"

class Column:
    def __init__(self, dtype, pk=False, nullable=True, unique=False, default=None):
        self.dtype = dtype
        self.pk = pk
        self.nullable = nullable
        self.unique = unique
        self.default = default

class Text(Column):
    def __init__(self, pk=False, nullable=True, unique=False, default=None):
        super().__init__(str, pk, nullable, unique, default)

class Number(Column):
    def __init__(self, pk=False, nullable=True, unique=False, default=None):
        super().__init__(int, pk, nullable, unique, default)

class ForeignKey(Column):
    def __init__(self, target_table, target_column, pk=False, nullable=True, unique=True):
        super().__init__(int, pk=pk, nullable=nullable, unique=unique)
        self.target_table = target_table
        self.target_column = target_column