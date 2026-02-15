class Transaction():
    def __init__(self, session, entity):
        self.session = session
        self.entity = entity

    def prepare(self):
        pass


class InsertTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper

        operations = mapper.prepare_insert(self.entity)
        # print(f"DEBUG: Insert operations: {operations}")
        fk_from_previous = operations.pop("_fk_from_previous", None)  # { table_name: fk_column_name }

        return [{"table_name": table_name, "data": data, "fk_col": fk_from_previous.get(table_name) if fk_from_previous else None} for table_name, data in operations.items()]


class UpdateTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper
        old_state = self.session._snapshots.get(id(self.entity))
        operations = mapper.prepare_update(self.entity, old_state)
        print(f"DEBUG: Update operations: {operations}")
        results = []

        for table_name, data in operations.items():
            results.append({"table_name": table_name, "data": data})

        return results

class DeleteTransaction(Transaction):
    def prepare(self):
        mapper = self.entity._mapper
        operations = mapper.prepare_delete(self.entity)
        # print(f"DEBUG: Delete operations: {operations}")
        
        results = []

        for table_name, data in operations.items():
            results.append({"table_name": table_name, "data": data})

        return results