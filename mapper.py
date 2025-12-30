class Mapper:
    def __init__(self, cls, columns, mapper_args):
        self.cls = cls
        self.table_name = getattr(cls, "__tablename__", cls.__name__.lower() + "s")
        self.pk = None
        self.parent = None
        self.inheritance = None
        self.columns = columns
        self.relationships = {}
        self.args = mapper_args

        self.resolve_parent()
        self.resolve_inheritance()
        self.resolve_columns()
        self.resolve_pk()

    def __repr__(self):
        cols = ", ".join(self.columns.keys())
        pk = self.pk if self.pk else "None"
        inherit = self.inheritance
        parent = self.parent._mapper.cls.__name__ if self.parent else "None"
        return (
            f"<Mapper class={self.cls.__name__} table={self.table_name} "
            f"columns=[{cols}] pk={pk} inheritance={inherit} parent={parent}>"
        )
        
    def resolve_parent(self):
        for base in self.cls.__bases__:
            is hasattr(base, "_mapper"):
                self.parent = base._mapper
                return

    # STRATEGY: inheritance resolution
    def resolve_inheritance(self):
        return "SINGLE"
        # return "CLASS"
        # return "CONCRETE"

    def resolve_columns(self):
        pass

    def resolve_pk(self):
        pk_cols = [name for name, col in self.columns.items() if col.pk]

        if not pk_cols and self.parent:
            return self.parent._mapper.pk

        if len(pk_cols) == 1:
            self.pk = pk_cols[0]
        elif len(pk_cols) > 1:
            self.pk = pk_cols
        else:
            raise Exception(f"No primary key defined for class {self.cls.__name__}")
