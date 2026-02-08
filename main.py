"""
Tests that different inheritance types (SINGLE, CLASS, CONCRETE) create appropriate mappers.
Prints parent, children, table name and columns for each mapper.
"""

from base import MiniBase
from orm_types import Text, Number, Relationship


def print_mapper_info(cls_name, mapper):
    """Print parent, children, table name and columns for a mapper."""
    parent = mapper.parent.cls.__name__ if mapper.parent else None
    children = [m.cls.__name__ for m in mapper.children] if mapper.children else []
    table_name = getattr(mapper, "table_name", "?")
    columns = list(mapper.columns.keys()) if mapper.columns else []
    local_cols = list(mapper.local_columns.keys()) if getattr(mapper, "local_columns", None) else []

    inheritance = "None"
    if mapper.inheritance:
        inheritance = mapper.inheritance.strategy.name

    print(f"  Class: {cls_name}")
    print(f"  Inheritance: {inheritance}")
    print(f"  Table name: {table_name}")
    print(f"  Parent: {parent}")
    print(f"  Children: {children}")
    print(f"  Columns (all): {columns}")
    print(f"  Local columns: {local_cols}")
    print()


# SINGLE
class PersonSingle(MiniBase):
    id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "people"
        inheritance = "SINGLE"
        discriminator = "type"
        discriminator_value = "PersonSingle"


class StudentSingle(PersonSingle):
    grade = Number()

    class Meta:
        inheritance = "SINGLE"
        discriminator_value = "StudentSingle"


class TeacherSingle(PersonSingle):
    subject = Text()

    class Meta:
        inheritance = "SINGLE"
        discriminator_value = "TeacherSingle"


# CLASS
class PersonClass(MiniBase):
    id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "persons"
        inheritance = "CLASS"


class StudentClass(PersonClass):
    grade = Number()
    person_id = Relationship(PersonClass, r_type="one-to-one")

    class Meta:
        inheritance = "CLASS"


class TeacherClass(PersonClass):
    subject = Text()
    person_id = Relationship(PersonClass, r_type="one-to-one")

    class Meta:
        inheritance = "CLASS"


# CONCRETE
class AnimalConcrete(MiniBase):
    id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "animals"
        inheritance = "CONCRETE"


class DogConcrete(AnimalConcrete):
    breed = Text()

    class Meta:
        inheritance = "CONCRETE"


# --- No inheritance (base table only) ---
class Standalone(MiniBase):
    id = Number(pk=True)
    title = Text()

    class Meta:
        table_name = "standalones"


def run_mapper_tests():
    for cls, mapper in MiniBase._registry.items():
        name = cls.__name__
        print_mapper_info(name, mapper)

if __name__ == "__main__":
    run_mapper_tests()
