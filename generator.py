import re

class SchemaGenerator:
    TYPE_MAP = {str: "TEXT", int: "INTEGER", bool: "INTEGER"}

    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Błąd bezpieczeństwa w nazwie schemy: {identifier}")
        return f'"{identifier}"'
    
    def create_all(self, engine, registry):
        created_tables = set()
        
        for model_class in sorted(registry.keys(), key=lambda x: len(registry[x].columns), reverse=True):
            mapper = registry[model_class]
            if mapper.table_name not in created_tables:
                sql = self.generate_create_table(mapper)
                engine.execute(sql)
                created_tables.add(mapper.table_name)
                print(f"DEBUG: Stworzono tabelę kompleksową: {mapper.table_name}")

        for mapper in registry.values():
            for rel in mapper.relationships.values():
                if rel.r_type == "many-to-many":
                    if rel.association_table not in created_tables:
                        sql = self.generate_m2m_table(rel)
                        engine.execute(sql)
                        created_tables.add(rel.association_table)
                        print(f"DEBUG: Stworzono tabelę M2M: {rel.association_table}")

    def generate_create_table(self, mapper):
        table_name = self._quote(mapper.table_name)
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
            if name == mapper.pk:
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

        return f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)});"
    

    def generate_m2m_table(self, rel_mapping):
        table_name = self._quote(rel_mapping.association_table)
        l_key = self._quote(rel_mapping._resolved_local_key)
        r_key = self._quote(rel_mapping._resolved_remote_key)
        
        local_table = self._quote(rel_mapping.local_table)
        remote_table = self._quote(rel_mapping.remote_table)

        return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {l_key} INTEGER,
            {r_key} INTEGER,
            FOREIGN KEY({l_key}) REFERENCES {local_table}(id),
            FOREIGN KEY({r_key}) REFERENCES {remote_table}(id),
            PRIMARY KEY ({l_key}, {r_key})
        );"""