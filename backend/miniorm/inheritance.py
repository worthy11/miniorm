from miniorm.orm_types import Text
from abc import ABC, abstractmethod

class InheritanceStrategy(ABC):
    name: str

    @abstractmethod
    def resolve_columns(self, mapper):
        pass

    @abstractmethod
    def resolve_table_name(self, mapper):
        pass
    
    @abstractmethod
    def resolve_insert(self, mapper, entity):
        """Return operations dict: table_name -> dict of fields to set."""
        pass

    @abstractmethod
    def resolve_update(self, mapper, entity, old_state):
        """Return operations dict: table_name -> dict of fields (incl. _pk for WHERE)."""
        pass
    
    @abstractmethod
    def resolve_delete(self, mapper, entity):
        """Return operations dict: table_name -> pk_value, optional _m2m_cleanup list."""
        pass
    
    @abstractmethod
    def resolve_target_class(self, mapper, row_dict):
        """Return the model class to instantiate for this row (for hydration)."""
        pass

    @abstractmethod
    def resolve_attributes(self, mapper):
        pass


class SingleTableInheritance(InheritanceStrategy):
    name = "SINGLE"

    def resolve_columns(self, mapper):
        if mapper.parent:
            mapper.columns = dict(mapper.parent.columns) | mapper.columns
        # TODO: Require discriminator column to be present in the parent
        mapper.columns[mapper.discriminator] = Text(nullable=False)

    def resolve_table_name(self, mapper):
        root = mapper
        while root.parent and not root.abstract:
            root = root.parent
        print(f"Resolved table name for class {mapper.cls.__name__}: {root.table_name}")
        mapper.table_name = root.table_name

    def resolve_insert(self, mapper, entity):
        """Return operations dict: table_name -> dict of fields to set."""
        operations = {}

        if mapper.parent:
            operations.update(self.resolve_insert(mapper.parent, entity))

        if mapper.table_name not in operations:
            operations[mapper.table_name] = {}
        operations[mapper.table_name].update(mapper._get_operation_columns(entity))
        operations[mapper.table_name][mapper.discriminator] = mapper.discriminator_value
        return operations

    def resolve_update(self, mapper, entity, old_state=None):
        """Return operations dict: table_name -> dict of fields to modify (incl. _pk for WHERE)."""
        operations = {}
        operations[mapper.table_name] = mapper._get_operation_columns(entity)
        operations[mapper.table_name][mapper.discriminator] = mapper.discriminator_value
        operations[mapper.table_name]["_pk"] = getattr(entity, mapper.pk)
        return operations

    def resolve_delete(self, mapper, entity):
        """Return operations dict: _m2m_cleanup list + table_name -> pk_value for each delete."""
        operations = {}
        pk_val = getattr(entity, mapper.pk)
        
        m2m_cleanup = []
        for name, rel in mapper.relationships.items():
            if rel.r_type == "many-to-many" and rel.association_table:
                assoc = rel.association_table
                m2m_cleanup.append({
                    "assoc_table": assoc.name,
                    "pk_val": pk_val,
                    "local_key": assoc.local_key,
                })
        
        if m2m_cleanup:
            operations["_m2m_cleanup"] = m2m_cleanup
        
        operations[mapper.table_name] = {mapper.pk: pk_val}
        return operations

    def resolve_target_class(self, mapper, row_dict):
        root = mapper
        while root.parent:
            root = root.parent
        disc_val = row_dict.get(root.discriminator)
        if root.discriminator_map and disc_val in root.discriminator_map:
            return root.discriminator_map[disc_val]
        return mapper.cls

    def resolve_attributes(self, mapper):
        attrs = mapper.columns
        if mapper.parent:
            attrs = dict(mapper.parent.columns) | attrs
        return attrs

