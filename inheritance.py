from abc import ABC, abstractmethod

class InheritanceStrategy(ABC):
    name: str

    @abstractmethod
    def resolve_columns(self, mapper):
        pass

    @abstractmethod
    def resolve_table_name(self, mapper):
        pass
    
    def resolve_insert(self, mapper, data):
        """Resolve insert operations for this inheritance strategy.
        
        Returns a list of operation info dicts, each containing:
        - 'table': table name to insert into
        - 'data': data dict for this table
        - 'returns_id': whether this operation returns an ID (for FK propagation)
        """
        # Default: single table insert
        return [{
            'table': mapper.table_name,
            'data': data,
            'returns_id': True
        }]
    
    def resolve_update(self, mapper, data, pk_value):
        """Resolve update operations for this inheritance strategy.
        
        Returns a list of operation info dicts, each containing:
        - 'table': table name to update
        - 'data': data dict for this table
        - 'pk_value': primary key value
        """
        # Default: single table update
        return [{
            'table': mapper.table_name,
            'data': data,
            'pk_value': pk_value
        }]
    
    def resolve_delete(self, mapper, pk_value):
        """Resolve delete operations for this inheritance strategy.
        
        Returns a list of operation info dicts, each containing:
        - 'table': table name to delete from
        - 'pk_value': primary key value
        """
        # Default: single table delete
        return [{
            'table': mapper.table_name,
            'pk_value': pk_value
        }]
    
    def resolve_select(self, mapper, filters=None):
        """Resolve select operations for this inheritance strategy.
        
        Returns operation info dict containing:
        - 'tables': list of tables to select from
        - 'joins': list of join info dicts
        - 'columns': dict mapping table to list of columns
        """
        # Default: single table select
        return {
            'tables': [mapper.table_name],
            'joins': [],
            'columns': {mapper.table_name: list(mapper.columns.keys())}
        }

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
        mapper.columns = dict(mapper.parent.columns) | mapper.columns

    def resolve_table_name(self, mapper):
        root = mapper
        while root.parent:
            root = root.parent
        return root.table_name
    
    def resolve_insert(self, mapper, data):
        """For CLASS inheritance, insert into parent first, then child."""
        operations = []
        
        if mapper.parent:
            parent_data = {}
            child_data = {}
            
            parent_cols = set(mapper.parent.local_columns.keys())
            for key, value in data.items():
                if key in parent_cols:
                    parent_data[key] = value
                else:
                    child_data[key] = value
            
            operations.append({
                'table': mapper.parent.table_name,
                'data': parent_data,
                'returns_id': True,
                'propagate_id_to': 'parent_id'  # Will be set on child FK
            })
            
            fk_name = None
            for rel_name, rel in mapper.relationships.items():
                from mapper import Mapper
                target_cls = mapper._resolve_target_class(rel.target)
                if target_cls == mapper.parent.cls and rel.r_type in ("many-to-one", "one-to-one"):
                    if hasattr(rel, '_resolved_fk_name'):
                        fk_name = rel._resolved_fk_name
                    break
            
            if fk_name:
                child_data[fk_name] = None  # Placeholder, will be updated
            else:
                fk_name = f"{mapper.parent.table_name.rstrip('s').lower()}_id"
                child_data[fk_name] = None
            
            operations.append({
                'table': mapper.table_name,
                'data': child_data,
                'returns_id': True,
                'fk_from_previous': fk_name  # FK column to update with previous operation's ID
            })
        else:
            operations.append({
                'table': mapper.table_name,
                'data': data,
                'returns_id': True
            })
        
        return operations


class ConcreteTableInheritance(InheritanceStrategy):
    name = "CONCRETE"

    def resolve_columns(self, mapper):
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
        self.discriminator = None
    
    @property
    def name(self):
        return self.strategy.name
