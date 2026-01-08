from abc import ABC, abstractmethod


class InheritanceStrategy(ABC):
    name: str

    @abstractmethod
    def apply_columns(self, mapper, parent_mapper):
        """Configure mapper columns/table according to inheritance type."""

    @abstractmethod
    def target_table(self, mapper):
        """Return table name to use for relations/foreign keys."""


class SingleTableInheritance(InheritanceStrategy):
    name = "SINGLE"

    def apply_columns(self, mapper, parent_mapper):
        mapper.table_name = parent_mapper.table_name
        mapper.local_columns = dict(mapper.declared_columns)
        mapper.columns = dict(parent_mapper.columns) | mapper.declared_columns

    def target_table(self, mapper):
        root = mapper
        while root.parent and getattr(root, "inheritance", None) and root.inheritance.name == "SINGLE":
            root = root.parent
        return root.table_name


class ClassTableInheritance(InheritanceStrategy):
    name = "CLASS"

    def apply_columns(self, mapper, parent_mapper):
        mapper.local_columns = dict(mapper.declared_columns)
        mapper.columns = dict(parent_mapper.columns) | mapper.declared_columns

    def target_table(self, mapper):
        root = mapper
        while root.parent:
            root = root.parent
        return root.table_name


class ConcreteTableInheritance(InheritanceStrategy):
    name = "CONCRETE"

    def apply_columns(self, mapper, parent_mapper):
        mapper.local_columns = dict(parent_mapper.columns) | mapper.declared_columns
        mapper.columns = dict(mapper.local_columns)

    def target_table(self, mapper):
        return mapper.table_name


STRATEGIES = {
    "SINGLE": SingleTableInheritance(),
    "CLASS": ClassTableInheritance(),
    "CONCRETE": ConcreteTableInheritance(),
}