class ClassTableInheritance(InheritanceStrategy):
    name = "CLASS"

    def resolve_columns(self, mapper):
        mapper.columns = mapper.declared_columns

    def resolve_table_name(self, mapper):
        pass

    def resolve_insert(self, mapper, entity):
        operations = {}

        if mapper.parent:
            operations.update(self.resolve_insert(mapper.parent, entity))
            prev = operations.get("_fk_from_previous", {})
            operations["_fk_from_previous"] = {**prev, mapper.table_name: mapper.pk}

        operations[mapper.table_name] = mapper._get_operation_columns(entity)
        return operations

    def resolve_update(self, mapper, entity, old_state=None):
        operations = {}

        if mapper.parent:
            operations.update(self.resolve_update(mapper.parent, entity, old_state))

        operations[mapper.table_name] = mapper._get_operation_columns(entity)
        operations[mapper.table_name]["_pk"] = getattr(entity, mapper.pk)
        return operations

    def resolve_delete(self, mapper, entity):
        operations = {}

        if mapper.parent:
            parent_ops = self.resolve_delete(mapper.parent, entity)
            if "_m2m_cleanup" in parent_ops:
                operations["_m2m_cleanup"] = parent_ops.pop("_m2m_cleanup")
            operations.update(parent_ops)

        pk_val = getattr(entity, mapper.pk)
        
        m2m_cleanup = operations.get("_m2m_cleanup", [])
        for name, rel in mapper.relationships.items():
            if rel.r_type == "many-to-many" and rel.association_table:
                assoc = rel.association_table
                m2m_cleanup.append({
                    "assoc_table": assoc.name,
                    "pk_val": pk_val,
                    "local_key": assoc.local_key,
                })
        
        if m2m_cleanup:
            operations["_m2m_cleanup"] = m2m_cleanup

        operations[mapper.table_name] = {mapper.pk: pk_val}
        return operations

    def resolve_target_class(self, mapper, row_dict):
        if not mapper.parent and mapper.children:
            for child_cls in mapper.children:
                child_mapper = child_cls._mapper
                pk_alias = f"{child_mapper.table_name}#{child_mapper.pk}"
                if row_dict.get(pk_alias) is not None:
                    return child_cls
        return mapper.cls

    def resolve_attributes(self, mapper):
        attrs = mapper.columns
        if mapper.parent:
            attrs = self.resolve_attributes(mapper.parent) | attrs
        return attrs

class ConcreteTableInheritance(InheritanceStrategy):
    name = "CONCRETE"

    def resolve_columns(self, mapper):
        if mapper.parent:
            mapper.columns = dict(mapper.parent.columns) | mapper.columns

    def resolve_table_name(self, mapper):
        pass

    def resolve_insert(self, mapper, entity):
        operations = {}
        operations[mapper.table_name] = mapper._get_operation_columns(entity)
        return operations

    def resolve_update(self, mapper, entity, old_state):
        operations = {}
        operations[mapper.table_name] = mapper._get_operation_columns(entity)
        operations[mapper.table_name]["_pk"] = getattr(entity, mapper.pk)
        return operations

    def resolve_delete(self, mapper, entity):
        operations = {}
        pk_val = getattr(entity, mapper.pk)
        
        m2m_cleanup = []
        for name, rel in mapper.relationships.items():
            if rel.r_type == "many-to-many" and rel.association_table:
                assoc = rel.association_table
                m2m_cleanup.append({
                    "assoc_table": assoc.name,
                    "pk_val": pk_val,
                    "local_key": assoc.local_key,
                })
        
        if m2m_cleanup:
            operations["_m2m_cleanup"] = m2m_cleanup
        
        operations[mapper.table_name] = {mapper.pk: pk_val}
        return operations

    def resolve_target_class(self, mapper, row_dict):
        if not mapper.parent:
            concrete_type = row_dict.get("_concrete_type")
            if concrete_type and mapper.children:
                for child_cls in mapper.children:
                    if child_cls.__name__ == concrete_type:
                        return child_cls
        return mapper.cls
    
    def resolve_attributes(self, mapper):
        return mapper.columns


STRATEGIES = {
    "SINGLE": SingleTableInheritance(),
    "CLASS": ClassTableInheritance(),
    "CONCRETE": ConcreteTableInheritance(),
}


class Inheritance:
    """
    Wraps inheritance strategy and discriminator value.
    """
    def __init__(self, strategy, discriminator_value):
        self.strategy = strategy
        self.discriminator_value = discriminator_value
        self.discriminator = None
    
    @property
    def name(self):
        return self.strategy.name
