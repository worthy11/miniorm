from miniorm.orm_types import Relationship, ForeignKey, Column, Text, AssociationTable
from miniorm.inheritance import STRATEGIES, Inheritance

class Mapper:
    def __init__(self, cls, columns, relationships, meta_attrs):
        self.cls = cls
        self.meta = meta_attrs or {}
        
        self.pk = None
        self.inheritance = None
        self.columns = columns
        self.abstract = self.meta.get("abstract", False)
        
        self.parent = None
        self.declared_relationships = dict(relationships)
        self.relationships = {}
        self.children = []
        self._pending_relationships = []

        self._resolve_parent()
        self._resolve_inheritance()
        self._resolve_table_name()
        self._resolve_columns()
        self._resolve_relationships()
        self._resolve_pk()

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
        requested = self.meta.get("inheritance")
        if requested:
            requested = requested.upper()
            if self.parent and self.parent.inheritance:
                parent_strategy = self.parent.inheritance.strategy.name
                if parent_strategy != requested:
                    raise ValueError(f"Inheritance strategy mismatch in class {self.cls.__name__} and {self.parent.cls.__name__}: {parent_strategy} != {requested}")
        else:
            requested = "SINGLE"

        if requested not in STRATEGIES:
            raise ValueError(f"Unknown inheritance strategy: {requested}")

        if self.parent:
            self.parent.children.append(self.cls)

        strategy = STRATEGIES[requested]
        self.inheritance = Inheritance(strategy)
    
    def _resolve_table_name(self):
        self.table_name = self.meta.get("table_name", self.cls.__name__+"s")
        self.inheritance.strategy.resolve_table_name(self)
        if "#" in self.table_name:
            raise ValueError("Table name cannot contain '#'")

    def _resolve_columns(self):
        self.inheritance.strategy.resolve_columns(self)
        
    def _resolve_relationships(self):
        """Try to resolve relationships immediately. Defer if target not available."""
        for name, rel in self.declared_relationships.items():
            target_cls = self._resolve_target_class(rel.target_table)
            if target_cls is None:
                self._pending_relationships.append((name, rel))
                continue
            self._apply_relationship(name, rel, target_cls, target_cls._mapper)

    def _resolve_pk(self):
        pk_cols = [name for name, col in self.columns.items() if col.pk]
        if pk_cols:
            self.pk = pk_cols[0]
        elif self.parent:
            self.pk = self.parent.pk
        else:
            raise Exception(f"Class {self.cls.__name__} has no primary key defined")
    
    def _resolve_target_class(self, target):
        if isinstance(target, type) and hasattr(target, "_mapper"):
            return target
        if isinstance(target, str):
            from miniorm.base import MiniBase
            for cls in MiniBase._registry:
                if getattr(cls, "_mapper", None) and (cls._mapper.table_name == target or cls.__name__ == target):
                    return cls
        return None

    def _apply_relationship(self, name, rel, target_cls, target_mapper):
        if name in self.relationships:
            return

        self.relationships[name] = rel
        rel._resolved_target = target_cls

        if rel.r_type == "many-to-many":
            tables = sorted([self.table_name, target_mapper.table_name])
            table_name = "_".join(tables)
            local_key = f"{self.table_name.rstrip('s')}_id"
            remote_key = f"{target_mapper.table_name.rstrip('s')}_id"
            rel.local_table = self.table_name
            rel.remote_table = target_mapper.table_name
            rel.local_table_pk = self.pk
            rel.remote_table_pk = target_mapper.pk

            rel.association_table = AssociationTable(
                name=table_name, local_key=local_key, remote_key=remote_key,
                local_table=self.table_name, remote_table=target_mapper.table_name
            )
            rel._resolved_local_key = local_key
            rel._resolved_remote_key = remote_key

            if getattr(rel, "backref", None) and rel.backref not in target_mapper.relationships:
                reverse_rel = Relationship(self.table_name, r_type="many-to-many", backref=name)
                reverse_rel._resolved_target = self.cls
                reverse_rel.local_table = target_mapper.table_name
                reverse_rel.remote_table = self.table_name

                reverse_rel.association_table = AssociationTable(
                    name=table_name, local_key=remote_key, remote_key=local_key,
                    local_table=target_mapper.table_name, remote_table=self.table_name
                )
                reverse_rel._resolved_local_key = remote_key
                reverse_rel._resolved_remote_key = local_key
                reverse_rel.local_table_pk = target_mapper.pk
                reverse_rel.remote_table_pk = self.pk
                target_mapper.relationships[rel.backref] = reverse_rel
        
        else:
            rel._resolved_fk_name = name
            rel.local_table = self.table_name
            rel.remote_table = target_mapper.table_name
            
            fk = ForeignKey(target_mapper.table_name, target_mapper.pk, pk=rel.pk, unique=rel.r_type == "one-to-one",
                            on_delete_cascade=getattr(rel, 'cascade_delete', True))
            self.columns[name] = fk
            
            if getattr(rel, "backref", None) and rel.r_type == "many-to-one":
                backref_name = rel.backref
                if backref_name in target_mapper.relationships:
                    raise ValueError(f"Backref '{backref_name}' already exists on {target_cls.__name__}")
                reverse_rel = Relationship(self.table_name, r_type="one-to-many")
                reverse_rel._resolved_target = self.cls
                reverse_rel._resolved_fk_name = name
                reverse_rel.local_table = target_mapper.table_name
                reverse_rel.remote_table = self.table_name
                target_mapper.relationships[backref_name] = reverse_rel
            else:
                target_mapper.relationships[self.table_name] = rel

    @staticmethod
    def finalize_mappers():
        from miniorm.base import MiniBase
        
        for mapper in MiniBase._registry.values():
            resolved = []
            for name, rel in mapper._pending_relationships:
                target_cls = mapper._resolve_target_class(rel.target_table)
                if target_cls is not None:
                    mapper._apply_relationship(name, rel, target_cls, target_cls._mapper)
                    resolved.append((name, rel))
            for item in resolved:
                mapper._pending_relationships.remove(item)
        
        for mapper in MiniBase._registry.values():
            if mapper._pending_relationships:
                pending = [(n, r.target_table) for n, r in mapper._pending_relationships]
                raise ValueError(f"Cannot resolve relationship target(s) after all models loaded: {mapper.cls.__name__} pending: {pending}")
        
        for mapper in MiniBase._registry.values():
            mapper._resolve_pk()
        
        for mapper in MiniBase._registry.values():
            if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS":
                if mapper.parent and not any(
                    getattr(rel, "_resolved_target", None) and getattr(rel._resolved_target, "_mapper", None) and rel._resolved_target._mapper.table_name == mapper.parent.table_name
                    for rel in mapper.relationships.values()
                ):
                    raise ValueError(f"Missing relationship to parent ({mapper.parent.table_name}) in {mapper.table_name} (CLASS inheritance requires it)")


    def _map_data_to_columns(self, entity):
        mapped_data = {}

        for attr in entity.__dict__:
            if attr in self.columns:
                val = getattr(entity, attr, None)
                if hasattr(val, '_mapper'):
                    target_pk = val._mapper.pk
                    val = getattr(val, target_pk, None)

                if val is not None:
                    mapped_data[attr] = val
                elif self.columns[attr].default is not None:
                    mapped_data[attr] = self.columns[attr].default
                else:
                    mapped_data[attr] = None

        return mapped_data

    def _get_mapper_for_table(self, table_name):
        from miniorm.base import MiniBase
        for m in MiniBase._registry.values():
            if m.table_name == table_name:
                return m
        return self

    def _get_column_name(self, column_attr):
        attrs = self.inheritance.strategy.resolve_attributes(self)
        for name, col in attrs.items():
            if col is column_attr:
                return name
        return None

    def _collect_cascade_dependents(self, entity):
        if _visited is None:
            _visited = set()
        if id(entity) in _visited:
            return []
        _visited.add(id(entity))
        out = []
        mapper = entity._mapper
        
        entity_pk = getattr(entity, mapper.pk, None)
        if entity_pk is None:
            return [entity]

        target_tables = {mapper.table_name}
        if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS" and mapper.parent:
            target_tables.add(mapper.parent.table_name)
        
        for other_mapper in MiniBase._registry.values():
            if other_mapper.cls is entity.__class__:
                continue
            for rel in other_mapper.relationships.values():
                if not getattr(rel, 'cascade_delete', True):
                    continue
                if rel.r_type not in ('many-to-one', 'one-to-one'):
                    continue
                if not getattr(rel, '_resolved_target', None):
                    continue
                
                fk_target_table = getattr(rel, 'remote_table', None)
                if not fk_target_table:
                    fk_target_table = rel._resolved_target._mapper.table_name
                
                if fk_target_table not in target_tables:
                    continue
                
                fk_name = getattr(rel, '_resolved_fk_name', None)
                if not fk_name:
                    continue
                self._is_loading = True
                try:
                    refs = self.query(other_mapper.cls).filter(**{fk_name: entity_pk}).all()
                finally:
                    self._is_loading = False
                for ref in refs:
                    out.extend(self._collect_cascade_dependents(ref, _visited))
        out.append(entity)
        return out

    def prepare_select(self):
        return self.inheritance.strategy.resolve_select(self)

    def prepare_insert(self, entity):
        return self.inheritance.strategy.resolve_insert(self, entity)
    
    def prepare_update(self, entity, old_state):
        operations = self.inheritance.strategy.resolve_update(self, entity)
        if old_state:
            for table_name in list(operations.keys()):
                print(f"DEBUG: OLD STATE: {old_state}")
                data = operations[table_name]
                filtered = {
                    k: v for k, v in data.items()
                    if old_state.get(k) != v
                }
                # nic nie zostało do zmiany
                if len(filtered) == 1 and "_pk" in filtered:
                    operations.pop(table_name)
                else:
                    operations[table_name] = filtered
        return operations   
    
    def prepare_delete(self, entity):
        return self.inheritance.strategy.resolve_delete(self, entity)
    
    def hydrate(self, row_dict):
        target_cls = self.inheritance.strategy.resolve_target_class(self, row_dict)
        attributes = self.inheritance.strategy.resolve_attributes(self)
        obj = target_cls()
        target_mapper = target_cls._mapper

        for key, value in row_dict.items():
            if value is not None:
                if "#" in key:
                    table_name, col_name = key.split("#", 1)
                    if table_name == target_mapper.table_name or col_name in attributes:
                        object.__setattr__(obj, col_name, value)
                else:
                    if key in attributes:
                        object.__setattr__(obj, key, value)

        return obj