from abc import ABC, abstractmethod

class Transaction(ABC):
    def __init__(self, session, entity):
        self.session = session
        self.entity = entity

    @abstractmethod
    def prepare(self):
        """Prepare SQL and parameters. Returns list of (sql, params, callback, rebuild_fn) tuples.
        
        callback is a function that takes (result, previous_id) and applies side effects.
        rebuild_fn is called before execution to rebuild SQL if needed (for FK updates).
        """
        pass


class InsertTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper

        operations = mapper.prepare_insert(self.entity)
        fk_from_parent = operations.pop("_fk_from_parent", None)  # { table_name: fk_column_name }

        results = []

        for table_name, data in operations.items():
            fk_col = fk_from_parent.get(table_name) if fk_from_parent else None
            results.append({"table_name": table_name, "data": data, "fk_col": fk_col})

        return results


class UpdateTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper
        old_state = self.session._snapshots.get(id(self.entity))
        operations = mapper.prepare_update(self.entity, old_state)
        results = []

        for table_name, data in operations.items():
            results.append({"table_name": table_name, "data": data})

        return results

class DeleteTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper
        operations = mapper.prepare_delete(self.entity)
        
        results = []

        for table_name, data in operations.items():
            results.append({"table_name": table_name, "data": data})

        return results