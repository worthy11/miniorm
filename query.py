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
    
    def all(self):
        if hasattr(self.session, '_autoflush'):
            self.session._autoflush()
            
        mapper = MiniBase._registry.get(self.model_class)
        sql, params = self.session.query_builder.build_select(
            mapper, self.filters, limit=self._limit, offset=self._offset, joins=self._joins
        )
        
        rows = self.session.engine.execute(sql, params)
        
        results = []
        for row in rows:
            row_dict = dict(row) if hasattr(row, 'keys') else {}
            
            obj = mapper.hydrate(row_dict)

            if obj:
                pk_val = getattr(obj, mapper.pk, None)
                if pk_val is not None:
                    existing = self.session.identity_map.get(obj.__class__, pk_val)
                    if existing:
                        if getattr(existing, '_orm_state', None) == ObjectState.DELETED:
                            continue
                        results.append(existing)
                        continue
                
                obj = self.session._make_persistent(obj)
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
            raise AttributeError(f"Model {self.model_class.__name__} has no relationship {relationship_name}")
        
        rel = mapper.relationships[relationship_name]
        self._joins.append(rel)
        return self
    
 
    def join_m2m(self, assoc_table, local_key, remote_key, local_id):
        target_mapper = self.model_class._mapper
        target_table = target_mapper.table_name
        target_pk = target_mapper.pk
        
        sql = (f'SELECT t.* FROM "{target_table}" AS t '
               f'JOIN "{assoc_table}" AS a ON t."{target_pk}" = a."{remote_key}" '
               f'WHERE a."{local_key}" = ?')
        
        rows = self.session.engine.execute(sql, (local_id,))
        
        results = []
        for row in rows:
            row_dict = dict(row) if hasattr(row, 'keys') else {}
            
            pk_val = row_dict.get(target_pk)
            existing = self.session.identity_map.get(self.model_class, pk_val)
            
            if existing:
                results.append(existing)
            else:
                obj = target_mapper.hydrate(row_dict)
                
                from states import ObjectState
                object.__setattr__(obj, '_orm_state', ObjectState.PERSISTENT)
                object.__setattr__(obj, '_session', self.session)
                
                self.session.identity_map.add(self.model_class, pk_val, obj)
                self.session._take_snapshot(obj)
                results.append(obj)
        
        self._results = results
        return self

    
