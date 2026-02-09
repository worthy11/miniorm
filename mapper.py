from orm_types import Relationship, ForeignKey, Text
from inheritance import STRATEGIES, Inheritance

class Mapper:
    def __init__(self, cls, columns, meta_attrs):
        self.cls = cls
        self.meta = meta_attrs or {}
        
        self.discriminator = self.meta.get("discriminator", "type")
        self.discriminator_value = self.meta.get("discriminator_value", cls.__name__)
        self.discriminator_map = None
        
        self.pk = None
        self.inheritance = None
        self.declared_columns = dict(columns)
        self.columns = {}
        self.abstract = self.meta.get("abstract", False)
        
        self.parent = None
        self.relationships = {}
        self.children = []

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
        self.columns = dict(self.declared_columns)
        
        if self.inheritance:
            self.columns = dict(self.declared_columns)
            self.inheritance.strategy.resolve_columns(self)

            if self.inheritance.discriminator is None:
                root = self
                while root.parent:
                    root = root.parent
                if root.discriminator in root.columns:
                    self.inheritance.discriminator = root.columns[root.discriminator]
            
            if self.inheritance.strategy.name == "SINGLE":
                root = self
                while root.parent:
                    root = root.parent

                if root.discriminator_map is None:
                    root.discriminator_map = {}
                root.discriminator_map[self.inheritance.discriminator_value] = self.cls
        
    def _resolve_pk(self):
        pk_cols = [name for name, col in self.columns.items() if col.pk]
        if pk_cols:
            self.pk = pk_cols[0]
        elif self.parent:
            self.pk = self.parent.pk
        else:
            raise Exception(f"Klasa {self.cls.__name__} nie ma zdefiniowanego klucza głównego.")
    
    def _resolve_relationships(self):
        pass

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
                root = self
                while root.parent:
                    root = root.parent
                disc_col_name = root.discriminator
                
                if disc_col_name and disc_col_name in row_dict and root.discriminator_map:
                    row_type_value = row_dict.get(disc_col_name)
                    if row_type_value in root.discriminator_map:
                        target_cls = root.discriminator_map[row_type_value]
            
            elif self.inheritance.strategy.name == "CLASS" and not self.parent:
                for child_mapper in self.children:
                    fk_col = None
                    for col_name, col in child_mapper.columns.items():
                        if isinstance(col, ForeignKey) and col.target_table == self.table_name:
                            fk_col = col_name
                            break

                    if fk_col is None:
                        for rel_name, rel in child_mapper.relationships.items():
                            target_cls = child_mapper._resolve_target_class(rel.target)
                            if target_cls == self.cls and rel.r_type in ("many-to-one", "one-to-one"):
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