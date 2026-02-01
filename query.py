from base import MiniBase
from states import ObjectState

class Query:
    def __init__(self, model_class, session):
        self.model_class = model_class
        self.session = session
        self.filters = {}
        self._limit = None
        self._offset = None
        self._joins = []

    def filter(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def limit(self, value: int):
        self._limit = value
        return self
    
    def offset(self, value: int):
        self._offset = value
        return self

    def all(self):
        if hasattr(self.session, '_autoflush'):
            self.session._autoflush()
        mapper = MiniBase._registry.get(self.model_class)
        sql, params = self.session.query_builder.build_select(
            mapper, self.filters, limit=self._limit, offset=self._offset, joins=self._joins
        )
        
        rows = self.session.engine.execute(sql, params)
        # Get column names - sqlite3.Row objects have keys() method
        if rows and hasattr(rows[0], 'keys'):
            # sqlite3.Row objects
            column_names = list(rows[0].keys()) if rows else list(mapper.columns.keys())
        else:
            # Fallback to mapper columns
            column_names = list(mapper.columns.keys())
        
        # Build mapping for CLASS inheritance subclass detection
        subclass_fk_mapping = {}
        if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS" and not mapper.parent:
            for subclass_mapper in mapper.children:
                # Find FK column in subclass
                from orm_types import ForeignKey
                fk_col = None
                # Get local columns (columns not in parent) for CLASS inheritance
                parent_cols = set(subclass_mapper.parent.columns.keys()) if subclass_mapper.parent else set()
                for col_name, col in subclass_mapper.columns.items():
                    if col_name in parent_cols:
                        continue  # Skip inherited columns
                    if isinstance(col, ForeignKey) and col.target_table == mapper.table_name:
                        fk_col = col_name
                        break
                if fk_col is None:
                    fk_col = f"{mapper.table_name.rstrip('s')}_id"
                subclass_fk_mapping[subclass_mapper.table_name] = {
                    'fk_col': fk_col,
                    'mapper': subclass_mapper
                }
        
        results = []
        for row in rows:
            # Handle sqlite3.Row objects (they're dict-like)
            if hasattr(row, 'keys'):
                row_dict = dict(row)
            else:
                row_dict = dict(zip(column_names, row))
            
            # Check identity map BEFORE hydrating to avoid unnecessary work
            pk_val = row_dict.get(mapper.pk)
            if pk_val is not None:
                existing = self.session.identity_map.get(self.model_class, pk_val)
                if existing:
                    # Object already in identity map - check if deleted
                    if getattr(existing, '_orm_state', None) == ObjectState.DELETED:
                        # Object is deleted in this session - skip it (Unit of Work behavior)
                        continue
                    # Return existing instance (identity map pattern - same PK = same instance)
                    results.append(existing)
                    continue
            
            # For CLASS inheritance, determine which subclass to instantiate
            target_class = self.model_class
            if subclass_fk_mapping:
                # Check which subclass table has a non-null FK (indicating it's that subclass)
                # The FK column from subclass table will be in the row_dict with alias {table}_{column}
                for subclass_table, info in subclass_fk_mapping.items():
                    fk_col = info['fk_col']
                    # The FK column is selected with alias: {subclass_table}_{fk_col}
                    alias_key = f"{info['mapper'].table_name}_{fk_col}"
                    # Also try just the column name (in case it's not aliased)
                    fk_value = row_dict.get(alias_key) or row_dict.get(fk_col)
                    if fk_value is not None:
                        # This is the subclass - the FK exists, so this Person is actually a Vet/Owner
                        target_class = info['mapper'].cls
                        break
            
            # Hydrate object (just creates and populates, no state management)
            obj = mapper.hydrate(row_dict, base_class=target_class)
            
            if obj:
                # Session handles making object persistent
                obj = self.session._make_persistent(obj)
                if obj:
                    results.append(obj)
                
        return results

    def first(self):
        self.limit(1)
        results = self.all()
        if not results:
            return None
        obj = results[0]
        if getattr(obj, '_orm_state', None) == ObjectState.DELETED:
            return None
        return obj
    
    def join(self, relationship_name):
        mapper = self.model_class._mapper
        if relationship_name not in mapper.relationships:
            raise AttributeError(f"Model {self.model_class.__name__} nie ma relacji {relationship_name}")
        
        rel = mapper.relationships[relationship_name]
        self._joins.append(rel)
        return self
    
 
    def join_m2m(self, assoc_table, local_key, remote_key, local_id):   #To do
        target_mapper = self.model_class._mapper
        target_table = target_mapper.table_name
        target_pk = target_mapper.pk
        
        sql = (f'SELECT t.* FROM "{target_table}" AS t '
               f'JOIN "{assoc_table}" AS a ON t."{target_pk}" = a."{remote_key}" '
               f'WHERE a."{local_key}" = ?')
        
        rows = self.session.engine.execute(sql, (local_id,))
        
        results = []
        for row in rows:
            pk_val = row[target_pk]
            existing = self.session.identity_map.get(self.model_class, pk_val)
            if existing:
                results.append(existing)
            else:
                obj = self.model_class()
                for key, val in row.items():
                    object.__setattr__(obj, key, val)
                object.__setattr__(obj, '_orm_state', "PERSISTENT")
                object.__setattr__(obj, '_session', self.session)
                self.session.identity_map.add(self.model_class, pk_val, obj)
                results.append(obj)
        
        self._results = results
        return self
