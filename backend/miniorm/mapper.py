from orm_types import Relationship, ForeignKey
from inheritance import STRATEGIES

class Mapper:
    def __init__(self, cls, columns, meta_attrs):
        self.cls = cls
        self.meta = meta_attrs or {}
        self.abstract = self.meta.get("abstract", False)
        self.discriminator = self.meta.get("discriminator", "type")
        self.discriminator_value = self.meta.get("discriminator_value", cls.__name__)
        
        # Table name resolution: Meta.table_name > __tablename__ > default
        self.table_name = (
            self.meta.get("table_name") or
            getattr(cls, "__tablename__", None) or
            cls.__name__.lower() + "s"
        )
        
        self.pk = None
        self.parent = None
        self.inheritance = None
        self.declared_columns = columns
        self.columns = {}
        self.local_columns = {}
        self.relationships = {}

        self.resolve_parent()
        self.resolve_inheritance()
        self.resolve_columns()
        self.resolve_pk()
        self.resolve_relationships()

    def __repr__(self):
        cols = ", ".join(self.columns.keys())
        pk = self.pk if self.pk else "None"
        inherit = self.inheritance.name if self.inheritance else "None"
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

        requested = self.meta.get("inheritance")
        if requested:
            requested = requested.upper()
        else:
            requested = (self.parent.inheritance.name if self.parent.inheritance else "SINGLE")

        if requested not in STRATEGIES:
            raise ValueError("Unknown inheritance strategy: %s" % requested)

        if self.parent.inheritance and self.parent.inheritance.name != requested:
            raise ValueError(
                f"Inheritance mismatch between {self.cls.__name__} and parent {self.parent.cls.__name__}"
            )

        self.inheritance = STRATEGIES[requested]
        return self.inheritance

    def resolve_columns(self):
        if not self.parent:
            self.columns = dict(self.declared_columns)
            self.local_columns = dict(self.declared_columns)
            from orm_types import Text
            self.columns[self.discriminator] = Text(nullable=False, default=self.discriminator_value)
            self.local_columns[self.discriminator] = Text(nullable=False, default=self.discriminator_value)
            return

        if self.inheritance:
            self.inheritance.apply_columns(self, self.parent)
        else:
            parent_cols = dict(self.parent.columns)
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

    def resolve_relationships(self):
        for name, val in self.cls.__dict__.items():
            if isinstance(val, Relationship):
                self.relationships[name] = val
                self._resolve_single_relationship(name, val)
    
    def _resolve_single_relationship(self, name, rel):
        target_cls = self._resolve_target_class(rel.target)
        if target_cls is None:
            return False
        
        target_mapper = getattr(target_cls, "_mapper", None)
        if target_mapper is None:
            return False
        
        target_table = self._get_target_table(target_mapper)
        target_pk = self._get_target_pk(target_mapper)
        
        fk_name = rel.fk_name
        if fk_name is None:
            if name.endswith("_id"):
                fk_name = name
            else:
                fk_name = f"{target_table.rstrip('s')}_id"
        
        if rel.r_type in ("many-to-one", "one-to-one"):
            if fk_name not in self.columns:
                fk_col = ForeignKey(
                    target_table=target_table,
                    target_column=target_pk,
                    nullable=rel.r_type == "many-to-one"
                )
                
                self.local_columns[fk_name] = fk_col
                self.columns[fk_name] = fk_col
            
            rel._resolved_target = target_cls
            rel._resolved_fk_name = fk_name
            
            if rel.backref:
                self._setup_backref(target_mapper, rel.backref, self.cls, rel.r_type)
            
            return True
        
        elif rel.r_type == "one-to-many":
            source_table = self._get_target_table(self)
            source_pk = self._get_target_pk(self)
            
            target_fk_name = rel.fk_name
            if target_fk_name is None:
                target_fk_name = f"{source_table.rstrip('s')}_id"
            
            if target_fk_name not in target_mapper.columns:
                fk_col = ForeignKey(
                    target_table=source_table,
                    target_column=source_pk,
                    nullable=True
                )
                target_mapper.local_columns[target_fk_name] = fk_col
                target_mapper.columns[target_fk_name] = fk_col
            
            rel._resolved_target = target_cls
            rel._resolved_fk_name = target_fk_name  # Store the FK name in target table
            
            if rel.backref:
                self._setup_backref(target_mapper, rel.backref, self.cls, "many-to-one")
            else:
                backref_name = f"{self.cls.__name__.lower()}s"
                self._setup_backref(target_mapper, backref_name, self.cls, "many-to-one")
            
            return True
        
        elif rel.r_type == "many-to-many":
            # Many-to-many: requires junction table (not implemented in this step)
            rel._resolved_target = target_cls
            # TODO: Create junction table for many-to-many
            return True
        
        self._resolve_deferred_relationships()
        return False
    
    def _resolve_deferred_relationships(self):
        for name, rel in list(self.relationships.items()):
            if not hasattr(rel, '_resolved_target') or rel._resolved_target is None:
                self._resolve_single_relationship(name, rel)
    
    def _resolve_target_class(self, target):
        from base import MiniBase
        if isinstance(target, type):
            return target
        if isinstance(target, str):
            for cls, mapper in MiniBase._registry.items():
                if cls.__name__ == target:
                    return cls
        return None
    
    def _get_target_table(self, target_mapper):
        if target_mapper.inheritance:
            return target_mapper.inheritance.target_table(target_mapper)
        return target_mapper.table_name
    
    def _get_target_pk(self, target_mapper):
        """Get the primary key column name from target mapper."""
        if isinstance(target_mapper.pk, str):
            return target_mapper.pk
        elif isinstance(target_mapper.pk, list):
            return target_mapper.pk[0]
        else:
            return "id"
    
    def _setup_backref(self, target_mapper, backref_name, source_cls, r_type):
        if backref_name in target_mapper.relationships:
            return
        
        reverse_rel = Relationship(
            target=source_cls,
            backref=None,
            r_type="one-to-many" if r_type == "many-to-one" else "many-to-one"
        )
        reverse_rel._resolved_target = source_cls
        target_mapper.relationships[backref_name] = reverse_rel