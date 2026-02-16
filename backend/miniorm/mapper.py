from miniorm.orm_types import Relationship, ForeignKey, Column, Text, AssociationTable
from miniorm.inheritance import STRATEGIES, Inheritance

class Mapper:
    def __init__(self, cls, columns, relationships, meta_attrs):
        self.cls = cls
        self.meta = meta_attrs or {}
        
        self.pk = None
        self.inheritance = None
        self.columns = columns
        
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

            if getattr(rel, "backref", None) and rel.backref not in target_mapper.relationships:
                target_mapper.relationships[rel.backref] = reverse_rel
            else:
                target_mapper.relationships[self.table_name] = reverse_rel
        
        else:
            rel._resolved_fk_name = name
            rel.local_table = self.table_name
            rel.remote_table = target_mapper.table_name
            
            fk = ForeignKey(target_mapper.table_name, target_mapper.pk, pk=rel.pk, unique=rel.r_type == "one-to-one",
                            on_delete_cascade=getattr(rel, 'cascade_delete', True))
            self.columns[name] = fk
            
            backref_name = rel.backref
            if backref_name in target_mapper.relationships:
                raise ValueError(f"Backref '{backref_name}' already exists on {target_cls.__name__}")

            if getattr(rel, "backref", None):
                rel._backref_owner = self.cls  # class that declared the rel (e.g. Subject); used when loading collection from "one" side
                target_mapper.relationships[backref_name] = rel
            else:
                target_mapper.relationships[self.table_name] = rel


    def _map_data_to_columns(self, entity):
        mapped_data = {}
        for col_name, col_obj in self.columns.items():
            val = entity.__dict__.get(col_name)

            if hasattr(val, '_mapper'):
                pk_attr = val._mapper.pk
                val = val.__dict__.get(pk_attr)
            
            if isinstance(val, list):
                val = None

            if val is not None:
                mapped_data[col_name] = val
            elif col_obj.default is not None:
                mapped_data[col_name] = col_obj.default
            else:
                mapped_data[col_name] = None

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
                    
    def prepare_select(self):
        return self.inheritance.strategy.resolve_select(self)

    def prepare_insert(self, entity):
        return self.inheritance.strategy.resolve_insert(self, entity)
    
    def prepare_update(self, entity, old_state):
        return self.inheritance.strategy.resolve_update(self, entity)
    
    def prepare_delete(self, entity, _visited=None):
        table_name = self.table_name
        if _visited is None: _visited = set()
        if table_name in _visited: return {}
        _visited.add(table_name)

        dependents = {}
        
        all_relationships = {}
        curr = self
        while curr:
            all_relationships.update(curr.relationships)
            curr = curr.parent

        all_my_tables = [self.table_name]
        curr_p = self.parent
        while curr_p:
            all_my_tables.append(curr_p.table_name)
            curr_p = curr_p.parent

        for rel in all_relationships.values():
            if getattr(rel, 'cascade_delete', True):
                if rel.r_type == 'many-to-many':
                    assoc = rel.association_table
                    key = None
                    if assoc.local_table in all_my_tables:
                        key = assoc.local_key
                    elif assoc.remote_table in all_my_tables:
                        key = assoc.remote_key
                    
                    if key:
                        dependents[assoc.name] = {key: getattr(entity, self.pk)}

                elif rel.r_type in ['one-to-one', 'many-to-one'] and rel.remote_table in all_my_tables:

                    pass

        inheritance_deletes = self.inheritance.strategy.resolve_delete(self, entity)
        
        final_ops = {**dependents, **inheritance_deletes}
        return final_ops
    
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