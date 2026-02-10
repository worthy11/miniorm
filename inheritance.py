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
    def resolve_update(self, mapper, data, pk_value):
        pass
    
    @abstractmethod
    def resolve_delete(self, mapper, pk_value):
        pass
    
    @abstractmethod
    def resolve_select(self, mapper):
        pass

class SingleTableInheritance(InheritanceStrategy):
    name = "SINGLE"

    def resolve_columns(self, mapper):
        if mapper.parent:
            mapper.columns = dict(mapper.parent.columns) | mapper.columns

    def resolve_table_name(self, mapper):
        root = mapper
        while root.parent and not root.abstract:
            root = root.parent
        print(f"Resolved table name for class {mapper.cls.__name__}: {root.table_name}")
        mapper.table_name = root.table_name

    def resolve_update(self, mapper, data, pk_value):
        pass

    def resolve_delete(self, mapper, pk_value):
        pass

    def resolve_select(self, mapper):
        pass

class ClassTableInheritance(InheritanceStrategy):
    name = "CLASS"

    def resolve_columns(self, mapper):
        mapper.columns = mapper.declared_columns

    def resolve_table_name(self, mapper):
        pass

    def resolve_update(self, mapper, data, pk_value):
        pass

    def resolve_delete(self, mapper, pk_value):
        pass

    def resolve_select(self, mapper):
        pass

class ConcreteTableInheritance(InheritanceStrategy):
    name = "CONCRETE"

    def resolve_columns(self, mapper):
        if mapper.parent:
            mapper.columns = dict(mapper.parent.columns) | mapper.columns

    def resolve_table_name(self, mapper):
        pass

    def resolve_update(self, mapper, data, pk_value):
        pass

    def resolve_delete(self, mapper, pk_value):
        pass

    def resolve_select(self, mapper):
        pass
    

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
