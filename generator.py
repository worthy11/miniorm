class SchemaGenerator:
    TYPE_MAP = {str: "TEXT", int: "INTEGER", bool: "INTEGER"}

    def generate_create_table(self, mapper):
        table_name = mapper.table_name
        column_defs = []

        for name, col in mapper.columns.items():
            sql_type = self.TYPE_MAP.get(col.dtype, "TEXT")
            
            constraints = []
            if name == mapper.pk:
                constraints.append("PRIMARY KEY AUTOINCREMENT")
            if not col.nullable:
                constraints.append("NOT NULL")
            
            column_defs.append(f"{name} {sql_type} {' '.join(constraints)}".strip())

        for name, col in mapper.local_columns.items():
            if hasattr(col, 'is_foreign_key') and col.is_foreign_key:
                column_defs.append(
                    f"FOREIGN KEY({name}) REFERENCES {col.target_table}({col.target_column})"
                )

        return f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)});"

    def generate_m2m_table(self, rel_mapping):
        table_name = rel_mapping.association_table
        l_key, r_key = rel_mapping._resolved_local_key, rel_mapping._resolved_remote_key
        
        return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {l_key} INTEGER,
            {r_key} INTEGER,
            FOREIGN KEY({l_key}) REFERENCES {rel_mapping.local_table}(id),
            FOREIGN KEY({r_key}) REFERENCES {rel_mapping.remote_table}(id),
            PRIMARY KEY ({l_key}, {r_key})
        );"""