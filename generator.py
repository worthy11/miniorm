import re

class SchemaGenerator:
    TYPE_MAP = {str: "TEXT", int: "INTEGER", bool: "INTEGER"}

    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Błąd bezpieczeństwa w nazwie identyfikatora SQL: {identifier}")
        return f'"{identifier}"'
    
    def create_all(self, engine, registry):
        table_definitions = {}
        
        for mapper in registry.values():
            name = mapper.table_name
            if name not in table_definitions:
                table_definitions[name] = {
                    'columns': {},
                    'fks': [],
                    'pk': mapper.pk,
                    'discriminator': mapper.discriminator
                }
            
            table_definitions[name]['columns'].update(mapper.columns)
            
            parent_cols = set(mapper.parent.columns.keys()) if mapper.parent else set()
            for col_name, col in mapper.columns.items():
                if col_name not in parent_cols and hasattr(col, 'is_foreign_key'):
                    table_definitions[name]['fks'].append((col_name, col))

        for t_name, info in table_definitions.items():
            sql = self._generate_sql(t_name, info)
            engine.execute(sql)
            print(f"DEBUG: Stworzono tabelę kompleksową: {t_name}")

        created_m2m = set()
        for mapper in registry.values():
            for rel in mapper.relationships.values():
                if rel.r_type == "many-to-many" and rel.association_table and rel.association_table.name not in created_m2m:
                    sql = self.generate_m2m_table(rel)
                    engine.execute(sql)
                    created_m2m.add(rel.association_table.name)
                    print(f"DEBUG: Stworzono tabelę M2M: {rel.association_table.name}")

    def _generate_sql(self, table_name, info):
        quoted_table = self._quote(table_name)
        column_defs = []

        # For CONCRETE inheritance, include ALL columns (parent + local) in each table
        # For CLASS inheritance, include only local columns (parent has its own table)
        # For SINGLE inheritance, include all columns (shared table)
        if mapper.inheritance and mapper.inheritance.strategy.name == "CONCRETE":
            # CONCRETE: Each table gets all columns (duplicated from parent)
            columns_to_include = mapper.columns
        elif mapper.inheritance and mapper.inheritance.strategy.name == "CLASS":
            # CLASS: Only local columns (parent has separate table)
            columns_to_include = mapper.local_columns
        else:
            # SINGLE or no inheritance: all columns
            columns_to_include = mapper.columns

        for name, col in columns_to_include.items():
            q_name = self._quote(name)
            sql_type = self.TYPE_MAP.get(col.dtype, "TEXT")
            constraints = []
            if name == info['pk']:
                constraints.append("PRIMARY KEY AUTOINCREMENT")
            if not col.nullable:
                constraints.append("NOT NULL")
            column_defs.append(f"{q_name} {sql_type} {' '.join(constraints)}".strip())

        # Add foreign key constraints for local columns only (not inherited ones)
        parent_cols = set(mapper.parent.columns.keys()) if mapper.parent else set()
        for name, col in columns_to_include.items():
            # Skip inherited columns for FK constraints (they're in parent table for CLASS)
            if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS":
                if name in parent_cols:
                    continue
            if hasattr(col, 'is_foreign_key') and col.is_foreign_key:
                column_defs.append(
                    f"FOREIGN KEY({self._quote(name)}) REFERENCES "
                    f"{self._quote(col.target_table)}({self._quote(col.target_column)})"
                )

        return f"CREATE TABLE IF NOT EXISTS {quoted_table} ({', '.join(column_defs)});"

    def generate_m2m_table(self, rel):
        assoc = rel.association_table
        table = self._quote(assoc.name)
        l_key = self._quote(assoc.local_key)
        r_key = self._quote(assoc.remote_key)
        target_pk = rel._resolved_target._mapper.pk
        local_pk = rel.local_table_pk if hasattr(rel, 'local_table_pk') else "id"
        return f"""
        CREATE TABLE IF NOT EXISTS {table} (
            {l_key} INTEGER,
            {r_key} INTEGER,
            FOREIGN KEY({l_key}) REFERENCES {self._quote(assoc.local_table)}({local_pk}),
            FOREIGN KEY({r_key}) REFERENCES {self._quote(assoc.remote_table)}({target_pk}),
            PRIMARY KEY ({l_key}, {r_key})
        );"""