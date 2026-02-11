from base import MiniBase
from session import Session

def print_mapper_info(cls_name, mapper):
    """Print parent, children, table name and columns for a mapper."""
    parent = mapper.parent.cls.__name__ if mapper.parent else None
    children = [m.__name__ for m in mapper.children] if mapper.children else []
    table_name = getattr(mapper, "table_name", "?")
    columns = list(mapper.columns.keys()) if mapper.columns else []
    local_cols = list(mapper.declared_columns.keys()) if getattr(mapper, "declared_columns", None) else []

    inheritance = "None"
    if mapper.inheritance:
        inheritance = mapper.inheritance.strategy.name

    print(f"  Class: {cls_name}")
    print(f"  Inheritance: {inheritance}")
    print(f"  Table name: {table_name}")
    print(f"  PK: {mapper.pk}")
    print(f"  Parent: {parent}")
    print(f"  Children: {children}")
    print(f"  Columns (all): {columns}")
    print(f"  Local columns: {local_cols}")
    print(f"  Relationships: {mapper.relationships}")
    print()

def run_mapper_tests():
    for cls, mapper in MiniBase._registry.items():
        name = cls.__name__
        print_mapper_info(name, mapper)
