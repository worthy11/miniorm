from orm_types import Relationship, ForeignKey, Text
from inheritance import STRATEGIES, Inheritance

class Mapper:
    def __init__(self, cls, columns, meta_attrs):
        self.cls = cls
        self.meta = meta_attrs or {}
        
        self.discriminator = self.meta.get("discriminator", "type")
        self.discriminator_value = self.meta.get("discriminator_value", cls.__name__)
        
        self.table_name = (
            self.meta.get("table_name") or
            getattr(cls, "__tablename__", None) or
            cls.__name__.lower() + "s"
        )
        
        self.pk = None
        self.parent = None
        self.inheritance = None
        
        self.declared_columns = dict(columns)
        self.columns = {} 
        self.local_columns = {}
        
        self.relationships = {}
        self.children = []
        self.discriminator_map = {}

        self.resolve_parent()
        self.resolve_inheritance()
        self.resolve_columns()
        self.resolve_pk()
        self.resolve_relationships()

        if self.parent:
            self.parent.children.append(self)
            self._register_in_discriminator_map()

    def resolve_parent(self):
        for base in self.cls.__bases__:
            if hasattr(base, "_mapper"):
                self.parent = base._mapper
                return

    def resolve_inheritance(self):
        if not self.parent:
            return

        requested = self.meta.get("inheritance")
        if requested:
            requested = requested.upper()
        else:
            requested = (self.parent.inheritance.strategy.name if self.parent.inheritance else "SINGLE")

        if requested not in STRATEGIES:
            raise ValueError(f"Nieznana strategia dziedziczenia: {requested}")

        strategy = STRATEGIES[requested]
        self.inheritance = Inheritance(strategy, self.discriminator_value)

    def resolve_columns(self):
        self.columns = dict(self.declared_columns)

        if not self.parent:
            if self.discriminator not in self.columns:
                self.columns[self.discriminator] = Text(nullable=False, default=self.discriminator_value)
            self.local_columns = dict(self.columns)
        else:
            if self.inheritance:
                self.inheritance.strategy.resolve_columns(self)
                
                if self.inheritance.strategy.name == "SINGLE":
                    self.local_columns = {} 
                    
                    root = self
                    while root.parent:
                        root = root.parent
                    
                    for col_name, col_obj in self.declared_columns.items():
                        if col_name not in root.columns:

                            col_obj.nullable = True
                            root.columns[col_name] = col_obj
                else:
                    self.local_columns = dict(self.declared_columns)
            else:
                self.columns = dict(self.parent.columns) | self.columns
                self.local_columns = dict(self.declared_columns)

    def resolve_pk(self):
        pk_cols = [name for name, col in self.columns.items() if col.pk]
        if pk_cols:
            self.pk = pk_cols[0]
        elif self.parent:
            self.pk = self.parent.pk
        else:
            raise Exception(f"Klasa {self.cls.__name__} nie ma zdefiniowanego klucza głównego.")

    def resolve_relationships(self):
        for name, val in self.cls.__dict__.items():
            if isinstance(val, Relationship):
                self.relationships[name] = val
                self._resolve_single_relationship(name, val)

    def _resolve_single_relationship(self, name, rel):
        target_cls = self._resolve_target_class(rel.target)
        if not target_cls or not hasattr(target_cls, "_mapper"):
            return
        
        target_mapper = target_cls._mapper
        rel._resolved_target = target_cls
        
        target_table = target_mapper.inheritance.strategy.resolve_table_name(target_mapper) if target_mapper.inheritance else target_mapper.table_name
        target_pk = target_mapper.pk

        if rel.r_type in ("many-to-one", "one-to-one"):
            fk_name = rel.fk_name or (name if name.endswith("_id") else f"{target_table.rstrip('s')}_id")
            if fk_name not in self.columns:
                fk_col = ForeignKey(target_table, target_pk, nullable=(rel.r_type == "many-to-one"))
                self.columns[fk_name] = fk_col
                self.local_columns[fk_name] = fk_col
            rel._resolved_fk_name = fk_name
            if rel.backref:
                self._setup_backref(target_mapper, rel.backref, self.cls, rel.r_type)
                target_mapper.relationships[rel.backref]._resolved_fk_name = fk_name

        elif rel.r_type == "one-to-many":
            source_table = self.inheritance.strategy.resolve_table_name(self) if self.inheritance else self.table_name
            target_fk_name = rel.fk_name or f"{source_table.rstrip('s')}_id"
            rel._resolved_fk_name = target_fk_name
            backref = rel.backref or f"{self.cls.__name__.lower()}s"
            self._setup_backref(target_mapper, backref, self.cls, "many-to-one")

        elif rel.r_type == "many-to-many":
            source_table = self.table_name
            target_table_real = target_table
            rel.association_table = f"{source_table}_{target_table_real}"
            rel.local_table = source_table
            rel.remote_table = target_table_real
            rel._resolved_local_key = f"{source_table.rstrip('s')}_id"
            rel._resolved_remote_key = f"{target_table_real.rstrip('s')}_id"

    def _register_in_discriminator_map(self):
        root = self
        while root.parent:
            root = root.parent
        root.discriminator_map[self.discriminator_value] = self.cls

    def _resolve_target_class(self, target):
        from base import MiniBase
        if isinstance(target, type): return target
        if isinstance(target, str):
            for cls in MiniBase._registry:
                if cls.__name__ == target: return cls
        return None

    def _setup_backref(self, target_mapper, backref_name, source_cls, r_type):
        if backref_name in target_mapper.relationships: return
        rev_type = "one-to-many" if r_type == "many-to-one" else "many-to-one"
        from orm_types import Relationship
        reverse_rel = Relationship(source_cls, r_type=rev_type)
        reverse_rel._resolved_target = source_cls
        target_mapper.relationships[backref_name] = reverse_rel

    def _resolve_deferred_relationships(self):
        for name, rel in list(self.relationships.items()):
            if not hasattr(rel, '_resolved_target') or rel._resolved_target is None:
                self._resolve_single_relationship(name, rel)

    def hydrate(self, row_dict, base_class=None):
        target_cls = base_class or self.cls
        
        root = self
        while root.parent: root = root.parent
        
        type_val = row_dict.get(self.discriminator)
        if type_val in root.discriminator_map:
            target_cls = root.discriminator_map[type_val]

        obj = target_cls()
        for name, value in row_dict.items():
            
            prefix = f"{target_cls._mapper.table_name}_"
            if name.startswith(prefix):
                attr_name = name[len(prefix):]
            else:
                attr_name = name
                
            if attr_name in target_cls._mapper.columns:
                object.__setattr__(obj, attr_name, value)
        return obj