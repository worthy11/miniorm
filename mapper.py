from orm_types import Relationship, ForeignKey, Text
from inheritance import STRATEGIES, Inheritance

class Mapper:
    def __init__(self, cls, columns, meta_attrs):
        self.cls = cls
        self.meta = meta_attrs or {}
        
        self.discriminator = self.meta.get("discriminator", "type")
        self.discriminator_value = self.meta.get("discriminator_value", cls.__name__)
        
        self.pk = None
        self.parent = None
        self.inheritance = None
        
        self.declared_columns = dict(columns)
        self.columns = {}
        
        self.relationships = {}
        self.discriminator_map = None  # For SINGLE inheritance: maps discriminator values to classes
        self.children = []  # For CLASS inheritance: list of child mappers

        self._resolve_parent()
        self._resolve_inheritance()
        self._resolve_table_name()
        self._resolve_columns()
        self._resolve_pk()
        self._resolve_relationships()

    def __repr__(self):
        cols = ", ".join(self.columns.keys())
        pk = self.pk if self.pk else "None"
        inherit = self.inheritance.strategy.name if self.inheritance else "None"
        parent = self.parent.cls.__name__ if self.parent else "None"
        return (
            f"<Mapper class={self.cls.__name__} table={self.table_name} "
            f"columns=[{cols}] pk={pk} inheritance={inherit} parent={parent}>"
        )
        
    def _resolve_parent(self):
        for base in self.cls.__bases__:
            if hasattr(base, "_mapper"):
                self.parent = base._mapper
                return

    def _resolve_inheritance(self):
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
        discriminator_value = self.meta.get("discriminator_value", self.cls.__name__)
        
        from inheritance import Inheritance
        self.inheritance = Inheritance(strategy, discriminator_value)
    
    def _resolve_table_name(self):
        self.table_name = self.meta.get("table_name", self.cls.__name__+"s")
        if self.inheritance:
            self.inheritance.strategy.resolve_table_name(self)

    def _resolve_columns(self):
        if not self.inheritance:
            # No inheritance: use declared columns as-is
            self.columns = dict(self.declared_columns)
            return
        # Start with child's declared columns so strategy can merge with parent
        self.columns = dict(self.declared_columns)
        self.inheritance.strategy.resolve_columns(self)

        if self.inheritance.discriminator is None:
            root = self
            while root.parent:
                root = root.parent
            if root.discriminator in root.columns:
                self.inheritance.discriminator = root.columns[root.discriminator]
        
        # add class to discriminator_map
        if self.inheritance.strategy.name == "SINGLE":
            root = self
            while root.parent:
                root = root.parent

            # create discriminator map at root
            if root.discriminator_map is None:
                root.discriminator_map = {}
            root.discriminator_map[self.inheritance.discriminator_value] = self.cls
        
        if self.inheritance and self.inheritance.strategy.name == "CLASS":
            fk_found = False
            
            relationships_to_check = list(self.relationships.items())
            for name, val in self.cls.__dict__.items():
                if isinstance(val, Relationship) and name not in self.relationships:
                    relationships_to_check.append((name, val))
            
            # Check if there's a relationship pointing to the parent class
            for rel_name, rel in relationships_to_check:
                # Try to resolve the target class
                target_cls = self._resolve_target_class(rel.target)
                if target_cls is not None:
                    # Check if the target is the parent class
                    if target_cls == self.parent.cls:
                        # This relationship will create a FK column pointing to parent
                        # For many-to-one or one-to-one, the FK will be in this table
                        if rel.r_type in ("many-to-one", "one-to-one"):
                            fk_found = True
                            break
            
            if not fk_found:
                raise ValueError(
                    f"CLASS inheritance requires a Relationship pointing to parent class '{self.parent.cls.__name__}'. "
                    f"Class '{self.cls.__name__}' is missing this relationship. "
                    f"Add a Relationship with r_type='many-to-one' or r_type='one-to-one' pointing to '{self.parent.cls.__name__}'."
                )
            
            root = self
            while root.parent:
                root = root.parent
            if self not in root.children:
                root.children.append(self)

    @property
    def local_columns(self):
        """Return only columns that are local to this class (not inherited from parent)."""
        if not self.parent:
            return self.columns
        parent_cols_set = set(self.parent.columns.keys())
        return {name: col for name, col in self.columns.items() if name not in parent_cols_set}

    def _resolve_pk(self):
        pk_cols = [name for name, col in self.columns.items() if col.pk]
        if pk_cols:
            self.pk = pk_cols[0]
        elif self.parent:
            self.pk = self.parent.pk
        else:
            raise Exception(f"Klasa {self.cls.__name__} nie ma zdefiniowanego klucza głównego.")

    def _resolve_relationships(self):
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
        
        target_table = self._get_target_table(target_mapper)
        target_pk = self._get_target_pk(target_mapper)
        
        fk_name = rel.fk_name
        if fk_name is None:
            if name.endswith("_id"):
                fk_name = name
            else:
                # Normalize to lowercase for consistency
                fk_name = f"{target_table.rstrip('s').lower()}_id"
        
        if rel.r_type in ("many-to-one", "one-to-one"):
            fk_name = rel.fk_name or (name if name.endswith("_id") else f"{target_table.rstrip('s')}_id")
            if fk_name not in self.columns:
                fk_col = ForeignKey(target_table, target_pk, nullable=(rel.r_type == "many-to-one"))
                self.columns[fk_name] = fk_col
            rel._resolved_fk_name = fk_name
            if rel.backref:
                self._setup_backref(target_mapper, rel.backref, self.cls, rel.r_type)
                target_mapper.relationships[rel.backref]._resolved_fk_name = fk_name

        elif rel.r_type == "one-to-many":
            source_table = self._get_target_table(self)
            source_pk = self._get_target_pk(self)
            
            target_fk_name = rel.fk_name
            if target_fk_name is None:
                # Normalize to lowercase for consistency
                target_fk_name = f"{source_table.rstrip('s').lower()}_id"
            
            if target_fk_name not in target_mapper.columns:
                fk_col = ForeignKey(
                    target_table=source_table,
                    target_column=source_pk,
                    nullable=True
                )
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

    def _get_target_table(self, target_mapper):
        """Return the table name for a mapper (respects inheritance, e.g. root table for CLASS)."""
        return getattr(target_mapper, "table_name", None)

    def _get_target_pk(self, target_mapper):
        """Return the primary key column name for a mapper."""
        pk = getattr(target_mapper, "pk", None)
        if isinstance(pk, str):
            return pk
        if isinstance(pk, list) and pk:
            return pk[0]
        return "id"

    def _setup_backref(self, target_mapper, backref_name, source_cls, r_type):
        if backref_name in target_mapper.relationships: return
        rev_type = "one-to-many" if r_type == "many-to-one" else "many-to-one"
        from orm_types import Relationship
        reverse_rel = Relationship(source_cls, r_type=rev_type)
        reverse_rel._resolved_target = source_cls
        target_mapper.relationships[backref_name] = reverse_rel
    
    def get(self, id):
        return None
    
    def get_all(self):
        return []
    
    def insert(self, entity):
        return None
    
    def update(self, entity):
        return None
    
    def delete(self, entity):
        return None
    
    def hydrate(self, row_dict):
        from base import MiniBase
        from orm_types import ForeignKey
        
        target_cls = self.cls
        
        if self.inheritance:
            if self.inheritance.strategy.name == "SINGLE":
                # use discriminator value to find class
                root = self
                while root.parent:
                    root = root.parent
                disc_col_name = root.discriminator
                
                if disc_col_name and disc_col_name in row_dict and root.discriminator_map:
                    row_type_value = row_dict.get(disc_col_name)
                    if row_type_value in root.discriminator_map:
                        target_cls = root.discriminator_map[row_type_value]
            
            elif self.inheritance.strategy.name == "CLASS" and not self.parent:
                # check which subclass table has a non-null FK
                for child_mapper in self.children:
                    fk_col = None
                    # Find FK column created by relationship pointing to parent
                    for col_name, col in child_mapper.columns.items():
                        # Check for actual ForeignKey
                        if isinstance(col, ForeignKey) and col.target_table == self.table_name:
                            fk_col = col_name
                            break
                    # If not found in columns, try to find it from relationships
                    if fk_col is None:
                        for rel_name, rel in child_mapper.relationships.items():
                            target_cls = child_mapper._resolve_target_class(rel.target)
                            if target_cls == self.cls and rel.r_type in ("many-to-one", "one-to-one"):
                                # The FK name will be resolved during relationship resolution
                                if hasattr(rel, '_resolved_fk_name') and rel._resolved_fk_name:
                                    fk_col = rel._resolved_fk_name
                                    break
                    if fk_col is None:
                        fk_col = f"{self.table_name.rstrip('s').lower()}_id"
                    
                    alias_key = f"{child_mapper.table_name}_{fk_col}"
                    fk_value = row_dict.get(alias_key) or row_dict.get(fk_col)
                    if fk_value is not None:
                        target_cls = child_mapper.cls
                        break
        
        obj = target_cls()
        target_mapper = target_cls._mapper
        
        for name, value in row_dict.items():
            if name in target_mapper.columns:
                object.__setattr__(obj, name, value)
            elif target_mapper.inheritance and target_mapper.inheritance.strategy.name == "CLASS":
                parent_cols = set(target_mapper.parent.columns.keys()) if target_mapper.parent else set()
                local_cols = [col_name for col_name in target_mapper.columns.keys() if col_name not in parent_cols]
                for col_name in local_cols:
                    alias = f"{target_mapper.table_name}_{col_name}"
                    if name == alias:
                        object.__setattr__(obj, col_name, value)
                        break
        
        return obj