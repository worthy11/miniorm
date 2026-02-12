import re
from orm_types import ForeignKey

class SchemaGenerator:
    TYPE_MAP = {str: "TEXT", int: "INTEGER", bool: "INTEGER"}

    def __init__(self):
        self._safe_ident_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def _quote(self, identifier):
        if not identifier or not self._safe_ident_pattern.match(str(identifier)):
            raise ValueError(f"Unsafe SQL identifier: {identifier}")
        return f'"{identifier}"'
    
    def _get_existing_columns(self, engine, table_name):
        rows = engine.execute(f"PRAGMA table_info({self._quote(table_name)})")
        return [row[1] for row in rows]
    
    def create_all(self, engine, registry):
        table_definitions = {}
        
        for mapper in registry.values():
            if mapper.inheritance.strategy.name == "CONCRETE" and getattr(mapper, 'children', None):
                continue
            name = mapper.table_name
            if name not in table_definitions:
                table_definitions[name] = {
                    'columns': {},
                    'pk': mapper.pk,
                    'mapper': mapper
                }
            
            if mapper.inheritance.strategy.name == "CLASS":
                table_definitions[name]['columns'].update(mapper.declared_columns)
            else:
                table_definitions[name]['columns'].update(mapper.columns)

        for t_name, info in table_definitions.items():
            sql = self._generate_sql(t_name, info)
            engine.execute(sql)
            existing_cols = self._get_existing_columns(engine, t_name)
            for col_name, col_obj in info['columns'].items():
                if col_name not in existing_cols:
                    print(f"DEBUG: Migration: Adding missing column '{col_name}' to table '{t_name}'")
                    sql_type = self.TYPE_MAP.get(col_obj.dtype, "TEXT")
                    
                    alter_sql = f"ALTER TABLE {self._quote(t_name)} ADD COLUMN {self._quote(col_name)} {sql_type} NULL"
                    engine.execute(alter_sql)
            print(f"DEBUG: Created table: {t_name}")

        created_m2m = set()
        for mapper in registry.values():
            for rel in mapper.relationships.values():
                if rel.r_type == "many-to-many" and rel.association_table:
                    assoc = rel.association_table
                    if assoc.name not in created_m2m:
                        sql = self.generate_m2m_table(rel)
                        engine.execute(sql)
                        created_m2m.add(assoc.name)
                        print(f"DEBUG: Created M2M table: {assoc.name}")


    def _generate_sql(self, table_name, info):
        quoted_table = self._quote(table_name)
        column_defs = []
        mapper = info['mapper']
        if mapper.inheritance.strategy.name == "CLASS":
            parent_cols = set(mapper.parent.columns.keys()) if mapper.parent else set()
            columns_to_include = {
                name: col for name, col in mapper.columns.items() 
                if name not in parent_cols or name == mapper.pk
            }
        else:
            columns_to_include = info['columns']

        for name, col in columns_to_include.items():
            q_name = self._quote(name)
            sql_type = self.TYPE_MAP.get(col.dtype, "TEXT")
            constraints = []
            
            if name == mapper.pk:
                if mapper.inheritance and mapper.inheritance.strategy.name == "CLASS" and mapper.parent:
                    constraints.append("PRIMARY KEY")
                else:
                    constraints.append("PRIMARY KEY AUTOINCREMENT")
            
            if not col.nullable:
                constraints.append("NOT NULL")
            column_defs.append(f"{q_name} {sql_type} {' '.join(constraints)}".strip())

        for name, col in columns_to_include.items():
            if hasattr(col, 'target_table'):
                ref_sql = (f"FOREIGN KEY({self._quote(name)}) REFERENCES "
                           f"{self._quote(col.target_table)}({self._quote(col.target_column)})")
                if getattr(col, 'on_delete_cascade', False):
                    ref_sql += " ON DELETE CASCADE"
                column_defs.append(ref_sql)

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