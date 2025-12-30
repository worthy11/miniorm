from base import MiniBase
from types import Text, Number


# Base entity
class Person(MiniBase):
    id = Number(pk=True)
    name = Text()


# Single-table inheritance: shares parent's table
class StudentSingle(Person):
    mapper_args = {"inheritance": "single"}
    grade = Number()


# Class-table (joined) inheritance: own table with new columns
class StudentClass(Person):
    mapper_args = {"inheritance": "class"}
    grade = Number()


# Concrete-table inheritance: own table duplicating inherited columns
class StudentConcrete(Person):
    mapper_args = {"inheritance": "concrete"}
    grade = Number()


# Vehicles examples: two subclasses per strategy
class Vehicle(MiniBase):
    id = Number(pk=True)
    name = Text()
    wheels = Number()


# Single-table inheritance
class CarSingle(Vehicle):
    mapper_args = {"inheritance": "single"}
    doors = Number()


class TruckSingle(Vehicle):
    mapper_args = {"inheritance": "single"}
    capacity = Number()

class BikeSingle(Vehicle):
    mapper_args = {"inheritance": "class"}
    color = Text()




def describe(mapper):
    print(mapper)
    print(" table:", mapper.table_name)
    print(" columns:", sorted(mapper.columns))
    print(" local columns:", sorted(mapper.local_columns))
    print(" pk:", mapper.pk)
    print()


def single_table_union(root_cls):
    """Return union of columns for all mappers sharing the root's table (single-table)."""
    table = root_cls._mapper.table_name
    cols = {}
    for mapper in root_cls._registry.values():
        if mapper.table_name == table:
            cols |= mapper.columns
    return cols


if __name__ == "__main__":

    print("-- Vehicles: single-table --")
    describe(CarSingle._mapper)
    describe(TruckSingle._mapper)
    print("Wspólna tabela:", Vehicle._mapper.table_name)
    union_cols = single_table_union(Vehicle)
    print("Wspólne kolumny (unia):", sorted(union_cols))
    print()
    describe(BikeSingle._mapper)

