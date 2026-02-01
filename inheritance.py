from abc import ABC, abstractmethod

class InheritanceStrategy(ABC):
    name: str

    @abstractmethod
    def resolve_columns(self, mapper):
        pass
        pass

    @abstractmethod
    def resolve_table_name(self, mapper):
        pass

class SingleTableInheritance(InheritanceStrategy):
    name = "SINGLE"

    def resolve_columns(self, mapper):
        mapper.columns = dict(mapper.parent.columns) | mapper.columns

    def resolve_table_name(self, mapper):
        root = mapper
        while root.parent and getattr(root, "inheritance", None) and root.inheritance.strategy.name == "SINGLE":
            root = root.parent
        return root.table_name


class ClassTableInheritance(InheritanceStrategy):
    name = "CLASS"

    def resolve_columns(self, mapper):
        # mapper.columns already contains declared columns, merge with parent columns
        mapper.columns = dict(mapper.parent.columns) | mapper.columns

    def resolve_table_name(self, mapper):
        root = mapper
        while root.parent:
            root = root.parent
        return root.table_name


class ConcreteTableInheritance(InheritanceStrategy):
    name = "CONCRETE"

    def resolve_columns(self, mapper):
        # mapper.columns already contains declared columns, merge with parent columns
        mapper.columns = dict(mapper.parent.columns) | mapper.columns

    def resolve_table_name(self, mapper):
        return mapper.table_name


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
        self.discriminator = None  # Column object representing discriminator column
    
    @property
    def name(self):
        """Delegate to strategy name for backward compatibility."""
        return self.strategy.name
