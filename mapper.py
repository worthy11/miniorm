class Mapper:
    def __init__(self, cls, columns, mapper_args):
        self.cls = cls
        self.table_name = getattr(cls, "__tablename__", cls.__name__.lower() + "s")
        self.pk = None
        self.parent = None
        self.inheritance = None
        self.declared_columns = columns
        self.columns = {}
        self.local_columns = {}
        self.relationships = {}
        self.args = mapper_args or {}

        self.resolve_parent()
        self.resolve_inheritance()
        self.resolve_columns()
        self.resolve_pk()

    def __repr__(self):
        cols = ", ".join(self.columns.keys())
        pk = self.pk if self.pk else "None"
        inherit = self.inheritance
        parent = self.parent.cls.__name__ if self.parent else "None"
        return (
            f"<Mapper class={self.cls.__name__} table={self.table_name} "
            f"columns=[{cols}] pk={pk} inheritance={inherit} parent={parent}>"
        )
        
    def resolve_parent(self):
        for base in self.cls.__bases__:
            if hasattr(base, "_mapper"):
                self.parent = base._mapper
                return

    def resolve_inheritance(self):
        if not self.parent:
            self.inheritance = None
            return None

        requested = (self.args or {}).get("inheritance")
        if requested:
            requested = requested.upper()
        else:
            requested = self.parent.inheritance or "SINGLE"

        if requested not in {"SINGLE", "CLASS", "CONCRETE"}:
            raise ValueError("Unknown inheritance strategy: %s" % requested)

        if self.parent.inheritance and self.parent.inheritance != requested:
            raise ValueError(
                f"Inheritance mismatch between {self.cls.__name__} and parent {self.parent.cls.__name__}"
            )

        self.inheritance = requested
        return requested

    def resolve_columns(self):
        if not self.parent:
            self.columns = dict(self.declared_columns)
            self.local_columns = dict(self.declared_columns)
            return

        parent_cols = dict(self.parent.columns)

        if self.inheritance == "SINGLE":
            self.table_name = self.parent.table_name
            self.local_columns = dict(self.declared_columns)
            merged = parent_cols | self.declared_columns
            self.columns = merged
        elif self.inheritance == "CLASS":
            self.local_columns = dict(self.declared_columns)
            merged = parent_cols | self.declared_columns
            self.columns = merged
        elif self.inheritance == "CONCRETE":
            self.local_columns = parent_cols | self.declared_columns
            self.columns = dict(self.local_columns)
        else:
            self.local_columns = dict(self.declared_columns)
            self.columns = parent_cols | self.declared_columns

    def resolve_pk(self):
        pk_cols = [name for name, col in self.columns.items() if col.pk]

        if not pk_cols and self.parent:
            return self.parent.pk

        if len(pk_cols) == 1:
            self.pk = pk_cols[0]
        elif len(pk_cols) > 1:
            self.pk = pk_cols
        else:
            raise Exception(f"No primary key defined for class {self.cls.__name__}")
