from abc import ABC, abstractmethod

class Transaction(ABC):
    def __init__(self, session, entity):
        self.session = session
        self.entity = entity
        self.mapper = entity._mapper

    @abstractmethod
    def execute(self):
        pass

    def _sync_foreign_keys(self):
        for name, rel in self.mapper.relationships.items():
            if rel.r_type == "many-to-one":
                parent_obj = getattr(self.entity, name, None)
                if parent_obj:
                    parent_pk_val = getattr(parent_obj, parent_obj._mapper.pk, None)
                    if parent_pk_val is not None:
                        setattr(self.entity, rel._resolved_fk_name, parent_pk_val)


class InsertTransaction(Transaction):
    def execute(self):
        self._sync_foreign_keys()

        data = {}
        for col_name in self.mapper.columns:
            if col_name == self.mapper.pk: continue
            val = getattr(self.entity, col_name, None)
            if val is not None:
                data[col_name] = val
        
        if "type" in self.mapper.columns and "type" not in data:
             data["type"] = self.entity.__class__.__name__

        sql, params = self.session.query_builder.build_insert(self.mapper, data)
        new_id = self.session.engine.execute_insert(sql, params)
        
        setattr(self.entity, self.mapper.pk, new_id)
        self.session.identity_map.add(self.entity.__class__, new_id, self.entity)
        
        from states import ObjectState
        object.__setattr__(self.entity, '_orm_state', ObjectState.PERSISTENT)


        self.session._flush_m2m(self.entity)
        self.session._take_snapshot(self.entity)


class UpdateTransaction(Transaction):
    def execute(self):
        self._sync_foreign_keys()

        pk_val = getattr(self.entity, self.mapper.pk)
        old_state = self.session._snapshots.get(id(self.entity))
        
        data = {}
        if old_state:
            for col_name in self.mapper.columns:
                if col_name == self.mapper.pk: continue
                new_val = getattr(self.entity, col_name, None)
                old_val = old_state.get(col_name)
                if new_val != old_val:
                    data[col_name] = new_val
        else:
            for col_name in self.mapper.columns:
                if col_name == self.mapper.pk: continue
                val = getattr(self.entity, col_name, None)
                if val is not None:
                    data[col_name] = val

        if data:
            sql, params = self.session.query_builder.build_update(self.mapper, data, pk_val)
            self.session.engine.execute(sql, params)

        self.session._flush_m2m(self.entity)
        self.session._take_snapshot(self.entity)

class DeleteTransaction(Transaction):
    def execute(self):
        pk_val = getattr(self.entity, self.mapper.pk)
        sql, params = self.session.query_builder.build_delete(self.mapper, pk_val)
        self.session.engine.execute(sql, params)
        self.session.identity_map.remove(self.entity.__class__, pk_val)