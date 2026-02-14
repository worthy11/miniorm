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
    def resolve_select(self, mapper):
        pass

    @abstractmethod
    def resolve_insert(self, mapper, entity):
        """Return operations dict: table_name -> dict of fields to set."""
        pass

    @abstractmethod
    def resolve_update(self, mapper, entity):
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

    def resolve_table_name(self, mapper):
        pass

    def resolve_select(self, mapper):
        return {mapper.table_name: mapper.columns}

    def resolve_insert(self, mapper, entity):
        operations = {}
        operations[mapper.table_name] = mapper._map_data_to_columns(entity)
        return operations

    def resolve_update(self, mapper, entity):
        operations = {}
        operations[mapper.table_name] = mapper._map_data_to_columns(entity)
        operations[mapper.table_name]["_pk"] = {mapper.pk: getattr(entity, mapper.pk)}
        return operations

    def resolve_delete(self, mapper, entity):
        operations = {mapper.table_name: {}}
        operations[mapper.table_name]["_pk"] = {mapper.pk: getattr(entity, mapper.pk)}
        return operations

    def resolve_target_class(self, mapper, row_dict):
        return mapper.cls

    def resolve_attributes(self, mapper):
        return mapper.columns

class ClassTableInheritance(InheritanceStrategy):
    name = "CLASS"

    def resolve_columns(self, mapper):
        pass

    def resolve_table_name(self, mapper):
        pass

    def resolve_select(self, mapper):
        columns = {}
        columns[mapper.table_name] = mapper.columns
        if mapper.parent:
            columns[mapper.table_name]["_join"] = (mapper.parent.table_name, mapper.pk, mapper.parent.pk)
            columns.update(self.resolve_select(mapper.parent))
        return columns

    def resolve_insert(self, mapper, entity):
        operations = {}

        if mapper.parent:
            operations.update(self.resolve_insert(mapper.parent, entity))
            ops = operations.pop("_fk_from_parent", {})
            ops.update({mapper.table_name: mapper.pk})
            operations["_fk_from_parent"] = ops

        operations[mapper.table_name] = mapper._map_data_to_columns(entity)
        return operations

    def resolve_update(self, mapper, entity):
        operations = {}

        if mapper.parent:
            operations.update(self.resolve_update(mapper.parent, entity))

        operations[mapper.table_name] = mapper._map_data_to_columns(entity)
        operations[mapper.table_name]["_pk"] = {mapper.pk: getattr(entity, mapper.pk)}
        return operations

    def resolve_delete(self, mapper, entity):
        operations = {}

        operations[mapper.table_name]["_pk"] = {mapper.pk: getattr(entity, mapper.pk)}
        
        if mapper.parent:
            operations.update(self.resolve_delete(mapper.parent, entity))

        return operations

    def resolve_target_class(self, mapper, row_dict):
        if mapper.children:
            for child_cls in mapper.children:
                pk_alias = f"{child_cls._mapper.table_name}#{child_cls._mapper.pk}"
                if row_dict.get(pk_alias) is not None:
                    return self.resolve_target_class(child_cls._mapper, row_dict)
        return mapper.cls

    def resolve_attributes(self, mapper):
        attrs = mapper.columns
        if mapper.parent:
            attrs = self.resolve_attributes(mapper.parent) | attrs
        return attrs

class ConcreteTableInheritance(InheritanceStrategy):
    name = "CONCRETE"

    def resolve_columns(self, mapper):
        STRATEGIES["CLASS"].resolve_columns(mapper)

    def resolve_table_name(self, mapper):
        STRATEGIES["CLASS"].resolve_table_name(mapper)

    def resolve_select(self, mapper):
        return STRATEGIES["CLASS"].resolve_select(mapper)

    def resolve_insert(self, mapper, entity):
        return STRATEGIES["CLASS"].resolve_insert(mapper, entity)

    def resolve_update(self, mapper, entity):
        return STRATEGIES["CLASS"].resolve_update(mapper, entity)

    def resolve_delete(self, mapper, entity):
        return STRATEGIES["CLASS"].resolve_delete(mapper, entity)

    def resolve_target_class(self, mapper, row_dict):
        return STRATEGIES["CLASS"].resolve_target_class(mapper, row_dict)
    
    def resolve_attributes(self, mapper):
        return STRATEGIES["CLASS"].resolve_attributes(mapper)


STRATEGIES = {
    "SINGLE": SingleTableInheritance(),
    "CLASS": ClassTableInheritance(),
    "CONCRETE": ConcreteTableInheritance(),
}


class Inheritance:
    """
    Wraps inheritance strategy and discriminator value.
    """
    def __init__(self, strategy):
        self.strategy = strategy
    
    @property
    def name(self):
        return self.strategy.name
