from orm_types import Relationship, ForeignKey, Column, Text, AssociationTable
from inheritance import STRATEGIES, Inheritance

class Mapper:
    def __init__(self, cls, columns, relationships, meta_attrs):
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
        self.declared_relationships = dict(relationships)
        self.relationships = {}
        self.children = []

        self._resolve_parent()
        self._resolve_inheritance()
        self._resolve_table_name()
        self._resolve_columns()

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
        # Process inheritance if:
        # 1. Has parent (child class)
        # 2. Has explicit inheritance in Meta (root class of inheritance hierarchy)
        requested = self.meta.get("inheritance")
        
        if not self.parent and not requested:
            return

        if requested:
            requested = requested.upper()
        else:
            if self.parent and self.parent.inheritance:
                requested = self.parent.inheritance.strategy.name
            else:
                requested = "SINGLE"

        if requested not in STRATEGIES:
            raise ValueError(f"Nieznana strategia dziedziczenia: {requested}")

        strategy = STRATEGIES[requested]
        discriminator_value = self.meta.get("discriminator_value", self.cls.__name__)

        self.inheritance = Inheritance(strategy, discriminator_value)
        if self.parent:
            self.parent.children.append(self.cls)
            if not self.parent.inheritance:
                self.parent.inheritance = Inheritance(strategy, self.parent.cls.__name__)
    
    def _resolve_table_name(self):
        self.table_name = self.meta.get("table_name", self.cls.__name__+"s")
        if self.inheritance:
            self.inheritance.strategy.resolve_table_name(self)

    def _resolve_columns(self):
        self.columns = dict(self.declared_columns)

        if self.inheritance:
            if self.parent:
                self.columns = dict(self.parent.columns) | self.columns
            
            if self.inheritance.strategy.name == "SINGLE":
                root = self
                while root.parent: root = root.parent

                if not hasattr(root, 'discriminator_map') or root.discriminator_map is None:
                    root.discriminator_map = {}
                
                root.discriminator_map[self.inheritance.discriminator_value] = self.cls
                print(f"DEBUG: Registering {self.cls.__name__} in {root.cls.__name__} map")
                
                if root.discriminator not in root.columns:
                    from orm_types import Text
                    root.columns[root.discriminator] = Text(nullable=False)
                
                if self.parent:
                    for name, col in self.declared_columns.items():
                        if name not in root.columns:
                            col.nullable = True
                            root.columns[name] = col
        
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
            from base import MiniBase
            for cls in MiniBase._registry:
                if getattr(cls, "_mapper", None) and cls._mapper.table_name == target:
                    return cls
        return None

    def _apply_relationship(self, name, rel, target_cls, target_mapper):
        if name in self.relationships:
            raise ValueError(f"Relationship '{name}' already exists for table {self.table_name}")
        self.relationships[name] = rel
        rel._resolved_target = target_cls

        if rel.r_type == "many-to-many":
            tables = sorted([self.table_name, target_mapper.table_name])
            table_name = "_".join(tables)
            local_key = f"{self.table_name.rstrip('s')}_id"
            remote_key = f"{target_mapper.table_name.rstrip('s')}_id"
            rel.local_table = self.table_name
            rel.remote_table = target_mapper.table_name

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
                target_mapper.relationships[rel.backref] = reverse_rel
        
        else:
            rel._resolved_fk_name = name
            rel.local_table = self.table_name
            rel.remote_table = target_mapper.table_name
            self.columns[name] = ForeignKey(target_mapper.table_name, target_mapper.pk, pk=rel.pk, unique=rel.r_type == "one-to-one")
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
        from base import MiniBase
        
        for mapper in MiniBase._registry.values():
            try:
                mapper._resolve_pk()
            except:
                pass

        for mapper in MiniBase._registry.values():
            for name, rel in mapper.declared_relationships.items():
                if name in mapper.relationships:
                    continue
                target_cls = mapper._resolve_target_class(rel.target_table)
                if target_cls is None:
                    raise ValueError(f"Cannot resolve target: {rel.target_table}")
                mapper._apply_relationship(name, rel, target_cls, target_cls._mapper)

        for mapper in MiniBase._registry.values():
            mapper._resolve_pk()


    def _get_insert_columns(self, entity):
        insert_data = {}
        for col_name, col_obj in self.columns.items():
            if col_name == self.pk:
                continue
            
            value = getattr(entity, col_name, None)
            
            if hasattr(value, '_mapper'):
                target_pk = value._mapper.pk
                value = getattr(value, target_pk, None)
                
            if value is not None and not hasattr(value, '__clause_element__'):
                insert_data[col_name] = value
            elif col_obj.default is not None:
                insert_data[col_name] = col_obj.default
            elif col_obj.nullable:
                insert_data[col_name] = None
                
        return insert_data

    def get(self, id):
        return None
    
    def get_all(self):
        return []
    

    def prepare_insert(self, entity, query_builder):
        operations = []

        def clean_val(v):
            if v.__class__.__name__ in ('Number', 'String', 'Relationship', 'Column'):
                return None
            return v
        
        if self.inheritance and self.inheritance.strategy.name == "CLASS" and self.parent:
            parent_ops = self.parent.prepare_insert(entity, query_builder)
            operations.extend(parent_ops)
            
            local_data = {}
            for col_name in self.declared_columns:
                if hasattr(entity, col_name):
                    local_data[col_name] = clean_val(getattr(entity, col_name))
            
            sql, params = query_builder.build_insert(self, local_data)
            operations.append((sql, params, {
                'table': self.table_name,
                'data': local_data,
                'fk_from_previous': self.pk 
            }))
            return operations

        insert_data = self._get_insert_columns(entity)
        insert_data = {k: clean_val(v) for k, v in insert_data.items()}
        
        if self.inheritance and self.inheritance.strategy.name == "SINGLE":
            insert_data[self.discriminator] = self.discriminator_value
            
        sql, params = query_builder.build_insert(self, insert_data)
        operations.append((sql, params, {'table': self.table_name, 'data': insert_data}))
        
        return operations
    
    def _get_mapper_for_table(self, table_name):
        from base import MiniBase
        for m in MiniBase._registry.values():
            if m.table_name == table_name:
                return m
        return self
    
    def prepare_update(self, entity, query_builder, old_state):
        if not old_state:
            return []

        operations = []
        
        changed_data = {}
        for col_name in self.columns:
            if col_name == self.pk: continue
            
            new_val = getattr(entity, col_name, None)
            if hasattr(new_val, '_mapper'):
                new_val = getattr(new_val, new_val._mapper.pk, None)
                
            if new_val != old_state.get(col_name):
                changed_data[col_name] = new_val

        if not changed_data:
            return []

        strategy_name = self.inheritance.strategy.name if self.inheritance else "NONE"

        if strategy_name == "CLASS":
            parent_data = {}
            child_data = {}
            
            for col, val in changed_data.items():
                if self.parent and col in self.parent.columns:
                    parent_data[col] = val
                elif col in self.declared_columns:
                    child_data[col] = val
            
            if parent_data and self.parent:
                sql, params = query_builder.build_update(
                    self.parent, parent_data, {self.parent.pk: getattr(entity, self.pk)}
                )
                operations.append((sql, params, {'table': self.parent.table_name}))

            if child_data:
                sql, params = query_builder.build_update(
                    self, child_data, {self.pk: getattr(entity, self.pk)}
                )
                operations.append((sql, params, {'table': self.table_name}))

        else:
            sql, params = query_builder.build_update(
                self, changed_data, {self.pk: getattr(entity, self.pk)}
            )
            operations.append((sql, params, {'table': self.table_name}))

        return operations
    
    def prepare_delete(self, entity, query_builder):
        operations = []
        pk_val = getattr(entity, self.pk)

        for name, rel in self.relationships.items():
            if rel.r_type == "many-to-many":
                sql, params = query_builder.build_m2m_cleanup(
                    rel.association_table.name,
                    pk_val,
                    rel.association_table.local_key
                )
                operations.append((sql, params, {'type': 'm2m_cleanup'}))
        
        if self.inheritance and self.inheritance.strategy.name == "CLASS":
            sql, params = query_builder.build_delete(self, pk_val)
            operations.append((sql, params, {'table': self.table_name}))
            
            if self.parent:
                parent_sql, parent_params = query_builder.build_delete(self.parent, pk_val)
                operations.append((parent_sql, parent_params, {'table': self.parent.table_name}))
        
        else:
            sql, params = query_builder.build_delete(self, pk_val)
            operations.append((sql, params, {'table': self.table_name}))
            
        return operations
    
    def hydrate(self, row_dict):
        target_cls = self.cls
        
        inheritance_info = self.inheritance
        if not inheritance_info and self.children:
            inheritance_info = self.children[0]._mapper.inheritance

        if inheritance_info:
            strategy_name = inheritance_info.strategy.name
            
            if strategy_name == "SINGLE":
                root_mapper = self
                while root_mapper.parent:
                    root_mapper = root_mapper.parent
                
                disc_val = row_dict.get(root_mapper.discriminator)
                if root_mapper.discriminator_map and disc_val in root_mapper.discriminator_map:
                    target_cls = root_mapper.discriminator_map[disc_val]

            elif strategy_name == "CLASS" and not self.parent:
                for child_cls in self.children:
                    child_mapper = child_cls._mapper
                    pk_alias = f"{child_mapper.table_name}_{child_mapper.pk}"
                    
                    if row_dict.get(pk_alias) is not None:
                        target_cls = child_cls
                        break

            elif strategy_name == "CONCRETE" and not self.parent:
                concrete_type = row_dict.get("_concrete_type")
                if concrete_type:
                    for child_cls in self.children:
                        if child_cls.__name__ == concrete_type:
                            target_cls = child_cls
                            break

        obj = target_cls()
        target_mapper = target_cls._mapper
        
        for key, value in row_dict.items():
            if key in target_mapper.columns:
                object.__setattr__(obj, key, value)
            
            elif "_" in key:
                parts = key.rsplit("_", 1)
                if len(parts) == 2:
                    table_prefix, col_name = parts
                    if table_prefix == target_mapper.table_name and col_name in target_mapper.columns:
                        object.__setattr__(obj, col_name, value)
        
        return obj
    
    def _hydrate_row_to_dict(self, row, column_names):
        data = {}
        row_map = dict(zip(column_names, row))
        
        for attr_name, col_obj in self.columns.items():
            if attr_name in row_map:
                data[attr_name] = row_map[attr_name]
        
        return data