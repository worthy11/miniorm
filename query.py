from base import MiniBase
from states import ObjectState

class Query:
    def __init__(self, model_class, session):
        self.model_class = model_class
        self.session = session
        self.filters = {}
        self._limit = None
        self._offset = None
        self._join_class = None

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
            mapper, self.filters, limit=self._limit, offset=self._offset
        )
        
        rows = self.session.engine.execute(sql, params)
        column_names = list(mapper.columns.keys())
        results = []
        for row in rows:
            obj = self._hydrate(row, column_names, mapper)
            
            if obj and getattr(obj, '_orm_state', None) != ObjectState.DELETED:
                results.append(obj)
                
        return results

    def first(self):
        self.limit(1)
        results = self.all()
        # if not results:
        #     null_obj = self.model_class()
        #     for col in self.model_class._mapper.columns:
        #         setattr(null_obj, col, "None")
        #     return null_obj
        # return results[0]
        return results[0] if results else None
    
    def join(self, target_class):
        self._join_class = target_class
        #TO DO 
        return self

    
    def _hydrate(self, row, column_names, base_mapper):
        target_cls = self.model_class
        if "type" in column_names:
            class_name = row[column_names.index("type")]
            target_cls = next((c for c in MiniBase._registry if c.__name__ == class_name), target_cls)

        pk_val = row[column_names.index(base_mapper.pk)]
        existing = self.session.identity_map.get(target_cls, pk_val)
        if existing: 
            if getattr(existing, '_orm_state', None) == ObjectState.DELETED:
                return None
            return existing

        obj = target_cls()
        for i, name in enumerate(column_names):
            if hasattr(obj, name) or name in target_cls._mapper.columns:
                setattr(obj, name, row[i])

        obj._orm_state = ObjectState.PERSISTENT
        obj._session = self.session
        self.session.identity_map.add(target_cls, pk_val, obj)
        return obj